import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Settings for the application."""
    openai_api_key: str
    database_url: str  # Leave empty to use local SQLite/Chroma store
    vector_persist_dir: str  # used when database_url is empty
    docs_dir: str
    collection_name: str
    embedding_model: str
    chat_model: str
    ingest_on_startup: bool
    ocr_language: str
    export_ocr_txt: str  # When set, write OCR text to this file and skip vector store (no OpenAI)
    encrypted_docs_dir: str  # Optional: folder with encrypted PDFs for batch decryption
    decrypted_docs_dir: str  # Output folder for decrypted PDFs (batch)
    processed_encrypted_dir: str  # Optional: move originals here after batch decryption

    @property
    def use_postgres(self) -> bool:
        return bool(self.database_url.strip())

    @property
    def export_only(self) -> bool:
        """True when only exporting OCR to txt (no embeddings/OpenAI)."""
        return bool(self.export_ocr_txt.strip())

    @property
    def use_batch_decryption(self) -> bool:
        """True when encrypted_docs_dir is set for batch PDF decryption."""
        return bool(self.encrypted_docs_dir.strip())


def load_settings() -> Settings:
    """Load settings from environment variables."""
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    database_url = os.getenv("DATABASE_URL", "").strip()
    vector_persist_dir = os.getenv("VECTOR_PERSIST_DIR", ".data/vectors").strip()
    export_ocr_txt = os.getenv("EXPORT_OCR_TXT", "").strip()
    encrypted_docs_dir = os.getenv("ENCRYPTED_DOCS_DIR", "").strip()
    decrypted_docs_dir = os.getenv("DECRYPTED_DOCS_DIR", ".data/decrypted").strip()
    processed_encrypted_dir = os.getenv("PROCESSED_ENCRYPTED_DIR", ".data/processed_encrypted").strip()

    if not openai_api_key and not export_ocr_txt:
        raise RuntimeError("Missing OPENAI_API_KEY in environment (.env). Set EXPORT_OCR_TXT to export OCR only without API.")

    return Settings(
        openai_api_key=openai_api_key,
        database_url=database_url,
        vector_persist_dir=vector_persist_dir or ".data/vectors",
        docs_dir=os.getenv("DOCS_DIR", "docs"),
        collection_name=os.getenv("COLLECTION_NAME", "legal_docs"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        chat_model=os.getenv("CHAT_MODEL", "gpt-4o-mini"),
        ingest_on_startup=os.getenv("INGEST_ON_STARTUP", "true").lower() == "true",
        ocr_language=os.getenv("OCR_LANGUAGE", "eng"),
        export_ocr_txt=export_ocr_txt,
        encrypted_docs_dir=encrypted_docs_dir,
        decrypted_docs_dir=decrypted_docs_dir or ".data/decrypted",
        processed_encrypted_dir=processed_encrypted_dir or ".data/processed_encrypted",
    )


SETTINGS = load_settings()
