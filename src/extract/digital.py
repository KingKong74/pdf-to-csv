from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

import pandas as pd
from pypdf import PdfReader

DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")


@dataclass
class ExtractedTable:
    name: str
    df: pd.DataFrame
    source: str


def extract_transactions_digital(pdf_path: str) -> pd.DataFrame:
    """
    Digital PDFs may have tables OR just text.
    We try text parsing first (fast + robust for statements),
    but you can swap the order if you prefer.
    """
    lines = _extract_text_lines(pdf_path)
    df = _parse_transaction_lines(lines)
    return df


def _extract_text_lines(pdf_path: str) -> List[tuple[int, str]]:
    reader = PdfReader(pdf_path)
    out: List[tuple[int, str]] = []
    for page_no, page in enumerate(reader.pages, start=1):
        txt = page.extract_text() or ""
        for ln in txt.splitlines():
            ln = " ".join(ln.split())
            if ln:
                out.append((page_no, ln))
    return out



def _parse_transaction_lines(lines: List[tuple[int, str]]) -> pd.DataFrame:
    records = []
    for page_no, line in lines:
        # only keep candidate transaction lines: must include at least 2 dates
        dates = DATE_RE.findall(line)
        if len(dates) < 2:
            continue

        parts = line.split()
        date_tokens = [p for p in parts if DATE_RE.fullmatch(p)]
        if len(date_tokens) < 2:
            continue

        post_date, txn_date = date_tokens[0], date_tokens[1]

        # monetary tokens: look for $ amounts (balance usually last)
        money = [p for p in parts if "$" in p]
        if len(money) < 2:
            continue

        amount = money[-2]
        balance = money[-1]

        # description: everything after txn_date until amount
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


def _normalise_amount(val: str) -> float:
    v = val.replace("$", "").replace(",", "").strip()
    if v.endswith("CR"):
        return -float(v[:-2])
    return float(v)
