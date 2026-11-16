"""Preset-System: Ebenenstapel samt eingebetteter Masken als eigenständige,
speicher- und austauschbare Objekte (GUI-frei).

Dateiformat `.pgpreset`: JSON mit Formatversion. Ein Preset enthält den
Ebenenstapel (Effekt, Parameter, Sichtbarkeit, 🎲-Marker, Maskenreferenzen)
und die Definitionen aller referenzierten Masken. Quellbild und Ausgabepfade
gehören ausdrücklich nicht hinein.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .params import EFFECTS
from .masks import Mask, MaskRef

PRESET_VERSION = 1
PRESET_EXT = ".pgpreset"


@dataclass
class Preset:
    name: str
    description: str = ""
    origin: str = "user"                    # "builtin" | "user" | "import"
    layers: list = field(default_factory=list)   # rohe Layer-JSON-Dicts
    masks: list = field(default_factory=list)    # rohe Mask-JSON-Dicts
    version: int = PRESET_VERSION
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])

    # ------------------------------------------------------------ ser/de
    def to_json(self) -> dict:
        return {"format": "pgpreset", "version": self.version, "id": self.id,
                "name": self.name, "description": self.description,
                "layers": self.layers, "masks": self.masks}

    @classmethod
    def from_json(cls, d: dict, origin: str = "user") -> "Preset":
        if not isinstance(d, dict) or d.get("format") != "pgpreset":
            raise ValueError("Keine Preset-Datei (Format-Kennung fehlt).")
        ver = int(d.get("version", 0))
        if ver > PRESET_VERSION:
            raise ValueError(
                f"Preset-Format Version {ver} ist neuer als diese App "
                f"(unterstützt bis {PRESET_VERSION}). Bitte App aktualisieren.")
        if not d.get("layers"):
            raise ValueError("Preset enthält keine Ebenen.")
        return cls(name=str(d.get("name", "Unbenannt")),
                   description=str(d.get("description", "")),
                   origin=origin,
                   layers=list(d.get("layers", [])),
                   masks=list(d.get("masks", [])),
                   version=ver,
                   id=d.get("id", uuid.uuid4().hex[:10]))

    # ------------------------------------------------------------ fabrik
    @classmethod
    def from_project(cls, project, name: str, description: str = "") -> "Preset":
        """Aktuellen Ebenenstapel + referenzierte Masken einfrieren."""
        used_ids = {r.mask_id for ly in project.layers for r in ly.refs}
        masks = [m.to_json() for m in project.ordered_masks() if m.id in used_ids]
        return cls(name=name, description=description,
                   layers=[ly.to_json() for ly in project.layers],
                   masks=masks)

    # ------------------------------------------------------------ anwenden
    def apply_to(self, project) -> list:
        """Ersetzt den Ebenenstapel des Projekts; legt eingebettete Masken an
        (Namenskonflikte bekommen ein Zahlensuffix). Gibt Hinweise zurück
        (z.B. übersprungene unbekannte Effekte)."""
        from .engine import Layer   # zyklusfrei zur Laufzeit
        notes = []

        # Masken übernehmen: neue IDs, Namen entschärfen
        id_map = {}
        existing = {m.name for m in project.masks.values()}
        for md in self.masks:
            try:
                m = Mask.from_json(md)
            except Exception:
                notes.append("Eine eingebettete Maske war beschädigt und "
                             "wurde übersprungen.")
                continue
            old_id = m.id
            m.id = uuid.uuid4().hex[:10]
            base, n = m.name, 2
            while m.name in existing:
                m.name = f"{base} {n}"
                n += 1
            existing.add(m.name)
            project.add_mask(m)
            id_map[old_id] = m.id

        layers = []
        for ld in self.layers:
            effect = ld.get("effect")
            if effect not in EFFECTS:
                notes.append(f"Effekt „{effect}“ ist in dieser App unbekannt "
                             "und wurde übersprungen.")
                continue
            ly = Layer.from_json(ld)
            ly.id = uuid.uuid4().hex[:10]
            kept = []
            for r in ly.refs:
                if r.mask_id in id_map:
                    kept.append(MaskRef(mask_id=id_map[r.mask_id], op=r.op,
                                        invert=r.invert, feather=r.feather))
                else:
                    notes.append(f"Eine Maskenreferenz in „{ly.label}“ fehlte "
                                 "im Preset und wurde entfernt.")
            ly.refs = kept
            layers.append(ly)
        project.layers = layers
        return notes

    def summary(self) -> str:
        labels = []
        for ld in self.layers:
            fx = ld.get("effect")
            labels.append(EFFECTS[fx].label if fx in EFFECTS else f"? {fx}")
        s = " → ".join(labels)
        if self.masks:
            s += f"  ·  {len(self.masks)} Maske(n)"
        return s


# ---------------------------------------------------------------- ablage

def save_preset(preset: Preset, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in preset.name if c not in '\\/:*?"<>|').strip() or "preset"
    path = folder / f"{safe}{PRESET_EXT}"
    n = 2
    while path.exists():
        path = folder / f"{safe} {n}{PRESET_EXT}"
        n += 1
    path.write_text(json.dumps(preset.to_json(), indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return path


def load_preset(path: str | Path, origin: str = "user") -> Preset:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Preset.from_json(data, origin=origin)


def scan_presets(folder: Path) -> tuple:
    """(Presets, Fehlerliste) – beschädigte Dateien mit Grund statt Absturz."""
    presets, errors = [], []
    if folder.exists():
        for p in sorted(folder.glob(f"*{PRESET_EXT}")):
            try:
                presets.append((str(p), load_preset(p)))
            except Exception as e:
                errors.append((str(p), str(e)))
    return presets, errors


# ---------------------------------------------------------------- builtins

def _b(name, desc, layers, masks=None) -> Preset:
    return Preset(name=name, description=desc, origin="builtin",
                  layers=layers, masks=masks or [], id="builtin-" + name.lower())


def builtin_presets() -> list:
    """Mitgelieferte, schreibgeschützte Startpunkte."""
    mid = Mask(kind="ellipse", name="Zentrum",
               params={"cx": 0.5, "cy": 0.5, "rx": 0.3, "ry": 0.35}).to_json()
    band = Mask(kind="linear", name="Verlauf",
                params={"angle": 90, "start": 0.5, "end": 0.95}).to_json()

    def L(effect, params=None, refs=None, rand=None):
        d = {"effect": effect, "params": params or {}, "enabled": True,
             "refs": refs or [], "final_feather": 0.0,
             "rand_keys": rand or [], "rand_enabled": True}
        return d

    return [
        _b("Klassischer Sort", "Horizontales Pixel-Sorting mit Schwellen.",
           [L("pixel_sort", {"direction": "horizontal"}, rand=["lo", "hi"])]),
        _b("Vertikaler Regen", "Vertikales Sorting mit Aussetzern.",
           [L("pixel_sort", {"direction": "vertical", "randomness": 0.25},
              rand=["lo", "hi", "randomness"])]),
        _b("Signalstörung", "Slice-Versatz, Aberration und Scanlines.",
           [L("slice_shift", rand=["count", "max_shift"]),
            L("chromatic", {"shift": 5}),
            L("scanlines")]),
        _b("Databend", "Byte-Glitch mit JPEG-Korruption obendrauf.",
           [L("byte_glitch", rand=["amount", "chunk"]),
            L("jpeg_corrupt", rand=["quality", "corruptions"])]),
        _b("Zentrum zerlegen", "Sortierter Kern, ruhiger Rand.",
           [L("pixel_sort", {"direction": "vertical"},
              refs=[{"mask_id": mid["id"], "op": "union", "invert": False,
                     "feather": 3.0}], rand=["lo", "hi"])],
           [mid]),
        _b("Horizont kippen", "Verlaufsmaske unten, Block-Shuffle darüber.",
           [L("block_shuffle",
              refs=[{"mask_id": band["id"], "op": "union", "invert": False,
                     "feather": 4.0}], rand=["block", "fraction"]),
            L("chromatic", {"shift": 3})],
           [band]),
    ]
