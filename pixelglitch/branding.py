"""Branding: prozedural gezeichnetes Logo und Splash-Screen.

Das Logo wird zur Laufzeit mit QPainter erzeugt (keine Binär-Assets):
ein "PG"-Glyph mit RGB-versetzten Echos und horizontalen Glitch-Slices,
abgestimmt auf den Magenta-Akzent des Themes.
"""
from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QLinearGradient, QPainter,
                           QPainterPath, QPixmap)

AUTHOR = "Florian Sawade"
COPYRIGHT = f"© 2026 {AUTHOR} · Konzept, Design & Entwicklung"

ACCENT = QColor("#e457d4")
CYAN = QColor("#4fd8e0")
BG = QColor("#17171c")
FG = QColor("#f2f2f6")


def _glyph_font(px: int) -> QFont:
    f = QFont()
    f.setPixelSize(px)
    f.setWeight(QFont.Black)
    f.setStyleHint(QFont.SansSerif)
    return f


def logo_pixmap(size: int = 128) -> QPixmap:
    """App-Logo: abgerundetes Quadrat, "PG" mit Chromatik-Echo und Slices."""
    dpr = 2
    s = size * dpr
    pm = QPixmap(s, s)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)

    # Hintergrund mit dezentem Verlauf
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, s, s), s * 0.22, s * 0.22)
    grad = QLinearGradient(0, 0, s, s)
    grad.setColorAt(0.0, QColor("#1d1d24"))
    grad.setColorAt(1.0, QColor("#121216"))
    p.fillPath(path, grad)
    p.setClipPath(path)

    font = _glyph_font(int(s * 0.52))
    p.setFont(font)
    rect = QRect(0, int(-s * 0.02), s, s)
    off = int(s * 0.028)

    # Chromatik-Echos, dann Hauptglyph
    p.setPen(CYAN)
    p.drawText(rect.translated(off, off), Qt.AlignCenter, "PG")
    p.setPen(ACCENT)
    p.drawText(rect.translated(-off, -off), Qt.AlignCenter, "PG")
    p.setPen(FG)
    p.drawText(rect, Qt.AlignCenter, "PG")

    # Glitch-Slices: zwei Bänder des Glyphen horizontal versetzt
    for y_frac, h_frac, dx in ((0.30, 0.075, int(s * 0.075)),
                               (0.62, 0.055, -int(s * 0.06))):
        y, h = int(s * y_frac), int(s * h_frac)
        band = pm.copy(0, y, s, h)
        p.fillRect(0, y, s, h, QColor("#17171c"))
        p.drawPixmap(dx, y, band)

    # Akzentlinie unten
    p.setClipping(False)
    p.setPen(Qt.NoPen)
    p.setBrush(ACCENT)
    p.drawRoundedRect(QRectF(s * 0.30, s * 0.86, s * 0.40, s * 0.045),
                      s * 0.02, s * 0.02)
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def splash_pixmap(version: str) -> QPixmap:
    """Splash: Logo, Name, Version, Tagline."""
    dpr = 2
    w, h = 460 * dpr, 260 * dpr
    pm = QPixmap(w, h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)

    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, w, h), 14 * dpr, 14 * dpr)
    p.fillPath(path, BG)
    p.setClipPath(path)

    logo = logo_pixmap(96)
    p.drawPixmap(int((w - 96 * dpr) / 2), 26 * dpr, logo)

    f = QFont(); f.setPixelSize(21 * dpr); f.setWeight(QFont.DemiBold)
    p.setFont(f)
    p.setPen(FG)
    p.drawText(QRect(0, 132 * dpr, w, 30 * dpr), Qt.AlignHCenter,
               "PixelGlitch Studio")

    f = QFont(); f.setPixelSize(12 * dpr)
    p.setFont(f)
    p.setPen(QColor("#9698a3"))
    p.drawText(QRect(0, 163 * dpr, w, 20 * dpr), Qt.AlignHCenter,
               f"Version {version}  ·  Pixel-Sorting & Glitch-Art")
    p.drawText(QRect(0, 226 * dpr, w, 20 * dpr), Qt.AlignHCenter,
               "Python · PySide6 · NumPy · Pillow")

    p.setPen(Qt.NoPen)
    p.setBrush(ACCENT)
    p.drawRect(QRectF(0, h - 4 * dpr, w, 4 * dpr))
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm
