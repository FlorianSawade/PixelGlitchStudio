"""Render a GitHub cover using the existing app logo and real UI screenshot."""
import os
from pathlib import Path
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath
from pixelglitch import branding


def main():
    app = QGuiApplication.instance() or QGuiApplication([])
    image = QImage(1280, 640, QImage.Format_RGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    gradient = QLinearGradient(0, 0, 1280, 640)
    gradient.setColorAt(0, QColor('#14141c'))
    gradient.setColorAt(1, QColor('#292039'))
    painter.fillRect(image.rect(), gradient)
    painter.setPen(QColor('#343041'))
    for y in range(16, 640, 32):
        painter.drawLine(0, y, 1280, y)
    painter.drawPixmap(56, 54, branding.logo_pixmap(84))

    def label(x, y, text, size, color, bold=False):
        font = QFont('Helvetica Neue')
        font.setPixelSize(size)
        font.setBold(bold)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(x, y, text)

    label(56, 233, 'PixelGlitch', 64, '#f2f2f6', True)
    label(56, 308, 'Studio', 64, '#f2f2f6', True)
    label(59, 365, 'Pixel-Sorting & Glitch-Art', 25, '#e457d4')
    label(59, 412, 'Ebenen. Masken. Varianten.', 23, '#c7c2d2')
    label(59, 552, 'macOS  ·  Windows  ·  Linux', 20, '#c7c2d2')
    label(59, 587, 'FlorianSawade / PixelGlitchStudio', 17, '#9e96ad')

    frame = QRectF(542, 94, 682, 452)
    path = QPainterPath()
    path.addRoundedRect(frame, 16, 16)
    painter.fillPath(path, QColor('#18181f'))
    painter.save()
    painter.setClipPath(path)
    shot = QImage(str(ROOT / 'docs/images/screenshot.png'))
    if shot.isNull():
        raise RuntimeError('Generate the README screenshot first')
    painter.drawImage(QRectF(548, 124, 670, 419), shot)
    painter.restore()
    for i, color in enumerate(('#e457d4', '#4fd8e0', '#c7c2d2')):
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(558 + i * 16, 105, 7, 7)
    painter.fillRect(QRectF(56, 468, 88, 4), QColor('#e457d4'))
    painter.fillRect(QRectF(144, 468, 32, 4), QColor('#4fd8e0'))
    painter.end()
    output = ROOT / 'docs/images/social-preview.png'
    if not image.save(str(output)):
        raise RuntimeError('Could not save social preview')
    assert output.stat().st_size < 1_000_000
    print(output)


if __name__ == '__main__':
    main()
