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
