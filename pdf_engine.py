"""Loads documents with PyMuPDF, searches for keywords, and exports highlighted PDFs."""

from __future__ import annotations

import fitz 

from PyQt6.QtGui import QColor

from ui.colors import export_color


class SearchResult:

    __slots__ = ("page_num", "rect", "snippet")

    def __init__(self, page_num: int, rect: fitz.Rect, snippet: str) -> None:
        self.page_num = page_num
        self.rect = rect
        self.snippet = snippet


class PDFEngine:

    def __init__(self) -> None:
        self._doc: fitz.Document | None = None
        self._path: str | None = None


    def open(self, path: str) -> int:
        self.close()
        self._doc = fitz.open(path)
        self._path = path
        return self._doc.page_count

    def close(self) -> None:
        if self._doc:
            self._doc.close()
            self._doc = None
            self._path = None

    @property
    def page_count(self) -> int:
        return self._doc.page_count if self._doc else 0

    @property
    def is_open(self) -> bool:
        return self._doc is not None


    def render_page(self, page_num: int, zoom: float = 1.5) -> fitz.Pixmap:
        page = self._doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        return page.get_pixmap(matrix=mat, alpha=False)


    def search(self, keywords: list[str]) -> dict[str, list[SearchResult]]:
        results: dict[str, list[SearchResult]] = {kw: [] for kw in keywords}

        for page_num in range(self._doc.page_count):
            page = self._doc[page_num]
            for kw in keywords:
                rects = page.search_for(kw)
                for rect in rects:
                    snippet = self._extract_snippet(page, rect)
                    results[kw].append(SearchResult(page_num, rect, snippet))

        return results


    def export_highlighted(
        self,
        output_path: str,
        results: dict[str, list[SearchResult]],
        color_map: dict[str, QColor],
    ) -> None:
        doc = fitz.open(self._path)
        try:
            for kw, matches in results.items():
                rgb = export_color(color_map[kw])
                for m in matches:
                    page = doc[m.page_num]
                    annot = page.add_highlight_annot(m.rect)
                    annot.set_colors(stroke=rgb)
                    annot.set_opacity(0.45)
                    annot.update()
            doc.save(output_path)
        finally:
            doc.close()


    @staticmethod
    def _extract_snippet(page: fitz.Page, rect: fitz.Rect, context: int = 40) -> str:
        full_text = page.get_text("text")
        clip = page.get_text("text", clip=rect).strip()
        if not clip:
            return ""
        idx = full_text.find(clip)
        if idx == -1:
            return clip
        start = max(0, idx - context)
        end = min(len(full_text), idx + len(clip) + context)
        snippet = full_text[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(full_text):
            snippet = snippet + "..."
        return snippet
