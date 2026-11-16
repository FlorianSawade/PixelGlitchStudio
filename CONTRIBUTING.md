# Mitmachen

Fehlerberichte, Ideen und gezielte Verbesserungen sind willkommen. Prüfe bitte
zuerst die [vorhandenen Issues](https://github.com/FlorianSawade/PixelGlitchStudio/issues),
ob dein Thema schon beschrieben ist. Für eine größere Änderung lohnt sich ein
Issue vor der Umsetzung, damit Ziel und Umfang abgestimmt werden können.

## Fehler und Vorschläge

Für Fehler gibt es eine Vorlage mit App-Version, Betriebssystem und Schritten
zum Nachvollziehen. Bei Problemen mit Bildern helfen zusätzlich Bildgröße,
Effektstapel, Parameter und Seed. Ein kleines Beispielprojekt ist nützlich,
wenn du es öffentlich teilen darfst.

Sicherheitslücken bitte nicht in einem öffentlichen Issue melden. Der private
Meldeweg steht in [SECURITY.md](SECURITY.md).

## Entwicklungsumgebung

Die Referenzversion ist Python 3.12. Erstelle eine eigene virtuelle Umgebung
und installiere die Abhängigkeiten wie in der [README](README.md#installation-und-start)
beschrieben. Für denselben Paketstand wie im Release-Build:

```bash
python -m pip install --require-hashes --only-binary=:all: -r requirements-release-lock.txt
```

Die drei bestehenden Testsuiten werden einzeln ausgeführt:

```bash
python test_engine.py
python test_gui.py
python test_ui_features.py
```

Die GUI-Tests arbeiten ohne Bildschirm und mit getrennten Testdaten. Bitte
prüfe Änderungen an der Oberfläche zusätzlich durch normales Starten der App
mit `python run.py`. Weitere Hinweise, etwa zum Ergänzen eigener Effekte,
stehen in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Pull Requests

Halte eine Änderung möglichst auf ein Thema begrenzt. Beschreibe das Problem,
das neue Verhalten und wie du es geprüft hast. Aktualisiere die Dokumentation,
wenn sich Bedienung oder Installation ändern. Bei sichtbaren Änderungen hilft
ein Screenshot; bei plattformspezifischen Änderungen die Angabe des Systems.

Bitte keine virtuellen Umgebungen, Build-Ausgaben, Zugangsdaten oder privaten
Bilder und Projekte einchecken. Neue Tests sind besonders für behobene Fehler
und Änderungen an der Bildverarbeitung sinnvoll.

## Lizenz

Beiträge zum Projekt werden unter derselben Lizenz wie PixelGlitch Studio
bereitgestellt: **GPL-3.0-only**, siehe [LICENSE](LICENSE). Verwende für neue
Beispielbilder eigenes Material oder Material mit einer passenden Lizenz und
dokumentiere gegebenenfalls Quelle und Lizenz.
