# PixelGlitch Studio — Faktenblatt für die Produktseite

**Stand: Version 2.9.1.** Dieses Dokument beschreibt ausschließlich Funktionen,
die im Code vorhanden und getestet sind. Es ist die verbindliche Grundlage für
Texte, Screenshots und Feature-Listen der Webseite.

> **Wichtigster Hinweis für die Umsetzung:** Ein früherer Entwurf der Seite
> enthielt erfundene Funktionen (Projektbaum, mehrere Quellbilder als Reiter,
> benannte Batch-Laufkonfigurationen, Mischmodi für Ebenen, ein „Rendern"-Knopf).
> Nichts davon existiert. Der Abschnitt **„Was es ausdrücklich nicht gibt"**
> weiter unten ist deshalb genauso verbindlich wie die Feature-Liste. Bitte
> keine Formulierung verwenden, die dort widerlegt wird.

---

## 1 Was das Programm ist

Eine plattformübergreifende Desktop-Anwendung (macOS, Windows, Linux) für
**Pixel-Sorting und Glitch-Art**. Bilder werden über einen Stapel von
Effekt-Ebenen verfremdet, deren Wirkung sich über wiederverwendbare Masken auf
Bildbereiche eingrenzen lässt. Ergebnisse können einzeln exportiert oder in
Serie mit zufällig variierten Parametern erzeugt werden.

Einzeiler, inhaltlich gedeckt:
„Die Ästhetik des Fehlers, präzise gesteuert."

Etwas länger, ebenfalls gedeckt:
„PixelGlitch Studio zerlegt Bilder in ihre Datenströme und setzt sie
kontrolliert neu zusammen — Pixel-Sorting, Databending und Signalstörungen,
geschichtet über Ebenen, geformt durch Masken, in Serie gewürfelt und dank
Seeds jederzeit exakt reproduzierbar."

**Technik:** Python mit PySide6 (Qt) für die Oberfläche, NumPy und Pillow für
die Bildverarbeitung. Keine GPU-Beschleunigung, keine Cloud-Anbindung, keine
Telemetrie. Die Bildverarbeitungs-Engine ist bewusst oberflächenfrei und lässt
sich aus eigenen Python-Skripten ansteuern.

---

## 2 Aufbau des Fensters (das zeigen die Screenshots)

Ein einzelnes Hauptfenster, kein rahmenloses Design:

- **Menüleiste**: Datei, Ansicht, Hilfe.
- **Werkzeugleiste** (feste Reihenfolge): links `Projekte · Speichern |
  Exportieren | Batch` (der Batch-Knopf blendet das Panel ein und aus), rechts
  die Umschalter `Maske zeigen` und `Schnell`.
- **Arbeitsfläche** links: das Bild mit Live-Vorschau. Unten links schwebt eine
  kleine Leiste mit `−`, `+` und `Einpassen`. Zoomen per Mausrad, Bild per
  Drag-and-Drop ablegbar.
- **Seitenleiste** rechts mit drei Reitern: **Ebenen**, **Masken**, **Presets**.
- **Batch & Galerie** als ausklappbares Panel am unteren Rand (standardmäßig
  zu): links die Einstellungen der Massengenerierung, rechts die Ergebnisse.
- **Statusleiste** unten über die volle Breite.

Farbschema folgt dem Betriebssystem (hell/dunkel, umschaltbar unter Ansicht →
Erscheinungsbild), Akzentfarbe Magenta. Die Arbeitsfläche hinter dem Bild
bleibt in beiden Schemata dunkelneutral, damit der Bildeindruck nicht
verfälscht wird.

---

## 3 Funktionen im Einzelnen

### 3.1 Effekt-Ebenen

20 Effekte, stapelbar in beliebiger Zahl und Reihenfolge, Verarbeitung
sequenziell von oben nach unten. Jede Ebene ist einzeln ein- und ausblendbar,
duplizierbar und verschiebbar. Die Parameter erscheinen als Regler, Auswahl-
und Ankreuzfelder; die Vorschau rechnet automatisch neu. In der Kopfzeile der
Effekt-Einstellungen würfelt ein Knopf die 🎲-markierten Parameter genau
dieser Ebene neu.

**Sortierung:** Pixel Sort (Richtung, Sortierschlüssel Helligkeit/Farbton/
Sättigung/Kanäle, Intervall-Funktionen Schwelle/Zufall/Wellen/Kanten/keine,
Reihenfolge, Zufalls-Aussetzer).

**Glitch:** RGB-Verschiebung, Kanaltausch, Slice-Verschiebung,
Wellen-Verzerrung, Chromatische Aberration, Scanlines/CRT, Byte-Glitch
(Databend), JPEG-Korruption, Block-Shuffle, Echo/Geisterbild.

**Farbe:** Pixelate/Mosaik, Posterize, Rauschen, Farbton drehen,
Helligkeit/Kontrast/Sättigung, Invertieren.

### 3.2 Masken

Masken sind **benannte, wiederverwendbare Objekte** in einer Bibliothek, keine
Eigenschaft einzelner Ebenen. Sechs Typen: Rechteck, Ellipse, Polygon,
linearer Verlauf, radialer Verlauf, Bildmaske.

- Rechteck und Ellipse zieht man direkt im Bild auf; Polygonpunkte werden per
  Klick gesetzt, per Ziehen verschoben, per Rechtsklick gelöscht, und ein Klick
  auf eine Kante fügt einen Punkt dazwischen ein.
- Jede Ebene **referenziert** Masken. Mehrere Referenzen lassen sich zu einer
  Kette verknüpfen: **Vereinigen, Schneiden, Abziehen**, ausgewertet von oben
  nach unten (Beispiel: `(Oben ∪ Verlauf) − Loch`).
- **Invertieren** und **weiche Kante** gehören zur Referenz, nicht zur Maske.
  Dadurch genügt für „Effekt A innen, Effekt B außen" dieselbe Maske zweimal,
  einmal mit gesetztem Invertieren.
- Die Bibliothek zeigt je Maske ein Graustufen-Vorschaubild, den Typ, wie oft
  sie verwendet wird und ihre wichtigsten Kennwerte. Referenzierte Masken sind
  gegen versehentliches Löschen geschützt, mit Nennung der betroffenen Ebenen.
- Ein Umschalter blendet die aktive Maske als Overlay über das Bild.

Wichtig für Texte: Die Verknüpfungsoperatoren gehören **zur Referenz in der
Ebene**, nicht zur Maske. Dieselbe Maske kann in einer Ebene geschnitten und in
einer anderen abgezogen werden.

### 3.3 Presets

Ein Preset ist ein gespeicherter Ebenenstapel samt Parametern,
Würfel-Markierungen und **eingebetteten Maskendefinitionen** — dadurch
funktioniert es auch in einem fremden Projekt. Quellbild und Ausgabepfade
gehören nicht hinein.

- **Sechs mitgelieferte Vorlagen**: Klassischer Sort, Vertikaler Regen,
  Signalstörung, Databend, Zentrum zerlegen, Horizont kippen. Sie sind
  schreibgeschützt; Duplizieren erzeugt eine bearbeitbare Kopie.
- Eigene Presets aus dem aktuellen Stapel speichern, duplizieren, löschen.
- **Import und Export** als Austauschdatei mit der Endung `.pgpreset` — damit
  lassen sich Rezepte weitergeben.
- Beim Anwenden werden eingebettete Masken angelegt; Namenskonflikte bekommen
  ein Zahlensuffix. Unbekannte Effekte werden übersprungen und gemeldet,
  beschädigte Dateien mit Grund in der Liste angezeigt statt zu stören, und
  eine neuere Formatversion wird mit klarer Meldung abgelehnt.

### 3.4 Massengenerierung (Batch)

Der Batch lebt seit 2.7 **im Panel „Batch & Galerie"**, nicht mehr in einem
eigenen Fenster — der Lauf blockiert die Anwendung also nicht. Neben jedem
Parameter sitzt ein Würfel-Knopf. Markierte Parameter werden je Variante
zufällig variiert.

- Anzahl, Start-Seed, Dateinamen-Präfix, Format (PNG/JPG), JPG-Qualität und
  Ausgabeordner; alle Einstellungen bleiben über Sitzungen erhalten. Die
  JPG-Qualität erscheint nur, wenn JPG gewählt ist.
- **Schnell-Modus**: rendert die Varianten in Vorschaugröße und legt sie in
  einen Unterordner `vorschau` — zum schnellen Durchmustern vieler Seeds.
- **Ebenen-Auswahl**: eine Liste zeigt alle aktiven Ebenen mit der Anzahl ihrer
  markierten Parameter; per Häkchen nimmt man einzelne Ebenen vom Würfeln aus.
- **Ergebnisse** erscheinen direkt in der Galerie daneben, mit Fortschritt in
  der Statusleiste und einem Abbrechen-Knopf. Das Projekt wird beim Start
  eingefroren, damit Änderungen während des Laufs die restlichen Varianten
  nicht verfälschen.
- **Übernehmen**: Kachel wählen und „Variante übernehmen" schreibt deren
  gewürfelte Werte samt Seed ins Projekt — man arbeitet nahtlos auf dem
  Favoriten weiter, die Würfel-Markierungen bleiben erhalten. Hat sich der
  Ebenenstapel seit dem Lauf geändert, bietet die App an, Stapel und Masken
  des damaligen Laufs wiederherzustellen.
- Der Seed steht als Zahlen-Suffix im Dateinamen; jedes Ergebnis ist darüber
  exakt reproduzierbar. „Variante aus Seed übernehmen…" im Datei-Menü holt eine
  Variante auch später zurück, solange das Projekt unverändert ist.

### 3.5 Galerie (rechte Hälfte desselben Panels)

Beobachtet **einen Ausgabeordner**:

- Kacheln mit Vorschau, Dateiname links, klickbare Sternebewertung (0–5) rechts.
- Filter nach Mindestbewertung sowie „Nur aktuelles Projekt", das anhand des
  Dateinamen-Präfixes auf die Ergebnisse des offenen Projekts eingrenzt.
- Doppelklick zeigt das Bild groß in der Vorschau; das Kontextmenü bietet
  „Variante ins Projekt übernehmen" und „Als Quellbild übernehmen".
- Neue Dateien erscheinen automatisch; nach einem Batch zeigt das Panel dessen
  Ordner.
- Bewertungen liegen als kleine Begleitdatei im Ordner selbst und wandern
  deshalb mit den Bildern mit.

### 3.6 Projekte

Ein Projekt wird als **einzelne Datei mit der Endung `.pgsz`** gespeichert. Sie
enthält die Projektbeschreibung, das **Quellbild byte-genau in Originalqualität**
und ein Vorschaubild. Beim Öffnen ist das Bild also sofort da.

- **Projektordner**: standardmäßig `Dokumente/PixelGlitchProjects`, im
  Startbildschirm sichtbar und änderbar.
- **Startbildschirm / Projektbrowser**: zeigt die Projekte des Ordners als
  Kacheln mit Bildvorschau, Name und Datum; ein Klick öffnet. Dazu „Neues
  Projekt" (fragt nach einem Namen) und „Projekt öffnen…". Jederzeit über den
  Werkzeugleisten-Knopf „Projekte" erreichbar.
- „Speichern" schreibt ein bereits gespeichertes Projekt ohne Rückfrage zurück;
  „Projekt speichern unter…" liegt im Datei-Menü. Sicherheitsabfrage bei
  ungespeicherten Änderungen; ein vorangestellter Punkt im Fenstertitel zeigt
  sie an.
- Zusätzlich existiert ein reines Einstellungsformat `.pgs.json` ohne Bild.

### 3.7 Statusleiste

Links Projektname, Ebenen- und Maskenzahl sowie Meldungen; rechts Bildmaße,
Zoomstufe und der Renderzustand: `bereit` → `rendert …` → `gerendert in 82 ms ·
Seed 1`. Im Schnell-Modus weist sie auf die verkleinerte Vorschau hin.
Renderfehler erscheinen einige Sekunden in Warnfarbe.

### 3.8 Export und Tastenkürzel

Export als PNG oder JPG (mit Qualitätsabfrage), immer in voller Auflösung
unabhängig von der Vorschau-Einstellung.

`Strg/Cmd+S` speichern · `+O` Projekt öffnen · `+E` exportieren · `+B` Panel
„Batch & Galerie" ein/aus · `+R` neuer Zufalls-Seed · `+G` Panel ein/aus.

---

## 4 Was es ausdrücklich **nicht** gibt

Diese Punkte bitte nirgends behaupten, andeuten oder bebildern:

- **Kein Projektbaum** und keine Ordnerstruktur. Ein Projekt ist eine einzelne
  Containerdatei.
- **Nur ein Quellbild pro Projekt.** Keine Reiter für mehrere Bilder, keine
  Reiter für mehrere gleichzeitig geöffnete Projekte.
- **Keine benannten oder gespeicherten Batch-Laufkonfigurationen**, keine
  Tabelle mit Laufhistorie, kein Wiederholen früherer Läufe per Klick. Der
  Batch ist ein Panel, das sich die letzten Einstellungen merkt.
- **Kein eigenes Batch-Fenster mehr.** Wer ein modales Dialogfenster zeigt,
  bebildert einen veralteten Stand.
- **Kein „Rendern"-Knopf.** Die Vorschau rechnet automatisch — es gibt nichts
  manuell anzustoßen.
- **Keine Mischmodi** (Multiply, Overlay …) für Ebenen. Ebenen wirken
  nacheinander, die Eingrenzung erfolgt über Masken.
- **Keine Deckkraft pro Ebene.**
- **Kein Rückgängig/Wiederholen** (Undo/Redo).
- **Keine Animation, kein Video, keine GIF-Ausgabe.** Standbilder.
- **Keine Ebenengruppen, keine Verschachtelung.**
- **Keine Cloud, kein Konto, keine Zusammenarbeit, keine Telemetrie.**
- **Keine GPU-Beschleunigung.**
- **Keine Stapelverarbeitung mehrerer Eingabebilder.** Der Batch variiert
  Parameter auf *einem* Bild.
- **Keine Bildbearbeitungs-Grundfunktionen** wie Zuschneiden, Skalieren, Drehen,
  Retusche oder Textwerkzeuge.
- **Keine Vorher/Nachher-Schiebeansicht.**
- **Keine Plugin-Schnittstelle für Endnutzer.** Eigene Effekte lassen sich im
  Quelltext ergänzen; das ist eine Entwickler-, keine Anwenderfunktion.
- **Kein Seed in Hexadezimal.** Seeds sind Dezimalzahlen.
- Die Endung `.pgpreset` gehört zum Preset-Austausch, `.pgsz` zum Projekt.
  Nicht vermischen.
- **Kein globaler „Neu würfeln"-Knopf in der Werkzeugleiste.** Das Würfeln
  gehört zur jeweiligen Effekt-Ebene.

---

## 5 Sprachregelung und Schreibweisen

Verbindliche Bezeichnungen (so heißt es in der Oberfläche):

| richtig | nicht |
|---|---|
| Effekt-Ebene, Ebenenstapel | Filter, Layer-Stack |
| Maskenbibliothek, Maskenzuweisung | Maskenordner, Auswahl |
| Vereinigen / Schneiden / Abziehen | Union / Intersect / Subtract im Fließtext |
| weiche Kante | Feather |
| Massengenerierung, Batch | Rendering-Queue, Job |
| Panel „Batch & Galerie" | Batch-Fenster, Batch-Dialog |
| Variante, Seed | Frame, Iteration |
| Preset | Filter-Vorlage, Style |
| Projektdatei (.pgsz) | Projektordner |
| Startbildschirm, Projektbrowser | Dashboard |
| Arbeitsfläche | Leinwand, Canvas |

Weitere Konventionen: Produktname immer „PixelGlitch Studio". Deutsche
Anführungszeichen („…"). Der Würfel-Knopf heißt im Text „Würfel-Markierung"
oder „🎲-Markierung", nicht „Randomizer".

---

## 6 Belastbare Aussagen für Marketingtexte

Diese Formulierungen sind durch den Code gedeckt:

- „Masken einmal anlegen, in beliebig vielen Ebenen verwenden."
- „Jedes Ergebnis ist über seinen Seed exakt reproduzierbar."
- „Ein Projekt ist eine Datei — Einstellungen und Originalbild zusammen."
- „Hundert Varianten in Vorschaugröße durchmustern, den Favoriten mit einem
  Doppelklick weiterbearbeiten."
- „Läuft lokal. Keine Cloud, kein Konto, keine Telemetrie."
- „Folgt dem Erscheinungsbild des Systems, hell wie dunkel."
- „20 Effekte, sechs Maskentypen, sechs mitgelieferte Presets."

Zahlen, die stimmen: 20 Effekte · 6 Maskentypen · 3 Verknüpfungsoperationen ·
6 mitgelieferte Presets · 2 Dateiformate (`.pgsz` Projekt, `.pgpreset` Preset) ·
Version 2.9.1.

**Nicht** behaupten: Geschwindigkeitsvergleiche mit anderen Programmen,
Nutzerzahlen, Auszeichnungen, Systemanforderungen jenseits von „Python 3.9 oder
neuer" bzw. der gebauten Standalone-App.

---

## 7 Screenshots

Vorhanden und verwendbar (Dateinamen wie geliefert):

- `271_batch_galerie.png` — Hauptfenster, dunkel, mit geöffnetem Panel
  „Batch & Galerie": links die Einstellungen, rechts bewertete Ergebnisse.
  **Bester Aufmacher, zeigt den aktuellen Stand.**
- `271_batch_galerie_hell.png` — dieselbe Ansicht im hellen Schema.
- `271_eingeklappt.png` — Panel mit eingeklappter Einstellungsspalte.
- `26_galerie.png` — älterer Stand (Galerie ohne Batch-Spalte); nur verwenden,
  wenn ausschließlich die Galerie gezeigt werden soll.
- `26_presets.png` — Hauptfenster, dunkel, Preset-Reiter geöffnet.
- `26_hell.png` — dieselbe Ansicht im hellen Schema, für einen
  Hell/Dunkel-Vergleich.

- `welcome_ordner.png` — Startbildschirm mit Projektkacheln.
- `ui_polygon.png` — Maskenbearbeitung mit Polygonpunkten im Bild.
- `demo_chain.png`, `demo_shared_invert.png` — reine Ergebnisbilder, geeignet
  als Beispielgalerie.

Die Oberfläche ist **deutschsprachig**. Screenshots also nicht mit englischen
Beschriftungen kombinieren; falls die Seite englisch wird, das im Text
kenntlich machen.

---

## 8 Wenn etwas fehlt

Sollte für die Seite eine Aussage nötig sein, die dieses Dokument nicht
abdeckt: bitte nicht ergänzen, sondern nachfragen. Der Code ist die einzige
gültige Quelle, und mehrere Funktionen aus dem ersten Entwurf waren frei
erfunden.
