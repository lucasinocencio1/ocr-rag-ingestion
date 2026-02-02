import os
from typing import List, Union

import psycopg2
from langchain_community.vectorstores.chroma import Chroma
from langchain_community.vectorstores.pgvector import PGVector
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from src.core.constants import APP_NAME
from src.core.logging import get_logger
from src.models import SETTINGS
from src.services.database_service import ensure_pgvector_extension

logger = get_logger(APP_NAME)


def _build_chroma(chunks: List[Document], embeddings: OpenAIEmbeddings) -> Chroma:
    """Local storage (Chroma on disk) when Postgres is not available."""
    persist_dir = SETTINGS.vector_persist_dir
    os.makedirs(persist_dir, exist_ok=True)
    logger.info("Using local vector store (SQLite/Chroma) at %s", persist_dir)
    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=SETTINGS.collection_name,
        persist_directory=persist_dir,
    )


def build_vectorstore(chunks: List[Document]) -> Union[PGVector, Chroma]:
    embeddings = OpenAIEmbeddings(model=SETTINGS.embedding_model)

    if SETTINGS.use_postgres:
        try:
            ensure_pgvector_extension(SETTINGS.database_url)
            return PGVector.from_documents(
                documents=chunks,
                embedding=embeddings,
                collection_name=SETTINGS.collection_name,
                connection_string=SETTINGS.database_url,
            )
        except psycopg2.OperationalError as exc:
            logger.warning(
                "Postgres unavailable (%s). Falling back to local vector store.",
                exc,
            )
            return _build_chroma(chunks, embeddings)

    return _build_chroma(chunks, embeddings)
