"""Main window. Wires the toolbar, search index, and PDF viewer into one application shell."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QFileDialog,
    QSplitter,
    QMessageBox,
    QStatusBar,
)

from pdf_engine import PDFEngine
from ui.colors import assign_colors
from ui.pdf_viewer import PDFViewer
from ui.index_panel import IndexPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF Keyword Search")
        self.resize(1100, 750)

        self._engine = PDFEngine()
        self._results: dict | None = None
        self._color_map: dict | None = None

        self._build_ui()


    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)

        toolbar = QHBoxLayout()
        self._btn_open = QPushButton("Open PDF")
        self._btn_open.clicked.connect(self._open_pdf)

        toolbar.addWidget(self._btn_open)
        toolbar.addWidget(QLabel("Keywords:"))

        self._keyword_input = QLineEdit()
        self._keyword_input.setPlaceholderText("Enter keywords separated by commas...")
        self._keyword_input.returnPressed.connect(self._run_search)
        toolbar.addWidget(self._keyword_input, stretch=1)

        self._btn_search = QPushButton("Search")
        self._btn_search.setEnabled(False)
        self._btn_search.clicked.connect(self._run_search)
        toolbar.addWidget(self._btn_search)

        self._btn_export = QPushButton("Export PDF")
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._export_pdf)
        toolbar.addWidget(self._btn_export)

        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._index_panel = IndexPanel()
        self._index_panel.navigate_to.connect(self._on_navigate)
        splitter.addWidget(self._index_panel)

        self._viewer = PDFViewer(self._engine)
        self._viewer.page_changed.connect(self._on_page_changed)
        splitter.addWidget(self._viewer)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 840])

        root.addWidget(splitter, stretch=1)

        self._status = QStatusBar()
        self.setStatusBar(self._status)


    def _open_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf)"
        )
        if not path:
            return
        try:
            count = self._engine.open(path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not open PDF:\n{exc}")
            return

        self._index_panel.clear_results()
        self._results = None
        self._color_map = None
        self._btn_search.setEnabled(True)
        self._btn_export.setEnabled(False)
        self._viewer.refresh()
        self._status.showMessage(f"Loaded {path}  —  {count} page(s)")

    def _run_search(self) -> None:
        if not self._engine.is_open:
            return

        raw = self._keyword_input.text().strip()
        if not raw:
            QMessageBox.information(self, "No keywords", "Please enter at least one keyword.")
            return

        keywords = [k.strip() for k in raw.split(",") if k.strip()]
        if not keywords:
            return

        self._color_map = assign_colors(keywords)
        self._results = self._engine.search(keywords)

        total = sum(len(v) for v in self._results.values())
        self._index_panel.populate(self._results, self._color_map)
        self._viewer.set_highlights(self._color_map, self._results)
        self._btn_export.setEnabled(total > 0)
        self._status.showMessage(f"Found {total} match(es) for {len(keywords)} keyword(s)")

    def _export_pdf(self) -> None:
        if not self._results or not self._color_map:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Highlighted PDF", "", "PDF Files (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        try:
            self._engine.export_highlighted(path, self._results, self._color_map)
            QMessageBox.information(self, "Exported", f"Highlighted PDF saved to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))

    def _on_navigate(self, page_num: int, rect) -> None:
        self._viewer.navigate_to(page_num, rect)

    def _on_page_changed(self, page_num: int) -> None:
        if self._results and self._color_map:
            self._viewer.set_highlights(self._color_map, self._results)


    def closeEvent(self, event) -> None:
        self._engine.close()
        super().closeEvent(event)
