"""Monochromes SVG-Icon-Set (Linienstil), eingefärbt aus den Theme-Tokens."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QSize
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_P = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
      'stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">')

ICONS = {
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M3.5 17l5-5 4 4 3-3 5 5"/>',
    "export": '<path d="M12 3v11"/><path d="M7.5 9.5L12 14l4.5-4.5"/><path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"/>',
    "batch": '<rect x="3" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5"/>',
    "dice": '<rect x="3.5" y="3.5" width="17" height="17" rx="3"/><circle cx="8.3" cy="8.3" r="1.2" fill="{c}" stroke="none"/><circle cx="15.7" cy="8.3" r="1.2" fill="{c}" stroke="none"/><circle cx="12" cy="12" r="1.2" fill="{c}" stroke="none"/><circle cx="8.3" cy="15.7" r="1.2" fill="{c}" stroke="none"/><circle cx="15.7" cy="15.7" r="1.2" fill="{c}" stroke="none"/>',
    "folder": '<path d="M3 7a2 2 0 012-2h4l2 2.5h8a2 2 0 012 2V17a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>',
    "save": '<path d="M5 3h11l5 5v11a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2z"/><path d="M8 3v5h7V3"/><rect x="7.5" y="13" width="9" height="8" rx="1"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "copy": '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>',
    "trash": '<path d="M4 6.5h16"/><path d="M9 6.5V4.8A1.3 1.3 0 0110.3 3.5h3.4A1.3 1.3 0 0115 4.8v1.7"/><path d="M6 6.5l1 13a2 2 0 002 1.9h6a2 2 0 002-1.9l1-13"/><path d="M10 11v5.5M14 11v5.5"/>',
    "up": '<path d="M12 19V5"/><path d="M6 11l6-6 6 6"/>',
    "down": '<path d="M12 5v14"/><path d="M6 13l6 6 6-6"/>',
    "eye": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    "eye_off": '<path d="M4 4l16 16"/><path d="M10.6 6c.46-.07.93-.1 1.4-.1 6 0 9.5 6.1 9.5 6.1a17 17 0 01-2.7 3.4M6.6 6.9A16.6 16.6 0 002.5 12S6 18.1 12 18.1c1.2 0 2.3-.2 3.3-.6"/><path d="M9.9 9.9a3 3 0 104.2 4.2"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3.6 12.5L12 17l8.4-4.5"/><path d="M3.6 16.5L12 21l8.4-4.5"/>',
    "mask": '<circle cx="12" cy="12" r="8.5" stroke-dasharray="3.6 3.4"/><circle cx="12" cy="12" r="3.6"/>',
    "overlay": '<path d="M3 8V5a2 2 0 012-2h3M16 3h3a2 2 0 012 2v3M21 16v3a2 2 0 01-2 2h-3M8 21H5a2 2 0 01-2-2v-3"/><circle cx="12" cy="12" r="3.4"/>',
    "fit": '<path d="M8 3H5a2 2 0 00-2 2v3M16 3h3a2 2 0 012 2v3M21 16v3a2 2 0 01-2 2h-3M3 16v3a2 2 0 002 2h3"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "chev_right": '<path d="M9 5l7 7-7 7"/>',
    "chev_down": '<path d="M5 9l7 7 7-7"/>',
    "bolt": '<path d="M13 2L4.5 13.5H11L10 22l8.5-11.5H12z"/>',
}

_cache: dict = {}


def icon(name: str, color: str, size: int = 20) -> QIcon:
    """Icon mit 1x- und 2x-Variante (beide DPR 1) – Qt wählt je Display die
    passende Auflösung; vermeidet Doppelskalierung von DPR-2-Pixmaps."""
    key = (name, color, size)
    if key in _cache:
        return _cache[key]
    svg = _P.format(c=color) + ICONS[name].replace("{c}", color) + "</svg>"
    renderer = QSvgRenderer(svg.encode())
    ic = QIcon()
    for s in (size, size * 2):
        img = QImage(s, s, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        renderer.render(p, QRectF(0, 0, s, s))
        p.end()
        ic.addPixmap(QPixmap.fromImage(img))
    _cache[key] = ic
    return ic


def clear_cache():
    _cache.clear()
