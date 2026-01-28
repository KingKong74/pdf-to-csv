from __future__ import annotations

import re
from typing import List, Tuple

import pandas as pd

from .money import looks_money, parse_money

RE_DATE = re.compile(r"^\d{2}/\d{2}/\d{2}\b")

IGNORE_CONTAINS = (
    "STATEMENT",
    "TRANSACTION FEE SUMMARY",
    "THANK YOU",
    "MORE INFORMATION",
    "DATE TRANSACTION DESCRIPTION",
    "OPENING BALANCE",
    "CLOSING BALANCE",
)


def score_westpac(lines: List[Tuple[int, str]]) -> int:
    text = "\n".join(l for _, l in lines).upper()
    score = 0
    if "WESTPAC" in text:
        score += 8
    if "DATE TRANSACTION DESCRIPTION DEBIT CREDIT BALANCE" in text:
        score += 10
    return score


def parse_westpac(lines: List[Tuple[int, str]]) -> pd.DataFrame:
    recs = []

    for page, line in lines:
        if not RE_DATE.match(line):
            continue
        up = line.upper()
        if any(k in up for k in IGNORE_CONTAINS):
            continue

        parts = line.split()
        date = parts[0]

        # numeric tokens tend to be at the end: [debit] [credit] [balance] OR [amount] [balance]
        nums = []
        i = len(parts) - 1
        while i >= 1 and looks_money(parts[i]):
            nums.append(parts[i])
            i -= 1
            if len(nums) >= 3:
                break
        nums = list(reversed(nums))
        if len(nums) < 2:
            continue

        balance = parse_money(nums[-1])

        debit = None
        credit = None

        # If 3 nums assume: debit credit balance (one can be missing in OCR though)
        if len(nums) == 3:
            d = parse_money(nums[0])
            c = parse_money(nums[1])
            debit = abs(d) if d != 0 else None
            credit = abs(c) if c != 0 else None
            desc = " ".join(parts[1 : len(parts) - 3]).strip()
        else:
            # 2 nums: amount + balance
            amt = parse_money(nums[0])
            desc = " ".join(parts[1 : len(parts) - 2]).strip()

            # Heuristic: Withdrawal/Fee/Payment => debit else credit
            updesc = desc.upper()
            if "WITHDRAWAL" in updesc or "FEE" in updesc or "PAYMENT" in updesc or "BPAY" in updesc:
                debit = abs(amt)
            else:
                credit = abs(amt)

        if not desc:
            continue

        recs.append(
            {
                "Page": page,
                "Date": date,
                "PostingDate": date,
                "TransactionDate": None,
                "Description": desc,
                "Debit": debit,
                "Credit": credit,
                "Balance": balance,
            }
        )

    return pd.DataFrame(recs)
