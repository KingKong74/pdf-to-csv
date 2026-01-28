from __future__ import annotations

import re
from typing import List, Tuple

import pandas as pd

from .money import join_trailing_cr, looks_money, parse_money

RE_DATE = re.compile(r"^\d{1,2}\s+[A-Za-z]{3}\b")  # "04 Oct"

IGNORE_CONTAINS = (
    "STATEMENT",
    "ACCOUNT NUMBER",
    "IMPORTANT INFORMATION",
    "TRANSACTION SUMMARY",
)


def score_cba(lines: List[Tuple[int, str]]) -> int:
    text = "\n".join(l for _, l in lines).upper()
    score = 0
    if "COMMBANK" in text or "COMMONWEALTH" in text:
        score += 7
    if "BUSINESS TRANSACTION ACCOUNT" in text:
        score += 5
    if "DATE TRANSACTION DEBIT CREDIT BALANCE" in text:
        score += 5
    return score


def parse_cba(lines: List[Tuple[int, str]]) -> pd.DataFrame:
    recs = []

    for page, line in lines:
        if not RE_DATE.match(line):
            continue
        up = line.upper()
        if any(k in up for k in IGNORE_CONTAINS):
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        date = " ".join(parts[:2])  # "04 Oct"
        tail = parts[2:]

        # Pull money-ish tokens; join CR/DR if separate
        money_tokens = [t for t in tail if t != "$"]
        money_tokens = join_trailing_cr(money_tokens)
        money = [t for t in money_tokens if looks_money(t)]

        if len(money) < 2:
            continue

        amount = parse_money(money[-2])
        balance = parse_money(money[-1])

        # Description = everything except the last 1-2 money-ish tokens
        desc = line
        # remove leading date
        desc = desc[len(date):].strip()
        # remove balance + amount occurrences
        desc = desc.replace(money[-1], "").replace(money[-2], "")
        desc = " ".join(desc.split()).strip()

        if not desc:
            continue

        # CBA doesn’t always label debit/credit clearly in OCR; keep Amount as signed-ish.
        # If you want: store debit/credit based on whether it says "Direct Credit"/"Direct Debit".
        debit = None
        credit = None
        updesc = desc.upper()
        if "DIRECT DEBIT" in updesc or "TRANSFER TO" in updesc or "BPAY" in updesc:
            debit = abs(amount)
            amount = -abs(amount)
        elif "DIRECT CREDIT" in updesc or "DEPOSIT" in updesc:
            credit = abs(amount)
            amount = abs(amount)

        recs.append(
            {
                "Page": page,
                "Date": date,
                "PostingDate": date,
                "TransactionDate": None,
                "Description": desc,
                "Debit": debit,
                "Credit": credit,
                "Amount": amount,
                "Balance": balance,
            }
        )

    return pd.DataFrame(recs)
