"""Engine-Tests (GUI-frei): Effekte, Masken, Ketten, Batch, Projekt-IO."""
import json
import tempfile
from pathlib import Path

import numpy as np

from pixelglitch.params import EFFECTS, effect_defaults
from pixelglitch.masks import Mask, MaskRef, combine_refs, MASK_KINDS
from pixelglitch import engine
from pixelglitch.engine import Project, Layer

rng = np.random.default_rng(7)
IMG = (rng.random((120, 160, 3)) * 255).astype(np.uint8)
ok = fail = 0


def check(name, cond):
    global ok, fail
    ok += cond
    fail += not cond
    print(("PASS " if cond else "FAIL ") + name)


# 1. Alle Effekte laufen und liefern korrekte Form/Typ
for name, cls in EFFECTS.items():
    try:
        out = cls().apply(IMG.copy(), effect_defaults(cls), np.random.default_rng(1))
        check(f"effect {name}", out.shape == IMG.shape and out.dtype == np.uint8)
    except Exception as e:
        check(f"effect {name} ({e})", False)

# 2. Effekte deterministisch bei gleichem Seed
for name in ("pixel_sort", "slice_shift", "byte_glitch", "block_shuffle", "noise"):
    cls = EFFECTS[name]
    a = cls().apply(IMG.copy(), effect_defaults(cls), np.random.default_rng(5))
    b = cls().apply(IMG.copy(), effect_defaults(cls), np.random.default_rng(5))
    check(f"deterministic {name}", np.array_equal(a, b))

# 3. Alle Maskentypen rendern
for kind in MASK_KINDS:
    m = Mask(kind=kind)
    if kind == "polygon":
        m.params["points"] = [(0.2, 0.2), (0.8, 0.3), (0.5, 0.9)]
    r = m.render(160, 120)
    check(f"mask {kind}", r.shape == (120, 160) and 0 <= r.min() and r.max() <= 1)

# 4. Ketten-Operationen: max / min / geklemmte Differenz
lib = {}
left = Mask(kind="rect", params={"x": 0.0, "y": 0.0, "w": 0.6, "h": 1.0}); lib[left.id] = left
right = Mask(kind="rect", params={"x": 0.4, "y": 0.0, "w": 0.6, "h": 1.0}); lib[right.id] = right
u = combine_refs([MaskRef(left.id), MaskRef(right.id, op="union")], lib, 100, 50)
i = combine_refs([MaskRef(left.id), MaskRef(right.id, op="intersect")], lib, 100, 50)
s = combine_refs([MaskRef(left.id), MaskRef(right.id, op="subtract")], lib, 100, 50)
check("union covers all", u.mean() > 0.95)
check("intersect only overlap", 0.15 < i.mean() < 0.25 and i[25, 50] > 0.9 and i[25, 10] < 0.1)
check("subtract clamps", s.min() >= 0 and s[25, 10] > 0.9 and s[25, 50] < 0.1 and s[25, 90] < 0.1)

# 5. Invert + Feather an der Referenz
inv = combine_refs([MaskRef(left.id, invert=True)], lib, 100, 50)
check("invert per ref", inv[25, 90] > 0.9 and inv[25, 10] < 0.1)
soft = combine_refs([MaskRef(left.id, feather=10.0)], lib, 100, 50)
check("feather softens", 0.05 < soft[25, 60] < 0.95)

# 6. Pipeline: Effekt wirkt nur im maskierten Bereich
proj = Project()
box = proj.add_mask(Mask(kind="rect", params={"x": 0.5, "y": 0.0, "w": 0.5, "h": 1.0}))
proj.layers = [Layer(effect="invert_colors", refs=[MaskRef(box.id)])]
out = engine.render(proj, IMG, seed=1)
check("masked pipeline left untouched", np.array_equal(out[:, :70], IMG[:, :70]))
check("masked pipeline right changed", not np.array_equal(out[:, 90:], IMG[:, 90:]))

# 7. Zwei Ebenen, gleiche Maske, eine invertiert -> ganzes Bild verändert, unterschiedlich
proj2 = Project()
m2 = proj2.add_mask(Mask(kind="rect", params={"x": 0.0, "y": 0.0, "w": 0.5, "h": 1.0}))
proj2.layers = [
    Layer(effect="invert_colors", refs=[MaskRef(m2.id)]),
    Layer(effect="posterize", params={"levels": 3}, refs=[MaskRef(m2.id, invert=True)]),
]
out2 = engine.render(proj2, IMG, seed=1)
check("dual-ref both sides changed",
      not np.array_equal(out2[:, :70], IMG[:, :70]) and not np.array_equal(out2[:, 90:], IMG[:, 90:]))

# 8. Löschschutz
check("delete blocked while referenced", proj.remove_mask(box.id) is False)
proj.layers[0].refs = []
check("delete allowed after unref", proj.remove_mask(box.id) is True)

# 9. Projekt speichern/laden (Roundtrip)
with tempfile.TemporaryDirectory() as td:
    path = str(Path(td) / "p.pgs.json")
    proj2.save(path)
    loaded = Project.load(path)
    check("roundtrip layers", [l.effect for l in loaded.layers] == [l.effect for l in proj2.layers])
    check("roundtrip masks", len(loaded.masks) == len(proj2.masks))
    check("roundtrip render identical",
          np.array_equal(engine.render(loaded, IMG, seed=1), out2))

# 10. Migration v1 (Inline-Maske)
v1 = {"version": 1, "layers": [
    {"effect": "pixel_sort", "params": {}, "enabled": True,
     "mask": {"mode": "ellipse", "params": {"cx": 0.5, "cy": 0.5, "rx": 0.2, "ry": 0.2},
              "invert": True, "feather": 5.0}},
    {"effect": "noise", "params": {"amount": 10}, "mask": {"mode": "none"}},
]}
mig = Project.from_json(v1)
check("migration creates library mask", len(mig.masks) == 1)
check("migration ref carries invert/feather",
      mig.layers[0].refs[0].invert and mig.layers[0].refs[0].feather == 5.0)
check("migration none-mask -> no refs", mig.layers[1].refs == [])

# 11. Batch: reproduzierbar + Dateien vorhanden
with tempfile.TemporaryDirectory() as td:
    proj3 = Project()
    ly = Layer(effect="slice_shift", rand_keys={"count", "max_shift"})
    proj3.layers = [ly]
    files = engine.run_batch(proj3, IMG, count=3, start_seed=100, outdir=td)
    check("batch files", len(files) == 3 and all(Path(f).exists() for f in files))
    from pixelglitch.engine import reproduce
    from PIL import Image as _PILImage
    first = np.asarray(_PILImage.open(files[0]).convert("RGB"))
    check("batch reproducible from seed", np.array_equal(reproduce(proj3, IMG, 100), first))
    v_a = engine.randomized_copy(proj3, 100).layers[0].params
    v_b = engine.randomized_copy(proj3, 101).layers[0].params
    check("batch actually randomizes", v_a != v_b)

# 10. Batch-Dateinamen: Seed nur als Suffix, ohne "seed"-Wort
import tempfile as _tf
with _tf.TemporaryDirectory() as td:
    files = engine.run_batch(proj, IMG, 2, 500, td, stem="art")
    names = [Path(f).name for f in files]
    check("filenames seed suffix", names == ["art_500.png", "art_501.png"])
    check("no seed word in name", all("seed" not in n for n in names))

# 11. JPG-Qualität wirkt (kleinere Datei bei niedriger Qualität)
with _tf.TemporaryDirectory() as td:
    hi, lo = Path(td) / "hi.jpg", Path(td) / "lo.jpg"
    engine.save_image(IMG, str(hi), "jpg", quality=95)
    engine.save_image(IMG, str(lo), "jpg", quality=20)
    check("jpg quality applied", lo.stat().st_size < hi.stat().st_size)

# 12. Veraltete rand_keys werden beim Laden verworfen
stale = Layer(effect="pixel_sort")
d = stale.to_json(); d["rand_keys"] = ["threshold_min", "lo", "unbekannt"]
loaded_l = Layer.from_json(d)
check("stale rand_keys dropped", loaded_l.rand_keys == {"lo"})

# 13. active_rand_keys zählt nur wirksame Marker aktiver Ebenen
pr = Project()
l1 = Layer(effect="pixel_sort"); l1.rand_keys = {"lo", "kaputt"}
l2 = Layer(effect="noise"); l2.rand_keys = {"amount"}; l2.enabled = False
pr.layers = [l1, l2]
check("active_rand_keys filters", engine.active_rand_keys(pr) == [("Pixel Sort", "lo")])

# 14. rand_hi begrenzt den Würfelbereich (Aussetzer nie > 0.6)
pr2 = Project()
l3 = Layer(effect="pixel_sort"); l3.rand_keys = {"randomness"}
pr2.layers = [l3]
vals = [engine.randomized_copy(pr2, s).layers[0].params["randomness"] for s in range(300)]
check("rand range capped", max(vals) <= 0.6 and min(vals) >= 0.0)

# 15. Batch mit gültigen 🎲-Keys erzeugt wirklich unterschiedliche Bilder
pr3 = Project()
mm = pr3.add_mask(Mask(kind="rect", name="B", params={"x":0.05,"y":0.05,"w":0.9,"h":0.9}))
l4 = Layer(effect="pixel_sort"); l4.rand_keys = {"lo", "hi"}
l4.refs = [MaskRef(mask_id=mm.id)]
pr3.layers = [l4]
outs = [engine.render(engine.randomized_copy(pr3, 1000+i), IMG, seed=1000+i) for i in range(6)]
check("batch variants differ", len({o.tobytes() for o in outs}) >= 5)
check("variants not untouched", all(not np.array_equal(o, IMG) for o in outs))

# 16. Bundle: Projekt + Originalbytes + Thumb, byte-genauer Roundtrip
import io as _io
from PIL import Image as _Image
with _tf.TemporaryDirectory() as td:
    buf = _io.BytesIO()
    _Image.fromarray(IMG).save(buf, "PNG")
    raw = buf.getvalue()
    bp = str(Path(td) / "p.pgsz")
    engine.save_bundle(bp, proj3, raw, "foto.png", engine.downscale(IMG, 64))
    p_l, b_l, n_l = engine.load_bundle(bp)
    check("bundle image bytes exact", b_l == raw)
    check("bundle image name", n_l == "foto.png")
    check("bundle project intact", len(p_l.layers) == len(proj3.layers)
          and set(p_l.masks) == set(proj3.masks))
    check("bundle thumb readable", engine.read_bundle_thumb(bp) is not None)
    arr_l = engine.decode_image_bytes(b_l)
    check("bundle image decodes", np.array_equal(arr_l, IMG))
    # ohne Bild speichern
    bp2 = str(Path(td) / "q.pgsz")
    engine.save_bundle(bp2, proj3)
    _, b2, _ = engine.load_bundle(bp2)
    check("bundle without image", b2 is None)
    check("thumb absent ok", engine.read_bundle_thumb(bp2) is None)

# 17. Presets: einfrieren, roundtrip, anwenden, Masken einbetten
from pixelglitch import presets as PS

pp = Project()
m_a = pp.add_mask(Mask(kind="ellipse", name="Kern"))
la = Layer(effect="pixel_sort"); la.rand_keys = {"lo"}
la.refs = [MaskRef(mask_id=m_a.id, feather=2.0)]
lb = Layer(effect="chromatic")
pp.layers = [la, lb]

pre = PS.Preset.from_project(pp, "Testvorlage", "Beschreibung")
check("preset freezes layers", len(pre.layers) == 2)
check("preset embeds only used masks", len(pre.masks) == 1)
check("preset summary readable", "Pixel Sort" in pre.summary())

rt = PS.Preset.from_json(pre.to_json())
check("preset json roundtrip", rt.name == "Testvorlage" and len(rt.layers) == 2)

# Anwenden in ein FREMDES Projekt: Masken werden neu angelegt, Refs zeigen darauf
target = Project()
target.add_mask(Mask(kind="rect", name="Kern"))       # Namenskonflikt provozieren
notes = rt.apply_to(target)
check("apply no notes", notes == [])
check("apply creates layers", len(target.layers) == 2)
check("apply adds mask", len(target.masks) == 2)
new_ref = target.layers[0].refs[0].mask_id
check("apply rewires refs", new_ref in target.masks)
check("apply keeps feather", target.layers[0].refs[0].feather == 2.0)
names = {m.name for m in target.masks.values()}
check("apply renames conflict", "Kern" in names and "Kern 2" in names)
check("apply keeps dice", target.layers[0].rand_keys == {"lo"})
check("applied project renders", engine.render(target, IMG, seed=1).shape == IMG.shape)

# Unbekannter Effekt wird übersprungen statt zu crashen
broken = PS.Preset.from_json(pre.to_json())
broken.layers = [dict(broken.layers[0]), {"effect": "gibt_es_nicht", "params": {}}]
t2 = Project()
notes2 = broken.apply_to(t2)
check("unknown effect skipped", len(t2.layers) == 1 and any("unbekannt" in n for n in notes2))

# Formatversion: Neueres wird abgelehnt, Fremdformat ebenso
future = pre.to_json(); future["version"] = PS.PRESET_VERSION + 1
try:
    PS.Preset.from_json(future); check("rejects newer version", False)
except ValueError as e:
    check("rejects newer version", "neuer" in str(e))
try:
    PS.Preset.from_json({"format": "etwas_anderes"}); check("rejects foreign", False)
except ValueError:
    check("rejects foreign", True)

# Ablage: speichern, scannen, beschädigte Datei meldet Grund statt Absturz
with _tf.TemporaryDirectory() as td:
    folder = Path(td)
    PS.save_preset(pre, folder)
    PS.save_preset(pre, folder)                 # Namenskollision -> Suffix
    (folder / f"kaputt{PS.PRESET_EXT}").write_text("{kein json")
    found, errs = PS.scan_presets(folder)
    check("scan finds saved", len(found) == 2)
    check("scan reports broken", len(errs) == 1 and "kaputt" in errs[0][0])

# Mitgelieferte Presets sind gültig und anwendbar
bts = PS.builtin_presets()
check("builtins exist", len(bts) >= 5 and all(b.origin == "builtin" for b in bts))
for b in bts:
    tp = Project()
    b.apply_to(tp)
    check(f"builtin applies: {b.name}", len(tp.layers) >= 1
          and engine.render(tp, IMG, seed=3).shape == IMG.shape)

# 18. Bewertungen: Sidecar neben den Bildern, 0 löscht
with _tf.TemporaryDirectory() as td:
    engine.save_rating(td, "a.png", 4)
    engine.save_rating(td, "b.png", 2)
    check("ratings stored", engine.load_ratings(td) == {"a.png": 4, "b.png": 2})
    engine.save_rating(td, "b.png", 0)
    check("zero removes", engine.load_ratings(td) == {"a.png": 4})
    check("sidecar in folder", (Path(td) / engine.RATINGS_FILE).exists())
check("missing folder tolerated", engine.load_ratings("/nicht/vorhanden") == {})

# 19. Displace: alle Modi, Randbehandlungen und Quellen
_y, _x = np.mgrid[0:120, 0:160]
STRUCT = np.stack([(_x * 2.4) % 256, (_y * 3.0) % 256,
                   ((_x + _y) * 1.7) % 256], -1).astype(np.uint8)
_dcls = EFFECTS["displace"]

_bad = []
for _mode in ("smear", "shift"):
    for _edge in ("clamp", "wrap", "mirror"):
        for _dir in ("horizontal", "vertical", "both"):
            for _src in ("brightness", "gradient", "hue", "saturation",
                         "red", "green", "blue"):
                _p = effect_defaults(_dcls)
                _p.update(mode=_mode, edge=_edge, direction=_dir, source=_src)
                _o = _dcls().apply(STRUCT.copy(), _p, np.random.default_rng(1))
                if not (_o.shape == STRUCT.shape and _o.dtype == np.uint8
                        and not np.array_equal(_o, STRUCT)):
                    _bad.append((_mode, _edge, _dir, _src))
check(f"displace 126 Kombinationen ({len(_bad)} fehlerhaft)", not _bad)

_p = effect_defaults(_dcls)
_p["strength"] = 0.0
check("displace strength 0 = No-Op",
      np.array_equal(_dcls().apply(STRUCT.copy(), _p, np.random.default_rng(1)),
                     STRUCT))

check("displace ignoriert rng",
      np.array_equal(_dcls().apply(STRUCT.copy(), effect_defaults(_dcls),
                                   np.random.default_rng(1)),
                     _dcls().apply(STRUCT.copy(), effect_defaults(_dcls),
                                   np.random.default_rng(999))))

# Randbehandlung: eine helle Spalte am rechten Rand wird nach rechts
# fortgeschrieben. Bei Klemmen fällt sie heraus, bei Umlaufen taucht sie links
# wieder auf. (bias=-1 setzt den Nullpunkt auf 0, der Versatz ist rein positiv.)
_edgetest = np.zeros((40, 60, 3), np.uint8)
_edgetest[:, -1] = 255
_p = effect_defaults(_dcls)
_p.update(mode="smear", direction="horizontal", edge="clamp", bias=-1.0,
          smoothness=0.0, strength=20.0)
_res = _dcls().apply(_edgetest.copy(), _p, np.random.default_rng(1))
check("displace clamp läuft nicht um", _res[:, 0].max() == 0)
_p["edge"] = "wrap"
check("displace wrap läuft um",
      _dcls().apply(_edgetest.copy(), _p, np.random.default_rng(1))[:, 0].max() > 0)

# Nullpunkt kehrt die Verschieberichtung um
_p = effect_defaults(_dcls)
_p.update(mode="shift", direction="horizontal", smoothness=0.0)
_a = _dcls().apply(STRUCT.copy(), dict(_p, bias=-1.0), np.random.default_rng(1))
_b = _dcls().apply(STRUCT.copy(), dict(_p, bias=1.0), np.random.default_rng(1))
check("displace bias ändert Richtung", not np.array_equal(_a, _b))

# Nur die vorgesehenen Parameter nehmen am Würfeln teil
_rk = {s.key for s in _dcls.params if s.randomizable}
check("displace rand keys", _rk == {"strength", "bias", "smoothness"})

# Als Ebene mit Maske im Projekt
_pr = Project()
_m = _pr.add_mask(Mask("radial", "Mitte"))
_pr.layers.append(Layer(effect="displace",
                        refs=[MaskRef(mask_id=_m.id, invert=True, feather=8.0)]))
_out = engine.render(_pr, STRUCT, seed=1)
check("displace als Ebene mit Maske", _out.shape == STRUCT.shape)
check("displace Maske schont Mitte",
      np.array_equal(_out[58:62, 78:82], STRUCT[58:62, 78:82]))

# 20. Kantenerhaltende Glättung: Bilateral und Kuwahara
FLAT = np.full((40, 50, 3), 120, np.uint8)
EDGE = np.zeros((40, 60, 3), np.uint8)
EDGE[:, 30:] = 255

for _name in ("bilateral", "kuwahara"):
    _c = EFFECTS[_name]
    _o = _c().apply(STRUCT.copy(), effect_defaults(_c), np.random.default_rng(1))
    check(f"{_name} Form/Typ", _o.shape == STRUCT.shape and _o.dtype == np.uint8)
    check(f"{_name} verändert Bild", not np.array_equal(_o, STRUCT))
    check(f"{_name} ignoriert rng",
          np.array_equal(_o, _c().apply(STRUCT.copy(), effect_defaults(_c),
                                        np.random.default_rng(999))))
    check(f"{_name} lässt Konstantfläche unberührt",
          np.array_equal(_c().apply(FLAT.copy(), effect_defaults(_c),
                                    np.random.default_rng(1)), FLAT))
    _e = _c().apply(EDGE.copy(), effect_defaults(_c), np.random.default_rng(1))
    check(f"{_name} hält harte Kante", _e[:, 29].max() < 40 and _e[:, 30].min() > 215)
    # Beide mitteln nur – es darf kein Wert außerhalb des Eingangsbereichs entstehen
    check(f"{_name} bleibt im Wertebereich",
          _o.min() >= STRUCT.min() and _o.max() <= STRUCT.max())
    # Randradien laufen durch
    _lo = dict(effect_defaults(_c), radius=1)
    _hi = dict(effect_defaults(_c), radius=[s for s in _c.params if s.key == "radius"][0].hi)
    check(f"{_name} Radiusgrenzen",
          all(_c().apply(STRUCT.copy(), _p, np.random.default_rng(1)).shape == STRUCT.shape
              for _p in (_lo, _hi)))

# Höhere Toleranz glättet stärker: die Restvarianz gegenüber dem Original sinkt
_bc = EFFECTS["bilateral"]
_soft = _bc().apply(STRUCT.copy(), dict(effect_defaults(_bc), tolerance=90.0),
                    np.random.default_rng(1))
_hard = _bc().apply(STRUCT.copy(), dict(effect_defaults(_bc), tolerance=2.0),
                    np.random.default_rng(1))
check("bilateral Toleranz wirkt", _soft.astype(np.int32).var() < _hard.astype(np.int32).var())

# Mehr Durchgänge glätten weiter
_one = _bc().apply(STRUCT.copy(), dict(effect_defaults(_bc), iterations=1),
                   np.random.default_rng(1))
_four = _bc().apply(STRUCT.copy(), dict(effect_defaults(_bc), iterations=4),
                    np.random.default_rng(1))
check("bilateral Durchgänge wirken", _four.astype(np.int32).var() < _one.astype(np.int32).var())

check("glättung rand keys",
      {s.key for s in _bc.params if s.randomizable} == {"radius", "tolerance"}
      and {s.key for s in EFFECTS["kuwahara"].params if s.randomizable} == {"radius"})

# 21. Dateinamen-Praefix plattformuebergreifend entschaerfen
_cases = {
    "glitch": "glitch",                      # unveraendert
    "mein bild": "mein bild",                # Leerzeichen sind erlaubt
    "a:b": "a_b",                            # Windows-verboten
    "a/b\\c": "a_b_c",                        # Pfadtrenner beider Welten
    'x<y>z|w?v*u"t': "x_y_z_w_v_u_t",
    "  ..  ": "glitch",                      # nur Punkte/Leerzeichen -> Fallback
    "": "glitch",
    "CON": "glitch",                         # Windows-Geraetename
    "con.png": "glitch",
}
_wrong = {k: engine.safe_stem(k) for k, v in _cases.items()
          if engine.safe_stem(k) != v}
check(f"safe_stem entschaerft Praefixe ({_wrong or 'alle korrekt'})", not _wrong)
check("safe_stem kuerzt lange Praefixe", len(engine.safe_stem("x" * 200)) == 60)

# run_batch darf keine Datei mit verbotenem Zeichen im Namen erzeugen
import tempfile as _tf
_bdir = _tf.mkdtemp()
_bp = Project()
_bp.layers.append(Layer(effect="posterize"))
_files = engine.run_batch(_bp, STRUCT, 2, 7, _bdir, "png", 'bad:name/x', 90)
check("run_batch erzeugt gueltige Dateinamen",
      len(_files) == 2 and all(not set(Path(f).name) & set('<>:"/\\|?*')
                               for f in _files))

print(f"\n{ok} passed, {fail} failed")
raise SystemExit(1 if fail else 0)
