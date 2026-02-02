# OCR RAG API

FastAPI service that indexes PDFs and images (OCR via Tesseract when needed) and answers questions over them using OpenAI embeddings and a vector store. Supports PostgreSQL/pgvector or Chroma (local fallback).

![RAG Architecture](assets/architecture_RAG.gif)

## Requirements

- Python 3.10+
- Tesseract OCR installed on the system
- OpenAI API key
- Optional: PostgreSQL with pgvector (Docker Compose provided)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set OPENAI_API_KEY, optionally DATABASE_URL 
```

See `.env.example` for optional vars (vector store paths, decryption folders, models).

## Run

From project root:

```bash
python -m src.app
```

Or:

```bash
uvicorn src.app:app --host 0.0.0.0 --port 8000
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs


# ocr-rag-ingestion
