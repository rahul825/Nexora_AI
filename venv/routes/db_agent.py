from fastapi import APIRouter, HTTPException
from langchain_google_genai._common import GoogleGenerativeAIError
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from database import DB_HOST, DB_NAME, check_connection
from db_qa_agent import ask_database, reindex

db_route = APIRouter(prefix="/db", tags=["DB RAG Agent"])


class QuestionRequest(BaseModel):
    question: str


def db_error(e: SQLAlchemyError) -> HTTPException:
    return HTTPException(status_code=503, detail=f"Database error: {getattr(e, 'orig', e)}")


@db_route.get("/health")
def health():
    try:
        check_connection()
    except SQLAlchemyError as e:
        raise db_error(e)
    return {"status": "success", "host": DB_HOST, "database": DB_NAME, "db_status": "connected"}


@db_route.post("/reindex")
def rebuild_index():
    try:
        result = reindex()
    except SQLAlchemyError as e:
        raise db_error(e)
    return {"status": "success", **result}


@db_route.post("/ask")
def db_ask(body: QuestionRequest):
    try:
        result = ask_database(body.question)
    except SQLAlchemyError as e:
        raise db_error(e)
    except GoogleGenerativeAIError as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")
    return {
        "question": body.question,
        "answer": result["answer"],
    }
