"""Rebuild README visuals with the real engine and Qt interface.

Run from the repository root: python docs/generate_readme_assets.py
The source artwork is procedural; no external photos or personal data are used.
Qt settings and application data are isolated in a temporary directory.
"""
from pathlib import Path
import os
import sys

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image, ImageDraw
from pixelglitch import engine, gui, __version__
from gui_test_support import GuiTestEnvironment

OUT = Path(__file__).resolve().parent / 'images'


def artwork():
    """A geometric sunset with a skyline and reflected lights."""
    w, h = 960, 640
    y = np.indices((h, w))[0]
    stops = np.array([[17, 22, 53], [98, 48, 110], [240, 110, 100],
                      [25, 30, 65], [10, 18, 40]])
    t = y / (h - 1) * 4
    idx = np.minimum(t.astype(int), 3)
    arr = stops[idx] * (1 - (t - idx)[..., None]) + stops[idx + 1] * (t - idx)[..., None]
    image = Image.fromarray(arr.astype('uint8'))
    d = ImageDraw.Draw(image)
    d.ellipse((333, 100, 627, 394), fill=(255, 186, 119))
    for yy in range(255, 394, 14):
        d.rectangle((328, yy, 632, yy + 4), fill=(145, 67, 112))
    rng = np.random.default_rng(12)
    for xx in range(0, w, 36):
        top = int(rng.integers(260, 398))
        d.rectangle((xx, top, xx + 28, 430), fill=(17, 26, 49))
        color = (80, 197, 205) if xx % 72 else (245, 122, 168)
        for yy in range(top + 12, 418, 15):
            for wx in (xx + 6, xx + 18):
                if rng.random() > .3:
                    d.rectangle((wx, yy, wx + 3, yy + 5), fill=color)
    for yy in range(438, h, 6):
        spread = int(45 + (yy - 430) * 1.4)
        for _ in range(5):
            xx = int(rng.integers(480 - spread, 480 + spread))
            d.line((xx, yy, xx + int(rng.integers(5, 45)), yy),
                   fill=(int(rng.integers(130, 245)), 105, 145), width=2)
    return np.asarray(image).copy()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = artwork()
    Image.fromarray(source).save(OUT / 'original.png')
    examples = [
        ('pixel-sort', [engine.Layer('pixel_sort', {
            'direction': 'vertical', 'lo': .25, 'hi': .9})]),
        ('signal-glitch', [engine.Layer('slice_shift'),
                          engine.Layer('chromatic', {'shift': 5}),
                          engine.Layer('scanlines')]),
        ('pixel-stretch', [engine.Layer('displace', {
            'strength': 18., 'direction': 'vertical'})]),
    ]
    for name, layers in examples:
        result = engine.render(engine.Project(layers=layers), source, seed=42)
        assert result.shape == source.shape and not np.array_equal(source, result)
        Image.fromarray(result).save(OUT / f'{name}.png')

    test_env = GuiTestEnvironment()
    try:
        app = test_env.app
        gui.QSettings('PixelGlitch', 'Studio').setValue('theme', 'dark')
        win = gui.MainWindow()
        win.resize(1440, 900)
        win.gallery_dock.hide()
        win.project_name = 'Neon City'
        win.seed = 42
        win._load_path(str(OUT / 'original.png'))
        win.project.layers = examples[1][1]
        win._refresh_layer_list()
        win.layer_list.setCurrentRow(0)
        win.show()
        app.processEvents()
        win._render_timer.stop()
        win._render_now()
        win.canvas.fit()
        app.processEvents()
        assert win.preview is not None
        assert win.grab().save(str(OUT / 'screenshot.png'))
        win.hide()
        win.deleteLater()
        app.processEvents()
    finally:
        test_env.cleanup()
    print(f'Generated README images for PixelGlitch Studio {__version__} in {OUT}')


if __name__ == '__main__':
    main()
