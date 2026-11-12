"""Chat sessions for the React UI: create / list / rename / delete sessions and ask questions.

Every question and answer is saved, so the history is still there after a reload or restart.
"""
from typing import Literal

from fastapi import APIRouter, HTTPException
from langchain_google_genai._common import GoogleGenerativeAIError
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

import chat_store
from db_qa_agent import ask_database
from rag_agent import ask_document

chat_route = APIRouter(prefix="/chat", tags=["Chat sessions"])

Source = Literal["document", "database"]


class NewSession(BaseModel):
    source: Source = "document"


class SessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    source: Source | None = None


class ChatQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    source: Source | None = None   # switch the session's source for this and later questions


def _get_or_404(session_id: str) -> dict:
    session = chat_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@chat_route.get("/sessions")
def list_sessions():
    return chat_store.list_sessions()


@chat_route.post("/sessions")
def create_session(body: NewSession):
    return chat_store.create_session(source=body.source)


@chat_route.get("/sessions/{session_id}")
def get_session(session_id: str):
    return _get_or_404(session_id)


@chat_route.patch("/sessions/{session_id}")
def update_session(session_id: str, body: SessionUpdate):
    _get_or_404(session_id)
    return chat_store.update_session(session_id, title=body.title, source=body.source)


@chat_route.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if not chat_store.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"status": "deleted"}


@chat_route.post("/sessions/{session_id}/ask")
def ask(session_id: str, body: ChatQuestion):
    session = _get_or_404(session_id)
    question = body.question.strip()
    source = body.source or session["source"]
    if source != session["source"]:
        chat_store.update_session(session_id, source=source)
    # First question becomes the session title, like ChatGPT
    if not session["messages"] and session["title"] == "New chat":
        chat_store.update_session(session_id, title=question[:60] + ("..." if len(question) > 60 else ""))

    user_msg = chat_store.add_message(session_id, "user", question)
    try:
        result = ask_document(question) if source == "document" else ask_database(question)
        answer, is_error = result["answer"], False
    except GoogleGenerativeAIError as e:
        answer, is_error = f"The AI model is unavailable right now ({e}). Please try again.", True
    except SQLAlchemyError as e:
        answer, is_error = f"Database error: {getattr(e, 'orig', e)}", True
    except Exception as e:   # keep the chat usable and record what went wrong
        answer, is_error = f"Something went wrong: {e}", True
    assistant_msg = chat_store.add_message(session_id, "assistant", answer, is_error=is_error)

    return {
        "session": {k: v for k, v in chat_store.get_session(session_id).items() if k != "messages"},
        "messages": [user_msg, assistant_msg],
    }
