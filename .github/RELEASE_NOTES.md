# PixelGlitch Studio 2.9.1

Erste öffentliche Release: eine lokale Desktop-App für Pixel-Sorting und
Glitch-Art mit Effekt-Ebenen, wiederverwendbaren Masken und Batch-Varianten.

## Funktionen

- Pixel Sort, Signalstörungen, Databending, Pixel Stretch und Farbfilter stapeln.
- Rechtecke, Ellipsen, Polygone, Verläufe und Bildmasken miteinander verknüpfen.
- Sechs mitgelieferte Presets verwenden und eigene Presets austauschen.
- Parameter im Batch variieren, Ergebnisse bewerten und Varianten übernehmen.
- Projekte samt Originalbild als `.pgsz` speichern; Bilder als PNG/JPEG exportieren.

## Downloads

| Plattform | App-Paket |
| --- | --- |
| macOS · Apple Silicon | `PixelGlitchStudio-v2.9.1-macos-arm64.zip` |
| macOS · Intel | `PixelGlitchStudio-v2.9.1-macos-x86_64.zip` |
| Windows · x86_64 | `PixelGlitchStudio-v2.9.1-windows-x86_64.zip` |
| Linux · x86_64 | `PixelGlitchStudio-v2.9.1-linux-x86_64.tar.gz` |

Die App-Pakete enthalten Python und die benötigten Bibliotheken. Das Archiv
vollständig entpacken; unter Windows anschließend im Unterordner
`PixelGlitchStudio` die EXE öffnen. Unter macOS die `.app` öffnen, unter Linux
`./PixelGlitchStudio/PixelGlitchStudio` ausführen.

Build-Referenzsysteme: macOS 15 (Apple Silicon/Intel), Windows Server 2022 und
Ubuntu 24.04. Linux benötigt glibc 2.39 oder neuer.

[Ausführliche Installation und Prüfsummenprüfung](https://github.com/FlorianSawade/PixelGlitchStudio/blob/v2.9.1/docs/INSTALLATION.md)

## Hinweise zu dieser ersten Release

- Oberfläche: Deutsch.
- macOS-Pakete sind nicht mit einem Entwicklerzertifikat signiert oder
  notarisiert; die Windows-App hat ebenfalls kein Code-Signing-Zertifikat.
  Das Betriebssystem kann beim ersten Start eine Warnung anzeigen.
- Große Bilder und aufwendige Effektstapel brauchen beim Export mehr Zeit.
  Die schnelle Vorschau kann gegenüber dem Export in voller Auflösung abweichen.
- Ein Seed reproduziert ein Ergebnis nur zusammen mit demselben Ausgangsbild,
  demselben Effektstapel, denselben Parametern und Masken.
- Fehlerberichte sind willkommen: Bitte Betriebssystem, App-Version und
  Schritte zum Nachvollziehen angeben.

## Quellcode und Lizenzen

Copyright (c) 2026 Florian Sawade. PixelGlitch Studio steht unter GPL-3.0-only.
Die App-Archive enthalten die Projektlizenz und Drittanbieter-Lizenztexte.
Der passende Projektquellcode und die Upstream-Quellarchive werden separat
bereitgestellt. Diese zusätzlichen Quellarchive sind zum Benutzen der App
nicht erforderlich. `.sha256`-Dateien und `SHA256SUMS` ermöglichen eine Prüfung
der Downloads.

[Changelog](https://github.com/FlorianSawade/PixelGlitchStudio/blob/v2.9.1/CHANGELOG.md)
