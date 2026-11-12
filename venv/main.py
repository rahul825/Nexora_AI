import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from routes.user import user_route
from routes.db_agent import db_route
from routes.chat import chat_route
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agent import IMAGE_DIR

import chat_store
from database import connect_on_startup, engine
from db_qa_agent import warm_up


@asynccontextmanager
async def lifespan(app: FastAPI):
    chat_store.init_db()   # create the chat history tables if they don't exist yet
    if connect_on_startup():   # check the MySQL connection once at startup
        # Load schema + vector index now, in a thread so startup isn't blocked
        threading.Thread(target=warm_up, daemon=True).start()
    yield
    engine.dispose()       # close pooled DB connections on shutdown


app = FastAPI(
    title="Naroxa AI",
    description="RAG-based AI assistant: document Q&A, database Q&A, text and image generation",
    version="1.0.0",
    lifespan=lifespan
)

# Images made by the image agent are saved in data/images and served at /images/<file>
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5180",   # React chat UI (frontend/, npm run dev)
        "http://127.0.0.1:5180",
    ],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
)


app.include_router(
    user_route,
    prefix="/api/v1"
)

app.include_router(
    db_route,
    prefix="/api/v1"
)

app.include_router(
    chat_route,
    prefix="/api/v1"
)



