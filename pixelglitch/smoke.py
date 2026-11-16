"""Startup/render/export check used for testing packaged desktop applications."""
import json
import os
from pathlib import Path
import tempfile

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from . import __version__, engine, gui


def main():
    # Kept separate from normal startup: do not touch real settings or presets.
    with tempfile.TemporaryDirectory(prefix='pixelglitch-smoke-') as temp:
        root = Path(temp)
        original_settings = gui.QSettings

        def settings(org, app):
            return QSettings(str(root / f'{org}-{app}.ini'), QSettings.IniFormat)

        gui.QSettings = settings
        settings('PixelGlitch', 'Studio').setValue('projects_dir', str(root / 'projects'))
        settings('PixelGlitch', 'Studio').setValue('theme', 'dark')
        app = QApplication([])

        class SmokeWindow(gui.MainWindow):
            def _presets_dir(self):
                folder = root / 'presets'
                folder.mkdir(exist_ok=True)
                return folder

        win = None
        try:
            win = SmokeWindow()
            win.show()
            app.processEvents()
            source = np.arange(120 * 160 * 3, dtype=np.uint32).reshape(120, 160, 3).astype(np.uint8)
            engine.save_image(source, str(root / 'source.png'))
            win._load_path(str(root / 'source.png'))
            win._add_layer('pixel_sort')
            win._add_layer('chromatic')
            win._render_timer.stop()
            win._render_now()
            app.processEvents()
            if win.preview is None or win.preview.shape != source.shape:
                raise RuntimeError('Startup/render check failed')
            target = root / 'export.png'
            engine.save_image(win.preview, str(target))
            if not np.array_equal(engine.load_image(str(target)), win.preview):
                raise RuntimeError('Export roundtrip failed')
            result = {'version': __version__, 'startup': True, 'render': True, 'export': True}
            report = os.environ.get('PIXELGLITCH_SMOKE_RESULT')
            if report:
                Path(report).write_text(json.dumps(result), encoding='utf-8')
            return 0
        finally:
            if win is not None:
                win.hide()
                win.deleteLater()
                app.processEvents()
            gui.QSettings = original_settings
