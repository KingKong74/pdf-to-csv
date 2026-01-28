from __future__ import annotations

import re
from typing import List, Tuple

import pandas as pd

from .money import join_trailing_cr, looks_money, parse_money

RE_DDMMYYYY = re.compile(r"\d{2}/\d{2}/\d{4}")


def score_anz(lines: List[Tuple[int, str]]) -> int:
    text = "\n".join(l for _, l in lines).upper()
    score = 0
    if "ANZ" in text or "AUSTRALIA AND NEW ZEALAND BANKING GROUP" in text:
        score += 8
    if "STATEMENT PERIOD" in text and "ACCOUNT NUMBER" in text:
        score += 4
    return score


def parse_anz(lines: List[Tuple[int, str]]) -> pd.DataFrame:
    recs = []
    for page, line in lines:
        dates = RE_DDMMYYYY.findall(line)
        if len(dates) < 2:
            continue

        parts = line.split()
        date_tokens = [p for p in parts if RE_DDMMYYYY.fullmatch(p)]
        if len(date_tokens) < 2:
            continue

        post_date, txn_date = date_tokens[0], date_tokens[1]

        tail = join_trailing_cr([p for p in parts if p != "$"])
        money = [p for p in tail if looks_money(p)]
        if len(money) < 2:
            continue

        amount = parse_money(money[-2])
        balance = parse_money(money[-1])

        # description: between txn_date and amount token
        desc_parts = []
        started = False
        for p in parts:
            if p == txn_date:
                started = True
                continue
            if p == money[-2]:
                break
            if started:
                desc_parts.append(p)

        desc = " ".join(desc_parts).strip()
        if not desc:
            continue

        recs.append(
            {
                "Page": page,
                "Date": txn_date,
                "PostingDate": post_date,
                "TransactionDate": txn_date,
                "Description": desc,
                "Debit": abs(amount) if amount < 0 else None,
                "Credit": abs(amount) if amount > 0 else None,
                "Amount": amount,
                "Balance": balance,
            }
        )
    return pd.DataFrame(recs)
