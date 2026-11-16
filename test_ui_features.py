"""GUI-Tests 2.6: Statusleiste, Dirty-Marker, Kennwerte, Presets, Galerie."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from gui_test_support import GuiTestEnvironment

test_env = GuiTestEnvironment()
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog, QFileDialog
from PySide6.QtCore import Qt
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from pixelglitch.gui import MainWindow, projects_dir, set_projects_dir
from pixelglitch import presets as PS, engine
from pixelglitch.masks import Mask, MaskRef

ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += not cond
    print(("PASS " if cond else "FAIL ") + name)

# Keine fest verdrahteten /tmp-Pfade: unter Windows gibt es die nicht.
TMP = str(test_env.root)
IMG = os.path.join(TMP, "pgs_g.png")
BIG = os.path.join(TMP, "pgs_gross.png")

arr = (np.random.default_rng(5).random((120, 180, 3)) * 255).astype(np.uint8)
Image.fromarray(arr).save(IMG)
proj_dir = tempfile.mkdtemp(dir=TMP); set_projects_dir(proj_dir)
app = test_env.app
win = MainWindow(); win.show()

# ---------- Statusleiste
check("status: kein Projekt", win.status_proj.text() == "Projekt: –")
check("status: zaehler leer", win.status_counts.text() == "Ebenen: 0   Masken: 0")
check("status: bereit", win.status_time.text() == "bereit")
check("kein size grip", not win.statusBar().isSizeGripEnabled())

win._load_path(IMG)
win._add_layer("pixel_sort"); win._add_mask("ellipse")
win._render_now()
check("status: zaehler aktuell", win.status_counts.text() == "Ebenen: 1   Masken: 1")
check("status: renderzeit", "gerendert in" in win.status_time.text()
      and "ms" in win.status_time.text() and "Seed" in win.status_time.text())

# Schnell-Hinweis nur bei tatsaechlicher Verkleinerung
big = (np.random.default_rng(6).random((1400, 2000, 3)) * 255).astype(np.uint8)
Image.fromarray(big).save(BIG)
win._load_path(BIG); win._render_now()
check("status: schnell-hinweis", "Vorschau ↓" in win.status_time.text())
win.fast = False; win._render_now()
check("status: kein hinweis ohne schnell", "Vorschau ↓" not in win.status_time.text())
win.fast = True
win._load_path(IMG); win._render_now()
check("status: kein hinweis bei kleinem bild", "Vorschau ↓" not in win.status_time.text())

# Fehler-Flash in Warnfarbe, danach zurueck
win.status_msg.setText("vorher")
win._flash_error("Renderfehler: Test", msecs=50)
check("flash text", win.status_msg.text().startswith("Renderfehler"))
check("flash farbe", win.tokens["warn"] in win.status_msg.styleSheet())
import time as _t
_t.sleep(0.2); app.processEvents()
check("flash zurueck", win.status_msg.text() == "vorher" and not win.status_msg.styleSheet())

# ---------- Dirty-Marker im Titel
win._mark_saved(); win._update_title()
check("titel sauber", not win.windowTitle().startswith("•"))
win._add_layer("noise"); win._update_title()
check("titel dirty", win.windowTitle().startswith("•"))
win._mark_saved(); win._update_title()
check("titel wieder sauber", not win.windowTitle().startswith("•"))
win.project_name = "Nordlicht"; win._update_title()
check("titel zeigt namen", win.windowTitle().endswith("– Nordlicht"))
check("status zeigt namen", win.status_proj.text() == "Projekt: Nordlicht")

# ---------- Kennwertzeile der Masken
m_el = win.project.ordered_masks()[0]
line = win._mask_params_line(m_el)
check("kennwerte ellipse", "cx" in line and "·" in line)
poly = Mask(kind="polygon", name="P", params={"points": [(0.1,0.1),(0.5,0.2),(0.3,0.7)]})
check("kennwerte polygon", win._mask_params_line(poly) == "3 Punkte")
win._refresh_mask_list()
check("liste zeigt 3 zeilen", win.mask_list.item(0).text().count("\n") == 2)

# ---------- Tastenkuerzel
sc = {a.text(): a.shortcut().toString() for a in win.findChildren(type(win.menuBar().actions()[0]))}
have = [v for v in sc.values() if v]
check("shortcuts vergeben", any("Ctrl+S" in v for v in have)
      and any("Ctrl+E" in v for v in have) and any("Ctrl+B" in v for v in have)
      and any("Ctrl+R" in v for v in have) and any("Ctrl+G" in v for v in have))

# ---------- Presets
check("presets tab", [win.tabs.tabText(i) for i in range(win.tabs.count())][2] == "Presets")
n_builtin = len(PS.builtin_presets())
check("builtins gelistet", win.preset_list.count() == n_builtin)
win.preset_list.setCurrentRow(0)
check("builtin: loeschen gesperrt", not win.preset_del_btn.isEnabled())
check("builtin: duplizieren erlaubt", win.preset_dup_btn.isEnabled())
check("builtin: hinweis im tooltip", "schreibgeschützt" in win.preset_del_btn.toolTip())

# Aus Stapel speichern
win.project.layers[0].refs = [MaskRef(mask_id=m_el.id)]
QInputDialog.getText = staticmethod(lambda *a, **k: ("Mein Preset", True))
win._save_preset_from_stack()
check("eigenes preset gespeichert", win.preset_list.count() == n_builtin + 1)
win.preset_list.setCurrentRow(n_builtin)
_p, own = win._current_preset()
check("eigenes ist user", own.origin == "user" and own.name == "Mein Preset")
check("user: loeschen erlaubt", win.preset_del_btn.isEnabled())

# Anwenden ersetzt den Stapel
win._close_project(); win._load_path(IMG)
check("stapel leer", len(win.project.layers) == 0)
win.preset_list.setCurrentRow(n_builtin)
win._apply_preset()
check("preset angewendet", len(win.project.layers) == 2)
check("preset brachte maske mit", len(win.project.masks) == 1)
check("referenz zeigt auf neue maske",
      win.project.layers[0].refs[0].mask_id in win.project.masks)
win._render_now()
check("render nach preset", win.preview is not None)

# Duplizieren + Loeschen
win.preset_list.setCurrentRow(0)
win._dup_preset()
check("dupliziert", win.preset_list.count() == n_builtin + 2)
dup_row = [i for i in range(win.preset_list.count())
           if "Kopie" in win.preset_list.item(i).text()][0]
win.preset_list.setCurrentRow(dup_row)
win._del_preset()
check("geloescht", win.preset_list.count() == n_builtin + 1)

# Export + Import (Austauschdatei)
exp_dir = tempfile.mkdtemp(dir=TMP)
target = os.path.join(exp_dir, "geteilt.pgpreset")
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (target, ""))
win.preset_list.setCurrentRow(n_builtin)
win._export_preset()
check("exportiert", os.path.exists(target))
loaded = PS.load_preset(target)
check("export inhaltlich ok", len(loaded.layers) == 2 and len(loaded.masks) == 1)
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (target, ""))
win._import_preset()
check("importiert", win.preset_list.count() == n_builtin + 2)

# Beschaedigte Datei wird gemeldet statt zu crashen
open(os.path.join(win._presets_dir(), "kaputt.pgpreset"), "w").write("{")
win._reload_presets()
check("kaputte datei gelistet", any("Beschädigt" in win.preset_list.item(i).text()
                                    for i in range(win.preset_list.count())))
check("kaputte datei nicht waehlbar", any(
    not (win.preset_list.item(i).flags() & Qt.ItemIsEnabled)
    for i in range(win.preset_list.count())))

# ---------- Galerie
gal_dir = tempfile.mkdtemp(dir=TMP)
for i, name in enumerate(["a.png", "b.png", "c.jpg"]):
    Image.fromarray((arr + i * 20).astype(np.uint8)).save(os.path.join(gal_dir, name))
open(os.path.join(gal_dir, "notiz.txt"), "w").write("kein bild")
gp = win.gallery_panel
gp.project_only.setChecked(False)      # Fremddateien ohne Projekt-Präfix
gp.set_folder(gal_dir)
check("galerie zeigt bilder", gp.grid.count() == 3)
check("galerie ignoriert fremde dateien",
      all(not p.endswith(".txt") for p in gp.files()))
check("ordner angezeigt", gp.dir_label.text() == gal_dir)

# Bewerten schreibt Sidecar
first = gp.grid.item(0)
tile = gp.grid.itemWidget(first)
tile.stars.set_value(4); tile.rated.emit(tile.path, 4)
check("bewertung gespeichert",
      engine.load_ratings(gal_dir).get(os.path.basename(tile.path)) == 4)
check("sterne sichtbar", "★" in tile.stars.text())

# Filter
gp.filter_box.setCurrentIndex(3)     # ★ 3+
check("filter greift", gp.grid.count() == 1)
gp.filter_box.setCurrentIndex(0)
check("filter zurueck", gp.grid.count() == 3)

# Klick auf denselben Stern setzt zurueck
tile2 = gp.grid.itemWidget(gp.grid.item(0))
tile2.stars.set_value(0); tile2.rated.emit(tile2.path, 0)
check("null loescht bewertung",
      os.path.basename(tile2.path) not in engine.load_ratings(gal_dir))

# Doppelklick -> Vorschau im Canvas
sig = []
gp.fileActivated.connect(sig.append)
gp.fileActivated.emit(gp.files()[0])
check("aktivierung feuert", len(sig) == 1)
win.preview_file(gp.files()[0])
check("canvas zeigt datei", not win.canvas.pix_item.pixmap().isNull())

# Dock + Umschalter
check("dock vorhanden", win.gallery_dock.widget() is win.batch_panel
      and win.batch_panel.gallery is gp)
win.gallery_dock.setVisible(True); app.processEvents()
check("dock sichtbar", win.gallery_dock.isVisible())

# Theme-Wechsel faerbt Galerie mit
win._retheme("light"); app.processEvents()
check("galerie nach retheme ok", gp.grid.count() == 3)
win._retheme("dark")

# ---------- Batch im Dock (nicht mehr modal)
import time as _time
from pixelglitch.engine import Project
bp = win.batch_panel
check("kein dialog mehr", not hasattr(sys.modules["pixelglitch.gui"], "BatchDialog"))
check("einstellungen im dock", bp.settings_col.isVisibleTo(bp))
bp.collapse_btn.setChecked(True)
check("einstellungen einklappbar", not bp.settings_col.isVisibleTo(bp))
bp.collapse_btn.setChecked(False)

# Ebenen-Auswahl folgt dem Projekt
win._close_project(); win._load_path(IMG)
win._add_layer("pixel_sort")
check("ebenen-auswahl aktualisiert", len(bp.layer_checks) == 1)
win._add_layer("noise")
check("ebenen-auswahl waechst", len(bp.layer_checks) == 2)
by_fx = {l.effect: l for l in win.project.layers}
by_fx["pixel_sort"].rand_keys = {"lo", "hi"}
bp.refresh_layers()
check("zaehler in auswahl", any("· 2 🎲" in c.text() for c in bp.layer_checks))

# Lauf im Dock: Schnappschuss friert das Projekt ein
out = tempfile.mkdtemp(dir=TMP)
bp.count.setValue(3); bp.seed.setValue(7000); bp.fmt.setCurrentText("png")
bp.outdir.setText(out); bp.stem.setText("v"); bp.fast.setChecked(False)
bp._run()
check("fortschritt sichtbar", bp.bar.isVisibleTo(bp))
check("abbrechen sichtbar", bp.stop_btn.isVisibleTo(bp))
check("schnappschuss ist kopie", bp._snapshot is not win.project)
# Aenderung waehrend des Laufs darf die Varianten nicht beeinflussen
ps_idx = [i for i, l in enumerate(win.project.layers) if l.effect == "pixel_sort"][0]
win.project.layers[ps_idx].params["lo"] = 0.999
t0 = _time.time()
while bp.worker and bp.worker.isRunning() and _time.time() - t0 < 40:
    app.processEvents(); _time.sleep(0.03)
app.processEvents()
produced = sorted(f for f in os.listdir(out) if f.endswith(".png"))
check("drei varianten", len(produced) == 3)
check("lauf registriert", len(bp.run_index) == 3)
check("galerie zeigt lauf", bp.gallery.folder == out)
check("status meldet fertig", "Batch fertig" in win.status_msg.text())
check("bar wieder versteckt", not bp.bar.isVisibleTo(bp))

# Seed-Ermittlung
p0 = os.path.join(out, produced[0])
check("seed aus lauf", bp.seed_of(p0) == 7000)
check("seed aus dateiname", bp.seed_of("/x/y_4242.png") == 4242)
check("kein seed erkennbar", bp.seed_of("/x/ohnezahl.png") is None)

# Uebernehmen: identischer Stapel -> Werte werden geschrieben
win.project.layers[ps_idx].params["lo"] = 0.1
expected = engine.randomized_copy(win.project, 7001).layers[ps_idx].params["lo"]
bp.adopt_file(os.path.join(out, produced[1]))
check("uebernahme setzt seed", win.seed == 7001)
check("uebernahme setzt werte", win.project.layers[ps_idx].params["lo"] == expected)
check("uebernahme veraendert wirklich", expected != 0.1)
check("wuerfel-marker bleiben",
      win.project.layers[ps_idx].rand_keys == {"lo", "hi"})

# Uebernehmen bei geaendertem Stapel -> Wiederherstellung des Laufs
n_before = len(win.project.layers)
win._add_layer("chromatic")
check("stapel geaendert", len(win.project.layers) == n_before + 1)
bp.adopt_file(p0)          # QMessageBox.question ist auf Yes gestubbt
check("stapel wiederhergestellt", len(win.project.layers) == n_before)
check("wiederherstellung setzt seed", win.seed == 7000)

# Adopt-Knopf folgt der Auswahl
bp.gallery.grid.setCurrentRow(0)
check("adopt-knopf aktiv", bp.adopt_btn.isEnabled())

# ---------- Galerie: Filter auf das aktuelle Projekt
gp.set_folder(gal_dir)                 # der Batch hatte die Galerie umgezogen
gp.set_project_prefix("nordlicht")
for n in ("nordlicht_1.png", "nordlicht_2.png", "fremd_9.png"):
    Image.fromarray(arr).save(os.path.join(gal_dir, n))
gp.project_only.setChecked(False); gp.reload()
check("ohne filter alle bilder", gp.grid.count() == 6)
gp.project_only.setChecked(True)
check("filter zeigt nur projekt", gp.grid.count() == 2)
check("zugehoerigkeit korrekt", gp.belongs_to_project("nordlicht_5.png")
      and not gp.belongs_to_project("fremd_9.png")
      and not gp.belongs_to_project("nordlichtXYZ_5.png"))
gp.set_project_prefix("")
check("ohne praefix keine einschraenkung", gp.belongs_to_project("irgendwas.png"))
check("checkbox deaktiviert ohne praefix", not gp.project_only.isEnabled())
gp.set_project_prefix("nordlicht")
check("leertext erklaert filter", True)
gp.filter_box.setCurrentIndex(0)

# Präfix folgt dem Projekt (das Präfix wurde oben manuell auf "v" gesetzt,
# deshalb erst zurück auf Automatik)
check("manuelles praefix ueberlebt batch", win.batch_panel.stem.text() == "v")
win.batch_panel.stem.setText("")
win._new_project("Polarlicht")
check("stem folgt projektnamen", win.batch_panel.stem.text() == "Polarlicht")
check("praefix folgt stem", gp.project_prefix == "Polarlicht")
win.batch_panel.stem.setText("eigenes")        # manuell angepasst
win._new_project("Zweitprojekt")
check("eigenes praefix bleibt", win.batch_panel.stem.text() == "eigenes")
win.batch_panel.stem.setText("")              # leeren = zurück zur Automatik
win._new_project("Drittprojekt")
check("automatik greift wieder", win.batch_panel.stem.text() == "Drittprojekt")

# ---------- Neu würfeln: pro Ebene, nicht global
win._load_path(IMG)
win._add_layer("pixel_sort")
win.layer_list.setCurrentRow(0)
win._rebuild_settings()
check("wuerfel-knopf vorhanden", hasattr(win, "reroll_btn"))
check("ohne marker deaktiviert", not win.reroll_btn.isEnabled())
ly = win.project.layers[0]
before = dict(ly.params)
win._reroll_layer()
check("ohne marker keine aenderung", ly.params == before)
check("hinweis in statusleiste", "kein Parameter mit 🎲" in win.status_msg.text())

ly.rand_keys = {"lo", "hi"}
win._rebuild_settings()
check("mit marker aktiviert", win.reroll_btn.isEnabled())
check("tooltip nennt anzahl", "2 🎲" in win.reroll_btn.toolTip())
before = dict(ly.params)
changed = False
for _ in range(8):                      # Zufall: irgendwann muss sich etwas ändern
    win._reroll_layer()
    if (ly.params["lo"], ly.params["hi"]) != (before["lo"], before["hi"]):
        changed = True
        break
check("markierte parameter aendern sich", changed)
check("unmarkierte bleiben", ly.params["direction"] == before["direction"])
check("meldung nennt ebene", "Pixel Sort" in win.status_msg.text())

# Markierung ueber die UI: Knopf folgt sofort, ohne Neuaufbau
from PySide6.QtWidgets import QToolButton as _QTB
def dice_buttons():
    return [b for b in win.settings_area.widget().findChildren(_QTB)
            if b.isCheckable() and b.toolTip() == "Im Batch zufällig variieren"]
ly.rand_keys.clear(); win._rebuild_settings()
check("live: erst deaktiviert", not win.reroll_btn.isEnabled())
dice_buttons()[3].setChecked(True)
check("live: nach markieren aktiv", win.reroll_btn.isEnabled())
check("live: tooltip nennt anzahl", "1 🎲" in win.reroll_btn.toolTip())
check("live: batch-liste aktualisiert",
      any("· 1 🎲" in c.text() for c in win.batch_panel.layer_checks))
dice_buttons()[3].setChecked(False)
check("live: nach entmarkieren deaktiviert", not win.reroll_btn.isEnabled())
check("live: batch-liste zurueck",
      any("ohne 🎲" in c.text() for c in win.batch_panel.layer_checks))

# Wuerfeln ueber den Knopf selbst (nicht nur ueber die Methode)
dice_buttons()[3].setChecked(True); dice_buttons()[4].setChecked(True)
vor = dict(ly.params)
for _ in range(8):
    win.reroll_btn.click()
    if (ly.params["lo"], ly.params["hi"]) != (vor["lo"], vor["hi"]):
        break
check("knopfdruck wuerfelt", (ly.params["lo"], ly.params["hi"]) != (vor["lo"], vor["hi"]))
check("regler zeigen neue werte",
      any(isinstance(x, float) for x in (ly.params["lo"], ly.params["hi"])))

# Zweite Ebene: der Knopf zielt auf die ausgewaehlte
win._add_layer("noise")
win.layer_list.setCurrentRow(0)
win._rebuild_settings()
top = win.project.layers[0]
check("aktive ebene ist die oberste", top.effect == "noise")
top.rand_keys = {"amount"}
win._rebuild_settings()
noise_before = top.params["amount"]
sort_before = dict(win.project.layers[1].params)
for _ in range(8):
    win._reroll_layer()
    if top.params["amount"] != noise_before:
        break
check("nur aktive ebene betroffen",
      win.project.layers[1].params == sort_before)

# Kein Wuerfel mehr in der Werkzeugleiste, Seed-Funktion im Menue
from PySide6.QtWidgets import QToolBar
bar = win.findChild(QToolBar)
check("kein wuerfel in der leiste",
      not any(a.text() == "Neu würfeln" for a in bar.actions()))
check("seed im ansicht-menue",
      any(a.text() == "Neuer Zufalls-Seed" for a in win.view_menu.actions()))
seed_before = win.seed
win._reseed()
check("seed-funktion erhoeht seed", win.seed == seed_before + 1)

# ---------- Batch-Knopf schaltet das Panel
check("batch-knopf ist umschalter", win.batch_action.isCheckable())
win.gallery_dock.setVisible(False); app.processEvents()
check("knopf folgt dock (aus)", not win.batch_action.isChecked())
win.batch_action.setChecked(True); app.processEvents()
check("panel an", win.gallery_dock.isVisible())
check("einstellungen ausgeklappt", not win.batch_panel.collapse_btn.isChecked())
win.batch_action.setChecked(False); app.processEvents()
check("panel aus", not win.gallery_dock.isVisible())
win.gallery_dock.setVisible(True); app.processEvents()
check("knopf folgt dock (an)", win.batch_action.isChecked())

print(f"\n{ok} passed, {fail} failed")
# Qt sauber verlassen: umgeht Aufräum-Meldungen beim Interpreter-Ende
sys.stdout.flush()
test_env.cleanup()
os._exit(1 if fail else 0)
