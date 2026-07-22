from pathlib import Path
from PyPDF2 import PdfReader


def extract_pages(file_obj):
    file_name = getattr(file_obj, "name", "")
    suffix = Path(file_name).suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(file_obj)
        pages = []
        for i, page in enumerate(reader.pages, 1):
            content = page.extract_text()
            if content:
                pages.append({"page": i, "text": content})
        return pages

    if suffix == ".txt":
        raw = file_obj.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8", errors="ignore").strip()
        else:
            text = str(raw).strip()
        return [{"page": 1, "text": text}]

    raise ValueError("Unsupported file type. Upload a PDF or TXT file.")


def extract_text(file_obj):
    pages = extract_pages(file_obj)
    return "\n".join(p["text"] for p in pages)
