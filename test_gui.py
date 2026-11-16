"""GUI-Smoke-Tests: Projekt-Container, Welcome, Masken, Polygon, Batch, Theme."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from gui_test_support import GuiTestEnvironment

test_env = GuiTestEnvironment()
import numpy as np
from PIL import Image

ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += not cond
    print(("PASS " if cond else "FAIL ") + name)

# Keine fest verdrahteten /tmp-Pfade: unter Windows gibt es die nicht.
TMP = str(test_env.root)
IMG = os.path.join(TMP, "pgs_t.png")
OUTDIR = os.path.join(TMP, "pgs_pxout")

rng = np.random.default_rng(3)
arr = (rng.random((200, 300, 3)) * 255).astype(np.uint8)
Image.fromarray(arr).save(IMG)

from PySide6.QtWidgets import QApplication
from pixelglitch import theme, icons, branding, __version__
from pixelglitch.gui import MainWindow, BatchGalleryPanel, projects_dir
from pixelglitch.masks import Mask, MaskRef

app = test_env.app
theme.apply_theme(app, "dark")

# Branding
check("logo renders", not branding.logo_pixmap(128).isNull())
check("splash renders", not branding.splash_pixmap(__version__).isNull())
check("version available", bool(__version__))

win = MainWindow()
check("presets isolated", win._presets_dir().is_relative_to(test_env.root))
check("projects isolated", projects_dir().is_relative_to(test_env.root))
win.show()
win._load_path(IMG); win._render_now()
check("window+image", win.canvas.has_image)

# --- Zoom-Overlay
check("zoom overlay exists", hasattr(win.canvas, "_zoom_box") and win.canvas._zoom_box.isVisible())
z0 = win.canvas.transform().m11()
win.canvas.zoom_in()
check("zoom in works", win.canvas.transform().m11() > z0)
win.canvas.zoom_out()
check("zoom out works", abs(win.canvas.transform().m11() - z0) < 1e-6)
tb_texts = [a.text() for a in win.findChildren(type(win.overlay_action))]
check("fit not in toolbar", "Einpassen" not in tb_texts)

# --- Abschnittstitel „Maskenzuweisung" mit Live-Update
win._add_layer("pixel_sort")
win.layer_list.setCurrentRow(0)
win._rebuild_settings()
check("title default", win._mask_section.header.text().strip() == "Maskenzuweisung")
m = win.project.add_mask(Mask(kind="rect", name="Box"))
win._refresh_mask_list()
win.project.layers[0].refs = [MaskRef(mask_id=m.id)]
win._chain_changed()
t = win._mask_section.header.text()
check("title live-updates", "Maskenzuweisung · Box" in t)
check("summary intact", "Box" in win._mask_summary(win.project.layers[0]))

# --- Polygon-Editing
pm = win.project.add_mask(Mask(kind="polygon", name="Poly"))
win._refresh_mask_list()
win.tabs.setCurrentIndex(1)
win.mask_list.setCurrentRow(1)
win._sync_draw_mode()
win._poly_point(0.1, 0.1); win._poly_point(0.9, 0.1); win._poly_point(0.5, 0.8)
check("poly 3 points", len(pm.params["points"]) == 3)
check("markers shown", len(win.canvas._poly_markers) == 3)
win._poly_moved(1, 0.95, 0.15)
check("poly moved", pm.params["points"][1] == (0.95, 0.15))
win._poly_inserted(1, 0.5, 0.05)
check("poly inserted", len(pm.params["points"]) == 4 and pm.params["points"][1] == (0.5, 0.05))
win._poly_deleted(0)
check("poly deleted", len(pm.params["points"]) == 3)
check("markers synced", len(win.canvas._poly_markers) == 3)

# --- Batch (jetzt im Dock): Persistenz + Qualität + Dateiname
bp = win.batch_panel
bp.count.setValue(7); bp.seed.setValue(4242); bp.fmt.setCurrentText("jpg")
bp.quality.setValue(55); bp.stem.setText("meinbild"); bp.outdir.setText(OUTDIR)
bp._save_settings()
bp2 = BatchGalleryPanel(win, win.tokens, OUTDIR)
check("batch persist count", bp2.count.value() == 7)
check("batch persist seed", bp2.seed.value() == 4242)
check("batch persist fmt+quality", bp2.fmt.currentText() == "jpg" and bp2.quality.value() == 55)
check("batch persist stem", bp2.stem.text() == "meinbild")
from PySide6.QtWidgets import QApplication as _QA
win.gallery_dock.setVisible(True); _QA.instance().processEvents()
check("quality visible for jpg", bp.quality.isVisible())
bp.fmt.setCurrentText("png"); _QA.instance().processEvents()
check("quality hidden for png", not bp.quality.isVisible())

from pixelglitch import engine
files = engine.run_batch(win.project, win.source, 2, 4242, OUTDIR, "jpg", "meinbild", 55)
import os.path
check("batch filename suffix", os.path.basename(files[0]) == "meinbild_4242.jpg")

# --- Projekt schließen + Dirty-Tracking
check("dirty after edits", win._is_dirty())
win._mark_saved()
check("clean after mark", not win._is_dirty())
win.project.layers[0].params["threshold_min"] = 0.11
check("dirty after param change", win._is_dirty())
win._mark_saved()
win._close_project()   # sauber -> keine Nachfrage
check("project closed", len(win.project.layers) == 0 and len(win.project.masks) == 0)
check("image cleared", win.source is None and not win.canvas.has_image)

# Menüeintrag vorhanden
actions = [a.text() for menu in win.menuBar().findChildren(type(win.menuBar().actions()[0].menu())) for a in menu.actions()]
check("close in menu", any("Projekt schließen" in a for a in actions))

# Theme-Wechsel stylt Overlay mit
win._retheme("light")
check("overlay styled after retheme", "background" in win.canvas._zoom_box.styleSheet())
win._retheme("dark")

print(f"\n{ok} passed, {fail} failed")
# Qt sauber verlassen: umgeht Aufräum-Meldungen beim Interpreter-Ende
sys.stdout.flush()
test_env.cleanup()
os._exit(1 if fail else 0)
