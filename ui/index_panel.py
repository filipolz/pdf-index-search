"""Search index panel. Lists keyword matches in a tree, clicking a hit navigates to that page and location."""

from __future__ import annotations

import fitz

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QPixmap, QIcon
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

from pdf_engine import SearchResult
from ui.colors import opaque


class IndexPanel(QTreeWidget):

    navigate_to = pyqtSignal(int, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["Keyword / Location"])
        self.setMinimumWidth(220)
        self.setIndentation(18)
        self.itemClicked.connect(self._on_item_clicked)

    def populate(
        self,
        results: dict[str, list[SearchResult]],
        color_map: dict[str, QColor],
    ) -> None:
        self.clear()

        for kw, matches in results.items():
            color = color_map.get(kw, QColor(200, 200, 200))
            parent_item = QTreeWidgetItem([f'"{kw}" ({len(matches)})'])
            parent_item.setIcon(0, self._swatch_icon(color))
            parent_item.setFlags(
                parent_item.flags() & ~Qt.ItemFlag.ItemIsSelectable
            )
            self.addTopLevelItem(parent_item)

            for m in matches:
                snippet = m.snippet if len(m.snippet) <= 60 else m.snippet[:57] + "..."
                label = f"p.{m.page_num + 1}: {snippet}"
                child = QTreeWidgetItem([label])
                child.setData(0, Qt.ItemDataRole.UserRole, (m.page_num, m.rect))
                parent_item.addChild(child)

            parent_item.setExpanded(True)

    def clear_results(self) -> None:
        self.clear()


    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is not None:
            page_num, rect = data
            self.navigate_to.emit(page_num, rect)

    @staticmethod
    def _swatch_icon(color: QColor, size: int = 14) -> QIcon:
        pm = QPixmap(size, size)
        pm.fill(opaque(color))
        return QIcon(pm)
