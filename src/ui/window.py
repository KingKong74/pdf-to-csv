from __future__ import annotations

import webbrowser
from typing import Optional

import pandas as pd
from PySide6.QtCore import QThread, QSettings, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QStackedWidget,
    QFileDialog,
    QMessageBox,
)

from updater import check_for_update
from ui_pages import HomePage, ConverterPage
from worker_extract import ExtractJob, ExtractWorker

APP_VERSION = "0.1.0"

HOME_SIZE = (420, 260)
CONVERTER_DEFAULT_SIZE = (1100, 650)

SETTINGS_ORG = "KingKong74"
SETTINGS_APP = "PdfToCsvApp"


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Ensure standard window buttons exist (incl maximise)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        self.setWindowTitle(f"PDF → CSV v{APP_VERSION}")
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

        self.stack = QStackedWidget()
        self.home = HomePage()
        self.converter = ConverterPage()

        self.stack.addWidget(self.home)
        self.stack.addWidget(self.converter)

        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)

        self.home.open_clicked.connect(self.open_pdfs)
        self.home.updates_clicked.connect(self.check_updates)
        self.converter.back_clicked.connect(self.go_home)

        # Add more PDFs without going home
        self.converter.add_pdfs_clicked.connect(self.add_more_pdfs)

        self._thread: Optional[QThread] = None
        self._worker: Optional[ExtractWorker] = None

        # append mode support
        self._append_mode: bool = False
        self._append_base: Optional[pd.DataFrame] = None

        self.apply_home_window_style()

    # ── centring
    def centre_on_screen(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + (geo.height() - self.height()) // 2
        self.move(x, y)

    # ── window styles
    def apply_home_window_style(self):
        # Small home window but NOT fixed-size (so maximise stays available)
        self.setMinimumSize(360, 220)
        self.setMaximumSize(16777215, 16777215)
        self.resize(*HOME_SIZE)
        self.centre_on_screen()
        self.stack.setCurrentWidget(self.home)

    def apply_converter_window_style(self):
        self.setMaximumSize(16777215, 16777215)
        self.setMinimumSize(900, 550)

        w = int(self.settings.value("converter_w", CONVERTER_DEFAULT_SIZE[0]))
        h = int(self.settings.value("converter_h", CONVERTER_DEFAULT_SIZE[1]))
        self.resize(w, h)
        self.centre_on_screen()

    # ── updates
    def check_updates(self):
        try:
            info = check_for_update(APP_VERSION)
        except Exception as e:
            QMessageBox.warning(self, "Updates", f"Couldn’t check for updates:\n{e}")
            return

        if not info:
            QMessageBox.information(self, "Updates", "You’re on the latest version.")
            return

        latest = info.get("latest", "?")
        notes = (info.get("notes", "") or "").strip()
        url = (info.get("download_url", "") or "").strip()

        msg = f"Update available: {latest}\n\n{notes}".strip()

        box = QMessageBox(self)
        box.setWindowTitle("Update available")
        box.setText(msg)
        box.setStandardButtons(QMessageBox.Ok | QMessageBox.Open)
        result = box.exec()

        if result == QMessageBox.Open and url:
            webbrowser.open(url)

    # ── navigation
    def go_home(self):
        self.home.status.setText("")
        self.apply_home_window_style()

    # ── open PDFs (fresh)
    def open_pdfs(self):
        pdf_paths, _ = QFileDialog.getOpenFileNames(self, "Select PDF(s)", "", "PDF Files (*.pdf)")
        if not pdf_paths:
            return

        self.stack.setCurrentWidget(self.converter)
        self.apply_converter_window_style()

        self.converter.reset_for_new_job()
        self.converter.set_status("Starting extraction…")
        self.converter.set_progress(0, 0)

        self._append_mode = False
        self._append_base = None
        self.start_extract_job(pdf_paths)

    # ── add PDFs (append)
    def add_more_pdfs(self):
        pdf_paths, _ = QFileDialog.getOpenFileNames(self, "Add PDF(s)", "", "PDF Files (*.pdf)")
        if not pdf_paths:
            return

        if self.converter.df_full is None or self.converter.df_full.empty:
            self.open_pdfs()
            return

        self._append_mode = True
        self._append_base = self.converter.df_full.copy()

        self.converter.set_status("Adding PDFs…")
        self.converter.set_progress(0, 0)
        self.start_extract_job(pdf_paths)

    # ── worker thread
    def start_extract_job(self, pdf_paths: list[str]):
        if self._thread is not None:
            try:
                self._thread.quit()
                self._thread.wait(200)
            except Exception:
                pass

        self._thread = QThread()
        self._worker = ExtractWorker(ExtractJob(pdf_paths=pdf_paths))
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.status.connect(self.converter.set_status)
        self._worker.progress.connect(self.converter.set_progress)
        self._worker.failed.connect(self.on_extract_failed)
        self._worker.finished.connect(self.on_extract_finished)

        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def on_extract_failed(self, msg: str):
        self.converter.clear_progress()
        QMessageBox.critical(self, "Error", f"Extraction failed:\n{msg}")
        self.converter.set_status("Extraction failed.")
        self.converter.export_btn.setEnabled(False)
        self._append_mode = False
        self._append_base = None

    def on_extract_finished(self, df: pd.DataFrame):
        self.converter.clear_progress()

        if df is None or df.empty:
            if self._append_mode:
                QMessageBox.information(self, "No new transactions", "No transactions were detected in the added PDF(s).")
                self.converter.set_status("No new transactions found.")
            else:
                QMessageBox.information(
                    self,
                    "No transactions found",
                    "No transaction rows were detected.\n"
                    "If this is a new bank layout, we may need a small template tweak.",
                )
                self.converter.set_status("No transactions found.")
                self.converter.export_btn.setEnabled(False)

            self._append_mode = False
            self._append_base = None
            return

        if self._append_mode and self._append_base is not None and not self._append_base.empty:
            combined = pd.concat([self._append_base, df], ignore_index=True)
            combined = combined.drop_duplicates()

            self.converter.set_status(f"Loaded {len(combined)} transactions (after adding PDFs).")
            self.converter.set_df(combined)
        else:
            self.converter.set_status(f"Loaded {len(df)} transactions.")
            self.converter.set_df(df)

        self._append_mode = False
        self._append_base = None

    # ── remember size
    def closeEvent(self, event):
        if self.stack.currentWidget() == self.converter and not self.isMaximized() and not self.isFullScreen():
            self.settings.setValue("converter_w", self.width())
            self.settings.setValue("converter_h", self.height())
        super().closeEvent(event)
