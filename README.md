# Naroxa AI

Naroxa AI is a RAG-based AI assistant. It has a FastAPI + LangGraph backend, Google Gemini models, a Qdrant vector database and a React chat UI.

## Features

- **Document Q&A (RAG):** answers questions from a PDF. The PDF is split into chunks, embedded locally with FastEmbed and stored in Qdrant.
- **Database Q&A:** an agent answers questions about a MySQL database. It writes read-only SQL and can also run vector search over the rows.
- **Multi-agent assistant:** a router agent sends each request to one of two agents:
  - **Text agent:** answers questions and writes text.
  - **Image agent:** generates images with a Gemini image model.
- **Chat sessions:** chat history is stored in SQLite, so it is still there after a restart.

```
START -> router --(text)--> text_agent  --> END
                +-(image)-> image_agent --> END
```

## Project structure

```
.
├── venv/                  # backend source (FastAPI app)
│   ├── main.py            # app entry point, CORS, routers, /images static files
│   ├── agent.py           # multi-agent: router -> text / image agent
│   ├── rag_agent.py       # PDF RAG agent
│   ├── db_qa_agent.py     # MySQL Q&A agent (SQL + vector search tools)
│   ├── vector_db.py       # shared Qdrant client
│   ├── database.py        # MySQL connection (SQLAlchemy)
│   ├── chat_store.py      # chat history (SQLite)
│   ├── routes/            # API routes
│   └── .env.example
├── frontend/              # React + Vite chat UI
├── docker-compose.yml     # Qdrant server
└── requirements.txt
```

## Setup

### 1. Backend

```bash
python -m venv venv
# Windows: venv\Scripts\activate    macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cp venv/.env.example venv/.env   # then fill in GOOGLE_API_KEY, DB_* etc.
```

Put the document for the RAG agent at `venv/data/RagDocument.pdf`.

Optional: start a Qdrant server with Docker and set `QDRANT_URL=http://localhost:6333`. If `QDRANT_URL` is empty, Qdrant runs locally on disk instead.

```bash
docker compose up -d
```

Run the API:

```bash
cd venv
uvicorn main:app --reload
```

The API docs are at http://localhost:8000/docs.

### 2. Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5180.

## Main API endpoints (prefix `/api/v1`)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/ask` | Multi-agent: returns a text answer, or an image (`image_url`) |
| POST | `/rag/ask` | Ask the PDF document |
| POST | `/db/ask` | Ask the MySQL database |
| POST | `/db/reindex` | Rebuild the vector index of the database |
| GET/POST/PATCH/DELETE | `/chat/sessions...` | Chat sessions used by the UI |

Example:

```bash
curl -X POST http://localhost:8000/api/v1/ask -H "Content-Type: application/json" \
     -d '{"question": "Generate an image of a sunset over mountains"}'
# {"agent": "image", "answer": "...", "image_url": "/images/<id>.png", ...}
```

Images are served at `http://localhost:8000/images/<id>.png`.

> **Note:** Gemini image models have no free-tier quota. Image generation needs an API key with billing enabled. Set `GEMINI_IMAGE_MODEL` to change the model.
