from __future__ import annotations

import fitz
import pytesseract
import pandas as pd
from PIL import Image
import io
import re
from collections import defaultdict
from typing import Callable, Optional, Tuple

# --- bundled tesseract setup ---
import os
import sys

def tesseract_dir() -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "tesseract")
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "third_party", "tesseract"))

tdir = tesseract_dir()
pytesseract.pytesseract.tesseract_cmd = os.path.join(tdir, "tesseract.exe")
os.environ["TESSDATA_PREFIX"] = os.path.join(tdir, "tessdata")
# ----------------------------------------------------------

DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")

def extract_transactions_scanned(
    pdf_path: str,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> pd.DataFrame:
    raw_lines: list[Tuple[int, str]] = []

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    for idx, page in enumerate(doc, start=1):
        if progress_cb:
            progress_cb(idx, total_pages, f"OCR page {idx}/{total_pages}…")

        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        data = pytesseract.image_to_data(
            img,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
        )

        rows = defaultdict(list)
        y_tolerance = 12

        for i in range(len(data["text"])):
            txt = data["text"][i].strip()
            if not txt:
                continue
            x = data["left"][i]
            y = data["top"][i]
            row_key = round(y / y_tolerance)
            rows[row_key].append((x, txt))

        for row in rows.values():
            row_sorted = sorted(row, key=lambda t: t[0])
            line = " ".join(w for _, w in row_sorted)
            if DATE_RE.search(line):
                raw_lines.append((idx, line))

    if progress_cb:
        progress_cb(total_pages, total_pages, "Parsing transactions…")

    return _parse_transaction_lines(raw_lines)


def _parse_transaction_lines(lines: list[tuple[int, str]]) -> pd.DataFrame:
    records = []

    for page_no, line in lines:
        parts = line.split()

        date_tokens = [p for p in parts if DATE_RE.fullmatch(p)]
        if len(date_tokens) < 2:
            continue
        post_date, txn_date = date_tokens[:2]

        money = [p for p in parts if "$" in p]
        if len(money) < 2:
            continue
        amount = money[-2]
        balance = money[-1]

        desc_parts = []
        started = False
        for p in parts:
            if p == txn_date:
                started = True
                continue
            if p == amount:
                break
            if started:
                desc_parts.append(p)

        records.append(
            {
                "Page": page_no,
                "Posting Date": post_date,
                "Transaction Date": txn_date,
                "Description": " ".join(desc_parts),
                "Amount": _normalise_amount(amount),
                "Balance": _normalise_amount(balance),
            }
        )

    return pd.DataFrame(records)
