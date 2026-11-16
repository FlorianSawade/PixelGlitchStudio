"""Parameter-Spezifikation und Effekt-Registry (GUI-frei)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ParamSpec:
    key: str
    label: str
    kind: str                      # 'int' | 'float' | 'choice' | 'bool'
    default: Any
    lo: Optional[float] = None
    hi: Optional[float] = None
    step: Optional[float] = None
    choices: Optional[list] = None
    choice_labels: Optional[list] = None
    randomizable: bool = True
    rand_lo: float | None = None   # engerer Würfelbereich für den Batch
    rand_hi: float | None = None


EFFECTS: dict[str, type] = {}


def register(name: str, label: str, group: str):
    def deco(cls):
        cls.name, cls.label, cls.group = name, label, group
        EFFECTS[name] = cls
        return cls
    return deco


def effect_defaults(cls) -> dict:
    return {p.key: p.default for p in cls.params}


def random_value(spec: ParamSpec, rng) -> Any:
    if spec.kind == "bool":
        return bool(rng.random() < 0.5)
    if spec.kind == "choice":
        return spec.choices[int(rng.integers(len(spec.choices)))]
    lo = spec.rand_lo if spec.rand_lo is not None else (spec.lo if spec.lo is not None else 0)
    hi = spec.rand_hi if spec.rand_hi is not None else (spec.hi if spec.hi is not None else 1)
    if spec.kind == "int":
        return int(rng.integers(int(lo), int(hi) + 1))
    return float(lo + rng.random() * (hi - lo))
