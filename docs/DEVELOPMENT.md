# Entwicklung

[Zurück zur README](../README.md)

## Eigene Effekte hinzufügen

Effekte sind selbstbeschreibend; die GUI baut Regler automatisch aus den
Parametern. In `pixelglitch/effects.py`:

```python
@register("my_effect", "Mein Effekt", "Glitch")
class MyEffect:
    params = [
        ParamSpec("strength", "Stärke", "float", 0.5, lo=0.0, hi=1.0, step=0.05),
        ParamSpec("mode", "Modus", "choice", "a", choices=["a", "b"]),
    ]
    def apply(self, arr, p, rng):
        # arr: uint8 (H, W, 3); p: dict; rng: numpy Generator
        return arr  # gleiche Form/Typ zurückgeben
```


Die Engine (`params`, `effects`, `masks`, `engine`) ist GUI-frei und lässt sich aus eigenen Python-Skripten ansteuern. Presets liegen in `pixelglitch/presets.py`, die Oberfläche in `pixelglitch/gui.py`.

## Tests ausführen

Mit installierten Projektabhängigkeiten im Repository-Stamm:

```bash
python test_engine.py
python test_gui.py
python test_ui_features.py
```

Jede Suite ist ein eigenständiges Skript und liefert bei fehlgeschlagenen
Prüfungen einen Exit-Code ungleich null. Die GUI-Suiten setzen Qt auf
`offscreen` und nutzen über `gui_test_support.py` pro Prozess einen eigenen
temporären Ordner für Einstellungen, Projekte, Presets und Testbilder. Die
regulären Anwendungsdaten werden dabei weder eingelesen noch gelöscht.

Der [Build-Workflow](../.github/workflows/build.yml) führt dieselben drei Befehle
auf macOS (arm64 und Intel), Windows und Linux aus. App-Pakete entstehen bei
manuellem Start und Versions-Tags; Details stehen in [BUILD.md](../BUILD.md).

## README-Bilder erzeugen

```bash
python docs/generate_readme_assets.py
```

Vom Repository-Stamm aus mit installierten Projektabhängigkeiten ausführen.
Das Skript zeichnet das Ausgangsmotiv, rendert drei Effektbeispiele und nimmt
die echte Qt-Oberfläche im Offscreen-Modus auf. Einstellungen, Projekte und
Presets der Vorschau werden getrennt von den regulären App-Daten gehalten.
Das Erscheinungsbild des Screenshots kann je nach Plattform und Qt-Version
abweichen. Die Bilder liegen anschließend in `docs/images/`.

## Release-Abhängigkeiten aktualisieren

Die direkten Release-Versionen stehen in `requirements-release.txt`. Ändere
sie gezielt und erzeuge anschließend die vollständige Lock-Datei mit uv:

```bash
python -m pip install uv==0.13.8
uv pip compile requirements-release.txt --universal --python-version 3.12 --generate-hashes --no-header --output-file requirements-release-lock.txt
python .github/scripts/check_release_lock.py
```

Die Lock-Datei gilt für die vier Release-Ziele und fixiert auch indirekte
Abhängigkeiten mit Hashes. Im CI erfolgt die Installation mit `pip`, uv wird
dort nicht benötigt. Nach einem Update die Tests und App-Builds prüfen;
Qt-/PySide-Quellen und Lizenzbeilagen müssen zu den neuen Versionen passen.
Dependabot schlägt wöchentlich Aktualisierungen für Python-Pakete und GitHub
Actions vor. Die Release-Pins und die Lock-Datei gehören zusammen in dieselbe
Änderung; die CI-Konsistenzprüfung erkennt abweichende direkte Versionen.

## GitHub-Social-Preview erzeugen

```bash
python docs/generate_social_preview.py
```

Das Skript verwendet das vorhandene App-Logo und den echten README-Screenshot.
Das PNG liegt unter `docs/images/social-preview.png` (1280 × 640 Pixel, unter
1 MB). Zum Hinterlegen auf GitHub unter **Settings → General → Social preview
→ Edit → Upload an image…** hochladen. Das Einchecken der Datei allein setzt
noch kein Social-Preview-Bild in den Repository-Einstellungen.
