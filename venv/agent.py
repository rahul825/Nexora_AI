"""Multi-agent assistant: a router agent sends each request to the right specialist.

    START -> router --(text)--> text_agent  --> END
                    +-(image)-> image_agent --> END

- router:      a small LLM call that decides whether the user wants text or an image
- text_agent:  answers questions with the Gemini chat model
- image_agent: generates an image with a Gemini image model and saves it to data/images/
"""
import os
import uuid
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# Load the .env next to this file, no matter which folder the server is started from
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
IMAGE_DIR = BASE_DIR / "data" / "images"   # served by main.py at /images
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    timeout=30,      # give up on a single call after 30s instead of waiting forever
    max_retries=2,   # default is 6 retries, which turned slow calls into 4-5 minute waits
)
# Image generation goes through the google-genai SDK directly (it returns the image bytes).
# It reads GOOGLE_API_KEY from the environment, same as the chat model.
image_client = genai.Client()

TEXT_PROMPT = "You are a helpful assistant. Answer the user's question clearly and concisely."
ROUTER_PROMPT = (
    "You route user requests to the right agent.\n"
    "- 'image': the user wants a picture/image/drawing/logo/illustration/photo to be CREATED.\n"
    "- 'text': everything else (questions, explanations, writing, code, describing things)."
)


# ---------- Shared state ----------

class AgentState(TypedDict):
    question: str
    messages: Annotated[list, add_messages]
    route: Literal["text", "image"]
    answer: str
    image_url: str | None


class RouteDecision(BaseModel):
    route: Literal["text", "image"] = Field(description="Which agent should handle the request")


router_llm = llm.with_structured_output(RouteDecision)


# ---------- Agents (graph nodes) ----------

def router(state: AgentState) -> dict:
    try:
        decision = router_llm.invoke([
            SystemMessage(content=ROUTER_PROMPT),
            HumanMessage(content=state["question"]),
        ])
        route = decision.route
    except Exception:   # if routing fails, a plain text answer is the safe default
        route = "text"
    return {"route": route}


def text_agent(state: AgentState) -> dict:
    question = HumanMessage(content=state["question"])
    response = llm.invoke([SystemMessage(content=TEXT_PROMPT), question])
    return {
        "messages": [question, response],
        "answer": response.text,
        "image_url": None,
    }


def image_agent(state: AgentState) -> dict:
    question = HumanMessage(content=state["question"])
    try:
        response = image_client.models.generate_content(
            model=IMAGE_MODEL,
            contents=state["question"],
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )
    except genai_errors.APIError as e:
        # 429 with "limit: 0" means the API key's plan has no quota for image models (free tier)
        reason = "the image quota for this API key is used up or not enabled (billing needed)" \
            if e.code == 429 else e.message
        answer = f"Sorry, I couldn't generate the image: {reason}."
        return {"messages": [question, AIMessage(content=answer)], "answer": answer, "image_url": None}

    caption, image_url = [], None
    for part in response.candidates[0].content.parts if response.candidates else []:
        if part.inline_data and part.inline_data.data and image_url is None:
            ext = (part.inline_data.mime_type or "image/png").split("/")[-1]
            filename = f"{uuid.uuid4().hex}.{ext}"
            (IMAGE_DIR / filename).write_bytes(part.inline_data.data)
            image_url = f"/images/{filename}"
        elif part.text:
            caption.append(part.text)

    answer = " ".join(caption).strip() or (
        "Here is your image." if image_url else "Sorry, I couldn't generate an image for that request."
    )
    return {
        "messages": [question, AIMessage(content=answer)],
        "answer": answer,
        "image_url": image_url,
    }


def pick_agent(state: AgentState) -> str:
    return "image_agent" if state["route"] == "image" else "text_agent"


# ---------- Graph ----------

graph = StateGraph(AgentState)
graph.add_node("router", router)
graph.add_node("text_agent", text_agent)
graph.add_node("image_agent", image_agent)
graph.add_edge(START, "router")
graph.add_conditional_edges("router", pick_agent, ["text_agent", "image_agent"])
graph.add_edge("text_agent", END)
graph.add_edge("image_agent", END)

qa_agent = graph.compile()


def ask_question(question: str) -> dict:
    """Returns {"agent": "text" | "image", "answer": str, "image_url": str | None}."""
    result = qa_agent.invoke({"question": question, "messages": []})
    return {
        "agent": result["route"],
        "answer": result["answer"],
        "image_url": result.get("image_url"),
    }
