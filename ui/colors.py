"""Highlight colors — assigns a distinct color per keyword and converts colors for display and PDF export."""

from PyQt6.QtGui import QColor

_PALETTE = [
    QColor(255, 235, 59, 100),
    QColor(76, 175, 80, 100),
    QColor(33, 150, 243, 100),
    QColor(244, 67, 54, 100),
    QColor(156, 39, 176, 100),
    QColor(255, 152, 0, 100),
    QColor(0, 188, 212, 100),
    QColor(233, 30, 99, 100),
    QColor(139, 195, 74, 100),
    QColor(121, 85, 72, 100),
    QColor(63, 81, 181, 100),
    QColor(255, 87, 34, 100),
    QColor(0, 150, 136, 100),
    QColor(103, 58, 183, 100),
    QColor(205, 220, 57, 100),
    QColor(158, 158, 158, 100),
]


def assign_colors(keywords: list[str]) -> dict[str, QColor]:
    mapping: dict[str, QColor] = {}
    for i, kw in enumerate(keywords):
        base = _PALETTE[i % len(_PALETTE)]
        if i >= len(_PALETTE):
            shift = 40 * ((i // len(_PALETTE)) % 3) + 30
            color = QColor(base.red(), base.green(), base.blue(), min(base.alpha() + shift, 200))
        else:
            color = QColor(base)
        mapping[kw] = color
    return mapping

def opaque(color: QColor) -> QColor:
    return QColor(color.red(), color.green(), color.blue(), 255)

def export_color(color: QColor) -> tuple[float, float, float]:
    return (color.redF(), color.greenF(), color.blueF())
