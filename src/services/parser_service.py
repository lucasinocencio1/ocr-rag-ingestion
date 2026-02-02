import os
from typing import List, Tuple

from langchain_core.documents import Document

from src.core.constants import APP_NAME, IMAGE_EXTENSIONS, MIN_TEXT_LEN
from src.core.logging import get_logger
from src.services.decryption_service import DecryptionService
from src.services.extraction_service import (
    extract_image_document,
    extract_pdf_documents_with_ocr,
)

logger = get_logger(APP_NAME)
_decryption_service: DecryptionService | None = None


def get_decryption_service() -> DecryptionService:
    global _decryption_service
    if _decryption_service is None:
        _decryption_service = DecryptionService()
    return _decryption_service


def list_supported_files(docs_dir: str) -> Tuple[List[str], List[str]]:
    pdf_files: List[str] = []
    image_files: List[str] = []
    for name in os.listdir(docs_dir):
        path = os.path.join(docs_dir, name)
        if not os.path.isfile(path):
            continue
        lower = name.lower()
        if lower.endswith(".pdf"):
            pdf_files.append(path)
        elif os.path.splitext(lower)[1] in IMAGE_EXTENSIONS:
            image_files.append(path)
    return pdf_files, image_files


def load_all_documents(docs_dir: str, ocr_language: str) -> List[Document]:
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(f"Docs folder not found: {docs_dir}")

    pdf_files, image_files = list_supported_files(docs_dir)
    if not pdf_files and not image_files:
        raise FileNotFoundError(f"No supported files found in: {docs_dir}")

    all_docs: List[Document] = []

    decryption = get_decryption_service()

    for pdf_path in pdf_files:
        path_to_use: str | None = None
        try:
            try:
                docs_chunk = extract_pdf_documents_with_ocr(
                    pdf_path,
                    min_text_len=MIN_TEXT_LEN,
                    ocr_language=ocr_language,
                )
            except Exception as exc:
                # Possibly encrypted; try decrypt then extract
                path_to_use = decryption.decrypt_single_pdf(pdf_path)
                if path_to_use:
                    logger.info("Decrypted PDF for extraction: %s", os.path.basename(pdf_path))
                    docs_chunk = extract_pdf_documents_with_ocr(
                        path_to_use,
                        min_text_len=MIN_TEXT_LEN,
                        ocr_language=ocr_language,
                    )
                else:
                    raise
            all_docs.extend(docs_chunk)
            logger.info("Loaded %s", os.path.basename(pdf_path))
        except Exception as exc:
            logger.warning("Failed to process %s. Error=%s", pdf_path, exc)
        finally:
            if path_to_use and path_to_use != pdf_path and os.path.isfile(path_to_use):
                try:
                    os.unlink(path_to_use)
                except OSError:
                    pass

    for image_path in image_files:
        doc = extract_image_document(image_path, ocr_language=ocr_language)
        if doc:
            all_docs.append(doc)
            logger.info("Loaded %s", os.path.basename(image_path))
        else:
            logger.warning("No text extracted from image %s", image_path)

    return all_docs


def export_documents_to_txt(docs: List[Document], output_path: str) -> None:
    """
    Write all extracted document text to a .txt file for inspection.
    Each block is prefixed with source, page, and used_ocr.
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "?")
            page = doc.metadata.get("page", "?")
            used_ocr = doc.metadata.get("used_ocr", False)
            f.write(f"=== source: {source} | page: {page} | used_ocr: {used_ocr} ===\n\n")
            f.write(doc.page_content)
            f.write("\n\n")
    logger.info("Exported %s document blocks to %s", len(docs), output_path)
