from __future__ import annotations

from pypdf import PdfReader


def is_digital_pdf(pdf_path: str, pages_to_check: int = 2, min_chars: int = 80) -> bool:
    """
    Returns True if the PDF likely contains selectable text (digital),
    otherwise False (likely scanned image PDF).
    """
    try:
        reader = PdfReader(pdf_path)
        n = min(pages_to_check, len(reader.pages))
        total = 0
        for i in range(n):
            txt = reader.pages[i].extract_text() or ""
            total += len(txt.strip())
        return total >= min_chars
    except Exception:
        # If parsing fails, assume scanned to be safe
        return False
