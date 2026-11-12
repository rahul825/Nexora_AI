from fastapi import APIRouter, HTTPException
from google.genai import errors as genai_errors
from langchain_google_genai._common import GoogleGenerativeAIError
from pydantic import BaseModel

from agent import ask_question
from rag_agent import ask_document

user_route = APIRouter()

@user_route.get("/")
def home(name:str):
    list = {"name" :f"{name}","age" : 29,"address" : "Noida sector 63"}
    return {
        "message": "Welcome to FastAPI",
        "status": "success",
        "data": list
    }



@user_route.get("/about")
def about():
    return {
        "application": "User Management API",
        "language": "Python",
        "framework": "FastAPI"
    }


@user_route.get("/page/{page_name}") 
def details(page_name:str):
     return {
        "contentName":"details page",
        "content":f"here is {page_name} conetent for you! hiiii"
     }


@user_route.get("/hello/{name}")
def hello(name: str):
    return {
        "message": f"Hello, {name}!"
    }


class QuestionRequest(BaseModel):
    question: str


@user_route.post("/ask")
def ask(body: QuestionRequest):
    try:
        result = ask_question(body.question)
    except (GoogleGenerativeAIError, genai_errors.APIError) as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")
    return {
        "status": "success",
        "question": body.question,
        "agent": result["agent"],          # "text" or "image"
        "answer": result["answer"],
        "image_url": result["image_url"],  # e.g. /images/<id>.png, or null for text answers
    }


@user_route.post("/rag/ask")
def rag_ask(body: QuestionRequest):
    try:
        result = ask_document(body.question)
    except GoogleGenerativeAIError as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")
    return {
        "question": body.question,
        "answer": result["answer"],
       
    }
