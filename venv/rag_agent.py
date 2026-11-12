import os
import re
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore
from langgraph.graph import END, START, StateGraph
from pypdf import PdfReader

from vector_db import collection_name, create_store, open_store

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

PDF_PATH = BASE_DIR / "data" / "RagDocument.pdf"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
TOP_K = 4
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION") or collection_name("rag_docs", EMBED_MODEL)

llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    timeout=30,
    max_retries=2,
)
# Small local embedding model: runs on this machine, so no API quota is used for search
embeddings = FastEmbedEmbeddings(model_name=EMBED_MODEL)

SYSTEM_PROMPT = (
    "You answer questions using ONLY the context below, which comes from a GK question document. "
    "If the answer is not in the context, reply exactly: "
    "\"I couldn't find the answer to that in the document.\" "
    "Keep the answer short.\n\nContext:\n{context}"
    "don't event answer if not present in document"
)


def load_chunks() -> list[Document]:
    """Split the PDF into one chunk per numbered question + answer."""
    text = "\n".join(page.extract_text() for page in PdfReader(PDF_PATH).pages)
    parts = re.split(r"\n\s*(?=\d{1,3}\)\s)", "\n" + text)
    docs = []
    for part in parts:
        match = re.match(r"\s*(\d{1,3})\)", part)
        if match:
            content = re.sub(r"\s+", " ", part).strip()
            docs.append(Document(page_content=content, metadata={"number": int(match.group(1))}))
    return docs


def build_vector_store() -> QdrantVectorStore:
    """Use the existing Qdrant collection, or embed the PDF once and store it in Qdrant."""
    return open_store(QDRANT_COLLECTION, embeddings) or create_store(
        QDRANT_COLLECTION, embeddings, load_chunks()
    )


vector_store = build_vector_store()


class RagState(TypedDict):
    question: str
    context: list[Document]
    answer: str


def retrieve(state: RagState) -> dict:
    return {"context": vector_store.similarity_search(state["question"], k=TOP_K)}


def generate(state: RagState) -> dict:
    context = "\n".join(doc.page_content for doc in state["context"])
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT.format(context=context)),
        HumanMessage(content=state["question"]),
    ])
    return {"answer": response.text}


graph = StateGraph(RagState)
graph.add_node("retrieve", retrieve)
graph.add_node("generate", generate)
graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "generate")
graph.add_edge("generate", END)

rag_agent = graph.compile()


def ask_document(question: str) -> dict:
    result = rag_agent.invoke({"question": question})
    return {
        "answer": result["answer"],
    }
