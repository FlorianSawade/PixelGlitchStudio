"""Engine: Bild-IO, Ebenen-Pipeline, Projekt (de)serialisierung, Batch.

Pipeline-Semantik: sequenziell, Ebenen von oben nach unten – jede Ebene sieht
das Ergebnis der vorherigen. Jede Ebene rendert ihren Effekt auf das volle
Bild und wird über ihre kombinierte Maske eingeblendet.
"""
from __future__ import annotations

import io
import json
import re
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from .params import EFFECTS, effect_defaults, random_value
from .masks import Mask, MaskRef, combine_refs

PROJECT_VERSION = 2


# ---------------------------------------------------------------- image io

def load_image(path: str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB")).copy()


def save_image(arr: np.ndarray, path: str, fmt: str | None = None,
               quality: int = 95):
    img = Image.fromarray(arr)
    if fmt and fmt.upper() in ("JPEG", "JPG"):
        img.save(path, "JPEG", quality=int(quality))
    else:
        img.save(path)


def downscale(arr: np.ndarray, max_size: int) -> np.ndarray:
    h, w = arr.shape[:2]
    if max(h, w) <= max_size:
        return arr
    scale = max_size / max(h, w)
    img = Image.fromarray(arr).resize((max(1, int(w * scale)), max(1, int(h * scale))),
                                      Image.BILINEAR)
    return np.asarray(img).copy()


# ---------------------------------------------------------------- model

@dataclass
class Layer:
    effect: str
    params: dict = field(default_factory=dict)
    enabled: bool = True
    refs: list = field(default_factory=list)        # list[MaskRef]
    final_feather: float = 0.0
    rand_keys: set = field(default_factory=set)     # 🎲-markierte Parameter
    rand_enabled: bool = True                       # Ebene nimmt am Batch-Würfeln teil
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])

    def __post_init__(self):
        cls = EFFECTS[self.effect]
        base = effect_defaults(cls)
        base.update(self.params)
        self.params = base

    @property
    def label(self) -> str:
        return EFFECTS[self.effect].label

    def to_json(self) -> dict:
        return {"id": self.id, "effect": self.effect, "params": self.params,
                "enabled": self.enabled, "final_feather": self.final_feather,
                "refs": [r.to_json() for r in self.refs],
                "rand_keys": sorted(self.rand_keys),
                "rand_enabled": self.rand_enabled}

    @classmethod
    def from_json(cls, d: dict) -> "Layer":
        valid = {s.key for s in EFFECTS[d["effect"]].params}
        return cls(effect=d["effect"], params=dict(d.get("params", {})),
                   enabled=bool(d.get("enabled", True)),
                   refs=[MaskRef.from_json(r) for r in d.get("refs", [])],
                   final_feather=float(d.get("final_feather", 0.0)),
                   rand_keys={k for k in d.get("rand_keys", []) if k in valid},
                   rand_enabled=bool(d.get("rand_enabled", True)),
                   id=d.get("id", uuid.uuid4().hex[:10]))


@dataclass
class Project:
    layers: list = field(default_factory=list)      # list[Layer], oben zuerst
    masks: dict = field(default_factory=dict)       # id -> Mask (Bibliothek)
    mask_order: list = field(default_factory=list)  # Anzeige-Reihenfolge (ids)

    # ---- mask library ----------------------------------------------------
    def add_mask(self, mask: Mask) -> Mask:
        base, i = mask.name, 2
        names = {m.name for m in self.masks.values()}
        while mask.name in names:
            mask.name = f"{base} {i}"
            i += 1
        self.masks[mask.id] = mask
        self.mask_order.append(mask.id)
        return mask

    def mask_usage(self, mask_id: str) -> list:
        """Ebenen, die diese Maske referenzieren."""
        return [ly for ly in self.layers if any(r.mask_id == mask_id for r in ly.refs)]

    def remove_mask(self, mask_id: str) -> bool:
        """Löschschutz: schlägt fehl, wenn noch referenziert."""
        if self.mask_usage(mask_id):
            return False
        self.masks.pop(mask_id, None)
        if mask_id in self.mask_order:
            self.mask_order.remove(mask_id)
        return True

    def ordered_masks(self) -> list:
        return [self.masks[i] for i in self.mask_order if i in self.masks]

    # ---- (de)serialization ----------------------------------------------
    def to_json(self) -> dict:
        return {"version": PROJECT_VERSION,
                "masks": [m.to_json() for m in self.ordered_masks()],
                "layers": [ly.to_json() for ly in self.layers]}

    @classmethod
    def from_json(cls, d: dict) -> "Project":
        p = cls()
        if d.get("version", 1) < 2:
            _migrate_v1(d, p)
            return p
        for md in d.get("masks", []):
            m = Mask.from_json(md)
            p.masks[m.id] = m
            p.mask_order.append(m.id)
        p.layers = [Layer.from_json(ld) for ld in d.get("layers", [])]
        # verwaiste Referenzen entfernen
        for ly in p.layers:
            ly.refs = [r for r in ly.refs if r.mask_id in p.masks]
        return p

    def save(self, path: str):
        Path(path).write_text(json.dumps(self.to_json(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "Project":
        return cls.from_json(json.loads(Path(path).read_text(encoding="utf-8")))


def _migrate_v1(d: dict, p: Project):
    """v1: Maske lag inline an der Ebene -> Bibliothekseintrag + eine Referenz."""
    for ld in d.get("layers", []):
        old = ld.pop("mask", None)
        ly = Layer(effect=ld["effect"], params=dict(ld.get("params", {})),
                   enabled=bool(ld.get("enabled", True)),
                   rand_keys=set(ld.get("rand_keys", [])))
        if old and old.get("mode", "none") != "none":
            m = p.add_mask(Mask(kind=old["mode"], params=dict(old.get("params", {}))))
            ly.refs = [MaskRef(mask_id=m.id, invert=bool(old.get("invert", False)),
                               feather=float(old.get("feather", 0.0)))]
        p.layers.append(ly)


# ---------------------------------------------------------------- render

# ---------------------------------------------------------------- bundle (.pgsz)

BUNDLE_PROJECT = "project.json"
BUNDLE_THUMB = "thumb.png"
BUNDLE_SOURCE_DIR = "source/"


def save_bundle(path: str, project: Project, image_bytes: bytes | None = None,
                image_name: str = "", thumb: np.ndarray | None = None):
    """Projekt + Originalbild + Vorschau in einer .pgsz-Datei (Zip)."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(BUNDLE_PROJECT,
                   json.dumps(project.to_json(), indent=2, ensure_ascii=False))
        if image_bytes:
            safe = Path(image_name or "image.png").name
            z.writestr(BUNDLE_SOURCE_DIR + safe, image_bytes)
        if thumb is not None:
            buf = io.BytesIO()
            Image.fromarray(thumb).save(buf, "PNG")
            z.writestr(BUNDLE_THUMB, buf.getvalue())


def load_bundle(path: str) -> tuple[Project, bytes | None, str]:
    """Liefert (Projekt, Original-Bildbytes | None, Bilddateiname)."""
    with zipfile.ZipFile(path, "r") as z:
        project = Project.from_json(json.loads(z.read(BUNDLE_PROJECT)))
        names = [n for n in z.namelist()
                 if n.startswith(BUNDLE_SOURCE_DIR) and not n.endswith("/")]
        if names:
            return project, z.read(names[0]), Path(names[0]).name
    return project, None, ""


def read_bundle_thumb(path: str) -> bytes | None:
    """Nur das Vorschaubild lesen (schnell, ohne das Projekt zu laden)."""
    try:
        with zipfile.ZipFile(path, "r") as z:
            if BUNDLE_THUMB in z.namelist():
                return z.read(BUNDLE_THUMB)
    except Exception:
        pass
    return None


def decode_image_bytes(data: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return np.asarray(img, dtype=np.uint8).copy()


def render(project: Project, source: np.ndarray, seed: int = 0,
           max_size: int | None = None) -> np.ndarray:
    arr = downscale(source, max_size) if max_size else source.copy()
    h, w = arr.shape[:2]
    for i, layer in enumerate(project.layers):        # oben zuerst
        if not layer.enabled:
            continue
        rng = np.random.default_rng((seed, i))
        fx = EFFECTS[layer.effect]()
        out = fx.apply(arr, layer.params, rng)
        m = combine_refs(layer.refs, project.masks, w, h, layer.final_feather)
        if m is None:
            arr = out
        else:
            m3 = m[..., None]
            arr = np.clip(arr.astype(np.float32) * (1 - m3)
                          + out.astype(np.float32) * m3, 0, 255).astype(np.uint8)
    return arr


def layer_mask_preview(project: Project, layer: Layer, w: int, h: int) -> np.ndarray | None:
    return combine_refs(layer.refs, project.masks, w, h, layer.final_feather)


# ---------------------------------------------------------------- batch

def active_rand_keys(project: Project) -> list:
    """(Ebenen-Label, Schlüssel)-Paare aller wirksamen 🎲-Markierungen."""
    out = []
    for ly in project.layers:
        if not ly.enabled or not ly.rand_enabled:
            continue
        valid = {s.key for s in EFFECTS[ly.effect].params}
        out += [(ly.label, k) for k in sorted(ly.rand_keys) if k in valid]
    return out


def randomized_copy(project: Project, seed: int) -> Project:
    """Kopie, in der alle 🎲-markierten Parameter deterministisch gewürfelt sind."""
    rng = np.random.default_rng(seed)
    p = Project.from_json(project.to_json())
    for ly in p.layers:
        if not ly.rand_enabled:
            continue
        specs = {s.key: s for s in EFFECTS[ly.effect].params}
        for key in sorted(ly.rand_keys):
            if key in specs:
                ly.params[key] = random_value(specs[key], rng)
    return p


# Unter Windows sind < > : " / \\ | ? * in Dateinamen verboten, unter POSIX
# zumindest der Schrägstrich. Der vom Nutzer eingegebene Präfix geht ungeprüft
# in den Dateinamen, also wird er hier entschärft.
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL",
             *(f"COM{i}" for i in range(1, 10)),
             *(f"LPT{i}" for i in range(1, 10))}


def safe_stem(stem: str, fallback: str = "glitch") -> str:
    """Einen Dateinamen-Präfix auf allen Plattformen benutzbar machen."""
    cleaned = _ILLEGAL.sub("_", stem or "").strip(" .")[:60]
    if not cleaned or cleaned.split(".")[0].upper() in _RESERVED:
        return fallback
    return cleaned


def run_batch(project: Project, source: np.ndarray, count: int, start_seed: int,
              outdir: str, fmt: str = "png", stem: str = "glitch",
              quality: int = 95, max_size: int | None = None,
              progress=None) -> list:
    outdir_p = Path(outdir)
    outdir_p.mkdir(parents=True, exist_ok=True)
    stem = safe_stem(stem)
    results = []
    for i in range(count):
        seed = start_seed + i
        variant = randomized_copy(project, seed)
        arr = render(variant, source, seed=seed, max_size=max_size)
        path = outdir_p / f"{stem}_{seed}.{fmt}"
        save_image(arr, str(path), fmt, quality)
        results.append(str(path))
        if progress and not progress(i + 1, count):
            break
    return results


def reproduce(project: Project, source: np.ndarray, seed: int) -> np.ndarray:
    """Ein Batch-Ergebnis aus seinem Seed exakt nachbauen."""
    return render(randomized_copy(project, seed), source, seed=seed)


# ---------------------------------------------------------------- ratings

RATINGS_FILE = ".pixelglitch-ratings.json"


def load_ratings(folder: str | Path) -> dict:
    p = Path(folder) / RATINGS_FILE
    try:
        return {k: int(v) for k, v in json.loads(p.read_text()).items()}
    except Exception:
        return {}


def save_rating(folder: str | Path, filename: str, stars: int):
    """0 Sterne entfernt den Eintrag. Sidecar bleibt neben den Bildern portabel."""
    folder = Path(folder)
    data = load_ratings(folder)
    if stars <= 0:
        data.pop(filename, None)
    else:
        data[filename] = int(stars)
    (folder / RATINGS_FILE).write_text(
        json.dumps(data, indent=0, ensure_ascii=False))


# ---------------------------------------------------------------- timing

class Stopwatch:
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.ms = (time.perf_counter() - self.t0) * 1000.0
