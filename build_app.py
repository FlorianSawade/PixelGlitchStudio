#!/usr/bin/env python3
"""Standalone-App bauen (macOS .app, Windows .exe, Linux-Binary).

    pip install -r requirements.txt pyinstaller
    python build_app.py

Das Ergebnis liegt danach in `dist/`.

WICHTIG: PyInstaller kann nicht über Plattformen hinweg bauen. Eine macOS-App
entsteht nur auf einem Mac, eine Windows-.exe nur unter Windows, ein
Linux-Binary nur unter Linux. Wer alle drei ohne drei Rechner braucht, nutzt
den mitgelieferten GitHub-Workflow in `.github/workflows/build.yml`.

Optionen:
    --onefile   eine einzelne Datei statt eines Ordners (startet langsamer)
    --console   Konsolenfenster mitlaufen lassen (zur Fehlersuche)
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pixelglitch import __version__                       # noqa: E402

APP_NAME = "PixelGlitch Studio"
BUNDLE_ID = "studio.pixelglitch.app"
ROOT = Path(__file__).parent
ICON_DIR = ROOT / "build" / "icons"


def make_icons() -> dict:
    """Logo aus branding.py in PNG/ICO/ICNS rendern (keine Binär-Assets nötig)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication
    from PIL import Image
    from pixelglitch import branding

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    png = ICON_DIR / "icon.png"
    branding.logo_pixmap(512).save(str(png))

    img = Image.open(png).convert("RGBA")
    ico = ICON_DIR / "icon.ico"
    img.save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64),
                         (128, 128), (256, 256)])
    icns = ICON_DIR / "icon.icns"
    try:
        img.save(icns)
    except Exception as exc:                              # pragma: no cover
        print(f"Hinweis: .icns nicht erzeugbar ({exc}) – Build läuft ohne "
              "macOS-Icon weiter.")
        icns = None
    return {"png": png, "ico": ico, "icns": icns}


def main():
    onefile = "--onefile" in sys.argv
    console = "--console" in sys.argv

    shutil.rmtree(ROOT / "dist", ignore_errors=True)
    icons = make_icons()

    args = [
        "run.py",
        "--name", "PixelGlitchStudio",
        "--noconfirm",
        "--clean",
        "--collect-submodules", "pixelglitch",
        "--onefile" if onefile else "--onedir",
        "--console" if console else "--windowed",
    ]
    if sys.platform == "darwin":
        if icons["icns"]:
            args += ["--icon", str(icons["icns"])]
        args += ["--osx-bundle-identifier", BUNDLE_ID]
    elif sys.platform.startswith("win"):
        args += ["--icon", str(icons["ico"])]
    else:
        args += ["--icon", str(icons["png"])]

    print(f"Baue {APP_NAME} {__version__} für {sys.platform} …")
    import PyInstaller.__main__ as pi
    pi.run(args)

    dist = ROOT / "dist"
    made = sorted(p.name for p in dist.iterdir()) if dist.exists() else []
    print("\nFertig. In dist/:", ", ".join(made) or "(nichts)")
    if sys.platform == "darwin":
        print("Die .app ist unsigniert: beim ersten Start Rechtsklick → Öffnen,\n"
              "sonst blockiert Gatekeeper sie.")


if __name__ == "__main__":
    main()
