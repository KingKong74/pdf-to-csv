from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass
class ExtractedTable:
    name: str
    df: pd.DataFrame
    source: str  # "camelot" or "pdfplumber"


def _clean_df_basic(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].astype(str).str.replace("\u00a0", " ").str.strip()
        df[c] = df[c].replace({"": None, "nan": None, "None": None})
    df = df.dropna(how="all").dropna(axis=1, how="all")
    return df


def extract_tables_camelot(pdf_path: str, pages: str = "all") -> List[ExtractedTable]:
    try:
        import camelot  # type: ignore
    except Exception:
        return []

    out: List[ExtractedTable] = []
    for flavour in ("lattice", "stream"):
        try:
            tables = camelot.read_pdf(pdf_path, pages=pages, flavor=flavour)
            for i, t in enumerate(tables):
                df = _clean_df_basic(t.df)

                # header heuristic
                if df.shape[0] >= 2:
                    first_row = df.iloc[0].tolist()
                    looks_header = sum(any(ch.isalpha() for ch in str(x)) for x in first_row) >= max(2, len(first_row) // 2)
                    if looks_header:
                        df.columns = [str(x).strip() for x in first_row]
                        df = df.iloc[1:].reset_index(drop=True)

                df = _clean_df_basic(df)
                if df.shape[0] >= 2 and df.shape[1] >= 2:
                    out.append(ExtractedTable(
                        name=f"Camelot ({flavour}) #{i+1}",
                        df=df,
                        source="camelot"
                    ))
        except Exception:
            continue

        if out:
            break

    return out


def extract_tables_pdfplumber(pdf_path: str) -> List[ExtractedTable]:
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return []

    out: List[ExtractedTable] = []
    with pdfplumber.open(pdf_path) as pdf:
        for p_idx, page in enumerate(pdf.pages, start=1):
            try:
                raw_tables = page.extract_tables()
                for t_idx, raw in enumerate(raw_tables, start=1):
                    if not raw or len(raw) < 2:
                        continue
                    df = _clean_df_basic(pd.DataFrame(raw))

                    if df.shape[0] >= 2:
                        first_row = df.iloc[0].tolist()
                        looks_header = sum(any(ch.isalpha() for ch in str(x)) for x in first_row) >= max(2, len(first_row) // 2)
                        if looks_header:
                            df.columns = [str(x).strip() for x in first_row]
                            df = df.iloc[1:].reset_index(drop=True)

                    df = _clean_df_basic(df)
                    if df.shape[0] >= 2 and df.shape[1] >= 2:
                        out.append(ExtractedTable(
                            name=f"pdfplumber p{p_idx} t{t_idx}",
                            df=df,
                            source="pdfplumber"
                        ))
            except Exception:
                continue
    return out


def extract_tables(pdf_path: str) -> List[ExtractedTable]:
    camelot_tables = extract_tables_camelot(pdf_path, pages="all")
    if camelot_tables:
        return camelot_tables
    return extract_tables_pdfplumber(pdf_path)
