from __future__ import annotations

import fitz
import pytesseract
import pandas as pd
from PIL import Image
import io
import re
from collections import defaultdict

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")


def extract_transactions_scanned(pdf_path: str) -> pd.DataFrame:
    raw_lines: list[str] = []

    doc = fitz.open(pdf_path)

    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        data = pytesseract.image_to_data(
            img,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6"
        )

        # --- bucket words into rows using Y tolerance ---
        rows = defaultdict(list)
        y_tolerance = 12  # pixels

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

            # transaction lines always contain at least one date
            if DATE_RE.search(line):
                raw_lines.append(line)

    return _parse_transaction_lines(raw_lines)


def _parse_transaction_lines(lines: list[str]) -> pd.DataFrame:
    records = []

    for line in lines:
        parts = line.split()

        # find first two dates anywhere in the line
        dates = [p for p in parts if DATE_RE.fullmatch(p)]
        if len(dates) < 2:
            continue

        post_date, txn_date = dates[:2]

        # find monetary values from right
        amounts = [p for p in parts if "$" in p]
        if len(amounts) < 2:
            continue

        amount = amounts[-2]
        balance = amounts[-1]

        # description = everything between dates and amount
        desc_parts = []
        started = False
        for p in parts:
            if p == dates[1]:
                started = True
                continue
            if p == amount:
                break
            if started:
                desc_parts.append(p)

        records.append({
            "Posting Date": post_date,
            "Transaction Date": txn_date,
            "Description": " ".join(desc_parts),
            "Amount": _normalise_amount(amount),
            "Balance": _normalise_amount(balance)
        })

    return pd.DataFrame(records)


def _normalise_amount(val: str) -> float:
    v = val.replace("$", "").replace(",", "").strip()
    if v.endswith("CR"):
        return -float(v[:-2])
    return float(v)
