"""Document ingestion service for PDF text extraction and page preservation."""

from typing import Any, Dict, List
from PyPDF2 import PdfReader


class DocumentService:

    def extract_text(self, file) -> List[Dict[str, Any]]:
        """Extract text from PDF pages while preserving page numbers."""
        reader = PdfReader(file)
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                pages.append({
                    "page": page_number,
                    "text": text.strip()
                })
        return pages
