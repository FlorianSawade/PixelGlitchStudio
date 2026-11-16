"""Effekt-Suite: Pixel Sort, Glitch- und Farb-Effekte (GUI-frei).

Jeder Effekt: apply(arr, p, rng) -> uint8 (H, W, 3), gleiche Form.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter

from .params import ParamSpec, register


# ---------------------------------------------------------------- helpers

def _lum(arr: np.ndarray) -> np.ndarray:
    a = arr.astype(np.float32)
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def _hsv(arr: np.ndarray) -> np.ndarray:
    return np.asarray(Image.fromarray(arr).convert("HSV"), dtype=np.float32)


def _sort_key(arr: np.ndarray, key: str) -> np.ndarray:
    if key == "brightness":
        return _lum(arr)
    if key in ("hue", "saturation"):
        return _hsv(arr)[..., 0 if key == "hue" else 1]
    idx = {"red": 0, "green": 1, "blue": 2}[key]
    return arr[..., idx].astype(np.float32)


def _runs(mask_row: np.ndarray):
    """Zusammenhängende True-Bereiche als (start, ende-exklusiv)."""
    if not mask_row.any():
        return
    padded = np.concatenate(([False], mask_row, [False]))
    diff = np.diff(padded.astype(np.int8))
    starts = np.flatnonzero(diff == 1)
    ends = np.flatnonzero(diff == -1)
    yield from zip(starts, ends)


# ---------------------------------------------------------------- sort

@register("pixel_sort", "Pixel Sort", "Sortierung")
class PixelSort:
    params = [
        ParamSpec("direction", "Richtung", "choice", "horizontal",
                  choices=["horizontal", "vertical"],
                  choice_labels=["Horizontal", "Vertikal"]),
        ParamSpec("key", "Sortierschlüssel", "choice", "brightness",
                  choices=["brightness", "hue", "saturation", "red", "green", "blue"],
                  choice_labels=["Helligkeit", "Farbton", "Sättigung", "Rot", "Grün", "Blau"]),
        ParamSpec("interval", "Intervall", "choice", "threshold",
                  choices=["threshold", "random", "waves", "edges", "none"],
                  choice_labels=["Schwelle", "Zufall", "Wellen", "Kanten", "Ganze Zeile"]),
        ParamSpec("lo", "Schwelle min", "float", 0.25, lo=0.0, hi=1.0, step=0.01),
        ParamSpec("hi", "Schwelle max", "float", 0.85, lo=0.0, hi=1.0, step=0.01),
        ParamSpec("randomness", "Aussetzer", "float", 0.0, lo=0.0, hi=1.0, step=0.05,
                  rand_hi=0.6),
        ParamSpec("reverse", "Absteigend", "bool", False),
    ]

    def apply(self, arr, p, rng):
        out = arr.copy()
        if p["direction"] == "vertical":
            out = np.swapaxes(out, 0, 1).copy()
        h, w = out.shape[:2]
        key = _sort_key(out, p["key"])
        kmax = max(float(key.max()), 1e-6)
        keyn = key / kmax

        mode = p["interval"]
        if mode == "threshold":
            sel = (keyn >= min(p["lo"], p["hi"])) & (keyn <= max(p["lo"], p["hi"]))
        elif mode == "random":
            width = max(4, int(w * (0.05 + 0.4 * (1.0 - p["lo"]))))
            cuts = rng.random((h, w)) < (1.0 / width)
            sel = ~cuts
        elif mode == "waves":
            xs = np.arange(w, dtype=np.float32)
            per = max(8.0, w * max(0.02, p["lo"]))
            phase = rng.random(h)[:, None] * 2 * np.pi
            sel = np.sin(xs[None, :] / per * 2 * np.pi + phase) > (2 * p["hi"] - 1)
        elif mode == "edges":
            gx = np.abs(np.diff(keyn, axis=1, prepend=keyn[:, :1]))
            sel = gx < max(0.01, p["lo"] * 0.5)
        else:
            sel = np.ones((h, w), dtype=bool)

        if p["randomness"] > 0:
            keep = rng.random(h) >= p["randomness"]
        else:
            keep = np.ones(h, dtype=bool)

        for y in range(h):
            if not keep[y]:
                continue
            for s, e in _runs(sel[y]):
                if e - s < 2:
                    continue
                order = np.argsort(key[y, s:e], kind="stable")
                if p["reverse"]:
                    order = order[::-1]
                out[y, s:e] = out[y, s:e][order]

        if p["direction"] == "vertical":
            out = np.swapaxes(out, 0, 1)
        return np.ascontiguousarray(out)


# ---------------------------------------------------------------- glitch

@register("rgb_shift", "RGB-Verschiebung", "Glitch")
class RGBShift:
    params = [
        ParamSpec("dx", "Versatz X", "int", 8, lo=-60, hi=60, step=1),
        ParamSpec("dy", "Versatz Y", "int", 0, lo=-60, hi=60, step=1),
    ]

    def apply(self, arr, p, rng):
        out = arr.copy()
        out[..., 0] = np.roll(arr[..., 0], (p["dy"], p["dx"]), axis=(0, 1))
        out[..., 2] = np.roll(arr[..., 2], (-p["dy"], -p["dx"]), axis=(0, 1))
        return out


@register("channel_swap", "Kanaltausch", "Glitch")
class ChannelSwap:
    params = [
        ParamSpec("mode", "Modus", "choice", "gbr",
                  choices=["gbr", "brg", "bgr", "rbg", "grb"],
                  choice_labels=["G-B-R", "B-R-G", "B-G-R", "R-B-G", "G-R-B"]),
    ]

    def apply(self, arr, p, rng):
        order = {"gbr": (1, 2, 0), "brg": (2, 0, 1), "bgr": (2, 1, 0),
                 "rbg": (0, 2, 1), "grb": (1, 0, 2)}[p["mode"]]
        return np.ascontiguousarray(arr[..., order])


@register("slice_shift", "Slice-Verschiebung", "Glitch")
class SliceShift:
    params = [
        ParamSpec("count", "Anzahl Slices", "int", 12, lo=1, hi=80, step=1),
        ParamSpec("max_shift", "Max. Versatz %", "float", 12.0, lo=0.0, hi=50.0, step=0.5),
        ParamSpec("direction", "Richtung", "choice", "horizontal",
                  choices=["horizontal", "vertical"],
                  choice_labels=["Horizontal", "Vertikal"]),
    ]

    def apply(self, arr, p, rng):
        out = arr.copy()
        vert = p["direction"] == "vertical"
        if vert:
            out = np.swapaxes(out, 0, 1).copy()
        h, w = out.shape[:2]
        for _ in range(int(p["count"])):
            y0 = int(rng.integers(0, max(1, h - 2)))
            y1 = min(h, y0 + int(rng.integers(2, max(3, h // 12))))
            shift = int((rng.random() * 2 - 1) * w * p["max_shift"] / 100.0)
            out[y0:y1] = np.roll(out[y0:y1], shift, axis=1)
        if vert:
            out = np.swapaxes(out, 0, 1)
        return np.ascontiguousarray(out)


@register("wave_distort", "Wellen-Verzerrung", "Glitch")
class WaveDistort:
    params = [
        ParamSpec("amplitude", "Amplitude %", "float", 4.0, lo=0.0, hi=25.0, step=0.5),
        ParamSpec("wavelength", "Wellenlänge %", "float", 20.0, lo=2.0, hi=100.0, step=1.0),
        ParamSpec("direction", "Richtung", "choice", "horizontal",
                  choices=["horizontal", "vertical"],
                  choice_labels=["Horizontal", "Vertikal"]),
    ]

    def apply(self, arr, p, rng):
        out = arr.copy()
        vert = p["direction"] == "vertical"
        if vert:
            out = np.swapaxes(out, 0, 1).copy()
        h, w = out.shape[:2]
        amp = w * p["amplitude"] / 100.0
        lam = max(2.0, h * p["wavelength"] / 100.0)
        phase = rng.random() * 2 * np.pi
        ys = np.arange(h, dtype=np.float32)
        shifts = (amp * np.sin(ys / lam * 2 * np.pi + phase)).astype(int)
        for y in range(h):
            if shifts[y]:
                out[y] = np.roll(out[y], shifts[y], axis=0)
        if vert:
            out = np.swapaxes(out, 0, 1)
        return np.ascontiguousarray(out)


@register("chromatic", "Chromatische Aberration", "Glitch")
class Chromatic:
    params = [
        ParamSpec("strength", "Stärke %", "float", 1.5, lo=0.0, hi=8.0, step=0.1),
    ]

    def apply(self, arr, p, rng):
        h, w = arr.shape[:2]
        img = Image.fromarray(arr)
        s = p["strength"] / 100.0
        r = img.getchannel(0).resize((int(w * (1 + s)), int(h * (1 + s))), Image.BILINEAR)
        b = img.getchannel(2).resize((max(1, int(w * (1 - s))), max(1, int(h * (1 - s)))), Image.BILINEAR)

        def center_fit(ch):
            cw, chh = ch.size
            if cw >= w:
                return ch.crop(((cw - w) // 2, (chh - h) // 2,
                                (cw - w) // 2 + w, (chh - h) // 2 + h))
            canvas = Image.new("L", (w, h), 0)
            canvas.paste(ch, ((w - cw) // 2, (h - chh) // 2))
            return canvas

        out = arr.copy()
        out[..., 0] = np.asarray(center_fit(r))
        out[..., 2] = np.asarray(center_fit(b))
        return out


@register("scanlines", "Scanlines / CRT", "Glitch")
class Scanlines:
    params = [
        ParamSpec("spacing", "Abstand px", "int", 3, lo=2, hi=16, step=1),
        ParamSpec("intensity", "Intensität", "float", 0.35, lo=0.0, hi=1.0, step=0.05),
        ParamSpec("rgb_offset", "RGB-Versatz", "bool", True),
    ]

    def apply(self, arr, p, rng):
        out = arr.astype(np.float32)
        h = out.shape[0]
        mask = (np.arange(h) % int(p["spacing"])) == 0
        out[mask] *= (1.0 - p["intensity"])
        out = out.astype(np.uint8)
        if p["rgb_offset"]:
            out[..., 0] = np.roll(out[..., 0], 1, axis=1)
            out[..., 2] = np.roll(out[..., 2], -1, axis=1)
        return out


@register("byte_glitch", "Byte-Glitch (Databend)", "Glitch")
class ByteGlitch:
    params = [
        ParamSpec("amount", "Menge", "float", 0.4, lo=0.0, hi=1.0, step=0.05),
        ParamSpec("chunk", "Chunk-Größe", "int", 800, lo=50, hi=5000, step=50),
    ]

    def apply(self, arr, p, rng):
        flat = arr.copy().reshape(-1)
        n = max(1, int(p["amount"] * 40))
        for _ in range(n):
            start = int(rng.integers(0, max(1, flat.size - p["chunk"])))
            mode = int(rng.integers(3))
            seg = slice(start, start + int(p["chunk"]))
            if mode == 0:
                flat[seg] = flat[seg][::-1]
            elif mode == 1:
                flat[seg] = np.roll(flat[seg], int(rng.integers(1, 64)))
            else:
                flat[seg] ^= int(rng.integers(1, 255))
        return flat.reshape(arr.shape)


@register("jpeg_corrupt", "JPEG-Korruption", "Glitch")
class JpegCorrupt:
    params = [
        ParamSpec("quality", "JPEG-Qualität", "int", 30, lo=1, hi=95, step=1),
        ParamSpec("corruptions", "Korruptionen", "int", 6, lo=0, hi=60, step=1),
    ]

    def apply(self, arr, p, rng):
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, "JPEG", quality=int(p["quality"]))
        data = bytearray(buf.getvalue())
        header = 1024
        for _ in range(int(p["corruptions"])):
            if len(data) <= header + 2:
                break
            pos = int(rng.integers(header, len(data) - 2))
            data[pos] = int(rng.integers(256))
        try:
            img = Image.open(io.BytesIO(bytes(data))).convert("RGB")
            out = np.asarray(img)
            if out.shape != arr.shape:
                img = img.resize((arr.shape[1], arr.shape[0]))
                out = np.asarray(img)
            return out.copy()
        except Exception:
            buf.seek(0)
            return np.asarray(Image.open(buf).convert("RGB")).copy()


@register("block_shuffle", "Block-Shuffle", "Glitch")
class BlockShuffle:
    params = [
        ParamSpec("block", "Blockgröße px", "int", 48, lo=8, hi=256, step=4),
        ParamSpec("fraction", "Anteil", "float", 0.25, lo=0.0, hi=1.0, step=0.05),
    ]

    def apply(self, arr, p, rng):
        out = arr.copy()
        b = int(p["block"])
        h, w = arr.shape[:2]
        coords = [(y, x) for y in range(0, h - b + 1, b) for x in range(0, w - b + 1, b)]
        if len(coords) < 2:
            return out
        k = int(len(coords) * p["fraction"])
        idx = rng.choice(len(coords), size=min(k, len(coords)), replace=False)
        picked = [coords[i] for i in idx]
        perm = rng.permutation(len(picked))
        src = [arr[y:y + b, x:x + b].copy() for y, x in picked]
        for (y, x), j in zip(picked, perm):
            out[y:y + b, x:x + b] = src[j]
        return out


@register("echo", "Echo / Geisterbild", "Glitch")
class Echo:
    params = [
        ParamSpec("offset", "Versatz px", "int", 14, lo=1, hi=120, step=1),
        ParamSpec("count", "Wiederholungen", "int", 3, lo=1, hi=8, step=1),
        ParamSpec("decay", "Abklingen", "float", 0.55, lo=0.1, hi=0.95, step=0.05),
    ]

    def apply(self, arr, p, rng):
        acc = arr.astype(np.float32)
        weight = 1.0
        total = 1.0
        for i in range(1, int(p["count"]) + 1):
            weight *= p["decay"]
            total += weight
            acc += np.roll(arr, (0, i * int(p["offset"])), axis=(0, 1)).astype(np.float32) * weight
        return np.clip(acc / total, 0, 255).astype(np.uint8)


@register("displace", "Verschiebung / Pixel Stretch", "Glitch")
class Displace:
    """Pro-Pixel-Versatz aus einer Displacement-Map des Bildes selbst.

    Anders als slice_shift/wave_distort/echo (konstanter Versatz je Zeile)
    bekommt hier jeder Pixel seinen eigenen Betrag. Modus "smear" schreibt
    den Pixel über die ganze Strecke fort und erzeugt so die typischen
    langgezogenen Reliefflächen.
    """

    params = [
        ParamSpec("source", "Quelle", "choice", "brightness",
                  choices=["brightness", "gradient", "hue", "saturation",
                           "red", "green", "blue"],
                  choice_labels=["Helligkeit", "Gradient", "Farbton",
                                 "Sättigung", "Rot", "Grün", "Blau"],
                  randomizable=False),
        ParamSpec("mode", "Modus", "choice", "smear",
                  choices=["smear", "shift"],
                  choice_labels=["Fortschreiben", "Verschieben"],
                  randomizable=False),
        ParamSpec("direction", "Richtung", "choice", "vertical",
                  choices=["horizontal", "vertical", "both"],
                  choice_labels=["Horizontal", "Vertikal", "Beide"],
                  randomizable=False),
        ParamSpec("strength", "Stärke %", "float", 6.0, lo=0.0, hi=30.0,
                  step=0.5, rand_hi=15.0),
        ParamSpec("bias", "Nullpunkt", "float", 0.0, lo=-1.0, hi=1.0, step=0.05,
                  rand_lo=-0.5, rand_hi=0.5),
        ParamSpec("smoothness", "Glättung %", "float", 4.0, lo=0.0, hi=20.0,
                  step=0.5, rand_hi=12.0),
        ParamSpec("edge", "Rand", "choice", "clamp",
                  choices=["clamp", "wrap", "mirror"],
                  choice_labels=["Klemmen", "Umlaufen", "Spiegeln"],
                  randomizable=False),
    ]

    # -- Hilfen ----------------------------------------------------------
    @staticmethod
    def _source_map(arr: np.ndarray, source: str) -> np.ndarray:
        if source == "gradient":
            l = _lum(arr)
            gx = np.abs(np.diff(l, axis=1, append=l[:, -1:]))
            gy = np.abs(np.diff(l, axis=0, append=l[-1:, :]))
            v = gx + gy
        else:
            v = _sort_key(arr, source)
        lo, hi = float(v.min()), float(v.max())
        if hi - lo < 1e-6:
            return np.zeros_like(v, dtype=np.float32)
        return ((v - lo) / (hi - lo)).astype(np.float32)

    @staticmethod
    def _smooth(m: np.ndarray, percent: float) -> np.ndarray:
        if percent <= 0:
            return m
        h, w = m.shape
        radius = percent / 100.0 * min(w, h)
        if radius < 0.5:
            return m
        img = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8))
        img = img.filter(ImageFilter.GaussianBlur(radius))
        return np.asarray(img, dtype=np.float32) / 255.0

    @staticmethod
    def _edge_idx(idx: np.ndarray, n: int, edge: str) -> np.ndarray:
        if edge == "wrap":
            return np.mod(idx, n)
        if edge == "mirror" and n > 1:
            period = 2 * n - 2
            k = np.mod(np.abs(idx), period)
            return np.where(k >= n, period - k, k)
        return np.clip(idx, 0, n - 1)

    # -- Kern ------------------------------------------------------------
    def _pass(self, arr: np.ndarray, p: dict) -> np.ndarray:
        """Ein horizontaler Durchgang. Vertikal via swapaxes im Aufrufer."""
        h, w = arr.shape[:2]
        m = self._source_map(arr, p["source"])
        m = self._smooth(m, p["smoothness"])
        zero = 0.5 + float(p["bias"]) * 0.5
        d = np.rint((m - zero) * (p["strength"] / 100.0) * w).astype(np.int32)
        maxd = int(np.abs(d).max())
        if maxd == 0:
            return arr

        base = np.arange(w, dtype=np.int32)
        edge = p["edge"]

        if p["mode"] == "shift":
            xs = self._edge_idx(base[None, :] - d, w, edge)
            return np.ascontiguousarray(
                np.take_along_axis(arr, xs[:, :, None], axis=1))

        # Fortschreiben: Stufe für Stufe die Spur des Originalpixels ziehen.
        # Der Rand wird einmal vorgepolstert, danach sind alle Zugriffe
        # reine Slices – kein Gather und keine Temporärkopie je Stufe.
        pad = {"wrap": "wrap", "mirror": "reflect"}.get(edge, "edge")
        pa = np.pad(arr, ((0, 0), (maxd, maxd), (0, 0)), mode=pad)
        pd = np.pad(d, ((0, 0), (maxd, maxd)), mode=pad)
        out = arr.copy()
        for s in range(1, maxd + 1):
            for sign in (1, -1):
                o = maxd - sign * s
                dd = pd[:, o:o + w]
                cond = (dd >= s) if sign > 0 else (dd <= -s)
                np.copyto(out, pa[:, o:o + w], where=cond[:, :, None])
        return out

    def apply(self, arr, p, rng):
        out = arr
        if p["direction"] in ("horizontal", "both"):
            out = self._pass(out, p)
        if p["direction"] in ("vertical", "both"):
            swapped = np.ascontiguousarray(np.swapaxes(out, 0, 1))
            swapped = self._pass(swapped, p)
            out = np.swapaxes(swapped, 0, 1)
        return np.ascontiguousarray(out)


# ---------------------------------------------------------------- color

@register("pixelate", "Pixelate / Mosaik", "Farbe")
class Pixelate:
    params = [ParamSpec("size", "Blockgröße px", "int", 12, lo=2, hi=128, step=1)]

    def apply(self, arr, p, rng):
        h, w = arr.shape[:2]
        s = max(2, int(p["size"]))
        img = Image.fromarray(arr)
        small = img.resize((max(1, w // s), max(1, h // s)), Image.BILINEAR)
        return np.asarray(small.resize((w, h), Image.NEAREST)).copy()


@register("posterize", "Posterize", "Farbe")
class Posterize:
    params = [ParamSpec("levels", "Stufen", "int", 4, lo=2, hi=16, step=1)]

    def apply(self, arr, p, rng):
        n = int(p["levels"])
        step = 255.0 / (n - 1)
        return (np.round(arr.astype(np.float32) / step) * step).astype(np.uint8)


@register("noise", "Rauschen", "Farbe")
class Noise:
    params = [
        ParamSpec("amount", "Stärke", "float", 20.0, lo=0.0, hi=120.0, step=1.0),
        ParamSpec("mono", "Monochrom", "bool", True),
    ]

    def apply(self, arr, p, rng):
        h, w = arr.shape[:2]
        if p["mono"]:
            n = rng.normal(0, p["amount"], (h, w, 1)).astype(np.float32)
        else:
            n = rng.normal(0, p["amount"], (h, w, 3)).astype(np.float32)
        return np.clip(arr.astype(np.float32) + n, 0, 255).astype(np.uint8)


@register("bilateral", "Bilateral-Glättung", "Farbe")
class Bilateral:
    """Kantenerhaltende Glättung: Flächen werden eingeebnet, Kanten bleiben.

    Der Range-Term ist als 256-Einträge-Tabelle vorberechnet – die
    Helligkeitsdifferenz zweier Pixel ist ganzzahlig, damit wird aus der
    Exponentialfunktion je Nachbar und Pixel eine reine Indizierung.
    """

    params = [
        ParamSpec("radius", "Radius px", "int", 3, lo=1, hi=6, step=1),
        ParamSpec("tolerance", "Farbtoleranz", "float", 25.0, lo=1.0, hi=100.0,
                  step=1.0, rand_hi=60.0),
        ParamSpec("iterations", "Durchgänge", "int", 2, lo=1, hi=4, step=1,
                  randomizable=False),
    ]

    @staticmethod
    def _pass(arr: np.ndarray, r: int, lut: np.ndarray, sigma_s: float) -> np.ndarray:
        h, w = arr.shape[:2]
        lum = np.rint(_lum(arr)).astype(np.int16)
        pa = np.pad(arr, ((r, r), (r, r), (0, 0)), mode="edge").astype(np.float32)
        pl = np.pad(lum, ((r, r), (r, r)), mode="edge")
        acc = np.zeros((h, w, 3), np.float32)
        wsum = np.zeros((h, w), np.float32)
        denom = 2.0 * sigma_s * sigma_s
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                sw = float(np.exp(-(dx * dx + dy * dy) / denom))
                ys, xs = dy + r, dx + r
                diff = np.abs(pl[ys:ys + h, xs:xs + w] - lum)
                wgt = lut[diff] * sw
                acc += pa[ys:ys + h, xs:xs + w] * wgt[:, :, None]
                wsum += wgt
        return np.clip(acc / wsum[:, :, None], 0, 255).astype(np.uint8)

    def apply(self, arr, p, rng):
        r = int(p["radius"])
        tol = max(1.0, float(p["tolerance"]))
        lut = np.exp(-(np.arange(256, dtype=np.float32) ** 2) / (2.0 * tol * tol))
        sigma_s = max(0.5, r / 2.0)
        out = arr
        for _ in range(int(p["iterations"])):
            out = self._pass(out, r, lut, sigma_s)
        return np.ascontiguousarray(out)


@register("kuwahara", "Kuwahara / Malerisch", "Farbe")
class Kuwahara:
    """Jeder Pixel wird durch den Mittelwert seines homogensten Quadranten
    ersetzt. Erzeugt abgerundete, flächige Formen mit harten Übergängen.
    """

    params = [
        ParamSpec("radius", "Radius px", "int", 3, lo=1, hi=8, step=1),
        ParamSpec("iterations", "Durchgänge", "int", 1, lo=1, hi=3, step=1,
                  randomizable=False),
    ]

    @staticmethod
    def _boxes(padded: np.ndarray, k: int) -> np.ndarray:
        """Fenstersummen k×k über alle Startpositionen, via Integralbild.

        float64 ist hier nötig: die Summe über ein großes Bild sprengt die
        Mantisse von float32 und die Varianz würde verrauschen.
        """
        ii = np.cumsum(np.cumsum(padded.astype(np.float64), axis=0), axis=1)
        pad = [(1, 0), (1, 0)] + [(0, 0)] * (padded.ndim - 2)
        ii = np.pad(ii, pad, mode="constant")
        return (ii[k:, k:] - ii[:-k, k:] - ii[k:, :-k] + ii[:-k, :-k])

    def _pass(self, arr: np.ndarray, r: int) -> np.ndarray:
        h, w = arr.shape[:2]
        k = r + 1
        n = float(k * k)
        rgb = np.pad(arr, ((r, r), (r, r), (0, 0)), mode="edge")
        lum = np.pad(np.rint(_lum(arr)), ((r, r), (r, r)), mode="edge")

        mean_rgb = self._boxes(rgb, k) / n
        mean_l = self._boxes(lum, k) / n
        mean_l2 = self._boxes(lum * lum, k) / n
        var = np.maximum(mean_l2 - mean_l * mean_l, 0.0)

        best_var = None
        best_rgb = None
        for sy, sx in ((0, 0), (0, r), (r, 0), (r, r)):     # NW, NE, SW, SE
            v = var[sy:sy + h, sx:sx + w]
            m = mean_rgb[sy:sy + h, sx:sx + w]
            if best_var is None:
                best_var, best_rgb = v.copy(), m.copy()
            else:
                sel = v < best_var
                best_rgb = np.where(sel[:, :, None], m, best_rgb)
                best_var = np.where(sel, v, best_var)
        return np.clip(best_rgb, 0, 255).astype(np.uint8)

    def apply(self, arr, p, rng):
        out = arr
        for _ in range(int(p["iterations"])):
            out = self._pass(out, int(p["radius"]))
        return np.ascontiguousarray(out)


@register("hue_rotate", "Farbton drehen", "Farbe")
class HueRotate:
    params = [ParamSpec("degrees", "Winkel °", "float", 60.0, lo=-180.0, hi=180.0, step=1.0)]

    def apply(self, arr, p, rng):
        hsv = np.asarray(Image.fromarray(arr).convert("HSV")).copy()
        shift = int(p["degrees"] / 360.0 * 255.0)
        hsv[..., 0] = (hsv[..., 0].astype(np.int16) + shift) % 256
        return np.asarray(Image.fromarray(hsv, "HSV").convert("RGB")).copy()


@register("bcs", "Helligkeit / Kontrast / Sättigung", "Farbe")
class BCS:
    params = [
        ParamSpec("brightness", "Helligkeit", "float", 1.0, lo=0.2, hi=2.0, step=0.05),
        ParamSpec("contrast", "Kontrast", "float", 1.0, lo=0.2, hi=2.5, step=0.05),
        ParamSpec("saturation", "Sättigung", "float", 1.0, lo=0.0, hi=2.5, step=0.05),
    ]

    def apply(self, arr, p, rng):
        a = arr.astype(np.float32)
        a = (a - 127.5) * p["contrast"] + 127.5
        a *= p["brightness"]
        lum = _lum(np.clip(a, 0, 255).astype(np.uint8))[..., None]
        a = lum + (a - lum) * p["saturation"]
        return np.clip(a, 0, 255).astype(np.uint8)


@register("invert_colors", "Invertieren", "Farbe")
class InvertColors:
    params = [ParamSpec("strength", "Stärke", "float", 1.0, lo=0.0, hi=1.0, step=0.05)]

    def apply(self, arr, p, rng):
        inv = 255 - arr.astype(np.float32)
        return np.clip(arr * (1 - p["strength"]) + inv * p["strength"], 0, 255).astype(np.uint8)
