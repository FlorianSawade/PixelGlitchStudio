# Installation der Desktop-App

[Zurück zur README](../README.md)

Die App-Pakete enthalten Python und die benötigten Bibliotheken. Eine eigene
Python-Installation ist dafür nicht nötig. Lade Pakete ausschließlich aus den
[Releases dieses Repositorys](https://github.com/FlorianSawade/PixelGlitchStudio/releases)
herunter.

## Das passende Paket wählen

| System | Datei für Version 2.9.1 | Referenzsystem für den Build |
| --- | --- | --- |
| Mac mit Apple Silicon (M1 oder neuer) | `PixelGlitchStudio-v2.9.1-macos-arm64.zip` | macOS 15, arm64 |
| Mac mit Intel-Prozessor | `PixelGlitchStudio-v2.9.1-macos-x86_64.zip` | macOS 15, Intel |
| Windows, 64 Bit | `PixelGlitchStudio-v2.9.1-windows-x86_64.zip` | Windows Server 2022, x86_64 |
| Linux, 64 Bit | `PixelGlitchStudio-v2.9.1-linux-x86_64.tar.gz` | Ubuntu 24.04, x86_64 |

Die Referenzsysteme beschreiben die Build-Umgebung. Sie sind keine Bestätigung,
dass jede andere Betriebssystemversion ebenfalls funktioniert. Insbesondere
das Linux-Paket setzt eine ausreichend neue glibc voraus; verwende Ubuntu
24.04 oder eine kompatible Distribution mit glibc 2.39 oder neuer.

## macOS

1. Das ZIP vollständig entpacken.
2. `PixelGlitchStudio.app` in den Ordner „Programme“ ziehen und öffnen.
3. Die erste Release ist nicht mit einem Apple-Entwicklerzertifikat signiert
   oder notarisiert. Wenn macOS den Start blockiert, findest du die Freigabe
   nach dem Startversuch unter **Systemeinstellungen → Datenschutz & Sicherheit**.
   Erlaube den Start nur, wenn du dem heruntergeladenen Paket vertraust.

Die genaue Meldung hängt von der macOS-Version und den Systemeinstellungen ab.
[Apple-Hinweise zu Apps außerhalb des App Store](https://support.apple.com/de-de/102445).

## Windows

1. Das ZIP über „Alle extrahieren“ vollständig entpacken.
2. Im Unterordner `PixelGlitchStudio` die Datei `PixelGlitchStudio.exe` starten.
3. Den kompletten App-Ordner zusammenlassen. Die EXE allein enthält nicht alle
   benötigten Bibliotheken; auch aus der ZIP-Vorschau heraus lässt sie sich
   nicht zuverlässig starten.

Die App besitzt kein Windows-Code-Signing-Zertifikat. Windows kann deshalb
beim ersten Start eine SmartScreen-Warnung anzeigen. Prüfe vor einer Freigabe
Quelle und Prüfsumme des Downloads.

## Linux

Das Archiv entpacken und die Anwendung im Terminal starten:

```bash
tar -xzf PixelGlitchStudio-v2.9.1-linux-x86_64.tar.gz
cd PixelGlitchStudio-v2.9.1-linux-x86_64
./PixelGlitchStudio/PixelGlitchStudio
```

Auf einem minimalen Ubuntu-System können folgende Qt-Systembibliotheken fehlen:

```bash
sudo apt install libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3 libxcb-cursor0
```

Der normale Betrieb benötigt eine grafische Desktop-Sitzung.

## Download prüfen

Zu jedem App-Archiv gehört eine Datei mit derselben Bezeichnung und der
Endung `.sha256`. Vergleiche deren Inhalt mit der berechneten Prüfsumme.

macOS, Beispiel:

```bash
shasum -a 256 PixelGlitchStudio-v2.9.1-macos-arm64.zip
```

Windows (PowerShell), Beispiel:

```powershell
Get-FileHash .\PixelGlitchStudio-v2.9.1-windows-x86_64.zip -Algorithm SHA256
```

Linux, Archiv und Prüfsummendatei im selben Ordner:

```bash
sha256sum -c PixelGlitchStudio-v2.9.1-linux-x86_64.tar.gz.sha256
```

Die SHA-256-Prüfsumme erkennt beschädigte oder gegenüber der Prüfsummendatei
veränderte Downloads; sie ersetzt keine digitale Signatur.

## Deinstallation und eigene Projekte

Zum Entfernen der App den entpackten App-Ordner beziehungsweise die `.app`
löschen. Eigene Projekte und Einstellungen liegen außerhalb der Anwendung und
bleiben erhalten. Der Standard-Projektordner ist `Dokumente/PixelGlitchProjects`;
einen anderen Ordner kannst du im Projektbrowser auswählen.
