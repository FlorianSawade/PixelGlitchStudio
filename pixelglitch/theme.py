"""Theme: semantische Farbtokens (hell/dunkel), QSS-Generierung, System-Folge.

Der Hell/Dunkel-Wechsel ist ein Austausch der Token-Werte – es gibt genau ein
Stylesheet-Template. Die Canvas-Fläche bleibt in beiden Themes dunkelneutral,
damit der Bildeindruck (Kontrast, Leuchtkraft) nicht verfälscht wird.
"""
from __future__ import annotations

from string import Template

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette, QGuiApplication

# ---------------------------------------------------------------- tokens

DARK = {
    "warn": "#e0a04f",
    "canvas":        "#131316",   # Arbeitsfläche hinter dem Bild
    "panel":         "#1e1e23",   # Panels, Fensterhintergrund
    "panel_alt":     "#26262c",   # abgesetzte Flächen (Listen, Abschnitte)
    "input":         "#2e2e35",   # Eingabefelder, Buttons
    "input_hover":   "#36363e",
    "border":        "#3a3a42",
    "border_soft":   "#2c2c33",
    "text":          "#ebebf0",
    "text_dim":      "#9698a3",
    "accent":        "#e457d4",   # Magenta – dunkles Theme: hell & kräftig
    "accent_hover":  "#ef70e0",
    "accent_soft":   "rgba(228, 87, 212, 0.16)",   # Flächen (Auswahl)
    "accent_border": "rgba(228, 87, 212, 0.55)",
    "on_accent":     "#17171a",
    "scroll":        "#3d3d46",
    "scroll_hover":  "#4a4a55",
}

LIGHT = {
    "warn": "#b06a10",
    "canvas":        "#2a2a2f",   # bewusst dunkel auch im hellen Theme
    "panel":         "#f2f2f5",
    "panel_alt":     "#e9e9ee",
    "input":         "#ffffff",
    "input_hover":   "#f7f7fb",
    "border":        "#d4d4dc",
    "border_soft":   "#e2e2e9",
    "text":          "#242429",
    "text_dim":      "#70707c",
    "accent":        "#a2249e",   # Magenta – helles Theme: dunkler, weniger gesättigt
    "accent_hover":  "#8d1f8a",
    "accent_soft":   "rgba(162, 36, 158, 0.12)",
    "accent_border": "rgba(162, 36, 158, 0.45)",
    "on_accent":     "#ffffff",
    "scroll":        "#c8c8d2",
    "scroll_hover":  "#b4b4c0",
}

_QSS = Template("""
QMainWindow, QDialog { background: $panel; }
QWidget { color: $text; font-size: 13px; }
QToolTip { background: $panel_alt; color: $text; border: 1px solid $border;
           padding: 4px 8px; }

/* ---- Buttons ---- */
QPushButton, QToolButton {
    background: $input; color: $text;
    border: 1px solid $border; border-radius: 6px;
    padding: 5px 12px;
}
QPushButton:hover, QToolButton:hover { background: $input_hover; }
QPushButton:pressed, QToolButton:pressed { background: $panel_alt; }
QPushButton:disabled, QToolButton:disabled { color: $text_dim; background: $panel_alt; }
QPushButton:default { border-color: $accent_border; }
QToolButton:checked {
    background: $accent_soft; border-color: $accent_border; color: $accent;
}
QPushButton[accent="true"] {
    background: $accent; color: $on_accent; border: none; font-weight: 600;
}
QPushButton[accent="true"]:hover { background: $accent_hover; }
QToolButton[flat="true"] { border: none; background: transparent; padding: 4px; }
QToolButton[flat="true"]:hover { background: $input_hover; border-radius: 5px; }
QToolButton[flat="true"]:checked { background: $accent_soft; color: $accent; }

/* ---- Toolbar ---- */
QToolBar {
    background: $panel; border: none; border-bottom: 1px solid $border_soft;
    padding: 5px 8px; spacing: 4px;
}
QToolBar QToolButton { border: none; background: transparent; padding: 5px 9px; }
QToolBar QToolButton:hover { background: $input_hover; border-radius: 6px; }
QToolBar QToolButton:checked { background: $accent_soft; color: $accent; border-radius: 6px; }
QToolBar::separator { background: $border_soft; width: 1px; margin: 5px 6px; }

/* ---- Inputs ---- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: $input; border: 1px solid $border; border-radius: 6px;
    padding: 4px 8px; selection-background-color: $accent;
    selection-color: $on_accent;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: $accent_border;
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow {
    image: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid $text_dim; margin-right: 7px;
}
QComboBox QAbstractItemView {
    background: $panel_alt; border: 1px solid $border; border-radius: 6px;
    selection-background-color: $accent_soft; selection-color: $text;
    outline: none; padding: 3px;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: transparent; border: none; width: 16px;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    border-left: 3px solid transparent; border-right: 3px solid transparent;
    border-bottom: 4px solid $text_dim;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    border-left: 3px solid transparent; border-right: 3px solid transparent;
    border-top: 4px solid $text_dim;
}
QCheckBox { spacing: 7px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid $border; border-radius: 4px;
    background: $input;
}
QCheckBox::indicator:hover { border-color: $accent_border; }
QCheckBox::indicator:checked { background: $accent; border-color: $accent; }

/* ---- Slider ---- */
QSlider::groove:horizontal {
    height: 4px; background: $border; border-radius: 2px;
}
QSlider::sub-page:horizontal { background: $accent; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 14px; height: 14px; margin: -5px 0;
    background: $text; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: $accent_hover; }

/* ---- Lists / Tabs ---- */
QListWidget {
    background: $panel_alt; border: 1px solid $border_soft; border-radius: 8px;
    padding: 4px; outline: none;
}
QListWidget::item { border-radius: 6px; padding: 2px; margin: 1px 0; }
QListWidget::item:hover { background: $input_hover; }
QListWidget::item:selected { background: $accent_soft; }
QTabWidget::pane { border: none; }
QTabBar::tab {
    background: transparent; color: $text_dim; padding: 7px 16px;
    border: none; border-bottom: 2px solid transparent; font-weight: 600;
}
QTabBar::tab:hover { color: $text; }
QTabBar::tab:selected { color: $accent; border-bottom: 2px solid $accent; }

/* ---- Scrollbars ---- */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical {
    background: $scroll; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: $scroll_hover; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: $scroll; border-radius: 4px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: $scroll_hover; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ---- Misc ---- */
QSplitter::handle { background: $border_soft; }
QSplitter::handle:horizontal { width: 1px; }
QStatusBar {
    background: $panel; border-top: 1px solid $border_soft; color: $text_dim;
}
QStatusBar::item { border: none; }
QMenu {
    background: $panel_alt; border: 1px solid $border; border-radius: 8px; padding: 5px;
}
QMenu::item { padding: 6px 24px 6px 12px; border-radius: 5px; }
QMenu::item:selected { background: $accent_soft; color: $text; }
QMenu::separator { height: 1px; background: $border_soft; margin: 5px 8px; }
QMenuBar { background: $panel; border-bottom: 1px solid $border_soft; }
QMenuBar::item { padding: 5px 10px; border-radius: 5px; }
QMenuBar::item:selected { background: $input_hover; }
QProgressBar {
    background: $panel_alt; border: 1px solid $border; border-radius: 6px;
    text-align: center; color: $text; height: 18px;
}
QProgressBar::chunk { background: $accent; border-radius: 5px; }
QLabel[role="hint"] { color: $text_dim; font-size: 12px; }
QLabel[role="section"] { color: $text_dim; font-size: 11px; font-weight: 700;
                          letter-spacing: 1px; }
QFrame[role="card"] {
    background: $panel_alt; border: 1px solid $border_soft; border-radius: 8px;
}
""")


def system_scheme() -> str:
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Light:
            return "light"
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
    except Exception:
        pass
    return "dark"  # Fallback: dunkel ist für Bildbearbeitung die sichere Wahl


def tokens(scheme: str) -> dict:
    return LIGHT if scheme == "light" else DARK


def apply_theme(app, scheme: str | None = None) -> dict:
    """Fusion-Style + Palette + generiertes QSS anwenden. Gibt Tokens zurück."""
    scheme = scheme or system_scheme()
    t = tokens(scheme)
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(t["panel"]))
    pal.setColor(QPalette.WindowText, QColor(t["text"]))
    pal.setColor(QPalette.Base, QColor(t["input"]))
    pal.setColor(QPalette.AlternateBase, QColor(t["panel_alt"]))
    pal.setColor(QPalette.Text, QColor(t["text"]))
    pal.setColor(QPalette.Button, QColor(t["input"]))
    pal.setColor(QPalette.ButtonText, QColor(t["text"]))
    pal.setColor(QPalette.Highlight, QColor(t["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor(t["on_accent"]))
    pal.setColor(QPalette.PlaceholderText, QColor(t["text_dim"]))
    pal.setColor(QPalette.ToolTipBase, QColor(t["panel_alt"]))
    pal.setColor(QPalette.ToolTipText, QColor(t["text"]))
    app.setPalette(pal)
    app.setStyleSheet(_QSS.substitute(t))
    return t


def watch_system(app, callback):
    """callback('dark'|'light') bei System-Umschaltung – live, ohne Neustart."""
    try:
        app.styleHints().colorSchemeChanged.connect(
            lambda *_: callback(system_scheme()))
    except Exception:
        pass
