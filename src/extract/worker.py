from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd
from PySide6.QtCore import QObject, Signal

from pdf_detect import is_digital_pdf
from extractor_scanned import extract_transactions_scanned
from extractor_digital import extract_transactions_digital


@dataclass
class ExtractJob:
    pdf_paths: list[str]


class ExtractWorker(QObject):
    status = Signal(str)
    progress = Signal(int, int)  # (cur,total) where (0,0) = indeterminate
    finished = Signal(pd.DataFrame)
    failed = Signal(str)

    def __init__(self, job: ExtractJob):
        super().__init__()
        self.job = job

    def run(self):
        try:
            all_frames: list[pd.DataFrame] = []
            total_files = len(self.job.pdf_paths)

            for file_index, pdf_path in enumerate(self.job.pdf_paths, start=1):
                name = os.path.basename(pdf_path)

                self.status.emit(f"({file_index}/{total_files}) Detecting PDF type: {name}")
                digital = is_digital_pdf(pdf_path)

                if digital:
                    self.status.emit(f"({file_index}/{total_files}) Digital PDF — extracting: {name}")
                    self.progress.emit(0, 0)  # indeterminate
                    df = extract_transactions_digital(pdf_path)
                else:
                    self.status.emit(f"({file_index}/{total_files}) Scanned PDF — running OCR: {name}")

                    def cb(cur: int, total: int, msg: str):
                        self.status.emit(f"({file_index}/{total_files}) {name} — {msg}")
                        self.progress.emit(cur, total)

                    df = extract_transactions_scanned(pdf_path, progress_cb=cb)

                if df is None or df.empty:
                    continue

                df = df.copy()
                # Multi-PDF support fields
                if "Source File" not in df.columns:
                    df.insert(0, "Source File", name)
                if "Source Path" not in df.columns:
                    df.insert(1, "Source Path", pdf_path)

                all_frames.append(df)

            if not all_frames:
                self.finished.emit(pd.DataFrame())
                return

            out = pd.concat(all_frames, ignore_index=True)
            self.finished.emit(out)

        except Exception as e:
            self.failed.emit(str(e))
