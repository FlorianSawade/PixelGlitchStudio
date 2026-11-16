"""UI-Bausteine: Canvas, aufklappbare Abschnitte, Parameter- und Ketten-Editor."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import (QFileSystemWatcher, QPointF, QRectF, QSize, Qt,
                            QTimer, Signal)
from PySide6.QtGui import (QBrush, QColor, QFont, QImage, QImageReader,
                           QPainter, QPen, QPixmap)
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFrame,
                               QGraphicsEllipseItem, QGraphicsPixmapItem,
                               QGraphicsRectItem, QGraphicsScene,
                               QGraphicsView, QGridLayout, QHBoxLayout,
                               QFileDialog, QLabel, QListWidget,
                               QListWidgetItem, QMenu, QPushButton, QSlider,
                               QSpinBox, QToolButton, QVBoxLayout, QWidget)

from .params import EFFECTS
from .masks import MaskRef, OPS, OP_LABELS
from . import icons


def np_to_qimage(arr: np.ndarray) -> QImage:
    h, w = arr.shape[:2]
    arr = np.ascontiguousarray(arr)
    return QImage(arr.data, w, h, 3 * w, QImage.Format_RGB888).copy()


# ================================================================= canvas

class Canvas(QGraphicsView):
    """Bildansicht: Zoom (Mausrad), Pan (Drag), Drag&Drop, Masken-Zeichnen."""

    fileDropped = Signal(str)
    rectDrawn = Signal(dict)      # normalisierte Geometrie
    ellipseDrawn = Signal(dict)
    polygonPoint = Signal(float, float)          # Punkt anhängen
    polygonMoved = Signal(int, float, float)     # Punkt i verschoben
    polygonInserted = Signal(int, float, float)  # Punkt bei i eingefügt
    polygonDeleted = Signal(int)                 # Punkt i gelöscht
    polygonDone = Signal()
    zoomChanged = Signal(float)

    def __init__(self, tokens: dict):
        super().__init__()
        self.tokens = tokens
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.pix_item = QGraphicsPixmapItem()
        self.pix_item.setTransformationMode(Qt.SmoothTransformation)
        self.overlay_item = QGraphicsPixmapItem()
        self.overlay_item.setZValue(5)
        self._scene.addItem(self.pix_item)
        self._scene.addItem(self.overlay_item)
        self._rubber = None
        self._draw_mode = "none"
        self._drag_start = None
        self._poly_markers = []
        self._poly_points: list = []     # normalisierte Punkte der aktiven Polygonmaske
        self._poly_drag = None           # Index des gezogenen Punkts
        self.has_image = False
        self._build_zoom_overlay()

        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.NoFrame)
        self.apply_tokens(tokens)

    def apply_tokens(self, tokens: dict):
        self.tokens = tokens
        self.setBackgroundBrush(QColor(tokens["canvas"]))
        self._style_zoom_overlay()
        self.viewport().update()

    # ---- zoom overlay (links unten im Bildbereich) -----------------------
    def _build_zoom_overlay(self):
        self._zoom_box = QWidget(self.viewport())
        lay = QHBoxLayout(self._zoom_box)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        self._zoom_btns = []
        for name, tip, fn in [("minus", "Herauszoomen", self.zoom_out),
                              ("plus", "Hineinzoomen", self.zoom_in),
                              ("fit", "Ansicht einpassen", self.fit)]:
            b = QToolButton(self._zoom_box)
            b.setToolTip(tip)
            b.setFixedSize(30, 30)
            b.setIconSize(QSize(18, 18))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            lay.addWidget(b)
            self._zoom_btns.append((b, name))
        self._style_zoom_overlay()
        self._zoom_box.adjustSize()
        self._zoom_box.raise_()

    def _style_zoom_overlay(self):
        if not hasattr(self, "_zoom_box"):
            return
        t = self.tokens
        self._zoom_box.setStyleSheet(
            f"QWidget {{ background: {t['panel']}; border: 1px solid {t['border_soft']};"
            f" border-radius: 8px; }}"
            f"QToolButton {{ background: transparent; border: none;"
            f" border-radius: 6px; padding: 0px; }}"
            f"QToolButton:hover {{ background: {t['input_hover']}; }}")
        for b, name in self._zoom_btns:
            b.setIcon(icons.icon(name, t["text"], 18))

    def _place_zoom_overlay(self):
        if hasattr(self, "_zoom_box"):
            self._zoom_box.move(10, self.viewport().height()
                                - self._zoom_box.height() - 10)
            self._zoom_box.raise_()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._place_zoom_overlay()

    def showEvent(self, ev):
        super().showEvent(ev)
        self._place_zoom_overlay()

    def _zoom_by(self, factor: float):
        if not self.has_image:
            return
        cur = self.transform().m11()
        if 0.02 < cur * factor < 40:
            self.scale(factor, factor)
            self.zoomChanged.emit(self.transform().m11())
            self._resize_poly_markers()

    def zoom_in(self):
        self._zoom_by(1.25)

    def zoom_out(self):
        self._zoom_by(1 / 1.25)

    # ---- image / overlay -------------------------------------------------
    def set_image(self, arr: np.ndarray | None):
        if arr is None:
            self.pix_item.setPixmap(QPixmap())
            self.overlay_item.setPixmap(QPixmap())
            self.has_image = False
        else:
            first = not self.has_image
            self.pix_item.setPixmap(QPixmap.fromImage(np_to_qimage(arr)))
            self._scene.setSceneRect(self.pix_item.boundingRect())
            self.has_image = True
            if first:
                self.fit()
        self.viewport().update()

    def set_overlay(self, mask: np.ndarray | None, accent: str):
        if mask is None or not self.has_image:
            self.overlay_item.setPixmap(QPixmap())
            return
        h, w = mask.shape
        c = QColor(accent)
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., 0], rgba[..., 1], rgba[..., 2] = c.red(), c.green(), c.blue()
        rgba[..., 3] = (mask * 150).astype(np.uint8)
        img = QImage(np.ascontiguousarray(rgba).data, w, h, 4 * w,
                     QImage.Format_RGBA8888).copy()
        pm = QPixmap.fromImage(img)
        br = self.pix_item.boundingRect()
        self.overlay_item.setPixmap(pm.scaled(int(br.width()), int(br.height())))

    # ---- zoom -------------------------------------------------------------
    def fit(self):
        if self.has_image:
            self.fitInView(self.pix_item, Qt.KeepAspectRatio)
            self.zoomChanged.emit(self.transform().m11())

    def wheelEvent(self, ev):
        self._zoom_by(1.15 if ev.angleDelta().y() > 0 else 1 / 1.15)

    # ---- drag & drop -------------------------------------------------------
    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dragMoveEvent(self, ev):
        ev.acceptProposedAction()

    def dropEvent(self, ev):
        urls = ev.mimeData().urls()
        if urls:
            self.fileDropped.emit(urls[0].toLocalFile())

    # ---- mask drawing -------------------------------------------------------
    def set_draw_mode(self, mode: str):
        self._draw_mode = mode
        self.clear_poly_markers()
        self.setDragMode(QGraphicsView.NoDrag if mode != "none"
                         else QGraphicsView.ScrollHandDrag)
        self.viewport().setCursor(Qt.CrossCursor if mode != "none" else Qt.ArrowCursor)

    def _norm(self, scene_pos: QPointF):
        br = self.pix_item.boundingRect()
        if br.width() < 1 or br.height() < 1:
            return None
        return (min(max(scene_pos.x() / br.width(), 0.0), 1.0),
                min(max(scene_pos.y() / br.height(), 0.0), 1.0))

    def clear_poly_markers(self):
        for m in self._poly_markers:
            self._scene.removeItem(m)
        self._poly_markers = []
        self._poly_points = []
        self._poly_drag = None

    def set_polygon_points(self, points: list):
        """Handles für alle Punkte der aktiven Polygonmaske anzeigen."""
        for m in self._poly_markers:
            self._scene.removeItem(m)
        self._poly_markers = []
        self._poly_points = [tuple(p) for p in points]
        br = self.pix_item.boundingRect()
        if not self.has_image or br.width() < 1:
            return
        for (nx, ny) in self._poly_points:
            self._make_marker(QPointF(nx * br.width(), ny * br.height()))

    def _marker_radius(self) -> float:
        return 5 / max(self.transform().m11(), 1e-3)

    def _make_marker(self, scene_pos: QPointF):
        r = self._marker_radius()
        dot = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
        dot.setPos(scene_pos)
        dot.setBrush(QBrush(QColor(self.tokens["accent"])))
        pen = QPen(QColor(self.tokens["on_accent"]))
        pen.setWidthF(r * 0.35)
        dot.setPen(pen)
        dot.setZValue(10)
        self._scene.addItem(dot)
        self._poly_markers.append(dot)

    def _resize_poly_markers(self):
        r = self._marker_radius()
        for dot in self._poly_markers:
            dot.setRect(-r, -r, 2 * r, 2 * r)

    def _hit_marker(self, scene_pos: QPointF) -> int | None:
        thresh = self._marker_radius() * 1.8
        for i, dot in enumerate(self._poly_markers):
            d = dot.pos() - scene_pos
            if (d.x() ** 2 + d.y() ** 2) ** 0.5 <= thresh:
                return i
        return None

    def _hit_edge(self, scene_pos: QPointF) -> int | None:
        """Index der Kante (i -> i+1), wenn nahe genug geklickt wurde."""
        if len(self._poly_markers) < 2:
            return None
        thresh = self._marker_radius() * 1.6
        best, best_d = None, thresh
        n = len(self._poly_markers)
        for i in range(n):
            a = self._poly_markers[i].pos()
            b = self._poly_markers[(i + 1) % n].pos()
            ab = b - a
            ap = scene_pos - a
            denom = ab.x() ** 2 + ab.y() ** 2
            if denom < 1e-9:
                continue
            t = max(0.0, min(1.0, (ap.x() * ab.x() + ap.y() * ab.y()) / denom))
            px, py = a.x() + t * ab.x(), a.y() + t * ab.y()
            d = ((scene_pos.x() - px) ** 2 + (scene_pos.y() - py) ** 2) ** 0.5
            if d < best_d:
                best, best_d = i, d
        return best

    def mousePressEvent(self, ev):
        if self._draw_mode in ("rect", "ellipse") and self.has_image \
                and ev.button() == Qt.LeftButton:
            self._drag_start = self.mapToScene(ev.position().toPoint())
            cls = QGraphicsRectItem if self._draw_mode == "rect" else QGraphicsEllipseItem
            self._rubber = cls()
            pen = QPen(QColor(self.tokens["accent"]), 0)
            pen.setStyle(Qt.DashLine)
            self._rubber.setPen(pen)
            self._rubber.setZValue(10)
            self._scene.addItem(self._rubber)
            return
        if self._draw_mode == "polygon" and self.has_image:
            pos = self.mapToScene(ev.position().toPoint())
            hit = self._hit_marker(pos)
            if ev.button() == Qt.RightButton:
                if hit is not None:
                    self.polygonDeleted.emit(hit)
                return
            if ev.button() == Qt.LeftButton:
                if hit is not None:                      # Punkt anfassen
                    self._poly_drag = hit
                    return
                edge = self._hit_edge(pos)
                n = self._norm(pos)
                if n is None:
                    return
                if edge is not None:                     # auf Kante einfügen
                    self.polygonInserted.emit(edge + 1, *n)
                else:                                    # neuen Punkt anhängen
                    self.polygonPoint.emit(*n)
                return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._rubber is not None and self._drag_start is not None:
            cur = self.mapToScene(ev.position().toPoint())
            self._rubber.setRect(QRectF(self._drag_start, cur).normalized())
            return
        if self._poly_drag is not None:
            pos = self.mapToScene(ev.position().toPoint())
            n = self._norm(pos)
            if n:
                br = self.pix_item.boundingRect()
                self._poly_markers[self._poly_drag].setPos(
                    QPointF(n[0] * br.width(), n[1] * br.height()))
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if self._poly_drag is not None:
            i = self._poly_drag
            self._poly_drag = None
            n = self._norm(self._poly_markers[i].pos())
            if n:
                self.polygonMoved.emit(i, *n)
            return
        if self._rubber is not None and self._drag_start is not None:
            rect = self._rubber.rect()
            self._scene.removeItem(self._rubber)
            self._rubber = None
            a = self._norm(rect.topLeft())
            b = self._norm(rect.bottomRight())
            self._drag_start = None
            if a and b and abs(b[0] - a[0]) > 0.005 and abs(b[1] - a[1]) > 0.005:
                if self._draw_mode == "rect":
                    self.rectDrawn.emit({"x": a[0], "y": a[1],
                                         "w": b[0] - a[0], "h": b[1] - a[1]})
                else:
                    self.ellipseDrawn.emit({"cx": (a[0] + b[0]) / 2, "cy": (a[1] + b[1]) / 2,
                                            "rx": (b[0] - a[0]) / 2, "ry": (b[1] - a[1]) / 2})
            return
        super().mouseReleaseEvent(ev)

    def mouseDoubleClickEvent(self, ev):
        if self._draw_mode == "polygon":
            self.polygonDone.emit()
            return
        super().mouseDoubleClickEvent(ev)

    # ---- empty state ---------------------------------------------------------
    def drawForeground(self, painter, rect):
        if self.has_image:
            return
        painter.resetTransform()
        painter.setPen(QColor(self.tokens["text_dim"]))
        f = QFont()
        f.setPointSize(13)
        painter.setFont(f)
        vp = self.viewport().rect()
        painter.drawText(vp.adjusted(0, -14, 0, -14), Qt.AlignCenter,
                         "Bild hierher ziehen")
        f.setPointSize(10)
        painter.setFont(f)
        painter.drawText(vp.adjusted(0, 16, 0, 16), Qt.AlignCenter,
                         "oder über „Bild öffnen“ in der Werkzeugleiste")


# ============================================================ collapsible

class CollapsibleSection(QWidget):
    def __init__(self, title: str, tokens: dict, expanded: bool = True):
        super().__init__()
        self.tokens = tokens
        self.header = QToolButton()
        self.header.setText("  " + title)
        self.header.setCheckable(True)
        self.header.setChecked(expanded)
        self.header.setProperty("flat", True)
        self.header.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.header.setStyleSheet("QToolButton { font-weight: 700; border: none;"
                                  " background: transparent; padding: 6px 2px; }")
        self.header.toggled.connect(self._toggle)

        self.body = QFrame()
        self.body.setProperty("role", "card")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(10, 10, 10, 10)
        self.body_layout.setSpacing(8)

        self.header_row = QHBoxLayout()
        self.header_row.setContentsMargins(0, 0, 0, 0)
        self.header_row.setSpacing(4)
        self.header_row.addWidget(self.header, 1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addLayout(self.header_row)
        lay.addWidget(self.body)
        self._update_icon()

    def _toggle(self, on):
        self.body.setVisible(on)
        self._update_icon()

    def _update_icon(self):
        name = "chev_down" if self.header.isChecked() else "chev_right"
        self.header.setIcon(icons.icon(name, self.tokens["text_dim"], 14))

    def add_header_widget(self, widget: QWidget):
        """Aktion rechts in der Abschnitts-Kopfzeile ablegen."""
        self.header_row.addWidget(widget)

    def set_title(self, title: str):
        self.header.setText("  " + title)

    def set_content(self, w: QWidget):
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.body_layout.addWidget(w)


# ============================================================ param editor

class ParamEditor(QWidget):
    """Baut Regler automatisch aus ParamSpecs; 🎲-Toggle pro Parameter."""
    changed = Signal()
    randChanged = Signal()      # 🎲-Markierung gesetzt oder entfernt

    def __init__(self, layer, tokens: dict):
        super().__init__()
        self.layer = layer
        self.tokens = tokens
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)

        for row, spec in enumerate(EFFECTS[layer.effect].params):
            lab = QLabel(spec.label)
            lab.setMinimumWidth(96)
            grid.addWidget(lab, row, 0)
            grid.addWidget(self._control(spec), row, 1)
            if spec.randomizable:
                dice = QToolButton()
                dice.setProperty("flat", True)
                dice.setCheckable(True)
                dice.setChecked(spec.key in layer.rand_keys)
                dice.setToolTip("Im Batch zufällig variieren")
                dice.setIcon(icons.icon(
                    "dice", tokens["accent"] if dice.isChecked() else tokens["text_dim"], 16))
                dice.toggled.connect(lambda on, k=spec.key, b=dice: self._dice(k, on, b))
                grid.addWidget(dice, row, 2)

    def _dice(self, key, on, btn):
        (self.layer.rand_keys.add if on else self.layer.rand_keys.discard)(key)
        self.randChanged.emit()
        btn.setIcon(icons.icon(
            "dice", self.tokens["accent"] if on else self.tokens["text_dim"], 16))

    def _set(self, key, value):
        self.layer.params[key] = value
        self.changed.emit()

    def _control(self, spec) -> QWidget:
        val = self.layer.params[spec.key]
        if spec.kind == "bool":
            cb = QCheckBox()
            cb.setChecked(bool(val))
            cb.toggled.connect(lambda on, k=spec.key: self._set(k, bool(on)))
            return cb
        if spec.kind == "choice":
            combo = QComboBox()
            labels = spec.choice_labels or spec.choices
            for c, lab in zip(spec.choices, labels):
                combo.addItem(lab, c)
            combo.setCurrentIndex(spec.choices.index(val))
            combo.currentIndexChanged.connect(
                lambda i, k=spec.key, c=combo: self._set(k, c.itemData(i)))
            return combo

        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        slider = QSlider(Qt.Horizontal)
        if spec.kind == "int":
            spin = QSpinBox()
            spin.setRange(int(spec.lo), int(spec.hi))
            spin.setSingleStep(int(spec.step or 1))
            spin.setValue(int(val))
            slider.setRange(int(spec.lo), int(spec.hi))
            slider.setValue(int(val))
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            spin.valueChanged.connect(lambda v, k=spec.key: self._set(k, int(v)))
        else:
            step = spec.step or 0.01
            spin = QDoubleSpinBox()
            spin.setDecimals(max(0, len(str(step).split(".")[-1])) if "." in str(step) else 1)
            spin.setRange(spec.lo, spec.hi)
            spin.setSingleStep(step)
            spin.setValue(float(val))
            mult = 1.0 / step
            slider.setRange(int(spec.lo * mult), int(spec.hi * mult))
            slider.setValue(int(float(val) * mult))
            slider.valueChanged.connect(lambda v: spin.setValue(v / mult))
            spin.valueChanged.connect(
                lambda v: slider.blockSignals(True) or slider.setValue(int(v * mult))
                or slider.blockSignals(False))
            spin.valueChanged.connect(lambda v, k=spec.key: self._set(k, float(v)))
        spin.setFixedWidth(74)
        lay.addWidget(slider, 1)
        lay.addWidget(spin)
        return box


# ============================================================ chain editor

class MaskChainEditor(QWidget):
    """Masken-Kette einer Ebene: [Op] [Maske] [Invert] [Kante %] [x], plus Endkante."""
    changed = Signal()

    def __init__(self, layer, project, tokens: dict):
        super().__init__()
        self.layer = layer
        self.project = project
        self.tokens = tokens
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(6)
        self.rebuild()

    def rebuild(self):
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear(item.layout())

        masks = self.project.ordered_masks()
        if not masks:
            hint = QLabel("Noch keine Masken – im Tab „Masken“ anlegen.")
            hint.setProperty("role", "hint")
            self.vbox.addWidget(hint)
            return

        for i, ref in enumerate(self.layer.refs):
            self.vbox.addWidget(self._row(i, ref, masks))

        addrow = QHBoxLayout()
        add = QPushButton(" Maske hinzufügen")
        add.setIcon(icons.icon("plus", self.tokens["text"], 14))
        add.clicked.connect(self._add)
        addrow.addWidget(add)
        addrow.addStretch(1)
        if self.layer.refs:
            addrow.addWidget(QLabel("Endkante %"))
            ff = QDoubleSpinBox()
            ff.setRange(0, 25)
            ff.setSingleStep(0.5)
            ff.setValue(self.layer.final_feather)
            ff.setFixedWidth(70)
            ff.setToolTip("Weiche Kante auf das kombinierte Ergebnis")
            ff.valueChanged.connect(self._set_ff)
            addrow.addWidget(ff)
        self.vbox.addLayout(addrow)

    def _clear(self, lay):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _row(self, i: int, ref: MaskRef, masks) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        if i > 0:
            op = QComboBox()
            for o in OPS:
                op.addItem(OP_LABELS[o], o)
            op.setCurrentIndex(OPS.index(ref.op if ref.op in OPS else "union"))
            op.setFixedWidth(118)
            op.currentIndexChanged.connect(
                lambda idx, r=ref, c=op: (setattr(r, "op", c.itemData(idx)),
                                          self.changed.emit()))
            lay.addWidget(op)

        combo = QComboBox()
        for m in masks:
            combo.addItem(m.name, m.id)
        ids = [m.id for m in masks]
        if ref.mask_id in ids:
            combo.setCurrentIndex(ids.index(ref.mask_id))
        combo.currentIndexChanged.connect(
            lambda idx, r=ref, c=combo: (setattr(r, "mask_id", c.itemData(idx)),
                                         self.changed.emit()))
        lay.addWidget(combo, 1)

        inv = QToolButton()
        inv.setProperty("flat", True)
        inv.setText("¬")
        inv.setCheckable(True)
        inv.setChecked(ref.invert)
        inv.setToolTip("Invertieren")
        inv.setFixedWidth(28)
        inv.toggled.connect(lambda on, r=ref: (setattr(r, "invert", bool(on)),
                                               self.changed.emit()))
        lay.addWidget(inv)

        feather = QDoubleSpinBox()
        feather.setRange(0, 25)
        feather.setSingleStep(0.5)
        feather.setValue(ref.feather)
        feather.setFixedWidth(66)
        feather.setToolTip("Weiche Kante %")
        feather.valueChanged.connect(lambda v, r=ref: (setattr(r, "feather", float(v)),
                                                       self.changed.emit()))
        lay.addWidget(feather)

        rm = QToolButton()
        rm.setProperty("flat", True)
        rm.setIcon(icons.icon("x", self.tokens["text_dim"], 13))
        rm.setToolTip("Entfernen")
        rm.clicked.connect(lambda _, idx=i: self._remove(idx))
        lay.addWidget(rm)
        return row

    def _add(self):
        masks = self.project.ordered_masks()
        if masks:
            self.layer.refs.append(MaskRef(mask_id=masks[0].id))
            self.rebuild()
            self.changed.emit()

    def _remove(self, idx: int):
        del self.layer.refs[idx]
        self.rebuild()
        self.changed.emit()

    def _set_ff(self, v):
        self.layer.final_feather = float(v)
        self.changed.emit()


# ============================================================ layer item

class LayerItemWidget(QWidget):
    visibilityToggled = Signal(bool)

    def __init__(self, title: str, subtitle: str, enabled: bool, tokens: dict):
        super().__init__()
        self.tokens = tokens
        self.title = QLabel(title)
        self.title.setStyleSheet("font-weight: 600;")
        self.sub = QLabel(subtitle)
        self.sub.setStyleSheet(f"color: {tokens['text_dim']}; font-size: 11px;")

        self.eye = QToolButton()
        self.eye.setProperty("flat", True)
        self.eye.setCheckable(True)
        self.eye.setChecked(enabled)
        self.eye.setFixedSize(26, 26)
        self._eye_icon(enabled)
        self.eye.toggled.connect(self._on_eye)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(0)
        text.addWidget(self.title)
        text.addWidget(self.sub)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 5, 6, 5)
        lay.setSpacing(8)
        lay.addWidget(self.eye)
        lay.addLayout(text, 1)

    def _eye_icon(self, on):
        color = self.tokens["text"] if on else self.tokens["text_dim"]
        self.eye.setIcon(icons.icon("eye" if on else "eye_off", color, 16))
        self.title.setStyleSheet(
            "font-weight: 600;" + ("" if on else f" color: {self.tokens['text_dim']};"))

    def _on_eye(self, on):
        self._eye_icon(on)
        self.visibilityToggled.emit(on)


# ---------------------------------------------------------------- gallery

class StarBar(QLabel):
    """Fünf klickbare Sterne (kompakt, monospace)."""

    changed = Signal(int)

    def __init__(self, tokens: dict, value: int = 0, parent=None):
        super().__init__(parent)
        self.tokens = tokens
        self.value = int(value)
        f = QFont("Menlo, Consolas, monospace")
        f.setPixelSize(12)
        self.setFont(f)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Bewerten – nochmal auf denselben Stern klickt zurück auf 0")
        self._render()

    def set_tokens(self, tokens: dict):
        self.tokens = tokens
        self._render()

    def set_value(self, value: int):
        self.value = max(0, min(5, int(value)))
        self._render()

    def _render(self):
        filled = "★" * self.value
        empty = "☆" * (5 - self.value)
        col = self.tokens["accent"] if self.value else self.tokens["text_dim"]
        self.setText(f"<span style='color:{col};'>{filled}</span>"
                     f"<span style='color:{self.tokens['text_dim']};'>{empty}</span>")

    def mousePressEvent(self, ev):
        if self.width() < 1:
            return
        star = int(ev.position().x() / (self.width() / 5)) + 1
        star = max(1, min(5, star))
        new = 0 if star == self.value else star     # gleicher Stern = zurücksetzen
        self.set_value(new)
        self.changed.emit(new)


class GalleryTile(QWidget):
    """Kachel: Vorschau 3:2, darunter Dateiname links, Bewertung rechts."""

    rated = Signal(str, int)

    THUMB_W, THUMB_H = 200, 133

    def __init__(self, path: str, pixmap: QPixmap, stars: int, tokens: dict,
                 parent=None):
        super().__init__(parent)
        self.path = path
        self.setFixedSize(self.THUMB_W + 12, self.THUMB_H + 34)

        thumb = QLabel()
        thumb.setFixedSize(self.THUMB_W, self.THUMB_H)
        thumb.setAlignment(Qt.AlignCenter)
        if not pixmap.isNull():
            thumb.setPixmap(pixmap.scaled(self.THUMB_W, self.THUMB_H,
                                          Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation))
        thumb.setStyleSheet(f"background: {tokens['canvas']}; border-radius: 4px;")

        from pathlib import Path as _P
        name = QLabel(_P(path).name)
        f = QFont("Menlo, Consolas, monospace")
        f.setPixelSize(10)
        name.setFont(f)
        name.setStyleSheet(f"color: {tokens['text_dim']};")
        name.setMinimumWidth(1)

        self.stars = StarBar(tokens, stars)
        self.stars.changed.connect(lambda v: self.rated.emit(self.path, v))

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(name, 1)
        row.addWidget(self.stars, 0, Qt.AlignRight)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(4)
        lay.addWidget(thumb, 0, Qt.AlignHCenter)
        lay.addLayout(row)


class GalleryPanel(QWidget):
    """Beobachtet einen Ausgabeordner, zeigt Bilder als bewertbare Kacheln."""

    fileActivated = Signal(str)      # Doppelklick: groß in der Vorschau zeigen
    openAsSource = Signal(str)       # Kontextmenü: als Quellbild übernehmen
    adoptRequested = Signal(str)     # Variante ins Projekt übernehmen

    EXTS = (".png", ".jpg", ".jpeg")
    FILTERS = [("Alle Bewertungen", 0), ("★ 1+", 1), ("★ 2+", 2),
               ("★ 3+", 3), ("★ 4+", 4), ("★ 5", 5)]

    def __init__(self, tokens: dict, folder: str = "", parent=None):
        super().__init__(parent)
        self.tokens = tokens
        self.folder = folder
        self._thumb_cache = {}       # pfad -> (mtime, QPixmap)

        self.dir_label = QLabel("–")
        self.dir_label.setProperty("role", "hint")
        self.dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        pick = QToolButton()
        pick.setText("Ordner…")
        pick.clicked.connect(self._pick_folder)
        self.project_only = QCheckBox("Nur aktuelles Projekt")
        self.project_only.setToolTip(
            "Zeigt nur Dateien, deren Name mit dem Präfix dieses Projekts "
            "beginnt.")
        self.project_only.setChecked(True)
        self.project_only.toggled.connect(lambda _v: self.reload())
        self.project_prefix = ""
        self.filter_box = QComboBox()
        for label, _v in self.FILTERS:
            self.filter_box.addItem(label)
        self.filter_box.currentIndexChanged.connect(lambda _i: self.reload())
        reload_btn = QToolButton()
        reload_btn.setText("Neu laden")
        reload_btn.clicked.connect(self.reload)

        self.head_row = QHBoxLayout()
        self.head_row.setSpacing(8)
        self.head_row.addWidget(self.dir_label, 1)
        self.head_row.addWidget(self.project_only)
        self.head_row.addWidget(self.filter_box)
        self.head_row.addWidget(pick)
        self.head_row.addWidget(reload_btn)
        head = self.head_row

        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.IconMode)
        self.grid.setResizeMode(QListWidget.Adjust)
        self.grid.setMovement(QListWidget.Static)
        self.grid.setUniformItemSizes(True)
        self.grid.setSpacing(6)
        self.grid.setGridSize(QSize(GalleryTile.THUMB_W + 20,
                                    GalleryTile.THUMB_H + 42))
        self.grid.setSelectionMode(QListWidget.SingleSelection)
        self.grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._context_menu)
        self.grid.itemDoubleClicked.connect(
            lambda it: self.fileActivated.emit(it.data(Qt.UserRole)))

        self.empty = QLabel("Keine Bilder in diesem Ordner.")
        self.empty.setProperty("role", "hint")
        self.empty.setAlignment(Qt.AlignCenter)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)
        lay.addLayout(head)
        lay.addWidget(self.grid, 1)
        lay.addWidget(self.empty, 1)

        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_dir_changed)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(400)
        self._debounce.timeout.connect(self.reload)

        if folder:
            self.set_folder(folder)

    # ------------------------------------------------------------- api
    def set_folder(self, folder: str):
        from pathlib import Path as _P
        old = self._watcher.directories()
        if old:
            self._watcher.removePaths(old)
        self.folder = folder
        self.dir_label.setText(folder or "–")
        if folder and _P(folder).is_dir():
            self._watcher.addPath(folder)
        self.reload()

    def set_tokens(self, tokens: dict):
        self.tokens = tokens
        self.reload()

    def current_path(self) -> str:
        item = self.grid.currentItem()
        return item.data(Qt.UserRole) if item is not None else ""

    def set_project_prefix(self, prefix: str):
        """Dateinamen-Präfix des aktuellen Projekts (Batch-Präfix)."""
        prefix = (prefix or "").strip()
        if prefix != self.project_prefix:
            self.project_prefix = prefix
            self.reload()
        self.project_only.setEnabled(bool(prefix))

    def belongs_to_project(self, name: str) -> bool:
        if not self.project_prefix:
            return True
        return name.startswith(self.project_prefix + "_")

    def min_stars(self) -> int:
        return self.FILTERS[self.filter_box.currentIndex()][1]

    def files(self) -> list:
        """Sichtbare Dateien nach Filter, neueste zuerst."""
        from pathlib import Path as _P
        from . import engine
        if not self.folder or not _P(self.folder).is_dir():
            return []
        ratings = engine.load_ratings(self.folder)
        items = [p for p in _P(self.folder).iterdir()
                 if p.suffix.lower() in self.EXTS]
        items.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        lo = self.min_stars()
        only = self.project_only.isChecked() and bool(self.project_prefix)
        return [str(p) for p in items
                if ratings.get(p.name, 0) >= lo
                and (not only or self.belongs_to_project(p.name))]

    def reload(self):
        from pathlib import Path as _P
        from . import engine
        self.grid.clear()
        ratings = (engine.load_ratings(self.folder) if self.folder else {})
        paths = self.files()
        for path in paths:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, path)
            item.setSizeHint(QSize(GalleryTile.THUMB_W + 12,
                                   GalleryTile.THUMB_H + 34))
            self.grid.addItem(item)
            tile = GalleryTile(path, self._thumb(path),
                               ratings.get(_P(path).name, 0), self.tokens)
            tile.rated.connect(self._on_rated)
            self.grid.setItemWidget(item, tile)
        has = bool(paths)
        self.grid.setVisible(has)
        self.empty.setVisible(not has)
        if self.min_stars() > 0:
            self.empty.setText("Keine Bilder mit dieser Mindestbewertung.")
        elif self.project_only.isChecked() and self.project_prefix:
            self.empty.setText(
                f"Keine Bilder mit dem Präfix »{self.project_prefix}« in diesem "
                "Ordner. Häkchen entfernen zeigt alle.")
        else:
            self.empty.setText("Keine Bilder in diesem Ordner.")

    # --------------------------------------------------------- intern
    def _thumb(self, path: str) -> QPixmap:
        from pathlib import Path as _P
        try:
            mtime = _P(path).stat().st_mtime
        except OSError:
            return QPixmap()
        cached = self._thumb_cache.get(path)
        if cached and cached[0] == mtime:
            return cached[1]
        reader = QImageReader(path)
        sz = reader.size()
        if sz.isValid() and sz.width() > 0:
            scale = min(1.0, (GalleryTile.THUMB_W * 2) / sz.width())
            reader.setScaledSize(QSize(max(1, int(sz.width() * scale)),
                                       max(1, int(sz.height() * scale))))
        img = reader.read()
        pm = QPixmap.fromImage(img) if not img.isNull() else QPixmap()
        self._thumb_cache[path] = (mtime, pm)
        return pm

    def _on_rated(self, path: str, stars: int):
        from pathlib import Path as _P
        from . import engine
        engine.save_rating(self.folder, _P(path).name, stars)
        if self.min_stars() > 0 and stars < self.min_stars():
            self.reload()                 # fällt aus dem aktiven Filter

    def _on_dir_changed(self, _path: str):
        self._debounce.start()

    def _pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Galerie-Ordner wählen",
                                             self.folder or "")
        if d:
            self.set_folder(d)

    def _context_menu(self, pos):
        item = self.grid.itemAt(pos)
        if item is None:
            return
        path = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("Groß in der Vorschau zeigen",
                       lambda: self.fileActivated.emit(path))
        menu.addAction("Variante ins Projekt übernehmen",
                       lambda: self.adoptRequested.emit(path))
        menu.addAction("Als Quellbild übernehmen",
                       lambda: self.openAsSource.emit(path))
        menu.exec(self.grid.mapToGlobal(pos))
