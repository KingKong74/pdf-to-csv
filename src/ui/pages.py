from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QProgressBar,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QScrollArea,
    QGroupBox,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
)


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


class HomePage(QWidget):
    open_clicked = Signal()
    updates_clicked = Signal()

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignTop)
        root.setSpacing(14)

        title = QLabel("PDF → CSV Converter")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        root.addWidget(title)

        subtitle = QLabel("Converts bank statement PDFs to CSV (scanned or digital).")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("opacity: 0.85;")
        root.addWidget(subtitle)

        root.addSpacing(8)

        self.open_btn = QPushButton("Open PDF(s)…")
        self.open_btn.setMinimumHeight(44)
        self.open_btn.clicked.connect(self.open_clicked.emit)
        root.addWidget(self.open_btn)

        self.update_btn = QPushButton("Check for updates")
        self.update_btn.setFixedHeight(30)
        self.update_btn.setStyleSheet("opacity: 0.9;")
        self.update_btn.clicked.connect(self.updates_clicked.emit)
        root.addWidget(self.update_btn, alignment=Qt.AlignLeft)

        root.addSpacing(14)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("opacity: 0.85;")
        root.addWidget(self.status)

        root.addStretch(1)


class ConverterPage(QWidget):
    back_clicked = Signal()
    add_pdfs_clicked = Signal()

    def __init__(self):
        super().__init__()

        self.df_full: Optional[pd.DataFrame] = None
        self.df_filtered: Optional[pd.DataFrame] = None

        self.selected_file: Optional[str] = None
        self.selected_page: Optional[int] = None

        # Preview pagination
        self.rows_per_page: int = 50
        self.row_page_index: int = 0

        self.col_widgets: Dict[str, ColumnRowWidget] = {}

        root = QVBoxLayout(self)

        # ── Top bar
        top = QHBoxLayout()

        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self.back_clicked.emit)

        self.add_btn = QPushButton("Add PDFs…")
        self.add_btn.clicked.connect(self.add_pdfs_clicked.emit)

        self.status = QLabel("")
        self.status.setStyleSheet("opacity: 0.85;")

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFixedHeight(16)
        self.progress.hide()

        # Page filter (only meaningful when a single PDF is selected)
        self.page_label = QLabel("Page:")
        self.page_combo = QComboBox()
        self.page_combo.currentIndexChanged.connect(self._on_page_change)
        self.page_label.hide()
        self.page_combo.hide()

        top.addWidget(self.back_btn)
        top.addWidget(self.add_btn)
        top.addWidget(self.status, 1)
        top.addWidget(self.progress)
        top.addSpacing(10)
        top.addWidget(self.page_label)
        top.addWidget(self.page_combo)

        root.addLayout(top)

        # ── Summary line
        self.summary = QLabel("")
        self.summary.setStyleSheet("opacity: 0.85;")
        root.addWidget(self.summary)

        # ── Main content
        body = QHBoxLayout()
        root.addLayout(body, 1)

        # LEFT: files panel (narrower)
        files_box = QGroupBox("Loaded PDFs")
        files_box.setFixedWidth(230)  # tighter
        files_v = QVBoxLayout(files_box)

        self.files_list = QListWidget()
        self.files_list.itemSelectionChanged.connect(self._on_file_selected)

        # Drag/drop reorder
        self.files_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.files_list.model().rowsMoved.connect(self._on_files_reordered)

        files_v.addWidget(self.files_list, 1)

        move_row = QHBoxLayout()
        self.move_up_btn = QPushButton("↑")
        self.move_down_btn = QPushButton("↓")
        self.move_up_btn.setFixedWidth(44)
        self.move_down_btn.setFixedWidth(44)
        self.move_up_btn.clicked.connect(self._move_selected_pdf_up)
        self.move_down_btn.clicked.connect(self._move_selected_pdf_down)
        move_row.addWidget(self.move_up_btn)
        move_row.addWidget(self.move_down_btn)
        move_row.addStretch(1)
        files_v.addLayout(move_row)

        body.addWidget(files_box, 1)

        # MIDDLE: preview + pager
        mid = QVBoxLayout()

        mid.addWidget(QLabel("Preview"))
        self.preview = QTableWidget()
        self.preview.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview.setAlternatingRowColors(True)
        mid.addWidget(self.preview, 1)

        pager = QHBoxLayout()
        self.rows_prev = QPushButton("←")
        self.rows_prev.setFixedWidth(44)
        self.rows_prev.clicked.connect(self._rows_prev)

        self.rows_next = QPushButton("→")
        self.rows_next.setFixedWidth_toggle = None
        self.rows_next.setFixedWidth(44)
        self.rows_next.clicked.connect(self._rows_next)

        self.rows_info = QLabel("")
        self.rows_info.setStyleSheet("opacity: 0.85;")

        pager.addWidget(self.rows_prev)
        pager.addWidget(self.rows_next)
        pager.addWidget(self.rows_info, 1)
        mid.addLayout(pager)

        body.addLayout(mid, 2)

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

        body.addLayout(right, 1)

        self._reset_ui_state()

    # ─────────────────────────────────────────────
    # Status/progress (hide preview while working to avoid black flash)
    # ─────────────────────────────────────────────
    def set_status(self, text: str):
        self.status.setText(text)

    def set_progress(self, cur: int, total: int):
        if not self.preview.isHidden():
            self.preview.hide()

        self.progress.show()
        if cur == 0 and total == 0:
            self.progress.setRange(0, 0)
            self.progress.setFormat("Working…")
        else:
            self.progress.setRange(0, total)
            self.progress.setValue(cur)
            self.progress.setFormat(f"{cur}/{total}")

    def clear_progress(self):
        self.progress.hide()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.preview.show()

    # ─────────────────────────────────────────────
    # Public helpers
    # ─────────────────────────────────────────────
    def reset_for_new_job(self):
        self._reset_ui_state()
        self.summary.setText("Extracting… this can take a moment for scanned PDFs.")

    def set_df(self, df: pd.DataFrame):
        self.df_full = df

        # Columns based on full df (stable)
        self._build_columns(df)

        # Files list + select All PDFs
        self._populate_files(df)
        self.selected_file = None
        self.selected_page = None
        self.row_page_index = 0

        self._rebuild_page_dropdown()
        self._apply_filters_and_render()

        self.export_btn.setEnabled(df is not None and not df.empty)

    # ─────────────────────────────────────────────
    # Ordering helpers (for All PDFs ordering + export ordering)
    # ─────────────────────────────────────────────
    def _current_file_order(self) -> list[str]:
        order: list[str] = []
        for i in range(self.files_list.count()):
            it = self.files_list.item(i)
            name = it.data(Qt.UserRole)
            if name is not None:
                order.append(name)
        return order

    def _sort_df_by_user_file_order(self, df: pd.DataFrame) -> pd.DataFrame:
        if "Source File" not in df.columns:
            return df

        order = self._current_file_order()
        if not order:
            return df

        order_map = {name: i for i, name in enumerate(order)}
        dfx = df.copy()
        dfx["_file_order"] = dfx["Source File"].map(lambda x: order_map.get(x, 10**9))

        if "Page" in dfx.columns:
            dfx = dfx.sort_values(by=["_file_order", "Page"], kind="stable")
        else:
            dfx = dfx.sort_values(by=["_file_order"], kind="stable")

        return dfx.drop(columns=["_file_order"])

    # ─────────────────────────────────────────────
    # Internal UI state
    # ─────────────────────────────────────────────
    def _reset_ui_state(self):
        self.df_full = None
        self.df_filtered = None
        self.selected_file = None
        self.selected_page = None
        self.row_page_index = 0

        self.summary.setText("")

        # Reset table gracefully
        self.preview.setUpdatesEnabled(False)
        self.preview.clear()
        self.preview.setRowCount(0)
        self.preview.setColumnCount(0)
        self.preview.setUpdatesEnabled(True)

        self._clear_columns()
        self.export_btn.setEnabled(False)

        self.files_list.clear()

        self.page_label.hide()
        self.page_combo.hide()
        self.page_combo.blockSignals(True)
        self.page_combo.clear()
        self.page_combo.blockSignals(False)

        self._update_rows_pager_state()

    def _populate_files(self, df: pd.DataFrame):
        self.files_list.blockSignals(True)
        self.files_list.clear()

        all_item = QListWidgetItem("All PDFs")
        all_item.setData(Qt.UserRole, None)
        self.files_list.addItem(all_item)

        if "Source File" in df.columns:
            files = sorted(df["Source File"].dropna().unique().tolist())
            for f in files:
                it = QListWidgetItem(f)
                it.setData(Qt.UserRole, f)
                self.files_list.addItem(it)

        self.files_list.setCurrentRow(0)
        self.files_list.blockSignals(False)

    def _on_file_selected(self):
        item = self.files_list.currentItem()
        if not item or self.df_full is None:
            return

        self.selected_file = item.data(Qt.UserRole)  # None => All PDFs
        self.selected_page = None
        self.row_page_index = 0

        self._rebuild_page_dropdown()
        self._apply_filters_and_render()

    def _rebuild_page_dropdown(self):
        self.page_combo.blockSignals(True)
        self.page_combo.clear()

        if self.df_full is None or self.selected_file is None:
            self.page_label.hide()
            self.page_combo.hide()
            self.page_combo.blockSignals(False)
            return

        df = self.df_full
        if "Source File" in df.columns:
            df = df[df["Source File"] == self.selected_file]

        if "Page" not in df.columns:
            self.page_label.hide()
            self.page_combo.hide()
            self.page_combo.blockSignals(False)
            return

        pages = sorted(int(p) for p in df["Page"].dropna().unique().tolist())
        if len(pages) <= 1:
            self.page_label.hide()
            self.page_combo.hide()
            self.page_combo.blockSignals(False)
            return

        self.page_combo.addItem("All pages", None)
        for p in pages:
            self.page_combo.addItem(f"Page {p}", p)

        self.page_combo.setCurrentIndex(0)
        self.page_label.show()
        self.page_combo.show()
        self.page_combo.blockSignals(False)

    def _on_page_change(self):
        self.selected_page = self.page_combo.currentData()
        self.row_page_index = 0
        self._apply_filters_and_render()

    # ─────────────────────────────────────────────
    # Reorder handling
    # ─────────────────────────────────────────────
    def _on_files_reordered(self, *args):
        # After drag/drop reorder, refresh ordering-dependent views.
        self.row_page_index = 0
        self._apply_filters_and_render()

    def _move_selected_pdf_up(self):
        row = self.files_list.currentRow()
        if row <= 1:  # 0 is All PDFs
            return
        item = self.files_list.takeItem(row)
        self.files_list.insertItem(row - 1, item)
        self.files_list.setCurrentRow(row - 1)
        self._on_files_reordered()

    def _move_selected_pdf_down(self):
        row = self.files_list.currentRow()
        if row < 1:
            return
        if row >= self.files_list.count() - 1:
            return
        item = self.files_list.takeItem(row)
        self.files_list.insertItem(row + 1, item)
        self.files_list.setCurrentRow(row + 1)
        self._on_files_reordered()

    # ─────────────────────────────────────────────
    # Filtering + preview pagination
    # ─────────────────────────────────────────────
    def _apply_filters_and_render(self):
        if self.df_full is None:
            return

        df = self.df_full

        # If viewing All PDFs, sort by user file order
        if self.selected_file is None and "Source File" in df.columns:
            df = self._sort_df_by_user_file_order(df)

        # Filter by selected PDF
        if self.selected_file is not None and "Source File" in df.columns:
            df = df[df["Source File"] == self.selected_file]

        # Filter by Page (only meaningful for a selected PDF)
        if self.selected_file is not None and self.selected_page is not None and "Page" in df.columns:
            df = df[df["Page"] == self.selected_page]

        self.df_filtered = df.reset_index(drop=True)

        pdf_count = (
            len(self.df_full["Source File"].dropna().unique())
            if "Source File" in self.df_full.columns
            else 1
        )
        tx_count = len(self.df_full)
        view_count = len(self.df_filtered)
        which_pdf = self.selected_file if self.selected_file is not None else "All PDFs"
        which_page = (
            f"Page {self.selected_page}"
            if (self.selected_file is not None and self.selected_page is not None)
            else "All pages"
        )

        self.summary.setText(
            f"Loaded: {pdf_count} PDF(s), {tx_count} transactions | Viewing: {which_pdf} · {which_page} · {view_count} rows"
        )

        self._render_preview_current_rows_page()

    def _render_preview_current_rows_page(self):
        if self.df_filtered is None:
            self.preview.setRowCount(0)
            self.preview.setColumnCount(0)
            self._update_rows_pager_state()
            return

        total_rows = len(self.df_filtered)
        if total_rows == 0:
            self.preview.setRowCount(0)
            self.preview.setColumnCount(0)
            self._update_rows_pager_state()
            return

        start = self.row_page_index * self.rows_per_page
        if start >= total_rows:
            self.row_page_index = 0
            start = 0
        end = min(start + self.rows_per_page, total_rows)

        dfp = self.df_filtered.iloc[start:end].copy()

        self.preview.setRowCount(len(dfp))
        self.preview.setColumnCount(len(dfp.columns))
        self.preview.setHorizontalHeaderLabels([str(c) for c in dfp.columns])

        for r in range(len(dfp)):
            for c, col in enumerate(dfp.columns):
                val = dfp.iloc[r, c]
                self.preview.setItem(r, c, QTableWidgetItem("" if pd.isna(val) else str(val)))

        self.preview.resizeColumnsToContents()
        self._update_rows_pager_state()

    def _update_rows_pager_state(self):
        if self.df_filtered is None:
            self.rows_prev.setEnabled(False)
            self.rows_next.setEnabled(False)
            self.rows_info.setText("")
            return

        total = len(self.df_filtered)
        if total == 0:
            self.rows_prev.setEnabled(False)
            self.rows_next.setEnabled(False)
            self.rows_info.setText("No rows")
            return

        start = self.row_page_index * self.rows_per_page
        end = min(start + self.rows_per_page, total)
        pages = (total + self.rows_per_page - 1) // self.rows_per_page

        self.rows_prev.setEnabled(self.row_page_index > 0)
        self.rows_next.setEnabled(self.row_page_index < pages - 1)
        self.rows_info.setText(f"Rows {start + 1}-{end} of {total} (page {self.row_page_index + 1}/{pages})")

    def _rows_prev(self):
        if self.row_page_index > 0:
            self.row_page_index -= 1
            self._render_preview_current_rows_page()

    def _rows_next(self):
        if self.df_filtered is None:
            return
        total = len(self.df_filtered)
        pages = (total + self.rows_per_page - 1) // self.rows_per_page
        if self.row_page_index < pages - 1:
            self.row_page_index += 1
            self._render_preview_current_rows_page()

    # ─────────────────────────────────────────────
    # Columns + export (export respects user file order)
    # ─────────────────────────────────────────────
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
        if self.df_full is None or self.df_full.empty:
            return

        # Apply user PDF order before export if multiple PDFs
        df_export = self.df_full
        if "Source File" in df_export.columns:
            df_export = self._sort_df_by_user_file_order(df_export)

        try:
            df_out = self._apply_selection(df_export)
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
