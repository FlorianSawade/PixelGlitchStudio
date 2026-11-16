"""PySide6-Oberfläche: Hauptfenster, Ebenen- und Masken-Tab, Batch-Dialog."""
from __future__ import annotations

import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
from PySide6.QtCore import (QSettings, QSize, QStandardPaths, Qt, QThread, QTimer, Signal)
from PySide6.QtGui import (QAction, QActionGroup, QIcon, QImage, QImageReader, QPixmap)
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDoubleSpinBox,
                               QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow, QMenu,
                               QMessageBox, QProgressBar, QPushButton,
                               QScrollArea, QSpinBox, QSplitter, QTabWidget,
                               QToolBar, QToolButton, QVBoxLayout, QWidget,
                               QGridLayout, QSizePolicy, QInputDialog, QCheckBox,
                               QDockWidget)

from . import branding, engine, icons, presets, theme
from . import __version__
from .engine import Layer, Project
from .masks import MASK_KINDS, MASK_KIND_LABELS, Mask
from .params import EFFECTS, random_value
from .widgets import (Canvas, CollapsibleSection, GalleryPanel,
                      LayerItemWidget,
                      MaskChainEditor, ParamEditor)

PREVIEW_FAST = 1000
IMG_FILTER = "Bilder (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)"
PROJ_FILTER_OPEN = "PixelGlitch-Projekte (*.pgsz *.pgs.json *.json)"
PROJ_FILTER_SAVE = "PixelGlitch-Projekt mit Bild (*.pgsz);;Nur Einstellungen (*.pgs.json)"
RECENT_MAX = 12


def projects_dir() -> Path:
    """Standard-Projektordner (Dokumente/PixelGlitchProjects), per Setting änderbar."""
    s = QSettings("PixelGlitch", "Studio")
    docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation) \
        or str(Path.home())
    d = Path(s.value("projects_dir", "") or (Path(docs) / "PixelGlitchProjects"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def set_projects_dir(path: str):
    QSettings("PixelGlitch", "Studio").setValue("projects_dir", path)


def scan_projects(folder: Path) -> list:
    """Projektdateien im Ordner, neueste zuerst."""
    files = list(folder.glob("*.pgsz")) + list(folder.glob("*.pgs.json"))
    return [str(p) for p in sorted(files, key=lambda p: p.stat().st_mtime,
                                   reverse=True)]


# ================================================================ batch

class BatchWorker(QThread):
    progressed = Signal(int, int)
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, project, source, count, seed, outdir, fmt, stem,
                 quality=95, max_size=None):
        super().__init__()
        self.args = (project, source, count, seed, outdir, fmt, stem,
                     quality, max_size)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        (project, source, count, seed, outdir, fmt, stem,
         quality, max_size) = self.args
        try:
            def cb(i, n):
                self.progressed.emit(i, n)
                return not self._stop
            files = engine.run_batch(project, source, count, seed, outdir,
                                     fmt, stem, quality, max_size, progress=cb)
            self.finished_ok.emit(files)
        except Exception as e:  # pragma: no cover
            self.failed.emit(str(e))


class BatchGalleryPanel(QWidget):
    """Massengenerierung und Ergebnis-Galerie in einem Panel.

    Links die Einstellungen samt Lauf (einklappbar), rechts die Kacheln des
    beobachteten Ausgabeordners. Nicht modal: Der Lauf arbeitet auf einem
    eingefrorenen Projekt-Schnappschuss, damit Änderungen während des Laufs
    die restlichen Varianten nicht verfälschen.
    """

    SETTINGS_W = 372

    def __init__(self, win, tokens: dict, folder: str = "", parent=None):
        super().__init__(parent)
        self.win = win
        self.tokens = tokens
        self.worker = None
        self.run_index = {}          # pfad -> (seed, projekt-schnappschuss)
        self.last_outdir = ""
        self._snapshot = None
        self._start_seed = 0
        s = QSettings("PixelGlitch", "Studio")

        # ---------------- linke Spalte: Einstellungen + Lauf
        self.count = QSpinBox(); self.count.setRange(1, 5000)
        self.count.setValue(int(s.value("batch/count", 20)))
        self.seed = QSpinBox(); self.seed.setRange(0, 10**9)
        self.seed.setValue(int(s.value("batch/seed", 1000)))
        self.stem = QLineEdit(s.value("batch/stem", "") or "glitch")
        self.fmt = QComboBox(); self.fmt.addItems(["png", "jpg"])
        self.fmt.setCurrentText(s.value("batch/fmt", "png"))
        self.quality = QSpinBox(); self.quality.setRange(1, 100)
        self.quality.setSuffix(" %")
        self.quality.setValue(int(s.value("batch/quality", 90)))
        self.quality_label = QLabel("JPG-Qualität")
        self.fmt.currentTextChanged.connect(self._sync_quality_row)
        self.fast = QCheckBox("Schnell (Vorschaugröße)")
        self.fast.setToolTip("Rendert die Varianten verkleinert und legt sie "
                             "in den Unterordner »vorschau«.")
        self.fast.setChecked(s.value("batch/fast", "false") in (True, "true", "1"))
        self.outdir = QLineEdit(s.value("batch/outdir", str(projects_dir())))
        browse = QToolButton()
        browse.setIcon(icons.icon("folder", tokens["text"], 15))
        browse.setToolTip("Ausgabeordner wählen")
        browse.setIconSize(QSize(16, 16))
        browse.setStyleSheet("padding: 0px;")     # sonst quetscht das Button-Padding
        browse.setFixedSize(30, 26)
        browse.clicked.connect(self._browse)
        outrow = QHBoxLayout(); outrow.addWidget(self.outdir, 1); outrow.addWidget(browse)
        for f in (self.count, self.seed, self.stem, self.fmt, self.quality,
                  self.outdir):
            f.setMinimumWidth(70)
            f.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        grid = QGridLayout()
        grid.setVerticalSpacing(7)
        grid.setColumnStretch(1, 1)
        for r, (label, wdg) in enumerate([("Anzahl Varianten", self.count),
                                          ("Start-Seed", self.seed),
                                          ("Präfix", self.stem),
                                          ("Format", self.fmt)]):
            grid.addWidget(QLabel(label), r, 0)
            grid.addWidget(wdg, r, 1)
        grid.addWidget(self.quality_label, 4, 0)
        grid.addWidget(self.quality, 4, 1)
        self._sync_quality_row(self.fmt.currentText())
        grid.addWidget(QLabel("Ausgabeordner"), 5, 0)
        grid.addLayout(outrow, 5, 1)
        grid.addWidget(self.fast, 6, 1)

        layers_label = QLabel("GEWÜRFELTE EBENEN")
        layers_label.setProperty("role", "section")
        self.layers_box = QVBoxLayout()
        self.layers_box.setSpacing(3)
        self.layer_checks = []

        hint = QLabel("🎲-markierte Parameter werden je Variante gewürfelt.")
        hint.setToolTip("Der Seed steht als Suffix im Dateinamen – darüber ist "
                        "jedes Ergebnis reproduzierbar.")
        hint.setWordWrap(True)
        hint.setProperty("role", "hint")

        self.bar = QProgressBar(); self.bar.setValue(0); self.bar.hide()
        self.run_btn = QPushButton("Generieren")
        self.run_btn.setProperty("accent", True)
        self.run_btn.clicked.connect(self._run)
        self.stop_btn = QPushButton("Abbrechen")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.hide()
        runrow = QHBoxLayout()
        runrow.addWidget(self.run_btn, 1)
        runrow.addWidget(self.stop_btn)

        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 0, 6, 0)
        col.setSpacing(8)
        head = QLabel("MASSENGENERIERUNG")
        head.setProperty("role", "section")
        col.addWidget(head)
        col.addLayout(grid)
        col.addWidget(layers_label)
        col.addLayout(self.layers_box)
        col.addWidget(hint)
        col.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.settings_col = QWidget()
        sc = QVBoxLayout(self.settings_col)
        sc.setContentsMargins(0, 0, 0, 0)
        sc.setSpacing(6)
        sc.addWidget(scroll, 1)
        sc.addWidget(self.bar)          # Fortschritt und Lauf bleiben sichtbar
        sc.addLayout(runrow)
        self.settings_col.setFixedWidth(self.SETTINGS_W)

        self.collapse_btn = QToolButton()
        self.collapse_btn.setCheckable(True)
        self.collapse_btn.setToolTip("Einstellungen ein-/ausklappen")
        self.collapse_btn.setFixedWidth(16)
        self.collapse_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.collapse_btn.toggled.connect(self._toggle_settings)
        self._sync_collapse_text()

        # ---------------- rechte Spalte: Galerie
        self.gallery = GalleryPanel(tokens, folder)
        self.gallery.fileActivated.connect(self.win.preview_file)
        self.gallery.openAsSource.connect(self.win._load_path)
        self.gallery.adoptRequested.connect(self.adopt_file)
        self.gallery.grid.currentItemChanged.connect(
            lambda cur, _p: self._sync_adopt(cur))

        self.adopt_btn = QPushButton("Variante übernehmen")
        self.adopt_btn.setProperty("accent", True)
        self.adopt_btn.setEnabled(False)
        self.adopt_btn.setToolTip(
            "Schreibt die gewürfelten Werte dieser Variante ins Projekt.")
        self.adopt_btn.clicked.connect(
            lambda: self.adopt_file(self.gallery.current_path()))
        self.gallery.head_row.addWidget(self.adopt_btn)
        self.stem.textChanged.connect(
            lambda s: self.gallery.set_project_prefix(engine.safe_stem(s)))
        self.gallery.set_project_prefix(engine.safe_stem(self.stem.text()))

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)
        lay.addWidget(self.settings_col)
        lay.addWidget(self.collapse_btn)
        lay.addWidget(self.gallery, 1)

        self.refresh_layers()

    # ------------------------------------------------------------- ui
    def set_tokens(self, tokens: dict):
        self.tokens = tokens
        self.gallery.set_tokens(tokens)

    def _sync_collapse_text(self):
        self.collapse_btn.setText("›" if self.collapse_btn.isChecked() else "‹")

    def _toggle_settings(self, collapsed: bool):
        self.settings_col.setVisible(not collapsed)
        self._sync_collapse_text()

    def _sync_quality_row(self, fmt: str):
        show = fmt == "jpg"
        self.quality_label.setVisible(show)
        self.quality.setVisible(show)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Ausgabeordner",
                                             self.outdir.text())
        if d:
            self.outdir.setText(d)

    def refresh_layers(self):
        """Ebenen-Auswahl neu aufbauen (das Projekt kann sich jederzeit ändern)."""
        while self.layers_box.count():
            item = self.layers_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)       # sofort weg, nicht erst beim Aufräumen
                w.deleteLater()
        self.layer_checks = []
        for ly in self.win.project.layers:
            if not ly.enabled:
                continue
            n = len([k for k in ly.rand_keys
                     if k in {sp.key for sp in EFFECTS[ly.effect].params}])
            cb = QCheckBox(f"{ly.label} · {n} 🎲" if n
                           else f"{ly.label} · ohne 🎲")
            cb.setToolTip(f"{n} markierte Parameter" if n else
                          "Für diese Ebene ist kein Parameter zum Würfeln "
                          "markiert.")
            cb.setChecked(ly.rand_enabled)
            cb.setEnabled(n > 0)
            cb.toggled.connect(lambda on, l=ly: setattr(l, "rand_enabled", on))
            self.layers_box.addWidget(cb)
            self.layer_checks.append(cb)
        if not self.layer_checks:
            lbl = QLabel("Keine aktiven Effekt-Ebenen im Projekt.")
            lbl.setProperty("role", "hint")
            self.layers_box.addWidget(lbl)

    def _sync_adopt(self, item):
        path = item.data(Qt.UserRole) if item is not None else ""
        self.adopt_btn.setEnabled(bool(path) and self.seed_of(path) is not None)

    # ---------------------------------------------------------- laufen
    def _save_settings(self):
        s = QSettings("PixelGlitch", "Studio")
        s.setValue("batch/count", self.count.value())
        s.setValue("batch/seed", self.seed.value())
        s.setValue("batch/stem", self.stem.text())
        s.setValue("batch/fmt", self.fmt.currentText())
        s.setValue("batch/quality", self.quality.value())
        s.setValue("batch/outdir", self.outdir.text())
        s.setValue("batch/fast", self.fast.isChecked())

    def _run(self):
        if self.win.source is None:
            QMessageBox.information(self.win, "Kein Bild", "Zuerst ein Bild laden.")
            return
        if not engine.active_rand_keys(self.win.project):
            ret = QMessageBox.question(
                self.win, "Keine 🎲-Parameter markiert",
                "Es ist kein Parameter zum Würfeln markiert – alle Varianten "
                "werden mit identischen Einstellungen gerendert und können "
                "gleich aussehen (nur zufallsbasierte Effekte wie Rauschen "
                "oder Byte-Glitch variieren über den Seed).\n\n"
                "Markiere Parameter über den 🎲-Knopf neben dem Regler.\n"
                "Trotzdem generieren?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        self._save_settings()
        outdir = self.outdir.text()
        max_size = None
        if self.fast.isChecked():
            outdir = str(Path(outdir) / "vorschau")
            max_size = PREVIEW_FAST
        self.last_outdir = outdir
        # Schnappschuss: Änderungen am Projekt beeinflussen den Lauf nicht mehr
        self._snapshot = Project.from_json(self.win.project.to_json())
        self._start_seed = self.seed.value()

        self.run_btn.setEnabled(False)
        self.stop_btn.show()
        self.bar.setMaximum(self.count.value())
        self.bar.setValue(0)
        self.bar.show()
        self.worker = BatchWorker(self._snapshot, self.win.source,
                                  self.count.value(), self._start_seed, outdir,
                                  self.fmt.currentText(),
                                  self.stem.text() or "glitch",
                                  self.quality.value(), max_size)
        self.worker.progressed.connect(self._progress)
        self.worker.finished_ok.connect(self._done)
        self.worker.failed.connect(self._fail)
        self.worker.start()

    def _progress(self, i: int, n: int):
        self.bar.setValue(i)
        self.win.status_msg.setText(f"Batch läuft: {i} / {n}")

    def _stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.win.status_msg.setText("Batch wird abgebrochen …")

    def _finish_ui(self):
        self.run_btn.setEnabled(True)
        self.stop_btn.hide()
        self.bar.hide()

    def _done(self, files):
        self._finish_ui()
        snap = self._snapshot.to_json() if self._snapshot else None
        for i, f in enumerate(files):
            self.run_index[str(Path(f).resolve())] = (self._start_seed + i, snap)
        if files:
            QSettings("PixelGlitch", "Studio").setValue("gallery/dir",
                                                        self.last_outdir)
            self.gallery.set_folder(self.last_outdir)
            self.gallery.grid.setCurrentRow(0)
        self.win.status_msg.setText(
            f"Batch fertig: {len(files)} Varianten in {self.last_outdir}")

    def _fail(self, msg):
        self._finish_ui()
        QMessageBox.warning(self.win, "Fehler", msg)

    # -------------------------------------------------------- übernehmen
    def seed_of(self, path: str):
        """Seed aus dem Lauf dieser Sitzung – sonst aus dem Dateinamen."""
        if not path:
            return None
        key = str(Path(path).resolve())
        if key in self.run_index:
            return self.run_index[key][0]
        tail = Path(path).stem.rsplit("_", 1)[-1]
        return int(tail) if tail.isdigit() else None

    def adopt_file(self, path: str):
        seed = self.seed_of(path)
        if seed is None:
            QMessageBox.information(
                self.win, "Kein Seed erkennbar",
                "Zu dieser Datei lässt sich kein Seed ermitteln. Übernehmen "
                "funktioniert für Batch-Ergebnisse, deren Seed im Dateinamen "
                "steht.")
            return
        entry = self.run_index.get(str(Path(path).resolve()))
        if entry is None or entry[1] is None:
            self.win.adopt_variant(seed, note=(
                "Datei stammt nicht aus dem Lauf dieser Sitzung – die Werte "
                "stimmen nur, wenn das Projekt seither unverändert ist."))
            return
        snapshot = Project.from_json(entry[1])
        same = ([(l.id, l.effect) for l in snapshot.layers]
                == [(l.id, l.effect) for l in self.win.project.layers])
        if same:
            self.win.adopt_variant(seed)
            return
        ret = QMessageBox.question(
            self.win, "Projekt hat sich geändert",
            "Der Ebenenstapel unterscheidet sich von dem, mit dem diese "
            "Variante erzeugt wurde.\n\nStapel und Masken des damaligen Laufs "
            "wiederherstellen?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if ret == QMessageBox.Yes:
            self.win.restore_variant(snapshot, seed)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PixelGlitch Studio")
        self.resize(1280, 800)
        self.settings = QSettings("PixelGlitch", "Studio")

        self.project = Project()
        self.source: np.ndarray | None = None
        self.source_path = ""
        self.source_bytes: bytes | None = None
        self.source_name = ""
        self.project_path = ""
        self.project_name = ""
        self.preview: np.ndarray | None = None
        self.seed = 1
        self.fast = True
        self._icon_bindings: list = []

        app = QApplication.instance()
        pref = self.settings.value("theme", "system")
        self.tokens = theme.apply_theme(app, self._resolve_scheme(pref))
        theme.watch_system(app, self._system_changed)

        self._mark_saved()
        self._build_ui()
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(120)
        self._render_timer.timeout.connect(self._render_now)
        self._refresh_layer_list()
        self._refresh_mask_list()
        self.status_msg.setText("Bereit – Bild laden, Masken anlegen, Effekte stapeln.")

    # ---------------------------------------------------------- dirty state

    def _mark_saved(self):
        """Aktuellen Projektstand als „gespeichert" merken."""
        import json as _json
        self._saved_state = _json.dumps(self.project.to_json(), sort_keys=True)

    def _is_dirty(self) -> bool:
        import json as _json
        return (_json.dumps(self.project.to_json(), sort_keys=True)
                != self._saved_state)

    def _confirm_discard(self, verb: str) -> bool:
        """True = fortfahren. Fragt bei ungespeicherten Änderungen nach."""
        if not self._is_dirty():
            return True
        ret = QMessageBox.question(
            self, "Ungespeicherte Änderungen",
            f"Das Projekt enthält ungespeicherte Änderungen.\n"
            f"Vor dem {verb} speichern?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save)
        if ret == QMessageBox.Cancel:
            return False
        if ret == QMessageBox.Save:
            return self._save_project()
        return True

    def _sync_project_stem(self):
        """Batch-Präfix (und damit den Galerie-Filter) an das Projekt binden.

        Ein selbst eingetragenes Präfix bleibt unangetastet – überschrieben
        wird nur, was zuvor automatisch gesetzt wurde.
        """
        if not hasattr(self, "batch_panel"):
            return
        name = self.project_name or Path(self.source_path).stem
        if not name:
            return
        current = self.batch_panel.stem.text().strip()
        if current and current != getattr(self, "_auto_stem", ""):
            return                      # vom Benutzer angepasst
        self._auto_stem = name
        self.batch_panel.stem.setText(name)

    def _update_title(self):
        base = "PixelGlitch Studio"
        name = self.project_name
        dirty = "• " if self._is_dirty() else ""
        self.setWindowTitle(f"{dirty}{base} – {name}" if name
                            else f"{dirty}{base}")
        if hasattr(self, "status_proj"):
            self.status_proj.setText(f"Projekt: {name or '–'}")

    def _update_counts(self):
        if hasattr(self, "status_counts"):
            self.status_counts.setText(
                f"Ebenen: {len(self.project.layers)}   "
                f"Masken: {len(self.project.masks)}")

    def _new_project(self, name: str):
        if not self._confirm_discard("Anlegen"):
            return
        self._reset_workspace()
        self.project_name = name
        self._update_title()
        self._sync_project_stem()
        self.status_msg.setText(f"Neues Projekt: {name}")

    def _close_project(self):
        if not self._confirm_discard("Schließen"):
            return
        self._reset_workspace()
        self.status_msg.setText("Projekt geschlossen.")

    def _reset_workspace(self):
        self.project = Project()
        self.source = None
        self.source_path = ""
        self.source_bytes = None
        self.source_name = ""
        self.project_path = ""
        self.project_name = ""
        self.preview = None
        self.canvas.set_image(None)
        self.canvas.clear_poly_markers()
        self._mark_saved()
        self._update_title()
        self._refresh_layer_list()
        self._refresh_mask_list()
        self._rebuild_settings()
        self._rebuild_mask_editor()
        self.status_size.setText("–")
        self.status_time.setText("")

    def closeEvent(self, ev):
        if self._confirm_discard("Beenden"):
            ev.accept()
        else:
            ev.ignore()

    # ---------------------------------------------------------- theme

    def _resolve_scheme(self, pref: str) -> str:
        return theme.system_scheme() if pref == "system" else pref

    def _system_changed(self, scheme: str):
        if self.settings.value("theme", "system") == "system":
            self._retheme(scheme)

    def _set_theme_pref(self, pref: str):
        self.settings.setValue("theme", pref)
        self._retheme(self._resolve_scheme(pref))

    def _retheme(self, scheme: str):
        icons.clear_cache()
        app = QApplication.instance()
        self.tokens = theme.apply_theme(app, scheme)
        style = app.style()
        for w in app.allWidgets():          # Live-Wechsel: alles neu polieren
            style.unpolish(w)
            style.polish(w)
            w.update()
        for obj, name, color_key, size in self._icon_bindings:
            obj.setIcon(icons.icon(name, self.tokens[color_key], size))
        if hasattr(self, "batch_panel"):
            self.batch_panel.set_tokens(self.tokens)
        if hasattr(self, "status_time"):
            self.statusBar().setStyleSheet(
                f"QStatusBar {{ background: {self.tokens['panel_alt']};"
                f" border-top: 1px solid {self.tokens['border_soft']}; }}"
                f"QStatusBar::item {{ border: none; }}"
                f"QStatusBar QLabel {{ color: {self.tokens['text_dim']};"
                f" font-family: Menlo, Consolas, monospace; font-size: 11px;"
                f" padding: 0 7px; }}")
        self.canvas.apply_tokens(self.tokens)
        self._refresh_layer_list()
        self._refresh_mask_list()
        self._rebuild_settings()
        self._update_overlay()

    def _bind_icon(self, obj, name, color_key="text", size=18):
        obj.setIcon(icons.icon(name, self.tokens[color_key], size))
        self._icon_bindings.append((obj, name, color_key, size))

    # ---------------------------------------------------------- ui build

    def _build_ui(self):
        self.canvas = Canvas(self.tokens)
        self.canvas.fileDropped.connect(self._load_path)
        self.canvas.zoomChanged.connect(
            lambda z: self.status_zoom.setText(f"{z * 100:.0f} %"))
        self.canvas.rectDrawn.connect(lambda p: self._shape_drawn("rect", p))
        self.canvas.ellipseDrawn.connect(lambda p: self._shape_drawn("ellipse", p))
        self.canvas.polygonPoint.connect(self._poly_point)
        self.canvas.polygonMoved.connect(self._poly_moved)
        self.canvas.polygonInserted.connect(self._poly_inserted)
        self.canvas.polygonDeleted.connect(self._poly_deleted)
        self.canvas.polygonDone.connect(lambda: self._schedule())

        self._build_menubar()
        self._build_toolbar()

        # ---- Tab: Ebenen
        self.layer_list = QListWidget()
        self.layer_list.currentRowChanged.connect(lambda _: self._layer_selected())

        lb = QHBoxLayout(); lb.setSpacing(4)
        self.add_btn = QToolButton(); self.add_btn.setText(" Effekt")
        self.add_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._bind_icon(self.add_btn, "plus", "text", 15)
        self.add_btn.setPopupMode(QToolButton.InstantPopup)
        self.add_btn.setMenu(self._effect_menu())
        lb.addWidget(self.add_btn)
        lb.addStretch(1)
        for name, tip, fn in [("copy", "Ebene duplizieren", self._dup_layer),
                              ("up", "Nach oben", lambda: self._move_layer(-1)),
                              ("down", "Nach unten", lambda: self._move_layer(1)),
                              ("trash", "Ebene löschen", self._del_layer)]:
            b = QToolButton(); b.setProperty("flat", True); b.setToolTip(tip)
            self._bind_icon(b, name, "text_dim", 16)
            b.clicked.connect(fn)
            lb.addWidget(b)

        self.settings_area = QScrollArea()
        self.settings_area.setWidgetResizable(True)

        layers_tab = QWidget()
        lt = QVBoxLayout(layers_tab)
        lt.setContentsMargins(10, 10, 10, 10)
        lt.setSpacing(8)
        head = QLabel("EFFEKT-EBENEN · OBEN ZUERST")
        head.setProperty("role", "section")
        lt.addWidget(head)
        lt.addWidget(self.layer_list, 2)
        lt.addLayout(lb)
        lt.addWidget(self.settings_area, 3)

        # ---- Tab: Masken
        self.mask_list = QListWidget()
        self.mask_list.setIconSize(QPixmap(64, 48).size())
        self.mask_list.currentRowChanged.connect(lambda _: self._mask_selected())

        mb = QHBoxLayout(); mb.setSpacing(4)
        self.mask_add_btn = QToolButton(); self.mask_add_btn.setText(" Maske")
        self.mask_add_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._bind_icon(self.mask_add_btn, "plus", "text", 15)
        self.mask_add_btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        for kind in MASK_KINDS:
            menu.addAction(MASK_KIND_LABELS[kind],
                           lambda k=kind: self._add_mask(k))
        self.mask_add_btn.setMenu(menu)
        mb.addWidget(self.mask_add_btn)
        mb.addStretch(1)
        for name, tip, fn in [("copy", "Maske duplizieren", self._dup_mask),
                              ("trash", "Maske löschen", self._del_mask)]:
            b = QToolButton(); b.setProperty("flat", True); b.setToolTip(tip)
            self._bind_icon(b, name, "text_dim", 16)
            b.clicked.connect(fn)
            mb.addWidget(b)

        self.mask_editor_area = QScrollArea()
        self.mask_editor_area.setWidgetResizable(True)

        masks_tab = QWidget()
        mt = QVBoxLayout(masks_tab)
        mt.setContentsMargins(10, 10, 10, 10)
        mt.setSpacing(8)
        mhead = QLabel("MASKEN-BIBLIOTHEK")
        mhead.setProperty("role", "section")
        mt.addWidget(mhead)
        mt.addWidget(self.mask_list, 2)
        mt.addLayout(mb)
        mt.addWidget(self.mask_editor_area, 3)

        presets_tab = self._build_presets_tab()

        self.tabs = QTabWidget()
        self.tabs.addTab(layers_tab, "Ebenen")
        self.tabs.addTab(masks_tab, "Masken")
        self.tabs.addTab(presets_tab, "Presets")
        self.tabs.currentChanged.connect(self._tab_changed)

        split = QSplitter()
        split.addWidget(self.canvas)
        split.addWidget(self.tabs)
        split.setStretchFactor(0, 1)
        split.setSizes([840, 420])
        self.setCentralWidget(split)

        # ---- Galerie-Dock (Ausgabeordner, bewertbar)
        self.batch_panel = BatchGalleryPanel(
            self, self.tokens,
            self.settings.value("gallery/dir", "") or str(projects_dir()))
        self.gallery_panel = self.batch_panel.gallery
        self._auto_stem = self.batch_panel.stem.text().strip()
        self.gallery_panel.dir_label.setToolTip(
            "Bewertungen liegen als kleine Begleitdatei im Ordner – "
            "sie wandern also mit den Bildern mit.")
        self.gallery_dock = QDockWidget("Batch & Galerie", self)
        self.gallery_dock.setObjectName("gallery_dock")
        self.gallery_dock.setAllowedAreas(Qt.BottomDockWidgetArea
                                          | Qt.RightDockWidgetArea)
        self.gallery_dock.setWidget(self.batch_panel)
        self.gallery_dock.setMinimumHeight(300)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.gallery_dock)
        self.gallery_dock.setVisible(
            self.settings.value("gallery/visible", "false") in (True, "true", "1"))
        self.gallery_dock.visibilityChanged.connect(self._on_dock_visibility)
        self.batch_action.setChecked(self.gallery_dock.isVisible())
        act_gal = self.gallery_dock.toggleViewAction()
        act_gal.setText("Batch & Galerie anzeigen")
        act_gal.setShortcut("Ctrl+G")
        self.view_menu.addAction(act_gal)

        # ---- status bar
        self.status_proj = QLabel("Projekt: –")
        self.status_counts = QLabel("Ebenen: 0   Masken: 0")
        self.status_msg = QLabel("")
        for w in (self.status_proj, self.status_counts):
            self.statusBar().addWidget(w)
        self.statusBar().addWidget(self.status_msg, 1)
        self.status_size = QLabel("–")
        self.status_zoom = QLabel("–")
        self.status_time = QLabel("bereit")
        self.statusBar().setSizeGripEnabled(False)
        sb = self.statusBar()
        sb.setStyleSheet(
            f"QStatusBar {{ background: {self.tokens['panel_alt']};"
            f" border-top: 1px solid {self.tokens['border_soft']}; }}"
            f"QStatusBar::item {{ border: none; }}"
            f"QStatusBar QLabel {{ color: {self.tokens['text_dim']};"
            f" font-family: Menlo, Consolas, monospace; font-size: 11px;"
            f" padding: 0 7px; }}")
        sb.setFixedHeight(26)
        for w in (self.status_size, self.status_zoom, self.status_time):
            self.statusBar().addPermanentWidget(w)

    # ------------------------------------------------------------ presets

    def _presets_dir(self) -> Path:
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) \
            or str(Path.home() / ".pixelglitch")
        d = Path(base) / "presets"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _build_presets_tab(self) -> QWidget:
        tab = QWidget()
        v = QVBoxLayout(tab)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(8)
        head = QLabel("PRESETS · Stapel als Vorlage speichern und anwenden")
        head.setProperty("role", "section")
        v.addWidget(head)

        self.preset_list = QListWidget()
        self.preset_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preset_list.setTextElideMode(Qt.ElideRight)
        self.preset_list.setWordWrap(False)
        self.preset_list.itemDoubleClicked.connect(lambda _i: self._apply_preset())
        self.preset_list.currentRowChanged.connect(self._preset_selection_changed)
        v.addWidget(self.preset_list, 1)

        self.preset_info = QLabel("")
        self.preset_info.setProperty("role", "hint")
        self.preset_info.setWordWrap(True)
        v.addWidget(self.preset_info)

        row1 = QHBoxLayout()
        self.preset_apply_btn = QPushButton("Anwenden")
        self.preset_apply_btn.setProperty("accent", True)
        self.preset_apply_btn.clicked.connect(self._apply_preset)
        save_btn = QPushButton("Aus Stapel speichern…")
        save_btn.clicked.connect(self._save_preset_from_stack)
        row1.addWidget(self.preset_apply_btn)
        row1.addWidget(save_btn)
        row1.addStretch(1)
        v.addLayout(row1)

        row2 = QHBoxLayout()
        self.preset_dup_btn = QPushButton("Duplizieren")
        self.preset_dup_btn.clicked.connect(self._dup_preset)
        self.preset_del_btn = QPushButton("Löschen")
        self.preset_del_btn.clicked.connect(self._del_preset)
        imp = QPushButton("Import…")
        imp.clicked.connect(self._import_preset)
        self.preset_exp_btn = QPushButton("Export…")
        self.preset_exp_btn.clicked.connect(self._export_preset)
        for b in (self.preset_dup_btn, self.preset_del_btn, imp, self.preset_exp_btn):
            row2.addWidget(b)
        row2.addStretch(1)
        v.addLayout(row2)

        self._reload_presets()
        return tab

    def _reload_presets(self):
        self.preset_list.clear()
        self._preset_entries = []            # (pfad|None, Preset)
        for p in presets.builtin_presets():
            self._preset_entries.append((None, p))
        user, errors = presets.scan_presets(self._presets_dir())
        self._preset_entries += user
        for path, p in self._preset_entries:
            origin = "mitgeliefert" if p.origin == "builtin" else "eigenes"
            item = QListWidgetItem(f"{p.name}   ·   {origin}\n{p.summary()}")
            self.preset_list.addItem(item)
        for path, why in errors:
            item = QListWidgetItem(f"⚠ {Path(path).name}\nBeschädigt: {why}")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.preset_list.addItem(item)
        self._preset_errors = errors
        if self._preset_entries:
            self.preset_list.setCurrentRow(0)
        self._preset_selection_changed(self.preset_list.currentRow())

    def _current_preset(self):
        row = self.preset_list.currentRow()
        if 0 <= row < len(self._preset_entries):
            return self._preset_entries[row]
        return None, None

    def _preset_selection_changed(self, _row):
        path, p = self._current_preset()
        if p is None:
            self.preset_info.setText("")
            for b in (self.preset_apply_btn, self.preset_dup_btn,
                      self.preset_del_btn, self.preset_exp_btn):
                b.setEnabled(False)
            return
        builtin = p.origin == "builtin"
        self.preset_apply_btn.setEnabled(True)
        self.preset_dup_btn.setEnabled(True)
        self.preset_del_btn.setEnabled(not builtin)
        self.preset_exp_btn.setEnabled(True)
        self.preset_del_btn.setToolTip(
            "Mitgelieferte Presets sind schreibgeschützt – Duplizieren "
            "erzeugt eine bearbeitbare Kopie." if builtin else "")
        self.preset_info.setText(p.description)

    def _apply_preset(self):
        _path, p = self._current_preset()
        if p is None:
            return
        if self.project.layers:
            ret = QMessageBox.question(
                self, "Preset anwenden",
                f"„{p.name}“ ersetzt den aktuellen Ebenenstapel "
                f"({len(self.project.layers)} Ebene(n)). Fortfahren?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if ret != QMessageBox.Yes:
                return
        notes = p.apply_to(self.project)
        self._refresh_layer_list(keep_row=0)
        self._refresh_mask_list()
        self._rebuild_settings()
        self._schedule()
        msg = f"Preset „{p.name}“ angewendet."
        if notes:
            msg += "  " + " ".join(notes)
        self.status_msg.setText(msg)

    def _save_preset_from_stack(self):
        if not self.project.layers:
            QMessageBox.information(self, "Leerer Stapel",
                                    "Zuerst Effekt-Ebenen anlegen.")
            return
        name, okp = QInputDialog.getText(
            self, "Preset speichern", "Name:",
            text=self.project_name or "Mein Preset")
        if not okp or not name.strip():
            return
        p = presets.Preset.from_project(self.project, name.strip())
        presets.save_preset(p, self._presets_dir())
        self._reload_presets()
        self.status_msg.setText(f"Preset „{p.name}“ gespeichert.")

    def _dup_preset(self):
        _path, p = self._current_preset()
        if p is None:
            return
        clone = presets.Preset(name=f"{p.name} Kopie",
                               description=p.description, origin="user",
                               layers=[dict(l) for l in p.layers],
                               masks=[dict(m) for m in p.masks])
        presets.save_preset(clone, self._presets_dir())
        self._reload_presets()

    def _del_preset(self):
        path, p = self._current_preset()
        if p is None or p.origin == "builtin" or not path:
            return
        ret = QMessageBox.question(self, "Preset löschen",
                                   f"„{p.name}“ endgültig löschen?",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        if ret == QMessageBox.Yes:
            Path(path).unlink(missing_ok=True)
            self._reload_presets()

    def _import_preset(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Preset importieren", str(projects_dir()),
            f"PixelGlitch-Preset (*{presets.PRESET_EXT})")
        if not path:
            return
        try:
            p = presets.load_preset(path, origin="import")
        except Exception as e:
            QMessageBox.warning(self, "Import fehlgeschlagen", str(e))
            return
        presets.save_preset(p, self._presets_dir())
        self._reload_presets()
        self.status_msg.setText(f"Preset „{p.name}“ importiert.")

    def _export_preset(self):
        _path, p = self._current_preset()
        if p is None:
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Preset exportieren",
            str(projects_dir() / f"{p.name}{presets.PRESET_EXT}"),
            f"PixelGlitch-Preset (*{presets.PRESET_EXT})")
        if not target:
            return
        Path(target).write_text(
            json.dumps(p.to_json(), indent=2, ensure_ascii=False),
            encoding="utf-8")
        self.status_msg.setText(f"Preset exportiert: {Path(target).name}")

    def _build_menubar(self):
        m = self.menuBar().addMenu("Datei")
        m.addAction("Bild öffnen…", self._open_image)
        m.addSeparator()
        act_open = m.addAction("Projekt öffnen…", self._open_project)
        act_open.setShortcut("Ctrl+O")
        self.recent_menu = m.addMenu("Zuletzt verwendet")
        self._rebuild_recent_menu()
        act_save = m.addAction("Projekt speichern", self._save_project)
        act_save.setShortcut("Ctrl+S")
        m.addAction("Projekt speichern unter…", self._save_project_as)
        m.addAction("Projekt schließen", self._close_project)
        m.addSeparator()
        m.addAction("Variante aus Seed übernehmen…", self._adopt_variant_by_seed)
        m.addSeparator()
        m.addAction("Vorschau exportieren…", self._export)
        m.addAction("Massengenerierung…", self._batch)
        m.addSeparator()
        m.addAction("Beenden", self.close)

        v = self.menuBar().addMenu("Ansicht")
        appearance = v.addMenu("Erscheinungsbild")
        group = QActionGroup(self)
        pref = self.settings.value("theme", "system")
        for key, label in [("system", "Dem System folgen"),
                           ("dark", "Dunkel"), ("light", "Hell")]:
            a = QAction(label, self, checkable=True)
            a.setChecked(pref == key)
            a.triggered.connect(lambda _, k=key: self._set_theme_pref(k))
            group.addAction(a)
            appearance.addAction(a)
        v.addAction("Ansicht einpassen", self.canvas.fit)
        a_seed = v.addAction("Neuer Zufalls-Seed", self._reseed)
        a_seed.setShortcut("Ctrl+R")
        v.addSeparator()
        self.view_menu = v

        h = self.menuBar().addMenu("Hilfe")
        h.addAction("Über PixelGlitch Studio", self._about)

    def _build_toolbar(self):
        tb = QToolBar("Werkzeuge")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        def act(icon_name, text, fn, checkable=False, checked=False, tip="",
                shortcut=""):
            a = QAction(text, self)
            self._bind_icon(a, icon_name, "text", 18)
            a.setCheckable(checkable)
            a.setChecked(checked)
            if shortcut:
                a.setShortcut(shortcut)
                tip = f"{tip or text} ({shortcut})"
            a.setToolTip(tip or text)
            if checkable:
                a.toggled.connect(fn)
            else:
                a.triggered.connect(fn)
            tb.addAction(a)
            return a

        act("folder", "Projekte", self._show_project_browser,
            tip="Projektbrowser: zuletzt bearbeitete Projekte öffnen")
        act("save", "Speichern", self._save_project, tip="Projekt speichern")
        tb.addSeparator()
        act("export", "Exportieren", self._export, shortcut="Ctrl+E")
        tb.addSeparator()
        self.batch_action = act("batch", "Batch", self._toggle_batch_panel,
                                checkable=True,
                                tip="Panel »Batch & Galerie« ein-/ausblenden",
                                shortcut="Ctrl+B")

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        self.overlay_action = act("overlay", "Maske zeigen", lambda _: self._update_overlay(),
                                  checkable=True, tip="Aktive Maske als Overlay einblenden")
        self.fast_action = act("bolt", "Schnell", self._set_fast, checkable=True,
                               checked=True, tip="Schnellvorschau (verkleinert rechnen)")


    def _effect_menu(self) -> QMenu:
        menu = QMenu(self)
        groups: dict[str, list] = {}
        for name, cls in EFFECTS.items():
            groups.setdefault(cls.group, []).append((name, cls.label))
        for group in ("Sortierung", "Glitch", "Farbe"):
            sub = menu.addMenu(group)
            for name, label in groups.get(group, []):
                sub.addAction(label, lambda n=name: self._add_layer(n))
        return menu

    def _about(self):
        box = QMessageBox(self)
        box.setWindowTitle("Über PixelGlitch Studio")
        box.setIconPixmap(branding.logo_pixmap(72))
        box.setText(f"<b>PixelGlitch Studio {__version__}</b>")
        box.setInformativeText(
            "Die Ästhetik des Fehlers, präzise gesteuert: PixelGlitch Studio "
            "zerlegt Bilder in ihre Datenströme und setzt sie kontrolliert neu "
            "zusammen – Pixel-Sorting, Databending und Signalstörungen, "
            "geschichtet über Ebenen, geformt durch Masken, in Serie gewürfelt "
            "und dank Seeds jederzeit exakt reproduzierbar.\n\n"
            f"{branding.COPYRIGHT}")
        box.exec()

    # ---------------------------------------------------------- image io

    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Bild öffnen", "", IMG_FILTER)
        if path:
            self._load_path(path)

    def _load_path(self, path: str):
        if str(path).lower().endswith((".pgsz", ".pgs.json")):
            self._open_project_path(path)          # Projektdatei auf Canvas gezogen
            return
        try:
            self.source = engine.load_image(path)
            self.source_bytes = Path(path).read_bytes()
            self.source_name = Path(path).name
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Bild konnte nicht geladen werden:\n{e}")
            return
        self.source_path = path
        h, w = self.source.shape[:2]
        self.status_size.setText(f"{w} × {h} px")
        self._sync_project_stem()
        self.status_msg.setText(Path(path).name)
        self._schedule()

    def _export(self):
        if self.source is None:
            QMessageBox.information(self, "Kein Bild", "Zuerst ein Bild laden.")
            return
        stem = Path(self.source_path).stem or "glitch"
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportieren",
            str(projects_dir() / f"{stem}_{self.seed}.png"),
            "PNG (*.png);;JPEG (*.jpg)")
        if not path:
            return
        fmt = Path(path).suffix.lstrip(".").lower()
        quality = 95
        if fmt in ("jpg", "jpeg"):
            default = int(self.settings.value("export/quality", 90))
            quality, ok = QInputDialog.getInt(
                self, "JPG-Qualität", "Qualität (1–100):", default, 1, 100, 5)
            if not ok:
                return
            self.settings.setValue("export/quality", quality)
        arr = engine.render(self.project, self.source, seed=self.seed)  # volle Auflösung
        engine.save_image(arr, path, fmt, quality)
        self.status_msg.setText(f"Exportiert: {Path(path).name}")

    def _toggle_batch_panel(self, show: bool):
        """Panel »Batch & Galerie« ein- oder ausblenden."""
        self.gallery_dock.setVisible(show)
        if show:
            self.gallery_dock.raise_()
            if self.batch_panel.collapse_btn.isChecked():
                self.batch_panel.collapse_btn.setChecked(False)
            self.batch_panel.refresh_layers()
            self.batch_panel.run_btn.setFocus()

    def _on_dock_visibility(self, visible: bool):
        self.settings.setValue("gallery/visible", visible)
        if hasattr(self, "batch_action"):
            self.batch_action.setChecked(visible)

    def _batch(self):
        self.batch_action.setChecked(True)

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Projekt öffnen",
                                      str(projects_dir()), PROJ_FILTER_OPEN)
        if path:
            self._open_project_path(path)

    def _show_project_browser(self):
        dlg = WelcomeDialog(self, self.tokens)
        if dlg.exec() and dlg.choice:
            if dlg.choice[0] == "project":
                self._open_project_path(dlg.choice[1])
            elif dlg.choice[0] == "new":
                self._new_project(dlg.choice[1])
            elif dlg.choice[0] == "browse":
                self._open_project()

    def _open_project_path(self, path: str) -> bool:
        if not self._confirm_discard("Öffnen"):
            return False
        try:
            if zipfile.is_zipfile(path):
                project, img_bytes, img_name = engine.load_bundle(path)
                self.project = project
                if img_bytes:
                    self.source = engine.decode_image_bytes(img_bytes)
                    self.source_bytes = img_bytes
                    self.source_name = img_name
                    self.source_path = img_name
                    h, w = self.source.shape[:2]
                    self.status_size.setText(f"{w} × {h} px")
            else:
                self.project = Project.load(path)      # Altformat ohne Bild
        except Exception as e:
            QMessageBox.warning(self, "Fehler",
                                f"Projekt konnte nicht geladen werden:\n{e}")
            return False
        self.project_path = path if path.lower().endswith(".pgsz") else ""
        self.project_name = Path(path).name.replace(".pgs.json", "").replace(".pgsz", "")
        self._update_title()
        self._sync_project_stem()
        self._add_recent(path)
        self._mark_saved()
        self._refresh_layer_list()
        self._refresh_mask_list()
        self._rebuild_settings()
        self._rebuild_mask_editor()
        self._schedule()
        self.status_msg.setText(f"Projekt geladen: {Path(path).name}")
        return True

    def _save_project(self) -> bool:
        """Speichern ohne Rückfrage: bekannter Pfad oder Default-Ordner."""
        if self.project_path:
            return self._write_project(self.project_path)
        return self._save_project_as()

    def _save_project_as(self) -> bool:
        start = self.project_path or str(
            projects_dir() / f"{self.project_name or 'projekt'}.pgsz")
        path, _ = QFileDialog.getSaveFileName(self, "Projekt speichern unter",
                                              start, PROJ_FILTER_SAVE)
        if not path:
            return False
        return self._write_project(path)

    def _write_project(self, path: str) -> bool:
        try:
            if path.lower().endswith(".pgsz"):
                thumb = None
                base = self.preview if self.preview is not None else self.source
                if base is not None:
                    thumb = engine.downscale(base, 320)
                engine.save_bundle(path, self.project, self.source_bytes,
                                   self.source_name, thumb)
                self.project_path = path
            else:
                self.project.save(path)                 # Nur Einstellungen
        except Exception as e:
            QMessageBox.warning(self, "Fehler",
                                f"Projekt konnte nicht gespeichert werden:\n{e}")
            return False
        self.project_name = Path(path).name.replace(".pgs.json", "").replace(".pgsz", "")
        self._update_title()
        self._sync_project_stem()
        self._add_recent(path)
        self._mark_saved()
        self.status_msg.setText(f"Projekt gespeichert: {Path(path).name}")
        return True

    # ---------------------------------------------------------- recents

    def _recent_list(self) -> list:
        raw = self.settings.value("recent_projects", []) or []
        if isinstance(raw, str):
            raw = [raw]
        return [p for p in raw if Path(p).exists()]

    def _add_recent(self, path: str):
        items = [p for p in self._recent_list() if p != path]
        items.insert(0, path)
        self.settings.setValue("recent_projects", items[:RECENT_MAX])
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self):
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.clear()
        items = self._recent_list()
        if not items:
            a = self.recent_menu.addAction("(leer)")
            a.setEnabled(False)
            return
        for p in items:
            self.recent_menu.addAction(
                Path(p).name, lambda p=p: self._open_project_path(p))

    # ---------------------------------------------------------- layers

    def _current_layer(self) -> Layer | None:
        row = self.layer_list.currentRow()
        if 0 <= row < len(self.project.layers):
            return self.project.layers[row]
        return None

    def _mask_summary(self, layer: Layer) -> str:
        if not layer.refs:
            return "ohne Maske"
        sym = {"union": " ∪ ", "intersect": " ∩ ", "subtract": " − "}
        parts = []
        for i, r in enumerate(layer.refs):
            m = self.project.masks.get(r.mask_id)
            name = ("¬" if r.invert else "") + (m.name if m else "?")
            parts.append((sym.get(r.op, " ∪ ") if i else "") + name)
        return "".join(parts)

    def _refresh_layer_list(self, keep_row: int | None = None):
        if hasattr(self, "batch_panel"):
            self.batch_panel.refresh_layers()
        row = keep_row if keep_row is not None else self.layer_list.currentRow()
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for ly in self.project.layers:
            item = QListWidgetItem()
            w = LayerItemWidget(ly.label, self._mask_summary(ly), ly.enabled, self.tokens)
            w.visibilityToggled.connect(
                lambda on, l=ly: (setattr(l, "enabled", on), self._schedule()))
            item.setSizeHint(w.sizeHint())
            self.layer_list.addItem(item)
            self.layer_list.setItemWidget(item, w)
        self.layer_list.blockSignals(False)
        if self.project.layers:
            self.layer_list.setCurrentRow(
                min(row if row >= 0 else 0, len(self.project.layers) - 1))
        else:
            self._rebuild_settings()

    def _add_layer(self, effect: str):
        self.project.layers.insert(0, Layer(effect=effect))
        self._refresh_layer_list(keep_row=0)
        self._schedule()

    def _dup_layer(self):
        ly = self._current_layer()
        if ly:
            copy = Layer.from_json(ly.to_json())
            copy.id = __import__("uuid").uuid4().hex[:10]
            self.project.layers.insert(self.layer_list.currentRow(), copy)
            self._refresh_layer_list()
            self._schedule()

    def _del_layer(self):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self.project.layers):
            del self.project.layers[row]
            self._refresh_layer_list(keep_row=max(0, row - 1))
            self._schedule()

    def _move_layer(self, delta: int):
        row = self.layer_list.currentRow()
        new = row + delta
        if 0 <= row < len(self.project.layers) and 0 <= new < len(self.project.layers):
            ls = self.project.layers
            ls[row], ls[new] = ls[new], ls[row]
            self._refresh_layer_list(keep_row=new)
            self._schedule()

    def _layer_selected(self):
        self._rebuild_settings()
        self._update_overlay()

    def _rebuild_settings(self):
        ly = self._current_layer()
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 4, 6, 4)
        v.setSpacing(10)
        if ly is None:
            hint = QLabel("Über „+ Effekt“ eine Ebene hinzufügen.")
            hint.setProperty("role", "hint")
            v.addWidget(hint)
        else:
            fx_sec = CollapsibleSection("Effekt · " + ly.label, self.tokens)
            reroll = QToolButton()
            reroll.setProperty("flat", True)
            reroll.setIcon(icons.icon("dice", self.tokens["text"], 16))
            reroll.setIconSize(QSize(16, 16))
            reroll.setStyleSheet("padding: 0px;")
            reroll.setFixedSize(26, 26)
            reroll.clicked.connect(self._reroll_layer)
            fx_sec.add_header_widget(reroll)
            self.reroll_btn = reroll
            self._sync_reroll_btn()
            editor = ParamEditor(ly, self.tokens)
            editor.changed.connect(self._schedule)
            editor.randChanged.connect(self._rand_marks_changed)
            fx_sec.set_content(editor)
            v.addWidget(fx_sec)

            self._mask_section = CollapsibleSection(
                self._mask_section_title(ly), self.tokens)
            chain = MaskChainEditor(ly, self.project, self.tokens)
            chain.changed.connect(self._chain_changed)
            self._mask_section.set_content(chain)
            v.addWidget(self._mask_section)
        v.addStretch(1)
        self.settings_area.setWidget(container)

    def _mask_section_title(self, ly: Layer) -> str:
        if not ly.refs:
            return "Maskenzuweisung"
        return "Maskenzuweisung · " + self._mask_summary(ly)

    def _chain_changed(self):
        row = self.layer_list.currentRow()
        ly = self._current_layer()
        if ly is not None:
            item = self.layer_list.item(row)
            w = self.layer_list.itemWidget(item)
            if w:
                w.sub.setText(self._mask_summary(ly))
            if getattr(self, "_mask_section", None):
                self._mask_section.set_title(self._mask_section_title(ly))
        self._schedule()

    # ---------------------------------------------------------- masks

    def _current_mask(self) -> Mask | None:
        row = self.mask_list.currentRow()
        masks = self.project.ordered_masks()
        if 0 <= row < len(masks):
            return masks[row]
        return None

    def _mask_thumb(self, mask: Mask) -> QPixmap:
        m = (mask.render(64, 48) * 255).astype(np.uint8)
        img = QImage(np.ascontiguousarray(m).data, 64, 48, 64,
                     QImage.Format_Grayscale8).copy()
        return QPixmap.fromImage(img)

    def _refresh_mask_list(self, keep_row: int | None = None):
        row = keep_row if keep_row is not None else self.mask_list.currentRow()
        self.mask_list.blockSignals(True)
        self.mask_list.clear()
        for mask in self.project.ordered_masks():
            item = QListWidgetItem(self._mask_thumb(mask), "")
            used = len(self.project.mask_usage(mask.id))
            item.setText(f"{mask.name}\n{MASK_KIND_LABELS[mask.kind]}"
                         + (f" · {used}× verwendet" if used else "")
                         + f"\n{self._mask_params_line(mask)}")
            self.mask_list.addItem(item)
        self.mask_list.blockSignals(False)
        masks = self.project.ordered_masks()
        if masks:
            self.mask_list.setCurrentRow(min(row if row >= 0 else 0, len(masks) - 1))
        else:
            self._rebuild_mask_editor()

    def _mask_params_line(self, mask) -> str:
        """Kennwerte generisch aus den Maskenparametern (kompakt)."""
        if mask.kind == "polygon":
            return f"{len(mask.params.get('points', []))} Punkte"
        if mask.kind == "image":
            src_name = Path(str(mask.params.get("path", ""))).name
            return src_name or "kein Bild gewählt"
        parts = []
        for key, val in mask.params.items():
            if isinstance(val, (int, float)):
                parts.append(f"{key} {val:.2f}".rstrip("0").rstrip("."))
        return " · ".join(parts[:4])

    def _add_mask(self, kind: str):
        self.project.add_mask(Mask(kind=kind))
        self._refresh_mask_list(keep_row=len(self.project.mask_order) - 1)
        self._rebuild_settings()

    def _dup_mask(self):
        m = self._current_mask()
        if m:
            import copy as _copy
            clone = Mask(kind=m.kind, name=m.name, params=_copy.deepcopy(m.params))
            self.project.add_mask(clone)
            self._refresh_mask_list(keep_row=len(self.project.mask_order) - 1)

    def _del_mask(self):
        m = self._current_mask()
        if not m:
            return
        used = self.project.mask_usage(m.id)
        if used:
            names = ", ".join(ly.label for ly in used[:4])
            QMessageBox.warning(
                self, "Maske in Verwendung",
                f"„{m.name}“ wird von {len(used)} Ebene(n) referenziert ({names}).\n"
                "Zuerst die Referenzen entfernen, dann löschen.")
            return
        self.project.remove_mask(m.id)
        self._refresh_mask_list(keep_row=max(0, self.mask_list.currentRow() - 1))
        self._rebuild_settings()

    def _mask_selected(self):
        self._rebuild_mask_editor()
        self._sync_draw_mode()
        self._update_overlay()

    def _rebuild_mask_editor(self):
        mask = self._current_mask()
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 4, 6, 4)
        v.setSpacing(10)
        if mask is None:
            hint = QLabel("Über „+ Maske“ eine Maske anlegen.\n"
                          "Masken sind wiederverwendbar – Ebenen referenzieren sie.")
            hint.setProperty("role", "hint")
            v.addWidget(hint)
        else:
            sec = CollapsibleSection("Geometrie · " + mask.name, self.tokens)
            sec.set_content(self._mask_geometry_editor(mask))
            v.addWidget(sec)
        v.addStretch(1)
        self.mask_editor_area.setWidget(container)

    def _mask_geometry_editor(self, mask: Mask) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        row = 0

        name = QLineEdit(mask.name)
        name.editingFinished.connect(
            lambda m=mask, e=name: self._rename_mask(m, e.text()))
        grid.addWidget(QLabel("Name"), row, 0)
        grid.addWidget(name, row, 1)
        row += 1

        def spin(key, lo, hi, step=0.01):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setSingleStep(step)
            s.setDecimals(3)
            s.setValue(float(mask.params.get(key, 0)))
            s.valueChanged.connect(
                lambda val, k=key, m=mask: self._mask_param(m, k, float(val)))
            return s

        fields = {
            "rect": [("x", "X", 0, 1), ("y", "Y", 0, 1), ("w", "Breite", 0, 1),
                     ("h", "Höhe", 0, 1)],
            "ellipse": [("cx", "Mitte X", 0, 1), ("cy", "Mitte Y", 0, 1),
                        ("rx", "Radius X", 0, 1), ("ry", "Radius Y", 0, 1)],
            "linear": [("angle", "Winkel °", -180, 180), ("start", "Start", 0, 1),
                       ("end", "Ende", 0, 1)],
            "radial": [("cx", "Mitte X", 0, 1), ("cy", "Mitte Y", 0, 1),
                       ("radius", "Radius", 0.01, 1.5), ("inner", "Kern", 0, 0.99)],
        }
        for key, label, lo, hi in fields.get(mask.kind, []):
            step = 1.0 if key == "angle" else 0.01
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(spin(key, lo, hi, step), row, 1)
            row += 1

        if mask.kind == "polygon":
            count = QLabel(f"{len(mask.params.get('points', []))} Punkte")
            reset = QPushButton("Punkte zurücksetzen")
            reset.clicked.connect(lambda _, m=mask: self._poly_reset(m))
            grid.addWidget(count, row, 0)
            grid.addWidget(reset, row, 1)
            row += 1
        if mask.kind == "image":
            pick = QPushButton("Maskenbild wählen…")
            pick.clicked.connect(lambda _, m=mask: self._pick_mask_image(m))
            grid.addWidget(pick, row, 0, 1, 2)
            row += 1

        hints = {
            "rect": "Direkt im Bild aufziehen (Ziehen mit der Maus).",
            "ellipse": "Direkt im Bild aufziehen (Ziehen mit der Maus).",
            "polygon": "Klick fügt Punkte hinzu, Ziehen verschiebt sie, Rechtsklick "
                       "löscht, Klick auf eine Kante fügt dazwischen ein.",
            "linear": "Verlauf von Start (0) nach Ende (1) entlang des Winkels.",
            "radial": "Kern = voll deckender innerer Anteil des Radius.",
            "image": "Graustufenbild: weiß = Effekt wirkt, schwarz = unberührt.",
        }
        hint = QLabel(hints[mask.kind])
        hint.setWordWrap(True)
        hint.setProperty("role", "hint")
        grid.addWidget(hint, row, 0, 1, 2)
        return w

    def _rename_mask(self, mask: Mask, text: str):
        text = text.strip()
        if text and text != mask.name:
            mask.name = text
            self._refresh_mask_list()
            self._refresh_layer_list()
            self._rebuild_settings()

    def _mask_param(self, mask: Mask, key: str, value: float):
        mask.params[key] = value
        self._mask_changed(mask)

    def _mask_changed(self, mask: Mask, rebuild_editor: bool = False):
        row = self.mask_list.currentRow()
        item = self.mask_list.item(row)
        if item:
            item.setIcon(self._mask_thumb(mask))
        if rebuild_editor:
            self._rebuild_mask_editor()
        self._schedule()

    def _poly_reset(self, mask: Mask):
        mask.params["points"] = []
        self.canvas.clear_poly_markers()
        self._mask_changed(mask, rebuild_editor=True)

    def _pick_mask_image(self, mask: Mask):
        path, _ = QFileDialog.getOpenFileName(self, "Maskenbild", "", IMG_FILTER)
        if path:
            mask.params["path"] = path
            self._mask_changed(mask, rebuild_editor=True)

    # ---------------------------------------------------------- canvas interactions

    def _tab_changed(self, _):
        self._sync_draw_mode()
        self._update_overlay()

    def _sync_draw_mode(self):
        if self.tabs.currentIndex() == 1:
            mask = self._current_mask()
            if mask and mask.kind in ("rect", "ellipse", "polygon"):
                self.canvas.set_draw_mode(mask.kind)
                if mask.kind == "polygon":
                    self.canvas.set_polygon_points(mask.params.get("points", []))
                return
        self.canvas.set_draw_mode("none")

    def _shape_drawn(self, kind: str, params: dict):
        mask = self._current_mask()
        if self.tabs.currentIndex() == 1 and mask and mask.kind == kind:
            mask.params.update(params)
            self._mask_changed(mask, rebuild_editor=True)

    def _active_polygon(self):
        mask = self._current_mask()
        if self.tabs.currentIndex() == 1 and mask and mask.kind == "polygon":
            return mask
        return None

    def _poly_point(self, x: float, y: float):
        mask = self._active_polygon()
        if mask:
            mask.params.setdefault("points", []).append((x, y))
            self._poly_sync(mask)

    def _poly_moved(self, i: int, x: float, y: float):
        mask = self._active_polygon()
        if mask and 0 <= i < len(mask.params.get("points", [])):
            mask.params["points"][i] = (x, y)
            self._poly_sync(mask)

    def _poly_inserted(self, i: int, x: float, y: float):
        mask = self._active_polygon()
        if mask:
            pts = mask.params.setdefault("points", [])
            mask.params["points"] = pts[:i] + [(x, y)] + pts[i:]
            self._poly_sync(mask)

    def _poly_deleted(self, i: int):
        mask = self._active_polygon()
        if mask and 0 <= i < len(mask.params.get("points", [])):
            del mask.params["points"][i]
            self._poly_sync(mask)

    def _poly_sync(self, mask):
        self.canvas.set_polygon_points(mask.params.get("points", []))
        self._mask_changed(mask, rebuild_editor=True)

    # ---------------------------------------------------------- rendering

    def _set_fast(self, on: bool):
        self.fast = on
        self._schedule()

    def preview_file(self, path: str):
        """Bilddatei temporär in der Hauptvorschau zeigen (Galerie-Klick)."""
        try:
            self.canvas.set_image(engine.load_image(path))
            self.status_msg.setText(f"Vorschau: {Path(path).name}")
        except Exception:
            pass

    def adopt_variant(self, seed: int, note: str = ""):
        """Gewürfelte Werte einer Variante ins aktuelle Projekt übernehmen."""
        if not self.project.layers:
            return
        variant = engine.randomized_copy(self.project, seed)
        for live, var in zip(self.project.layers, variant.layers):
            live.params = dict(var.params)
        self.seed = seed
        self._rebuild_settings()
        self._schedule()
        msg = f"Variante {seed} übernommen – 🎲-Markierungen bleiben aktiv."
        self.status_msg.setText(f"{msg}  {note}" if note else msg)

    def restore_variant(self, snapshot: Project, seed: int):
        """Ebenenstapel und Masken des damaligen Laufs wiederherstellen."""
        variant = engine.randomized_copy(snapshot, seed)
        self.project.layers = variant.layers
        self.project.masks = variant.masks
        self.project.mask_order = list(variant.mask_order)
        self.seed = seed
        self._refresh_layer_list(keep_row=0)
        self._refresh_mask_list()
        self._rebuild_settings()
        self._schedule()
        self.status_msg.setText(
            f"Stapel des Laufs wiederhergestellt (Variante {seed}).")

    def _apply_batch_variant(self, seed: int):
        """Menü „Variante aus Seed übernehmen…"."""
        self.adopt_variant(seed)

    def _adopt_variant_by_seed(self):
        """Menü: Variante eines früheren Batches per Seed übernehmen."""
        if not self.project.layers:
            QMessageBox.information(self, "Keine Ebenen",
                                    "Zuerst ein Projekt mit Effekt-Ebenen laden.")
            return
        seed, okp = QInputDialog.getInt(
            self, "Variante aus Seed übernehmen",
            "Seed (Zahl am Ende des Batch-Dateinamens):",
            self.seed, 0, 10**9)
        if not okp:
            return
        self._apply_batch_variant(seed)

    def _marked_keys(self, ly) -> list:
        """🎲-Markierungen der Ebene, die es im Effekt wirklich gibt."""
        specs = {s.key for s in EFFECTS[ly.effect].params}
        return [k for k in sorted(ly.rand_keys) if k in specs]

    def _sync_reroll_btn(self):
        """Würfel-Knopf des Effekt-Abschnitts an die Markierungen anpassen."""
        btn = getattr(self, "reroll_btn", None)
        ly = self._current_layer()
        if btn is None or ly is None:
            return
        n = len(self._marked_keys(ly))
        btn.setEnabled(n > 0)
        btn.setToolTip(
            f"Die {n} 🎲-markierten Parameter dieser Ebene neu würfeln" if n
            else "Kein Parameter dieser Ebene ist mit 🎲 markiert – "
                 "markiere sie über den Würfel neben einem Regler.")

    def _rand_marks_changed(self):
        """Eine 🎲-Markierung wurde gesetzt oder entfernt."""
        self._sync_reroll_btn()
        if hasattr(self, "batch_panel"):
            self.batch_panel.refresh_layers()

    def _reroll_layer(self):
        """🎲-markierte Parameter der aktiven Ebene neu würfeln."""
        ly = self._current_layer()
        if ly is None:
            return
        specs = {s.key: s for s in EFFECTS[ly.effect].params}
        keys = self._marked_keys(ly)
        if not keys:
            self.status_msg.setText(
                f"{ly.label}: kein Parameter mit 🎲 markiert – markiere sie "
                "über den Würfel neben dem Regler.")
            return
        rng = np.random.default_rng()          # bewusst nicht reproduzierbar
        for key in keys:
            ly.params[key] = random_value(specs[key], rng)
        self._rebuild_settings()
        self._schedule()
        self.status_msg.setText(
            f"{ly.label}: {len(keys)} Parameter neu gewürfelt.")

    def _reseed(self):
        """Neuer Zufalls-Seed – wirkt auf zufallsbasierte Effekte."""
        self.seed += 1
        self._schedule()

    def _schedule(self):
        self._render_timer.start()

    def _render_now(self):
        if self.source is None:
            self.canvas.set_image(None)
            self.status_time.setText("bereit")
            return
        self.status_time.setText("rendert …")
        self.status_time.repaint()
        try:
            with engine.Stopwatch() as sw:
                self.preview = engine.render(
                    self.project, self.source, seed=self.seed,
                    max_size=PREVIEW_FAST if self.fast else None)
        except Exception as e:
            self._flash_error(f"Renderfehler: {e}")
            self.status_time.setText("bereit")
            return
        self.canvas.set_image(self.preview)
        ms = (f"{sw.ms:.0f} ms" if sw.ms < 10_000 else f"{sw.ms / 1000:.1f} s")
        fast_note = f" · Vorschau ↓{PREVIEW_FAST} px" if (
            self.fast and max(self.source.shape[:2]) > PREVIEW_FAST) else ""
        self.status_time.setText(
            f"gerendert in {ms}{fast_note} · Seed {self.seed}")
        self._update_counts()
        self._update_title()
        self._update_overlay()

    def _flash_error(self, text: str, msecs: int = 6000):
        prev = self.status_msg.text()
        self.status_msg.setStyleSheet(f"color: {self.tokens['warn']};")
        self.status_msg.setText(text)
        def back():
            self.status_msg.setStyleSheet("")
            if self.status_msg.text() == text:
                self.status_msg.setText(prev)
        QTimer.singleShot(msecs, back)

    def _update_overlay(self):
        if not self.overlay_action.isChecked() or self.preview is None:
            self.canvas.set_overlay(None, self.tokens["accent"])
            return
        h, w = self.preview.shape[:2]
        mask = None
        if self.tabs.currentIndex() == 1:
            m = self._current_mask()
            if m:
                mask = m.render(w, h)
        else:
            ly = self._current_layer()
            if ly and ly.refs:
                mask = engine.layer_mask_preview(self.project, ly, w, h)
        self.canvas.set_overlay(mask, self.tokens["accent"])


class WelcomeDialog(QDialog):
    """Startbildschirm: zuletzt bearbeitete Projekte mit Vorschau + Aktionen."""

    def __init__(self, parent, tokens: dict):
        super().__init__(parent)
        self.setWindowTitle("Willkommen – PixelGlitch Studio")
        self.choice = None            # ("project", pfad) | ("new", name) | ("browse",)
        self.tokens = tokens
        self.setMinimumSize(660, 480)

        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(branding.logo_pixmap(56))
        title = QLabel(f"<div style='font-size:19px; font-weight:600;'>"
                       f"PixelGlitch Studio</div>"
                       f"<div style='color:{tokens['text_dim']};'>"
                       f"Version {__version__} · Pixel-Sorting &amp; Glitch-Art</div>")
        head.addWidget(logo)
        head.addSpacing(10)
        head.addWidget(title)
        head.addStretch(1)

        sub = QLabel("PROJEKTORDNER")
        sub.setProperty("role", "section")
        self.dir_label = QLabel()
        self.dir_label.setProperty("role", "hint")
        self.dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        dir_btn = QToolButton()
        dir_btn.setText("Ändern…")
        dir_btn.setToolTip("Anderen Projektordner wählen")
        dir_btn.clicked.connect(self._change_dir)
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        dir_row.addWidget(self.dir_label, 1)
        dir_row.addWidget(dir_btn)

        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.IconMode)
        self.grid.setIconSize(QSize(176, 120))
        self.grid.setGridSize(QSize(200, 172))
        self.grid.setResizeMode(QListWidget.Adjust)
        self.grid.setMovement(QListWidget.Static)
        self.grid.setWordWrap(True)
        self.grid.setUniformItemSizes(True)
        self.grid.itemActivated.connect(self._pick)
        self.grid.itemClicked.connect(self._pick)

        self.empty = QLabel("Noch keine Projekte in diesem Ordner – "
                            "leg mit »Neues Projekt« los.")
        self.empty.setProperty("role", "hint")
        self.empty.setAlignment(Qt.AlignCenter)

        btn_new = QPushButton(" Neues Projekt")
        btn_new.setIcon(icons.icon("plus", tokens["on_accent"], 16))
        btn_new.setProperty("accent", True)
        btn_new.clicked.connect(self._new_project)
        btn_proj = QPushButton(" Projekt öffnen…")
        btn_proj.setIcon(icons.icon("folder", tokens["text"], 16))
        btn_proj.clicked.connect(lambda: self._done(("browse",)))
        btns = QHBoxLayout()
        btns.addWidget(btn_new)
        btns.addWidget(btn_proj)
        btns.addStretch(1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 14)
        lay.setSpacing(10)
        lay.addLayout(head)
        lay.addSpacing(4)
        lay.addWidget(sub)
        lay.addLayout(dir_row)
        lay.addWidget(self.grid, 1)
        lay.addWidget(self.empty, 1)
        lay.addLayout(btns)
        self._reload()

    def _reload(self):
        folder = projects_dir()
        self.dir_label.setText(str(folder))
        self.grid.clear()
        files = scan_projects(folder)
        for p in files:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, p)
            ts = datetime.fromtimestamp(Path(p).stat().st_mtime)
            item.setText(f"{Path(p).stem}\n{ts.strftime('%d.%m.%Y %H:%M')}")
            pm = None
            data = engine.read_bundle_thumb(p)
            if data:
                pm = QPixmap()
                pm.loadFromData(data)
            if pm is None or pm.isNull():
                pm = branding.logo_pixmap(96)
            item.setIcon(QIcon(pm))
            self.grid.addItem(item)
        self.grid.setVisible(bool(files))
        self.empty.setVisible(not files)

    def _change_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Projektordner wählen",
                                             str(projects_dir()))
        if d:
            set_projects_dir(d)
            self._reload()

    def _new_project(self):
        default = f"Projekt {datetime.now():%Y-%m-%d}"
        name, okp = QInputDialog.getText(
            self, "Neues Projekt", "Projektname:", text=default)
        if not okp:
            return
        self._done(("new", name.strip() or default))

    def _pick(self, item):
        self._done(("project", item.data(Qt.UserRole)))

    def _done(self, choice):
        self.choice = choice
        self.accept()


def _set_process_name(name: str):
    """App-Name statt „Python" in Menüleiste/Taskbar (best effort)."""
    if sys.platform == "darwin":
        try:  # pyobjc (optional, in requirements.txt für macOS enthalten)
            from Foundation import NSBundle
            bundle = NSBundle.mainBundle()
            info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
            if info is not None:
                info["CFBundleName"] = name
                info["CFBundleDisplayName"] = name
        except Exception:
            pass
    elif sys.platform.startswith("win"):
        try:  # eigener Taskbar-Eintrag mit App-Icon statt Python-Gruppe
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "PixelGlitch.Studio")
        except Exception:
            pass


def main():
    _set_process_name("PixelGlitch Studio")
    app = QApplication(sys.argv)
    app.setApplicationName("PixelGlitch Studio")
    app.setApplicationDisplayName("PixelGlitch Studio")
    app.setDesktopFileName("pixelglitch-studio")
    app.setWindowIcon(QIcon(branding.logo_pixmap(128)))

    win = MainWindow()
    win.show()

    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg and Path(arg).exists():
        win._open_project_path(arg)              # Doppelklick/Argument: direkt öffnen
    else:
        dlg = WelcomeDialog(win, win.tokens)
        if dlg.exec() and dlg.choice:
            if dlg.choice[0] == "project":
                win._open_project_path(dlg.choice[1])
            elif dlg.choice[0] == "new":
                win._new_project(dlg.choice[1])
            elif dlg.choice[0] == "browse":
                win._open_project()
    sys.exit(app.exec())
