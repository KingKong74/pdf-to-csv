from __future__ import annotations

import re
from typing import List, Tuple

import pandas as pd

from .money import looks_money, parse_money

RE_DATE = re.compile(r"^\d{2}\.\d{2}\.\d{2}\b")  # 28.06.24

IGNORE_CONTAINS = (
    "OPENING BALANCE",
    "CLOSING BALANCE",
    "TRANSACTION DESCRIPTION",
    "CONTINUED ON NEXT PAGE",
    "MACQUARIE",
    "STATEMENT NO",
    "ACCOUNT NO",
)


def score_macquarie(lines: List[Tuple[int, str]]) -> int:
    text = "\n".join(l for _, l in lines).upper()
    score = 0
    if "MACQUARIE" in text:
        score += 8
    if "TRANSACTION DESCRIPTION DEBITS CREDITS BALANCE" in text:
        score += 10
    return score


def parse_macquarie(lines: List[Tuple[int, str]]) -> pd.DataFrame:
    recs = []

    for page, line in lines:
        if not RE_DATE.match(line):
            continue

        up = line.upper()
        if any(k in up for k in IGNORE_CONTAINS):
            continue

        parts = line.split()
        date = parts[0]

        # Macquarie often: date  [desc words...]  [debit?] [credit?] [balance]  (but OCR may reorder)
        # We pick last 1-3 money tokens as candidates.
        nums = []
        i = len(parts) - 1
        while i >= 1 and looks_money(parts[i]):
            nums.append(parts[i])
            i -= 1
            if len(nums) >= 3:
                break
        nums = list(reversed(nums))
        if len(nums) < 1:
            continue

        debit = None
        credit = None
        balance = None

        if len(nums) >= 3:
            # likely debit, credit, balance
            debit = abs(parse_money(nums[-3])) if nums[-3] else None
            credit = abs(parse_money(nums[-2])) if nums[-2] else None
            balance = parse_money(nums[-1])
            desc = " ".join(parts[1 : len(parts) - 3]).strip()
        elif len(nums) == 2:
            # likely amount + balance (most common in your pasted text: "Deposit 50.00 64,485.28...")
            amt = parse_money(nums[0])
            balance = parse_money(nums[1])
            desc = " ".join(parts[1 : len(parts) - 2]).strip()

            # Deposit/Interest => credit; Direct debit/BPAY/Funds transfer => debit
            updesc = desc.upper()
            if "DIRECT DEBIT" in updesc or "BPAY" in updesc or "FUNDS TRANSFER" in updesc:
                debit = abs(amt)
            else:
                credit = abs(amt)
        else:
            # only one amount found, keep it as Amount
            amt = parse_money(nums[0])
            desc = " ".join(parts[1 : len(parts) - 1]).strip()

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
