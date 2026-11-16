"""Temporary storage for GUI tests; never read or clear real application data."""
import atexit
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class GuiTestEnvironment:
    def __init__(self):
        from PySide6.QtCore import QSettings, QStandardPaths
        from PySide6.QtWidgets import QApplication

        self.temp = tempfile.TemporaryDirectory(prefix="pixelglitch-test-")
        self.root = Path(self.temp.name).resolve()
        for scope in (QSettings.UserScope, QSettings.SystemScope):
            QSettings.setPath(QSettings.IniFormat, scope, str(self.root / "settings"))
        # Redirect every Qt writable location before constructing any widgets.
        # Test mode alone would still use a shared directory across test runs.
        self.paths = patch.object(
            QStandardPaths, "writableLocation",
            side_effect=lambda location: str(self.root / location.name),
        )
        self.paths.start()
        self.app = QApplication.instance() or QApplication([])
        # The (organization, application) overload uses NativeFormat on macOS
        # even after setDefaultFormat(). Select the format explicitly instead.
        from pixelglitch import gui
        self.settings = patch.object(
            gui, "QSettings",
            side_effect=lambda org, app: QSettings(
                QSettings.IniFormat, QSettings.UserScope, org, app),
        )
        self.settings.start()
        assert Path(gui.QSettings("PixelGlitch", "Studio").fileName()).resolve().is_relative_to(self.root)
        gui.QSettings("PixelGlitch", "Studio").setValue(
            "projects_dir", str(self.root / "projects"))
        atexit.register(self.cleanup)

    def cleanup(self):
        self.temp.cleanup()
        self.settings.stop()
        self.paths.stop()
