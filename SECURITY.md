# Sicherheitsprobleme melden

Bitte melde vermutete Sicherheitslücken über
[GitHubs privaten Meldeweg](https://github.com/FlorianSawade/PixelGlitchStudio/security/advisories/new)
für dieses Repository. Öffne dafür kein öffentliches Issue.

Hilfreich sind App-Version oder Commit, Betriebssystem, betroffene Funktion
und möglichst kleine Schritte zum Nachvollziehen. Teile nur die Dateien, die
für die Analyse nötig sind; entferne Zugangsdaten und private Bildinhalte.

## Unterstützter Stand

Sicherheitskorrekturen erfolgen im aktuellen Entwicklungsstand auf `main` und
in nachfolgenden Releases. Für ältere Versionen gibt es derzeit keine
separaten Wartungszweige oder zugesagten Rückportierungen.

## Umgang mit fremden Dateien

PixelGlitch Studio verarbeitet Bilder sowie Projekt-, Preset- und Maskendateien
lokal. Auch lokal geöffnete Dateien können unerwartete oder sehr große Inhalte
enthalten. Verwende die aktuelle App-Version und melde reproduzierbare Probleme
über den privaten Meldeweg, wenn sie sicherheitsrelevant sein könnten.

Repository-Schutz und Abhängigkeiten werden über Secret Scanning, Push
Protection und Dependabot überwacht. Das ersetzt keine Sicherheitsprüfung der
Anwendung und ist keine Garantie, dass alle Schwachstellen erkannt werden.
