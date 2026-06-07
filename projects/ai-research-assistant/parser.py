from pathlib import Path

from PyPDF2 import PdfReader


def extract_text(file_obj):
    file_name = getattr(file_obj, "name", "")
    suffix = Path(file_name).suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(file_obj)
        text = ""

        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"

        return text.strip()

    if suffix == ".txt":
        raw = file_obj.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="ignore").strip()
        return str(raw).strip()

    raise ValueError("Unsupported file type. Upload a PDF or TXT file.")
