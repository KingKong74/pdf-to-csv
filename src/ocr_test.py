import io
import os

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

PDF_PATH = r"C:\PDF_Converter\pdf-to-csv\Anz_CC_Statement.pdf"

if not os.path.exists(PDF_PATH):
    raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

doc = fitz.open(PDF_PATH)
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes("png")))

    text = pytesseract.image_to_string(
        img,
        config="--oem 3 --psm 6"
    )

    print(f"\n===== PAGE {i + 1} =====\n")
    print(text[:2000])

