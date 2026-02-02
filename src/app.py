import os
import traceback
from contextlib import asynccontextmanager
from typing import Dict, Optional, Union

from fastapi import FastAPI, HTTPException
from openai import RateLimitError
from langchain_community.vectorstores.chroma import Chroma
from langchain_community.vectorstores.pgvector import PGVector

from src.core.constants import APP_NAME, RAG_TOP_K
from src.core.logging import configure_logging, get_logger
from src.models import SETTINGS
from src.schemas import RAGRequest, RAGResponse
from src.services import (
    DecryptionService,
    answer_with_rag,
    build_vectorstore,
    chunk_documents,
    export_documents_to_txt,
    load_all_documents,
)

configure_logging()
logger = get_logger(APP_NAME)

VECTORSTORE: Optional[Union[PGVector, Chroma]] = None


def startup_ingest() -> None:
    global VECTORSTORE

    docs_dir = SETTINGS.docs_dir
    if SETTINGS.use_batch_decryption:
        decrypted = DecryptionService().decrypt_pdfs_batch()
        if decrypted:
            docs_dir = SETTINGS.decrypted_docs_dir
            logger.info("Batch decryption: loading from %s", docs_dir)

    docs = load_all_documents(docs_dir, ocr_language=SETTINGS.ocr_language)

    if SETTINGS.export_only:
        export_documents_to_txt(docs, SETTINGS.export_ocr_txt)
        logger.info("Export-only mode: OCR text written to %s. Skipping vector store (no OpenAI).", SETTINGS.export_ocr_txt)
        return

    chunks = chunk_documents(docs)

    try:
        VECTORSTORE = build_vectorstore(chunks)
    except RateLimitError as exc:
        logger.error(
            "OpenAI quota exceeded (no balance or rate limit). "
            "Add credits at https://platform.openai.com/account/billing"
        )
        raise RuntimeError(
            "OpenAI quota exceeded. Add credits at https://platform.openai.com/account/billing"
        ) from exc

    logger.info(
        "Ingested %s pages, %s chunks into '%s'.",
        len(docs),
        len(chunks),
        SETTINGS.collection_name,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    if SETTINGS.ingest_on_startup:
        startup_ingest()
    else:
        logger.info("INGEST_ON_STARTUP=false -> Skipping ingestion")
    yield


app = FastAPI(title="OCR RAG API", lifespan=lifespan)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "collection": SETTINGS.collection_name}


@app.post("/rag", response_model=RAGResponse)
def rag(request_body: RAGRequest) -> RAGResponse:
    if VECTORSTORE is None:
        raise HTTPException(status_code=500, detail="Vector store not initialized.")

    question = (request_body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing 'question' in JSON body.")

    try:
        result = answer_with_rag(VECTORSTORE, question, k=RAG_TOP_K)
        return RAGResponse(**result)
    except Exception as exc:
        logger.error("Internal error: %s", exc)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("FASTAPI_DEBUG", "false").lower() == "true",
    )
