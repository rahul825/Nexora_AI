"""Shared Qdrant connection for all agents.

QDRANT_URL set   -> Qdrant server (Docker: http://localhost:6333, or Qdrant Cloud + QDRANT_API_KEY)
QDRANT_URL empty -> embedded local Qdrant on disk at QDRANT_PATH (one process at a time)

Only ONE client is created per process: local mode locks its folder, so two clients
in the same process (e.g. rag_agent + db_qa_agent) would block each other.
"""
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

QDRANT_URL = os.getenv("QDRANT_URL", "").strip()
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
QDRANT_PATH = os.getenv("QDRANT_PATH", str(BASE_DIR / "data" / "qdrant_db"))


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    if QDRANT_URL:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)
    return QdrantClient(path=QDRANT_PATH)


def collection_name(prefix: str, embed_model: str) -> str:
    """Model name goes in the collection name so vectors from different models never mix."""
    return f"{prefix}_{embed_model.split('/')[-1]}".replace(".", "_").replace("-", "_")


def open_store(name: str, embeddings: Embeddings) -> QdrantVectorStore | None:
    """Return the existing collection if it has vectors of the right size, else None."""
    client = get_qdrant_client()
    if not client.collection_exists(name):
        return None
    info = client.get_collection(name)
    if info.config.params.vectors.size != len(embeddings.embed_query("test")) or not info.points_count:
        return None
    return QdrantVectorStore(client=client, collection_name=name, embedding=embeddings)


def create_store(name: str, embeddings: Embeddings, docs: list[Document]) -> QdrantVectorStore:
    """(Re)create the collection and fill it with docs."""
    client = get_qdrant_client()
    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=len(embeddings.embed_query("test")), distance=Distance.COSINE),
    )
    store = QdrantVectorStore(client=client, collection_name=name, embedding=embeddings)
    if docs:
        store.add_documents(docs, batch_size=256)
    return store
