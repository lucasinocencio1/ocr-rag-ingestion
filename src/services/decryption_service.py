"""
Service for handling PDF decryption (password-protected or encrypted PDFs).
Uses pikepdf to decrypt and save to a readable format before OCR/extraction.
Install with: pip install pikepdf
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

try:
    import pikepdf
except ImportError:
    pikepdf = None  # type: ignore[assignment]

from src.core.constants import APP_NAME
from src.core.logging import get_logger
from src.models import SETTINGS

logger = get_logger(APP_NAME)

_PIKEPDF_REQUIRED_MSG = "pikepdf is required for decryption. Install with: pip install pikepdf"


class DecryptionService:
    """Service for handling PDF decryption."""

    def __init__(self):
        self.source_folder = Path(SETTINGS.encrypted_docs_dir) if SETTINGS.encrypted_docs_dir else None
        self.processed_folder = Path(SETTINGS.processed_encrypted_dir)
        self.target_folder = Path(SETTINGS.decrypted_docs_dir)

    def ensure_directories(self) -> None:
        """Create encrypted/decrypted/processed directories if using batch decryption."""
        if self.source_folder and self.source_folder.exists():
            self.target_folder.mkdir(parents=True, exist_ok=True)
            self.processed_folder.mkdir(parents=True, exist_ok=True)

    def decrypt_pdfs_batch(self) -> List[str]:
        """
        Decrypt all PDFs in the encrypted folder.

        Returns:
            List of paths to successfully decrypted PDFs.
        """
        if pikepdf is None:
            raise ImportError(_PIKEPDF_REQUIRED_MSG)
        if not self.source_folder or not self.source_folder.exists():
            logger.info("Encrypted folder not set or not found: %s", self.source_folder)
            return []

        self.ensure_directories()
        pdf_files = [f for f in os.listdir(self.source_folder) if f.lower().endswith(".pdf")]
        total_files = len(pdf_files)

        if total_files == 0:
            logger.info("No PDF files found in encrypted folder")
            return []

        decrypted_files: List[str] = []

        for index, pdf_file in enumerate(pdf_files, start=1):
            encrypted_pdf_path = self.source_folder / pdf_file
            clean_filename = self._clean_filename(pdf_file)
            decrypted_pdf_path = self.target_folder / f"decrypted_{clean_filename}"

            try:
                logger.info("Processing %s of %s PDFs...", index, total_files)

                with pikepdf.open(encrypted_pdf_path) as pdf:
                    pdf.save(decrypted_pdf_path)

                logger.info("PDF decrypted: %s", decrypted_pdf_path)

                processed_path = self.processed_folder / pdf_file
                shutil.move(str(encrypted_pdf_path), str(processed_path))
                logger.info("Original encrypted PDF moved to: %s", processed_path)

                decrypted_files.append(str(decrypted_pdf_path))

            except pikepdf.PasswordError:
                logger.error("PDF '%s' is password protected and cannot be decrypted", pdf_file)
            except FileNotFoundError as exc:
                logger.error("File not found: %s", exc)
            except Exception as exc:
                logger.error("Error decrypting '%s': %s", pdf_file, exc)

        return decrypted_files

    def decrypt_single_pdf(self, input_path: str) -> Optional[str]:
        """
        Decrypt a single PDF file (or copy if not encrypted).
        Caller must delete the returned path if it is a temp file (path != input_path).

        Args:
            input_path: Path to the PDF file to decrypt.

        Returns:
            Path to decrypted file (temp file), or None if failed.
            If PDF was not encrypted, returns path to a temp copy.
        """
        if pikepdf is None:
            raise ImportError(_PIKEPDF_REQUIRED_MSG)
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_path = temp_file.name
            temp_file.close()

            try:
                with pikepdf.open(input_path) as pdf:
                    pdf.save(temp_path)
                logger.debug("PDF decrypted with pikepdf: %s", temp_path)
            except pikepdf.PasswordError:
                logger.warning("PDF is password protected, cannot decrypt: %s", input_path)
                os.unlink(temp_path)
                return None
            except Exception:
                # If not encrypted or pikepdf can't open, just copy and try extraction
                shutil.copy(input_path, temp_path)
                logger.debug("PDF not encrypted or opened by copy: %s", temp_path)

            return temp_path

        except Exception as exc:
            logger.error("Error processing single PDF %s: %s", input_path, exc)
            return None

    def _clean_filename(self, filename: str) -> str:
        """Remove 'decrypted_' prefixes from filename."""
        clean_name = filename
        while clean_name.lower().startswith("decrypted_"):
            clean_name = clean_name[len("decrypted_"):]
        return clean_name
