from __future__ import annotations

import re
from typing import List, Tuple

import pandas as pd
from .money import looks_money, parse_money

RE_DDMMYY = re.compile(r"^\d{2}/\d{2}/\d{2}\b")
RE_DDMMYYYY = re.compile(r"^\d{2}/\d{2}/\d{4}\b")
RE_DD_MON = re.compile(r"^\d{1,2}\s+[A-Za-z]{3}\b")


def score_generic_au(lines: List[Tuple[int, str]]) -> int:
    # Always available as a fallback
    return 1


def parse_generic_au(lines: List[Tuple[int, str]]) -> pd.DataFrame:
    recs = []

    for page, line in lines:
        parts = line.split()
        if not parts:
            continue

        # detect date token (one of the common forms)
        date = None
        if RE_DDMMYYYY.match(line) or RE_DDMMYY.match(line):
            date = parts[0]
            rest = " ".join(parts[1:])
        elif RE_DD_MON.match(line) and len(parts) >= 2:
            date = " ".join(parts[:2])
            rest = " ".join(parts[2:])
        else:
            continue

        toks = rest.split()
        monies = [t for t in toks if looks_money(t)]
        if not monies:
            continue

        # last money is often balance; keep both if present
        balance = parse_money(monies[-1]) if len(monies) >= 2 else None
        amount = parse_money(monies[-2]) if len(monies) >= 2 else parse_money(monies[-1])

        desc = rest
        # remove last 1–2 money tokens from description
        desc = desc.replace(monies[-1], "")
        if len(monies) >= 2:
            desc = desc.replace(monies[-2], "")
        desc = " ".join(desc.split()).strip()

        if not desc:
            continue

        recs.append({"Page": page, "Date": date, "Description": desc, "Amount": amount, "Balance": balance})

    return pd.DataFrame(recs)
