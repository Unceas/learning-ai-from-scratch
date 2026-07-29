"""Document parser module for extracting text and page contents from PDF and TXT files."""

from pathlib import Path
from typing import Any, Dict, List, Union
from PyPDF2 import PdfReader


def extract_pages(file_obj: Any) -> List[Dict[str, Union[int, str]]]:
    """Extract page-level content with 1-based page numbers from a file object.

    Args:
        file_obj: Uploaded file object (PDF or TXT).

    Returns:
        List of dictionaries containing page number and text content.
    """
    file_name = getattr(file_obj, "name", "")
    suffix = Path(file_name).suffix.lower()

    # Reset file pointer if supported
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    try:
        if suffix == ".pdf":
            reader = PdfReader(file_obj)
            pages = []
            for i, page in enumerate(reader.pages, 1):
                content = page.extract_text()
                if content and content.strip():
                    pages.append({"page": i, "text": content.strip()})
            
            # Reset file pointer after reading
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            return pages

        if suffix == ".txt":
            raw = file_obj.read()
            if isinstance(raw, bytes):
                text = raw.decode("utf-8", errors="ignore").strip()
            else:
                text = str(raw).strip()

            # Reset file pointer after reading
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)

            if not text:
                return []
            return [{"page": 1, "text": text}]

    except Exception as e:
        raise ValueError(f"Failed to parse document '{file_name}': {str(e)}")

    raise ValueError("Unsupported file type. Upload a PDF or TXT file.")


def extract_text(file_obj: Any) -> str:
    """Extract all text content from a file object as a single string.

    Args:
        file_obj: Uploaded file object (PDF or TXT).

    Returns:
        Complete extracted text.
    """
    pages = extract_pages(file_obj)
    return "\n\n".join(p["text"] for p in pages)
