from __future__ import annotations

import re
from typing import List, Tuple, Optional

import pandas as pd

from .money import looks_money, parse_money

RE_DATE_FULL = re.compile(r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\b")  # "11 Jul 2025"

IGNORE_CONTAINS = (
    "BROUGHT FORWARD",
    "CARRIED FORWARD",
    "TRANSACTION SUMMARY",
    "STATEMENT NUMBER",
    "ACCOUNT DETAILS",
    "NATIONAL AUSTRALIA BANK",
)


def score_nab(lines: List[Tuple[int, str]]) -> int:
    text = "\n".join(l for _, l in lines).upper()
    score = 0
    if "NATIONAL AUSTRALIA BANK" in text or " NAB " in f" {text} ":
        score += 7
    if "TRANSACTION DETAILS" in text:
        score += 7
    return score


def parse_nab(lines: List[Tuple[int, str]]) -> pd.DataFrame:
    recs = []
    current_date: Optional[str] = None

    for page, line in lines:
        up = line.upper()
        if any(k in up for k in IGNORE_CONTAINS):
            continue

        rest = line.strip()

        # date “carry” behaviour
        if RE_DATE_FULL.match(rest):
            parts = rest.split()
            current_date = " ".join(parts[:3])  # "11 Jul 2025"
            rest = " ".join(parts[3:]).strip()

        if not current_date:
            continue

        # NAB dotted leaders / noise
        rest = rest.replace("…", " ").replace(".", " ")
        rest = " ".join(rest.split())
        toks = rest.split()
        if not toks:
            continue

        money = [t for t in toks if looks_money(t) or re.match(r"^(CR|Cr|cr|DR|Dr|dr)\d", t)]
        money = [t.replace("Cr", "CR").replace("cr", "CR") for t in money]

        if len(money) == 0:
            continue

        amount = None
        balance = None

        if len(money) >= 2:
            amount = parse_money(money[-2])
            balance = parse_money(money[-1])
        else:
            amount = parse_money(money[-1])

        desc = rest
        for m in money[-2:]:
            desc = desc.replace(m, "")
        desc = " ".join(desc.split()).strip()

        if not desc:
            continue

        recs.append(
            {
                "Page": page,
                "Date": current_date,
                "PostingDate": current_date,
                "TransactionDate": None,
                "Description": desc,
                "Debit": abs(amount) if amount is not None and amount < 0 else None,
                "Credit": abs(amount) if amount is not None and amount > 0 else None,
                "Amount": amount,
                "Balance": balance,
            }
        )

    return pd.DataFrame(recs)
