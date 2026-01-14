from __future__ import annotations

import sys
from typing import Dict, List

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QGroupBox
)

from extractor_scanned import extract_transactions_scanned

APP_VERSION = "0.1.0"


class ColumnRowWidget(QWidget):
    def __init__(self, col_name: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.keep_btn = QPushButton("✓")
        self.keep_btn.setCheckable(True)
        self.keep_btn.setChecked(True)
        self.keep_btn.setFixedWidth(36)

        self.orig_label = QLabel(col_name)
        self.orig_label.setMinimumWidth(170)

        self.rename_edit = QLineEdit()
        self.rename_edit.setPlaceholderText("Rename… (optional)")

        layout.addWidget(self.keep_btn)
        layout.addWidget(self.orig_label)
        layout.addWidget(self.rename_edit, 1)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"PDF → CSV (Scanned Statements) v{APP_VERSION}")

        self.df: pd.DataFrame | None = None
        self.col_widgets: Dict[str, ColumnRowWidget] = {}

        root = QHBoxLayout(self)

        # LEFT: open + info
        left = QVBoxLayout()
        self.open_btn = QPushButton("Open scanned PDF…")
        self.open_btn.clicked.connect(self.open_pdf)
        left.addWidget(self.open_btn)

        self.status = QLabel("Open a scanned statement PDF to begin.")
        self.status.setWordWrap(True)
        left.addWidget(self.status)
        left.addStretch(1)

        # MIDDLE: preview
        mid = QVBoxLayout()
        mid.addWidget(QLabel("Preview"))
        self.preview = QTableWidget()
        self.preview.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview.setAlternatingRowColors(True)
        mid.addWidget(self.preview, 1)

        # RIGHT: columns + export
        right = QVBoxLayout()

        col_box = QGroupBox("Choose columns + rename")
        col_v = QVBoxLayout(col_box)

        self.columns_area = QScrollArea()
        self.columns_area.setWidgetResizable(True)
        self.columns_container = QWidget()
        self.columns_v = QVBoxLayout(self.columns_container)
        self.columns_v.setAlignment(Qt.AlignTop)
        self.columns_area.setWidget(self.columns_container)
        col_v.addWidget(self.columns_area, 1)

        self.export_btn = QPushButton("Export CSV…")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_csv)

        right.addWidget(col_box, 1)
        right.addWidget(self.export_btn)

        root.addLayout(left, 1)
        root.addLayout(mid, 2)
        root.addLayout(right, 1)

    def open_pdf(self):
        pdf_path, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if not pdf_path:
            return

        self.status.setText("Extracting transactions… (OCR can take a moment)")
        QApplication.processEvents()

        try:
            df = extract_transactions_scanned(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Extraction failed:\n{e}")
            self.status.setText("Extraction failed.")
            return

        if df.empty:
            QMessageBox.information(self, "No transactions found",
                                    "OCR ran, but no transaction rows were detected.\n"
                                    "This usually means the layout is different or OCR quality is low.")
            self.status.setText("No transactions found.")
            return

        self.df = df
        self.status.setText(f"Loaded {len(df)} transactions.")
        self._show_preview(df)
        self._build_columns(df)
        self.export_btn.setEnabled(True)

    def _show_preview(self, df: pd.DataFrame, max_rows: int = 40):
        dfp = df.iloc[:max_rows].copy()
        self.preview.setRowCount(len(dfp))
        self.preview.setColumnCount(len(dfp.columns))
        self.preview.setHorizontalHeaderLabels([str(c) for c in dfp.columns])

        for r in range(len(dfp)):
            for c, col in enumerate(dfp.columns):
                val = dfp.iloc[r, c]
                self.preview.setItem(r, c, QTableWidgetItem("" if pd.isna(val) else str(val)))

        self.preview.resizeColumnsToContents()

    def _clear_columns(self):
        while self.columns_v.count():
            it = self.columns_v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.col_widgets = {}

    def _build_columns(self, df: pd.DataFrame):
        self._clear_columns()
        for col in df.columns:
            w = ColumnRowWidget(str(col))
            self.columns_v.addWidget(w)
            self.col_widgets[str(col)] = w

    def _apply_selection(self, df: pd.DataFrame) -> pd.DataFrame:
        keep: List[str] = []
        rename: Dict[str, str] = {}

        for orig, w in self.col_widgets.items():
            if w.keep_btn.isChecked():
                keep.append(orig)
                new = w.rename_edit.text().strip()
                if new:
                    rename[orig] = new

        if not keep:
            raise ValueError("No columns selected.")

        out = df[keep].copy()
        if rename:
            out = out.rename(columns=rename)
        return out

    def export_csv(self):
        if self.df is None or self.df.empty:
            return

        try:
            df_out = self._apply_selection(self.df)
        except Exception as e:
            QMessageBox.warning(self, "Can’t export", str(e))
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if not save_path:
            return
        if not save_path.lower().endswith(".csv"):
            save_path += ".csv"

        try:
            df_out.to_csv(save_path, index=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{e}")
            return

        QMessageBox.information(self, "Done", f"Saved:\n{save_path}")


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1200, 650)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
