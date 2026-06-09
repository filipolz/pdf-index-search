"""PDF viewer. Renders pages, overlays keyword highlights, and handles page navigation and zoom."""

from __future__ import annotations

import fitz

from PyQt6.QtCore import Qt, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
)

from pdf_engine import PDFEngine, SearchResult


class _PageLabel(QLabel):

    def __init__(self, parent: PDFViewer) -> None:
        super().__init__(parent)
        self._viewer = parent
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._viewer._base_pixmap:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        zoom = self._viewer._zoom
        ox, oy = self._content_offset()

        for kw, color in (self._viewer._highlights or {}).items():
            matches = self._viewer._page_matches.get(kw, [])
            brush = QBrush(color)
            pen = QPen(Qt.PenStyle.NoPen)
            painter.setPen(pen)
            painter.setBrush(brush)
            for m in matches:
                r = m.rect
                x = ox + r.x0 * zoom
                y = oy + r.y0 * zoom
                w = (r.x1 - r.x0) * zoom
                h = (r.y1 - r.y0) * zoom
                painter.drawRect(QRectF(x, y, w, h))

        pulse = self._viewer._pulse_rect
        if pulse is not None:
            pen = QPen(QColor(255, 0, 0, 200), 3)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 0, 0, 60)))
            r = pulse
            x = ox + r.x0 * zoom
            y = oy + r.y0 * zoom
            w = (r.x1 - r.x0) * zoom
            h = (r.y1 - r.y0) * zoom
            painter.drawRect(QRectF(x, y, w, h))

        painter.end()

    def _content_offset(self) -> tuple[float, float]:
        pm = self.pixmap()
        if pm is None:
            return (0.0, 0.0)
        ox = (self.width() - pm.width()) / 2.0
        oy = (self.height() - pm.height()) / 2.0
        return (max(ox, 0.0), max(oy, 0.0))


class PDFViewer(QWidget):

    page_changed = pyqtSignal(int)

    ZOOM_MIN = 0.5
    ZOOM_MAX = 4.0
    ZOOM_STEP = 0.25
    DEFAULT_ZOOM = 1.5

    def __init__(self, engine: PDFEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._current_page = 0
        self._zoom = self.DEFAULT_ZOOM
        self._base_pixmap: QPixmap | None = None
        self._highlights: dict[str, QColor] | None = None
        self._page_matches: dict[str, list[SearchResult]] = {}
        self._pulse_rect: fitz.Rect | None = None
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setSingleShot(True)
        self._pulse_timer.timeout.connect(self._clear_pulse)

        self._build_ui()


    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._page_label = _PageLabel(self)
        self._page_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._scroll.setWidget(self._page_label)
        layout.addWidget(self._scroll, stretch=1)

        nav = QHBoxLayout()
        self._btn_prev = QPushButton("< Prev")
        self._btn_prev.clicked.connect(self._prev_page)
        self._lbl_page = QLabel("No PDF loaded")
        self._lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_next = QPushButton("Next >")
        self._btn_next.clicked.connect(self._next_page)

        self._btn_zoom_out = QPushButton("-")
        self._btn_zoom_out.setFixedWidth(32)
        self._btn_zoom_out.clicked.connect(self._zoom_out)
        self._lbl_zoom = QLabel(f"{int(self._zoom / self.DEFAULT_ZOOM * 100)}%")
        self._lbl_zoom.setFixedWidth(45)
        self._lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_zoom_in = QPushButton("+")
        self._btn_zoom_in.setFixedWidth(32)
        self._btn_zoom_in.clicked.connect(self._zoom_in)

        nav.addWidget(self._btn_prev)
        nav.addStretch()
        nav.addWidget(self._btn_zoom_out)
        nav.addWidget(self._lbl_zoom)
        nav.addWidget(self._btn_zoom_in)
        nav.addStretch()
        nav.addWidget(self._lbl_page)
        nav.addStretch()
        nav.addWidget(self._btn_next)
        layout.addLayout(nav)


    def show_page(self, page_num: int) -> None:
        if not self._engine.is_open:
            return
        page_num = max(0, min(page_num, self._engine.page_count - 1))
        self._current_page = page_num
        self._render()
        self.page_changed.emit(page_num)

    def set_highlights(
        self,
        color_map: dict[str, QColor],
        results: dict[str, list[SearchResult]],
    ) -> None:
        self._highlights = color_map
        self._all_results = results
        self._rebuild_page_matches()
        self._render()

    def clear_highlights(self) -> None:
        self._highlights = None
        self._page_matches = {}
        self._render()

    def navigate_to(self, page_num: int, rect: fitz.Rect) -> None:
        self.show_page(page_num)
        self._pulse_rect = rect
        self._page_label.update()
        self._pulse_timer.start(1200)
        self._scroll_to_rect(rect)

    def refresh(self) -> None:
        self._current_page = 0
        self._highlights = None
        self._page_matches = {}
        self._render()


    def _render(self) -> None:
        if not self._engine.is_open:
            self._page_label.clear()
            self._lbl_page.setText("No PDF loaded")
            return

        pix = self._engine.render_page(self._current_page, self._zoom)
        fmt = QImage.Format.Format_RGB888
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
        self._base_pixmap = QPixmap.fromImage(img)
        self._page_label.setPixmap(self._base_pixmap)
        self._page_label.resize(self._base_pixmap.size())

        total = self._engine.page_count
        self._lbl_page.setText(f"Page {self._current_page + 1} of {total}")
        self._btn_prev.setEnabled(self._current_page > 0)
        self._btn_next.setEnabled(self._current_page < total - 1)
        pct = int(self._zoom / self.DEFAULT_ZOOM * 100)
        self._lbl_zoom.setText(f"{pct}%")

    def _rebuild_page_matches(self) -> None:
        self._page_matches = {}
        if not self._highlights:
            return
        for kw in self._highlights:
            matches = [
                m
                for m in self._all_results.get(kw, [])
                if m.page_num == self._current_page
            ]
            if matches:
                self._page_matches[kw] = matches

    def _scroll_to_rect(self, rect: fitz.Rect) -> None:
        y = int(rect.y0 * self._zoom) - 80
        self._scroll.verticalScrollBar().setValue(max(y, 0))

    def _clear_pulse(self) -> None:
        self._pulse_rect = None
        self._page_label.update()


    def _prev_page(self) -> None:
        self.show_page(self._current_page - 1)

    def _next_page(self) -> None:
        self.show_page(self._current_page + 1)

    def _zoom_in(self) -> None:
        if self._zoom < self.ZOOM_MAX:
            self._zoom = min(self._zoom + self.ZOOM_STEP, self.ZOOM_MAX)
            self._render()

    def _zoom_out(self) -> None:
        if self._zoom > self.ZOOM_MIN:
            self._zoom = max(self._zoom - self.ZOOM_STEP, self.ZOOM_MIN)
            self._render()
