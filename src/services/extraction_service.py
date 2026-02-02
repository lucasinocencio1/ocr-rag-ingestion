import io
import os
from typing import List, Optional

import fitz  # PyMuPDF
import pytesseract
from langchain_core.documents import Document
from PIL import Image

from src.core.constants import APP_NAME, DEFAULT_DPI, MIN_TEXT_LEN
from src.core.logging import get_logger

logger = get_logger(APP_NAME)


def page_to_pil_image(page: fitz.Page, dpi: int = DEFAULT_DPI) -> Image.Image:
    """
    Renders a PDF page to a PIL image using PyMuPDF (no poppler needed).
    """
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_bytes))
    return img.convert("RGB")


def extract_pdf_documents_with_ocr(
    pdf_path: str,
    min_text_len: int = MIN_TEXT_LEN,
    ocr_language: str = "eng",
) -> List[Document]:
    """
    Extracts per-page text from a PDF. If extracted text is too short, uses OCR.
    """
    docs: List[Document] = []
    pdf_name = os.path.basename(pdf_path)

    with fitz.open(pdf_path) as pdf_doc:
        for page_index in range(len(pdf_doc)):
            page = pdf_doc[page_index]
            text = (page.get_text("text") or "").strip()

            used_ocr = False
            if len(text) < min_text_len:
                try:
                    img = page_to_pil_image(page, dpi=DEFAULT_DPI)
                    ocr_text = (
                        pytesseract.image_to_string(img, lang=ocr_language) or ""
                    ).strip()
                    if len(ocr_text) > len(text):
                        text = ocr_text
                        used_ocr = True
                except Exception as exc:
                    logger.warning(
                        "OCR failed for %s page %s. Error=%s",
                        pdf_name,
                        page_index + 1,
                        exc,
                    )

            if not text:
                continue

            metadata = {
                "source": pdf_name,
                "path": pdf_path,
                "page": page_index + 1,
                "used_ocr": used_ocr,
            }
            docs.append(Document(page_content=text, metadata=metadata))

    return docs


def extract_image_document(image_path: str, ocr_language: str) -> Optional[Document]:
    try:
        with Image.open(image_path) as img:
            text = (pytesseract.image_to_string(img, lang=ocr_language) or "").strip()
    except Exception as exc:
        logger.warning("OCR failed for image %s. Error=%s", image_path, exc)
        return None

    if not text:
        return None

    metadata = {
        "source": os.path.basename(image_path),
        "path": image_path,
        "page": 1,
        "used_ocr": True,
    }
    return Document(page_content=text, metadata=metadata)
