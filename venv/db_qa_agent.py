"""DB agent: answers user questions using ONLY data stored in the MySQL database.

The LLM sees the full schema (tables, columns, foreign keys) in its system prompt and gets
two tools: `run_sql_query` (read-only SQL, for counts / filters / joins) and
`search_database` (vector search over the DB rows, for fuzzy text lookups).
It must answer only from what the tools return.
"""
import os
import threading
from datetime import date
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from database import DB_NAME, fetch_rows, get_schema_text, get_tables, run_select
from qdrant_client.models import FieldCondition, Filter, MatchValue

from vector_db import collection_name, create_store, open_store

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# false -> SQL only: no embeddings, no Qdrant, the agent just writes SELECT queries
USE_VECTOR_SEARCH = os.getenv("DB_USE_VECTOR_SEARCH", "true").strip().lower() in ("1", "true", "yes")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
# DB and model names are in the collection name so vectors from another
# database or embedding model are never mixed in by mistake.
QDRANT_DB_COLLECTION = collection_name(f"db_{DB_NAME}", EMBED_MODEL)
TOP_K = int(os.getenv("RAG_TOP_K", "8"))
MAX_ROWS_PER_TABLE = int(os.getenv("RAG_MAX_ROWS_PER_TABLE", "50000"))
# Empty RAG_TABLES means: index every table in the database
RAG_TABLES = [t.strip() for t in os.getenv("RAG_TABLES", "").split(",") if t.strip()]
MAX_CHUNK_CHARS = 1500
MAX_TOOL_CALLS = int(os.getenv("DB_MAX_TOOL_CALLS", "3"))   # each extra round = one more LLM call
MAX_SQL_ROWS = int(os.getenv("DB_MAX_SQL_ROWS", "50"))
NOT_FOUND = "I couldn't find this information related to your query."

llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    timeout=30,
    max_retries=2,
    # Writing SQL from a given schema needs little reasoning; "minimal" thinking makes each
    # call faster and far more consistent (default thinking had 9-21s outliers)
    thinking_level=os.getenv("GEMINI_THINKING_LEVEL", "minimal"),
)
embeddings = FastEmbedEmbeddings(model_name=EMBED_MODEL) if USE_VECTOR_SEARCH else None


def system_prompt() -> str:
    search_hint = (
        "- Use search_database only for fuzzy text lookups that SQL can't do.\n"
        if USE_VECTOR_SEARCH else ""
    )
    return (
        f"You answer questions about data stored in the MySQL database '{DB_NAME}'. "
        f"Today is {date.today()}.\n"
        f"Database schema (table(columns), FK = foreign key):\n{get_schema_text()}\n\n"
        "How to answer:\n"
        "- Use run_sql_query for almost everything: lists, counts, dates, filters, and JOINs "
        "across tables (e.g. attendance.user_id -> users.id to get a person's name).\n"
        "- Use only tables and columns from the schema above. Match names with LIKE '%...%'.\n"
        "- Get everything you need in ONE query where possible (use JOINs, not follow-up queries).\n"
        "- If a query fails with an error, fix it and try again.\n"
        "- If a correct query returns no rows, the data does not exist: answer that it was not "
        "found. Never change the dates, names or filters the user asked for to find other data.\n"
        f"{search_hint}"
        "- Answer using ONLY the data returned by the tools. Do not use outside or general "
        "knowledge, even if you know the answer.\n"
        f"- If the data doesn't contain the answer, reply exactly: \"{NOT_FOUND}\"\n"
        "\nHow to write the answer (the reader is an end user, not a developer):\n"
        "- NEVER mention table names, column names, IDs used for joins, SQL, queries or "
        "'the database'. Just state the facts, e.g. 'There are 137 users.' not "
        "'The users table has 137 rows.'\n"
        "- Use friendly labels instead of column names (e.g. 'Start date', not start_date).\n"
        "- Pick the format that fits the result, using Markdown:\n"
        "  * a single value or yes/no -> one short sentence\n"
        "  * a few items -> a bullet list\n"
        "  * several records with multiple fields -> a Markdown table with clear headers\n"
        "  * a large or mixed result -> a short summary first, then the key details\n"
        "  * the user asks for a summary / overview / breakdown -> do NOT list every row: "
        "query with COUNT/GROUP BY (e.g. by status, person, month) and give totals, "
        "a small breakdown table and 1-2 sentences of key points\n"
        "- Leave out empty/None values and internal codes unless they matter to the question.\n"
        "- Keep it concise."
    )


# ---------- Vector index over the DB rows ----------

def row_to_text(table: str, columns: list[str], row) -> str:
    fields = [f"{col}: {val}" for col, val in zip(columns, row) if val not in (None, "")]
    return f"[table: {table}] " + " | ".join(fields)


def load_documents() -> list[Document]:
    """Read the tables and turn every row into one or more Documents."""
    docs = []
    for table in RAG_TABLES or get_tables():
        columns, rows = fetch_rows(table, MAX_ROWS_PER_TABLE)
        header = f"[table: {table}] "
        step = MAX_CHUNK_CHARS - len(header)
        for row_num, row in enumerate(rows):
            # Split very long rows so each chunk still starts with its table name
            body = row_to_text(table, columns, row)[len(header):]
            for i in range(0, max(len(body), 1), step):
                docs.append(Document(
                    page_content=header + body[i:i + step],
                    metadata={"table": table, "row": row_num},
                ))
    return docs


_store: QdrantVectorStore | None = None
_store_lock = threading.Lock()


def build_vector_store(force: bool = False) -> QdrantVectorStore:
    """Use the existing Qdrant collection, or read the DB, embed the rows and store them in Qdrant."""
    global _store
    with _store_lock:
        if not force and _store is not None:
            return _store
        store = None if force else open_store(QDRANT_DB_COLLECTION, embeddings)
        _store = store or create_store(QDRANT_DB_COLLECTION, embeddings, load_documents())
        return _store


def reindex() -> dict:
    """Re-read the database and rebuild the index (call after the table data changes)."""
    get_schema_text.cache_clear()   # pick up new tables / columns too
    if not USE_VECTOR_SEARCH:
        return {"database": DB_NAME, "vector_search": False,
                "message": "Vector search is off (DB_USE_VECTOR_SEARCH=false); only the schema cache was refreshed."}
    store = build_vector_store(force=True)
    per_table: dict[str, int] = {}
    for table in RAG_TABLES or get_tables():
        count = store.client.count(
            QDRANT_DB_COLLECTION,
            count_filter=Filter(must=[FieldCondition(key="metadata.table", match=MatchValue(value=table))]),
        ).count
        if count:
            per_table[table] = count
    total = store.client.count(QDRANT_DB_COLLECTION).count
    return {"database": DB_NAME, "collection": QDRANT_DB_COLLECTION, "documents": total, "tables": per_table}


# ---------- Tool the agent calls ----------

@tool(response_format="content_and_artifact")
def search_database(query: str) -> tuple[str, list[Document]]:
    """Search the database records for rows relevant to the query.

    Args:
        query: what to look for, e.g. the user's question or key words from it.
    """
    docs = build_vector_store().similarity_search(query, k=TOP_K)
    if not docs:
        return "No matching records found.", []
    content = "\n".join(f"<record>{doc.page_content}</record>" for doc in docs)
    return content, docs


@tool(response_format="content_and_artifact")
def run_sql_query(sql: str) -> tuple[str, list[dict]]:
    """Run one read-only MySQL SELECT query on the database and return the result rows.

    Args:
        sql: a single SELECT statement using the tables and columns from the schema.
    """
    try:
        columns, rows = run_select(sql, MAX_SQL_ROWS)
    except Exception as e:   # send the error back so the LLM can fix its query
        return f"Query failed: {getattr(e, 'orig', e)}", []
    if not rows:
        return "The query returned no rows.", []
    rows = [[str(v) for v in row] for row in rows]
    lines = [" | ".join(columns)] + [" | ".join(row) for row in rows]
    if len(rows) == MAX_SQL_ROWS:
        lines.append(f"(only the first {MAX_SQL_ROWS} rows are shown)")
    return "\n".join(lines), [{"sql": sql, "columns": columns, "rows": rows}]


tools = [run_sql_query, search_database] if USE_VECTOR_SEARCH else [run_sql_query]
llm_with_tools = llm.bind_tools(tools)


# ---------- Agent graph: agent -> tools -> agent -> ... -> END ----------

class DbAgentState(TypedDict):
    messages: Annotated[list, add_messages]


def agent(state: DbAgentState) -> dict:
    tool_calls_so_far = sum(isinstance(m, ToolMessage) for m in state["messages"])
    # After MAX_TOOL_CALLS searches, make the LLM answer with what it already has
    model = llm if tool_calls_so_far >= MAX_TOOL_CALLS else llm_with_tools
    response = model.invoke([SystemMessage(content=system_prompt()), *state["messages"]])
    return {"messages": [response]}


graph = StateGraph(DbAgentState)
graph.add_node("agent", agent)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", tools_condition)  # tool call -> "tools", else -> END
graph.add_edge("tools", "agent")

db_rag_agent = graph.compile()


def warm_up() -> None:
    """Load the slow, one-time things at startup instead of on the first user request."""
    get_schema_text()
    if USE_VECTOR_SEARCH:
        build_vector_store()


def ask_database(question: str) -> dict:
    result = db_rag_agent.invoke({"messages": [HumanMessage(content=question)]})
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]

    sources, seen = [], set()
    for message in tool_messages:
        for item in message.artifact or []:
            if isinstance(item, dict):   # from run_sql_query
                sources.append({"type": "sql", **item})
            elif item.page_content not in seen:   # from search_database
                seen.add(item.page_content)
                sources.append({"type": "search", "table": item.metadata["table"],
                                "content": item.page_content})

    # The answer must come from the DB: if the tool was never used or found nothing, don't trust it
    answer = result["messages"][-1].text
    return {"answer": answer}
