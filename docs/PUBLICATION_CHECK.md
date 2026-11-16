# Prüfung vor der ersten Veröffentlichung

Stand: 16. November 2026, Vorbereitung für Version 2.9.1.

## Installation und Builds

| Prüfung | Ergebnis |
| --- | --- |
| Installation aus `requirements.txt` in einer frischen Umgebung | Erfolgreich auf macOS / Apple Silicon mit Python 3.12.16 |
| Installation aus `requirements-release-lock.txt` mit verpflichtenden Hashes und ausschließlich Wheels | Erfolgreich; direkte und indirekte Pakete festgelegt |
| `pip check` | Keine widersprüchlichen Abhängigkeiten |
| Engine-Tests | 122 erfolgreich |
| GUI-Tests | 33 erfolgreich |
| UI-Funktionstests | 118 erfolgreich |
| Eigenständige Mac-App unter Python 3.12 gebaut | Erfolgreich |
| Gepackte App: Start, Rendern und PNG-Export | Erfolgreich im Offscreen-Modus |
| Workflow-Konfiguration | Mit actionlint geprüft |

Die Ergebnisse bestätigen den lokal geprüften Mac-Stand. Die separaten
GitHub-Läufe für Windows, Linux und Intel-Macs stehen vor dem Upload noch aus.
Ein erfolgreicher Offscreen-Test ersetzt keine vollständige manuelle Prüfung
der Oberfläche auf allen Zielsystemen.

## Inhalte und Sicherheitsprüfung

- Git-Historie und Veröffentlichungssnapshot mit **gitleaks 8.30.1** geprüft:
  keine Geheimnisfunde.
- Alle **18 festgelegten Release-Pakete**, einschließlich der nur auf Windows
  oder macOS verwendeten Abhängigkeiten, mit **pip-audit 2.10.1** geprüft:
  keine bekannten Schwachstellen gemeldet.
- Keine versionierten Zugangsdaten-Dateien, lokalen virtuellen Umgebungen,
  Build-Ausgaben, privaten Projektdateien oder absoluten persönlichen Pfade
  gefunden. Alle zur Veröffentlichung vorgesehenen Dateien liegen unter 1 MB.
- Die Dokumentationsbilder stammen aus der App beziehungsweise aus dem eigenen
  geometrischen Beispielmotiv und enthalten keine EXIF-Metadaten.
- Die noch nicht veröffentlichten lokalen Git-Autoren- und Committer-Adressen
  wurden auf die GitHub-noreply-Adresse umgestellt. Der Name Florian Sawade bleibt.

Das sind die Ergebnisse der genannten Werkzeuge zum Prüfzeitpunkt, keine
Garantie, dass jede mögliche Sicherheitslücke oder vertrauliche Information
automatisch erkannt wird.

## GitHub-Einstellungen

Direkt auf GitHub eingerichtet beziehungsweise überprüft:

- Repository-Beschreibung und acht passende Topics.
- Secret Scanning und Push Protection aktiv.
- Dependabot-Warnungen und automatische Sicherheitsupdates aktiv.
- Private Meldungen von Sicherheitslücken aktiv.

Die Dateien im Repository ergänzen wöchentliche Dependabot-Versionsupdates,
Vorlagen für Fehlerberichte und Funktionswünsche, eine Pull-Request-Vorlage,
[Beitragsrichtlinien](../CONTRIBUTING.md) und [Sicherheitshinweise](../SECURITY.md).
Diese Dateien wirken auf GitHub nach dem Push.

## Noch auszuführen

1. `docs/images/social-preview.png` unter **Settings → General → Social preview
   → Edit → Upload an image…** hochladen. Das PNG ist 1280 × 640 Pixel groß und
   kleiner als 1 MB; das Einchecken ersetzt den Upload in den Einstellungen nicht.
2. Zuerst `main` hochladen und die vier Plattform-Tests abwarten.
3. Bei erfolgreichen Tests den lokalen Tag `v2.9.1` hochladen. Er muss auf den
   fertig geprüften Stand zeigen; der Workflow prüft die Übereinstimmung mit
   der App-Version und erstellt einen Release-Entwurf.
4. Build-/Starttests und Release-Entwurf kontrollieren, die verfügbare
   interaktive Prüfung ergänzen und die Release anschließend veröffentlichen.
