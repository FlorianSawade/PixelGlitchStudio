# Ausführbare Programme bauen

PixelGlitch Studio wird mit **PyInstaller** zu einer eigenständigen Anwendung
gebündelt. Wichtig vorweg, weil es der häufigste Irrtum ist:

> **PyInstaller kann nicht über Plattformen hinweg bauen.** Eine macOS-`.app`
> entsteht nur auf einem Mac, eine Windows-`.exe` nur unter Windows, ein
> Linux-Binary nur unter Linux. Es gibt dafür keinen Schalter — das Bündel
> enthält den Python-Interpreter und die Qt-Bibliotheken des jeweiligen
> Betriebssystems.

Daraus ergeben sich zwei Wege.

---

## Weg 1 — Auf dem eigenen Rechner bauen

Für die Plattform, auf der du gerade sitzt:

```bash
cd PixelGlitchStudio
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements-release-lock.txt
python build_app.py
```

Unter Windows (PowerShell), mit Python 3.12:

```powershell
cd PixelGlitchStudio
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-release-lock.txt
.\.venv\Scripts\python.exe build_app.py
```

`requirements-release.txt` legt die direkten Release-Versionen fest;
`requirements-release-lock.txt` fixiert zusätzlich die indirekten Pakete und
die erlaubten SHA-256-Hashes. Der Workflow installiert ausschließlich aus der
Lock-Datei und bricht ab, wenn die direkten Versionen nicht dazu passen.
Ein identischer Paketstand allein garantiert keine byte-identischen Programme:
Python-Patchversion, Betriebssystem und Build-Werkzeuge außerhalb von Python
können das Ergebnis weiterhin beeinflussen. Der Workflow dokumentiert seine
installierten Pakete in `dependencies.txt`.

Das Ergebnis liegt in `dist/`:

| System  | Ergebnis                              |
|---------|---------------------------------------|
| macOS   | `dist/PixelGlitchStudio.app`          |
| Windows | `dist/PixelGlitchStudio/PixelGlitchStudio.exe` |
| Linux   | `dist/PixelGlitchStudio/PixelGlitchStudio`     |

Optionen: `--onefile` packt alles in eine einzige Datei (bequemer zu
verschicken, startet aber spürbar langsamer, weil sie sich bei jedem Start
entpackt). `--console` lässt ein Terminalfenster mitlaufen — nützlich, wenn
die App startet und sofort wieder verschwindet.

Das App-Icon wird beim Bauen aus `pixelglitch/branding.py` gerendert
(PNG, ICO und ICNS), es liegen also keine Bilddateien im Projekt herum.

### Hinweise für macOS
Die App ist **nicht mit einem Entwicklerzertifikat signiert und nicht
notarisiert**. Aktuelle macOS-Versionen können den Start deshalb blockieren.
Die Freigabe erfolgt nach einem Startversuch gegebenenfalls unter
**Systemeinstellungen → Datenschutz & Sicherheit**. Details stehen in der
[Installationsanleitung](docs/INSTALLATION.md#macos). Für eine regulär signierte
und notarisierte Weitergabe sind ein passendes Entwicklerzertifikat und die
Apple-Notarisierung nötig.

Eine auf Apple Silicon gebaute App läuft nicht auf Intel-Macs und umgekehrt.
Für beides baut man zweimal — oder nutzt Weg 2.

### Hinweise für Windows
Der SmartScreen-Filter warnt bei unsignierten Programmen („Windows hat den
Start einer unbekannten App verhindert"). *Weitere Informationen* →
*Trotzdem ausführen*. Auch hier hilft dauerhaft nur ein Code-Signing-Zertifikat.

### Hinweise für Linux
Das Bündel ist an die glibc-Version des Build-Systems gebunden: Ein auf
Ubuntu 24.04 gebautes Programm läuft **nicht** auf Ubuntu 22.04 (umgekehrt
schon). Deshalb möglichst auf der ältesten Distribution bauen, die man
unterstützen will. Außerdem braucht Qt einige Systembibliotheken; auf einem
nackten Server hilft:

```bash
sudo apt install libgl1 libegl1 libxkbcommon-x11-0 libdbus-1-3 libxcb-cursor0
```

---

## Weg 2 — Alle drei Plattformen automatisch bauen lassen

Der Workflow [`.github/workflows/build.yml`](.github/workflows/build.yml)
verwendet Python 3.12 auf vier Runnern:

| Paket | Runner | Architektur |
| --- | --- | --- |
| macOS Apple Silicon | `macos-15` | arm64 |
| macOS Intel | `macos-15-intel` | x86_64 |
| Windows | `windows-2022` | x86_64 |
| Linux | `ubuntu-24.04` | x86_64 |

Bei Pushes auf `main` und Pull Requests laufen alle drei Testsuiten auf diesen
vier Runnern. Bei einem manuellen Start oder einem Versions-Tag baut jeder
Runner nach seinen erfolgreichen Tests zusätzlich seine Standalone-App.
Fehler auf einer Plattform verhindern nicht die Diagnose der anderen.

1. Projekt in ein GitHub-Repository legen (privat genügt).
2. Reiter **Actions** öffnen, Workflow **Build apps** wählen,
   **Run workflow** klicken.
3. Nach erfolgreichem Lauf liegen die Pakete unter **Artifacts** zum
   Herunterladen bereit (Aufbewahrung: 14 Tage). Die Artifact-ZIP enthält das
   eigentliche App-Archiv und eine SHA-256-Prüfsummendatei. Zum Starten auch
   das innere Archiv vollständig entpacken.

Der Workflow führt vor jedem Bauen alle Testsuiten aus (Engine und Oberfläche,
letztere headless über `QT_QPA_PLATFORM=offscreen`). Nur bei erfolgreichen
Tests auf dem jeweiligen Runner entsteht dort ein App-Paket. Der Release-Job
startet erst, wenn alle vier Runner erfolgreich abgeschlossen sind. Nach dem
Build muss außerdem die tatsächlich gepackte Anwendung mit `--smoke-test`
starten, ein Bild rendern und erfolgreich exportieren.

Wenn alle vier Plattformen erfolgreich sind, legt ein gepushter Versions-Tag
zusätzlich einen **Release-Entwurf** mit allen Paketen und einem Archiv des
zugehörigen Projektquellcodes an. Er wird nicht automatisch veröffentlicht.
Der Tag muss exakt zu `pixelglitch.__version__` passen:

```bash
git tag v2.9.1
git push origin v2.9.1
```

Der Workflow braucht keine selbst hinterlegten Secrets. Tests und Builds
haben nur Leserechte; ausschließlich der Release-Job erhält Schreibrechte für
Repository-Inhalte über den eingebauten `GITHUB_TOKEN`. Bei einem erneuten Lauf
werden nur Assets eines bestehenden Entwurfs ersetzt; ein bereits
veröffentlichter Release wird nicht überschrieben.

Die Archive enthalten die App, GPLv3-Lizenz, Drittanbieter-Lizenztexte, Dokumentation, Startanweisungen und
die konkret installierten Abhängigkeiten (`dependencies.txt`). macOS-ZIPs
werden mit `ditto` erstellt, Linux-Archive als `.tar.gz`, damit Symlinks und
Ausführungsrechte erhalten bleiben. Windows erhält eine `.zip` mit dem
vollständigen App-Ordner.

Der Job `materials` lädt die zu den festgelegten Release-Versionen passenden
Qt-/PySide-Quellen und weitere Upstream-Quellpakete herunter. Er sammelt deren
Lizenztexte; jeder Build ergänzt die Texte aus seinen installierten Paketen
und die Lizenz seiner CPython-Version. Die App-Archive enthalten diese Texte
unter `THIRD_PARTY_LICENSES`. Der Release-Entwurf erhält neben dem
Projektquellcode auch die Upstream-Quellarchive mit Herkunftsmanifest und
Prüfsummen. Details: [Drittanbieter](docs/THIRD_PARTY.md).

Vor der Veröffentlichung die automatischen Testergebnisse kontrollieren und
die normale interaktive Bedienung auf den verfügbaren Zielsystemen prüfen.
Die automatischen Start-, Render- und Exporttests laufen ohne Bildschirm und
ersetzen keine vollständige manuelle Prüfung der Oberfläche.

Für Standard-Runner öffentlicher Repositories stellt GitHub kostenlose
Actions-Läufe bereit. Bei privaten Repositories gelten die Kontingente und
Preise deines GitHub-Plans.

---

## Größe und Startverhalten

Die Paketgröße hängt von Plattform und Bibliotheksversionen ab. Python, Qt
und native Bibliotheken sind enthalten und machen den größten Teil aus. Wer
das drücken will, kann in `build_app.py` gezielt ungenutzte Qt-Module
ausschließen, etwa:

```python
args += ["--exclude-module", "PySide6.QtWebEngineCore",
         "--exclude-module", "PySide6.QtQuick",
         "--exclude-module", "PySide6.Qt3DCore"]
```

Vor dem Ausliefern dann unbedingt einmal starten und alle Bereiche öffnen —
ein zu viel ausgeschlossenes Modul fällt sonst erst beim Nutzer auf.
