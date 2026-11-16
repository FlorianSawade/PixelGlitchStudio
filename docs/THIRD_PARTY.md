# Mitgelieferte Bibliotheken und Quellcode

PixelGlitch Studio: Copyright (c) 2026 Florian Sawade, GPL-3.0-only.
Die Lizenz des Projekts steht in [LICENSE](../LICENSE). Drittanbieter behalten
ihre jeweiligen Urheberrechte und Lizenzen.

Die Desktop-Pakete enthalten Python, PySide6/Qt und Shiboken6, NumPy, Pillow
sowie auf macOS PyObjC. PyInstaller erstellt das Paket. Zu diesen Komponenten
können weitere native Bibliotheken gehören, etwa Bild-Codecs und numerische
Bibliotheken. Die vollständigen mitgelieferten Texte stehen im App-Archiv im
Ordner `THIRD_PARTY_LICENSES`; die konkret installierten Python-Pakete sind in
`dependencies.txt` dokumentiert.

## Quellen und Lizenztexte

Die Release stellt neben dem Projektquellcode die verwendeten
Qt-/PySide-Quellarchive und die Quellpakete von NumPy, Pillow, PyObjC und
PyInstaller als separate Downloads bereit. Sie müssen nicht heruntergeladen
werden, um die App zu benutzen.

`UPSTREAM-SOURCES.json` nennt Originalquelle, Dateiname und SHA-256-Prüfsumme.
`SHA256SUMS` enthält die Prüfsummen der Upstream-Quellarchive. Die Quellen liegen
als Release-Assets im selben Repository wie die App-Pakete, unabhängig von
der Verfügbarkeit der Original-Downloadserver.

Für die Release werden die Versionen in `requirements-release.txt` verwendet.
Der Build verändert Qt und PySide nicht. Die Archive enthalten deren
Build-Dateien, Hinweise und ursprüngliche Drittanbieter-Lizenztexte.
`THIRD_PARTY_LICENSES` sammelt diese Texte, ergänzt um die Lizenzdateien der
installierten Python-Distributionen und die Lizenz der tatsächlich eingebetteten
CPython-Version.

## Wiederaufbau und Bibliotheken austauschen

Den passenden Projektquellcode aus der Release entpacken, eine Python-3.12-
Umgebung anlegen und die Versionen aus `requirements-release.txt` installieren:

```bash
python -m pip install -r requirements-release.txt
python build_app.py
```

Details und Plattformvoraussetzungen stehen in [BUILD.md](../BUILD.md).
Die Bibliotheken werden im regulären Ordner-Build dynamisch eingebunden.
Der Projektquellcode und die Build-Anleitung ermöglichen auch einen erneuten
Build mit veränderten Bibliotheken. Die mitgelieferten Komponenten stehen unter
ihren jeweiligen Lizenzbedingungen; deren Rechte werden durch die Projektlizenz
nicht eingeschränkt.
