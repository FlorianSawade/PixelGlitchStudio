"""Masken-Bibliothek (GUI-frei).

Masken sind benannte, wiederverwendbare Objekte mit normalisierter Geometrie
(Koordinaten 0..1, damit Vorschau und Export identisch wirken). Ebenen
referenzieren Masken über MaskRef-Ketten: der erste Eintrag setzt die Basis,
weitere verknüpfen per Vereinigung (max), Schnitt (min) oder Abzug (Differenz).
Invertieren und weiche Kante gehören zur Referenz, nicht zur Maske.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

MASK_KINDS = ["rect", "ellipse", "polygon", "linear", "radial", "image"]
MASK_KIND_LABELS = {
    "rect": "Rechteck", "ellipse": "Ellipse", "polygon": "Polygon",
    "linear": "Linearer Verlauf", "radial": "Radialer Verlauf", "image": "Bildmaske",
}
OPS = ["union", "intersect", "subtract"]
OP_LABELS = {"union": "∪ Vereinigen", "intersect": "∩ Schneiden", "subtract": "− Abziehen"}

_SS = 3  # Supersampling für glatte Formkanten


def _default_params(kind: str) -> dict:
    if kind == "rect":
        return {"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5}
    if kind == "ellipse":
        return {"cx": 0.5, "cy": 0.5, "rx": 0.3, "ry": 0.3}
    if kind == "polygon":
        return {"points": []}
    if kind == "linear":
        return {"angle": 0.0, "start": 0.2, "end": 0.8}
    if kind == "radial":
        return {"cx": 0.5, "cy": 0.5, "radius": 0.4, "inner": 0.5}
    if kind == "image":
        return {"path": ""}
    raise ValueError(kind)


@dataclass
class Mask:
    kind: str
    name: str = ""
    params: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])

    def __post_init__(self):
        base = _default_params(self.kind)
        base.update(self.params)
        self.params = base
        if not self.name:
            self.name = MASK_KIND_LABELS[self.kind]

    # ---- rendering ------------------------------------------------------
    def render(self, w: int, h: int) -> np.ndarray:
        """Float32-Maske (H, W) in [0, 1]."""
        p = self.params
        if self.kind in ("rect", "ellipse", "polygon"):
            W, H = w * _SS, h * _SS
            img = Image.new("L", (W, H), 0)
            d = ImageDraw.Draw(img)
            if self.kind == "rect":
                d.rectangle([p["x"] * W, p["y"] * H,
                             (p["x"] + p["w"]) * W, (p["y"] + p["h"]) * H], fill=255)
            elif self.kind == "ellipse":
                d.ellipse([(p["cx"] - p["rx"]) * W, (p["cy"] - p["ry"]) * H,
                           (p["cx"] + p["rx"]) * W, (p["cy"] + p["ry"]) * H], fill=255)
            else:
                pts = [(x * W, y * H) for x, y in p.get("points", [])]
                if len(pts) >= 3:
                    d.polygon(pts, fill=255)
            img = img.resize((w, h), Image.BILINEAR)
            return np.asarray(img, dtype=np.float32) / 255.0

        if self.kind == "linear":
            ang = np.deg2rad(p["angle"])
            xs, ys = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
            t = xs * np.cos(ang) + ys * np.sin(ang)
            t = (t - t.min()) / max(t.max() - t.min(), 1e-6)
            a, b = p["start"], p["end"]
            if abs(b - a) < 1e-6:
                return (t >= a).astype(np.float32)
            return np.clip((t - a) / (b - a), 0, 1).astype(np.float32)

        if self.kind == "radial":
            xs, ys = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
            aspect = w / max(h, 1)
            dx = (xs - p["cx"]) * aspect
            dy = ys - p["cy"]
            dist = np.sqrt(dx * dx + dy * dy) / max(p["radius"] * max(aspect, 1.0), 1e-6)
            inner = np.clip(p["inner"], 0.0, 0.99)
            m = 1.0 - np.clip((dist - inner) / max(1.0 - inner, 1e-6), 0, 1)
            return m.astype(np.float32)

        if self.kind == "image":
            path = p.get("path", "")
            try:
                img = Image.open(path).convert("L").resize((w, h), Image.BILINEAR)
                return np.asarray(img, dtype=np.float32) / 255.0
            except Exception:
                return np.zeros((h, w), dtype=np.float32)

        raise ValueError(self.kind)

    # ---- (de)serialization ----------------------------------------------
    def to_json(self) -> dict:
        return {"id": self.id, "kind": self.kind, "name": self.name, "params": self.params}

    @classmethod
    def from_json(cls, d: dict) -> "Mask":
        return cls(kind=d["kind"], name=d.get("name", ""),
                   params=dict(d.get("params", {})), id=d.get("id", uuid.uuid4().hex[:10]))


@dataclass
class MaskRef:
    """Ein Glied der Masken-Kette einer Ebene."""
    mask_id: str
    op: str = "union"          # beim ersten Eintrag ignoriert
    invert: bool = False
    feather: float = 0.0       # weiche Kante, % der kürzeren Bildseite (0..25)

    def to_json(self) -> dict:
        return {"mask_id": self.mask_id, "op": self.op,
                "invert": self.invert, "feather": self.feather}

    @classmethod
    def from_json(cls, d: dict) -> "MaskRef":
        return cls(mask_id=d["mask_id"], op=d.get("op", "union"),
                   invert=bool(d.get("invert", False)), feather=float(d.get("feather", 0.0)))


def _feather(m: np.ndarray, percent: float) -> np.ndarray:
    if percent <= 0:
        return m
    h, w = m.shape
    radius = percent / 100.0 * min(w, h)
    if radius < 0.5:
        return m
    img = Image.fromarray((m * 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(img, dtype=np.float32) / 255.0


def combine_refs(refs: list[MaskRef], library: dict[str, Mask],
                 w: int, h: int, final_feather: float = 0.0) -> np.ndarray | None:
    """Masken-Kette auswerten. None = keine Maske (Effekt wirkt überall).

    Verknüpfung auf Graustufen: Vereinigung = max, Schnitt = min,
    Abzug = auf 0 geklemmte Differenz – verhält sich an harten Kanten wie
    Mengenlogik und an weichen Kanten intuitiv.
    """
    acc = None
    for i, ref in enumerate(refs):
        mask = library.get(ref.mask_id)
        if mask is None:
            continue
        m = mask.render(w, h)
        m = _feather(m, ref.feather)
        if ref.invert:
            m = 1.0 - m
        if acc is None:
            acc = m
        elif ref.op == "intersect":
            acc = np.minimum(acc, m)
        elif ref.op == "subtract":
            acc = np.clip(acc - m, 0.0, 1.0)
        else:
            acc = np.maximum(acc, m)
    if acc is not None and final_feather > 0:
        acc = _feather(acc, final_feather)
    return acc
