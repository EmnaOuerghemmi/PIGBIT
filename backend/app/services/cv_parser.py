from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CVParser:
    @staticmethod
    async def extract_text(file_path: str) -> str:
        """Extract text from PDF or DOCX file."""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"CV file not found: {file_path}")
                return ""

            if path.suffix.lower() == ".pdf":
                return CVParser._extract_pdf_text(file_path)
            elif path.suffix.lower() in {".docx", ".doc"}:
                return CVParser._extract_docx_text(file_path)
            else:
                logger.warning(f"Unsupported file format: {path.suffix}")
                return ""
        except Exception as e:
            logger.error(f"Error extracting CV text from {file_path}: {str(e)}")
            return ""

    @staticmethod
    def _extract_pdf_text(file_path: str) -> str:
        """Extract text from PDF using pdfplumber."""
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except ImportError:
            logger.error("pdfplumber not installed")
            return ""
        except Exception as e:
            logger.error(f"Error extracting PDF text: {str(e)}")
            return ""

    @staticmethod
    def _extract_docx_text(file_path: str) -> str:
        """Extract text from DOCX using python-docx."""
        try:
            from docx import Document
            text_parts = []
            doc = Document(file_path)
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            return "\n".join(text_parts)
        except ImportError:
            logger.error("python-docx not installed")
            return ""
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {str(e)}")
            return ""


cv_parser = CVParser()
