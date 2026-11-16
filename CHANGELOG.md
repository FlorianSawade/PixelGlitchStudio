# Changelog

Versionshistorie von PixelGlitch Studio, neueste Änderungen zuerst.

## Fehlerbehebung in 2.9.1 (Windows)

- **Batch-Präfix wird entschärft.** Der im Batch-Panel eingegebene Präfix ging
  ungeprüft in den Dateinamen. Unter Windows sind `< > : " / \ | ? *` dort
  verboten – eine Eingabe wie `bild: v2` brach den Batch mit einem
  Schreibfehler ab. `engine.safe_stem()` ersetzt solche Zeichen jetzt durch
  Unterstriche, kürzt auf 60 Zeichen und fällt bei leerer Eingabe oder einem
  Windows-Gerätenamen (`CON`, `LPT1`, …) auf `glitch` zurück. Die Batch-Galerie
  filtert nach demselben entschärften Präfix, sonst bliebe sie leer.
- **Oberflächen-Tests laufen unter Windows.** `test_gui.py` und
  `test_ui_features.py` schrieben ihre Testbilder nach fest verdrahteten
  `/tmp`-Pfaden. Sie nutzen jetzt `tempfile.gettempdir()`.
- **`PixelGlitchStudio.spec` entfernt.** Die Datei war ein von `build_app.py`
  erzeugtes Nebenprodukt und enthielt einen absoluten Icon-Pfad aus der
  Maschine, auf der sie entstanden ist. Sie wird bei jedem Build neu
  geschrieben und steht jetzt in `.gitignore`.
- **`.gitignore` ergänzt** (`.venv/`, `__pycache__/`, `build/`, `dist/`,
  `*.spec`, `.idea/`, `.vscode/`, `.DS_Store`).

## Neu in 2.9.0

Zwei kantenerhaltende Glättungsfilter in der Gruppe Farbe. Beide ebnen Flächen
ein, ohne Kanten zu verwischen – im Gegensatz zu einem gewöhnlichen
Weichzeichner. Zusammen mit der Verschiebung aus 2.8.0 ergeben sie den
plastischen, fast gummiartigen Charakter, den man aus der Glitch-Art kennt.

- **Bilateral-Glättung.** Gewichtet jeden Nachbarpixel nach Abstand *und* nach
  Farbunterschied.
  - **Radius** (1–6 px) bestimmt die Reichweite.
  - **Farbtoleranz** ist das Sigma des Farbterms: niedrig hält selbst schwache
    Kanten scharf, hoch nähert sich einem normalen Weichzeichner an.
  - **Durchgänge** (1–4): mehrfaches Anwenden mit kleinem Radius glättet
    ähnlich stark wie ein großer Radius, kostet aber deutlich weniger Zeit.

- **Kuwahara / Malerisch.** Ersetzt jeden Pixel durch den Mittelwert des
  homogensten der vier Quadranten seiner Nachbarschaft. Rundet Formen ab und
  erzeugt flächige Bereiche mit harten Übergängen – malerischer als Bilateral.
  Parameter: **Radius** (1–8 px) und **Durchgänge** (1–3).

Beide nutzen den Zufallsgenerator nicht und sind reproduzierbar; am Würfeln
nehmen nur Radius und Farbtoleranz teil, nicht die Durchgangszahl.

Umgesetzt in reinem NumPy, ohne neue Abhängigkeit. Der Range-Term der
Bilateral-Glättung ist als 256-Einträge-Tabelle vorberechnet, Kuwahara nutzt
ein Integralbild für die Fenstersummen. Laufzeit auf knapp 3 Megapixeln mit
Voreinstellungen: rund vier Sekunden für Bilateral, gut eine für Kuwahara.

## Neu in 2.8.0

- **Neuer Effekt „Verschiebung / Pixel Stretch"** (Gruppe Glitch, 18. Effekt).
  Jeder Pixel wird um einen Betrag versetzt, der aus dem Bild selbst stammt –
  im Gegensatz zu Slice-Verschiebung, Wellen-Verzerrung und Echo, die einen
  konstanten Versatz je Zeile anwenden.
  - **Quelle**: Helligkeit, Gradient, Farbton, Sättigung oder ein Farbkanal.
  - **Modus**: *Fortschreiben* kopiert den Pixel über die gesamte Strecke und
    erzeugt die langgezogenen, reliefartigen Flächen; *Verschieben* versetzt
    ihn nur und lässt das Bild gefaltet, aber lückenlos.
  - **Richtung**: horizontal, vertikal oder beides (zwei Durchgänge, X dann Y).
  - **Stärke** in Prozent der Bildkante – deshalb sieht der Export aus wie die
    heruntergerechnete Vorschau.
  - **Nullpunkt** legt fest, welcher Quellwert sich nicht bewegt. Bei 0 wandern
    dunkle Pixel in die eine, helle in die andere Richtung.
  - **Glättung** weichzeichnet die Displacement-Map vor dem Versatz. Bei 0
    springt jeder Pixel einzeln; erst hier entstehen große zusammenhängende
    Flächen. Dies ist der wichtigste Regler für den Charakter des Effekts.
  - **Rand**: Klemmen, Umlaufen oder Spiegeln. Voreinstellung ist Klemmen –
    anders als bei den älteren Effekten, die grundsätzlich umlaufen.

  Der Effekt nutzt den Zufallsgenerator nicht und ist bei gleichen Parametern
  reproduzierbar. Beim Batch nehmen nur Stärke, Nullpunkt und Glättung am
  Würfeln teil; Quelle, Modus, Richtung und Rand sind ausgenommen, weil ein
  Wurf dort den Charakter umwerfen statt ihn variieren würde.

  **Laufzeit:** Der Modus *Verschieben* ist vollständig vektorisiert und
  praktisch verzögerungsfrei. *Fortschreiben* arbeitet die Verschiebungsstufen
  einzeln ab; bei Standardstärke braucht ein 3-Megapixel-Bild rund drei
  Sekunden, bei 30 % in beide Richtungen knapp dreißig. Die Vorschau ist davon
  kaum betroffen, weil sie heruntergerechnet arbeitet – beim Export in voller
  Auflösung ist die Wartezeit spürbar.

## Fehlerbehebung in 2.7.2

- **Der Würfel im Effekt-Abschnitt reagiert jetzt sofort.** Bisher wurde sein
  Zustand nur beim Aufbau der Einstellungen berechnet: Markierte man danach
  Parameter, blieb er deaktiviert; entfernte man alle Markierungen, blieb er
  klickbar und meldete beim Drücken „kein Parameter markiert". Markierungen
  werden nun live gemeldet – Knopf, Tooltip und die Ebenen-Liste im
  Batch-Panel ziehen unmittelbar nach.

## Änderungen in 2.7.1

- **Galerie zeigt das aktuelle Projekt.** Neues Häkchen „Nur aktuelles
  Projekt" (an) blendet Dateien aus, deren Name nicht mit dem Präfix des
  Projekts beginnt. Das Batch-Präfix folgt dabei automatisch dem Projektnamen –
  ein selbst eingetragenes Präfix bleibt erhalten (leeren stellt die Automatik
  wieder her).
- **„Neu würfeln" sitzt jetzt an der Ebene.** Der Knopf ist aus der
  Werkzeugleiste verschwunden; stattdessen liegt ein Würfel rechts in der
  Kopfzeile des Abschnitts „Effekt · <Name>" und würfelt genau die
  🎲-markierten Parameter **dieser** Ebene neu. Ohne Markierungen ist er
  deaktiviert und erklärt das im Tooltip. Der frühere reine Seed-Wechsel
  (wirkt nur auf zufallsbasierte Effekte wie Rauschen oder Byte-Glitch) liegt
  jetzt unter Ansicht → „Neuer Zufalls-Seed" (`Strg/Cmd+R`).
- **Der Knopf „Batch"** blendet das Panel „Batch & Galerie" ein und aus und
  zeigt dessen Zustand an.

## Neu in 2.7

- **Batch und Galerie in einem Panel.** Das modale Batch-Fenster ist
  verschwunden; Einstellungen, Lauf und Ergebnisse liegen jetzt gemeinsam im
  andockbaren Panel „Batch & Galerie" (`Strg/Cmd+G`, oder der Werkzeugleisten-
  Knopf „Batch"). Links die Einstellungen samt Ebenen-Auswahl und
  „Generieren" — einklappbar über den schmalen Griff —, rechts die Kacheln des
  Ausgabeordners.
- **Der Lauf blockiert nichts mehr.** Während der Batch rechnet, lässt sich
  weiterarbeiten; der Fortschritt steht zusätzlich in der Statusleiste
  (`Batch läuft: 12 / 64`), und ein Abbrechen-Knopf stoppt sauber.
- **Projekt-Schnappschuss**: Beim Start eines Laufs wird das Projekt
  eingefroren. Änderungen während des Laufs verfälschen die restlichen
  Varianten also nicht.
- **Übernehmen aus der Galerie**: Kachel auswählen und „Variante übernehmen"
  (oder Kontextmenü). Stammt die Datei aus dem Lauf dieser Sitzung, sind die
  Werte exakt; hat sich der Ebenenstapel seither geändert, bietet die App an,
  Stapel und Masken des damaligen Laufs wiederherzustellen. Für fremde oder
  ältere Dateien wird der Seed aus dem Dateinamen gelesen — mit dem Hinweis,
  dass das nur bei unverändertem Projekt stimmt.
- Nur noch **eine** Galerie-Implementierung statt zweier fast gleicher.

## Neu in 2.6

- **Presets**: Neuer Tab neben Ebenen und Masken. Sechs mitgelieferte Vorlagen
  (schreibgeschützt, per Duplizieren bearbeitbar), eigene Presets aus dem
  aktuellen Stapel speichern, umbenennen über Duplizieren, löschen, sowie
  Import/Export als Austauschdatei `.pgpreset`. Ein Preset enthält den
  Ebenenstapel samt Parametern, 🎲-Markierungen und **eingebetteten
  Maskendefinitionen** – es funktioniert damit auch in fremden Projekten;
  Namenskonflikte bekommen ein Zahlensuffix. Quellbild und Ausgabepfade
  gehören nicht ins Preset. Beschädigte Dateien werden mit Grund gelistet
  statt zu stören, unbekannte Effekte beim Anwenden übersprungen, und eine
  neuere Formatversion wird mit klarer Meldung abgelehnt.
- **Galerie-Panel** (seit 2.7 Teil von „Batch & Galerie", `Strg/Cmd+G`): dauerhaftes
  andockbares Panel, das einen Ausgabeordner beobachtet und dessen Bilder als
  Kacheln zeigt – Dateiname links, klickbare Sternebewertung rechts. Filter
  nach Mindestbewertung, Doppelklick zeigt groß in der Vorschau, Kontextmenü
  bietet „Als Quellbild übernehmen". Neue Dateien erscheinen automatisch.
  Bewertungen liegen als kleine Begleitdatei im Ordner und wandern mit den
  Bildern mit. Nach einem Batch zeigt das Panel automatisch dessen Ordner.
- **Statusleiste ausgebaut**: links Projektname, Ebenen- und Maskenzahl sowie
  Meldungen, rechts Bildmaße, Zoom und der Renderzustand (`bereit` →
  `rendert …` → `gerendert in 82 ms · Seed 1`, im Schnell-Modus mit Hinweis
  auf die verkleinerte Vorschau). Renderfehler erscheinen einige Sekunden in
  Warnfarbe und weichen dann dem vorherigen Text.
- **Ungespeicherte Änderungen** sind im Fenstertitel an einem vorangestellten
  Punkt erkennbar.
- **Kennwerte in der Maskenliste**: dritte Zeile je Maske mit den wichtigsten
  Parametern (bzw. Punktzahl bei Polygonen).
- **Tastenkürzel**: `Strg/Cmd+S` speichern, `+O` Projekt öffnen, `+E`
  exportieren, `+B` Batch, `+R` neu würfeln, `+G` Galerie.

## Neu in 2.5

- **Ebenen-Auswahl fürs Würfeln**: Der Batch-Dialog listet unter „Gewürfelte
  Ebenen" alle aktiven Effekt-Ebenen mit der Zahl ihrer 🎲-Parameter; per
  Häkchen nimmst du Ebenen vom Würfeln aus (ihre Werte bleiben dann in allen
  Varianten fix). Die Wahl wird pro Ebene im Projekt gespeichert. Ebenen ohne
  🎲-Marker erscheinen ausgegraut.
- **Deutlich größerer Batch-Dialog und größere Galerie-Kacheln** (≈ 250 px,
  in höherer Schärfe geladen).

## Neu in 2.4

- **Schnell-Batch**: Checkbox im Batch-Dialog rendert alle Varianten in
  Vorschaugröße und legt sie im Unterordner `vorschau` ab – ideal zum
  Durchmustern vieler Seeds, ohne Voll-Renderzeiten.
- **Ergebnis-Galerie**: Nach dem Batch zeigt der Dialog die Varianten als
  Kachelraster. Ein Klick zeigt die Variante groß in der Hauptvorschau,
  Doppelklick (oder „Übernehmen") schreibt ihre gewürfelten Werte samt Seed
  ins Projekt – die 🎲-Markierungen bleiben dabei erhalten, und du arbeitest
  nahtlos auf dieser Basis weiter.
- **Variante aus Seed übernehmen…** (Datei-Menü): rekonstruiert auch später
  eine Batch-Variante aus ihrem Seed – vorausgesetzt, das Projekt ist seit dem
  Batch unverändert.

## Neu in 2.3

- **Projektordner**: Die App nutzt standardmäßig `Dokumente/PixelGlitchProjects`
  (wird automatisch angelegt). Der Welcome/Projekte-Screen zeigt den Ordner an,
  listet die darin liegenden Projekte und lässt den Ordner über „Ändern…"
  wechseln – die Liste lädt dann neu. Auch Export- und Batch-Dialoge starten
  standardmäßig dort.
- **Speichern ohne Rückfrage**: „Speichern" (Toolbar/Menü) schreibt ein bereits
  gespeichertes Projekt direkt auf seinen Pfad zurück; nur das erste Speichern
  fragt (voreingestellt: Projektordner + Projektname).
- **„Projekt speichern unter…"** neu im Datei-Menü für Kopien an anderem Ort.

## Änderungen in 2.2.2

- **Welcome/Projektbrowser**: „Ohne Projekt starten" heißt jetzt **„Neues
  Projekt"** und fragt zuerst nach einem Projektnamen (mit Datums-Vorschlag).
  Es startet ein leeres, noch ungespeichertes Projekt; der Name erscheint im
  Fenstertitel und wird beim ersten Speichern als Dateiname vorgeschlagen.
  „Bild öffnen" ist aus dem Dialog entfernt (weiterhin im Datei-Menü und in
  der Arbeitsfläche per Drag&Drop).

## Änderungen in 2.2.1

- **Werkzeugleiste neu geordnet**: Projekte · Speichern | Exportieren | Batch.
  „Projekte" öffnet den Projektbrowser (der Welcome Screen, jederzeit aus der
  App heraus); „Bild öffnen" ist in den Projektbrowser und das Datei-Menü
  gewandert.
- **Batch-Dialog**: Die JPG-Qualitätszeile erscheint nur noch, wenn JPG als
  Format gewählt ist.
- **Über-Dialog** (Hilfe) mit Urheberschafts-Hinweis und neuer
  Kurzbeschreibung (Autor anpassbar über `AUTHOR`-Konstante in
  `pixelglitch/branding.py`).

## Neu in 2.2

- **Alles in einer Datei (.pgsz)**: „Projekt speichern" legt jetzt einen
  Container an, der die Einstellungen, das Originalbild (byte-genau, in
  Originalqualität) und ein Vorschaubild enthält. Beim Öffnen ist das Bild
  sofort da – kein separates Laden mehr. Das alte Nur-Einstellungen-Format
  (.pgs.json) lässt sich weiterhin öffnen und im Speichern-Dialog gezielt
  wählen; Projektdateien können auch direkt auf die Arbeitsfläche gezogen
  werden.
- **Welcome Screen statt Splash**: Beim Start erscheint eine Übersicht der
  zuletzt bearbeiteten Projekte als Kacheln mit Bildvorschau, Name und Datum –
  ein Klick öffnet direkt. Dazu „Bild öffnen…", „Projekt öffnen…" und „Ohne
  Projekt starten". Wird die App mit einem Projektpfad als Argument gestartet
  (z.B. Doppelklick auf eine .pgsz-Datei mit Dateizuordnung), öffnet sich das
  Projekt direkt ohne Welcome Screen.
- **„Zuletzt verwendet"** im Datei-Menü (die letzten 12 Projekte).

---


## Fehlerbehebungen in 2.1.1

- **Batch erzeugt wieder echte Varianten.** Drei Ursachen behoben: 🎲-Marker
  aus älteren Projektdateien, deren Parameternamen nicht mehr existieren,
  wurden stillschweigend ignoriert (werden beim Laden jetzt bereinigt);
  „Aussetzer" konnte auf Werte nahe 1,0 gewürfelt werden und ließ das Bild
  dann praktisch unbehandelt (würfelt jetzt im Bereich 0–0,6); und ohne
  markierte 🎲-Parameter warnt der Batch-Dialog jetzt vor dem Start, statt
  kommentarlos identische Bilder zu erzeugen.
- **Splash-Screen** bleibt mindestens 1 Sekunde sichtbar.
- **App-Name statt „Python"** in macOS-Menüleiste bzw. Windows-Taskleiste
  (unter macOS über das optionale pyobjc-Paket, das requirements.txt dort
  automatisch mitinstalliert – nach `pip install -r requirements.txt` einmal
  neu starten). Vollständig sauber, inklusive Dock/Prozessname, wird es mit
  der Standalone-App aus `build_app.py`.

## Neu in 2.1

- **Zoom-Overlay**: −/+/Einpassen liegen jetzt als schwebende Leiste links
  unten im Bildbereich (statt in der Werkzeugleiste).
- **Polygon-Bearbeitung**: Punkte lassen sich per Anfassen verschieben, per
  Rechtsklick löschen; Klick auf eine Kante fügt einen Punkt dazwischen ein.
- **Batch merkt sich Einstellungen**: Anzahl, Seed, Präfix, Format, Qualität
  und Ausgabeordner bleiben über Aufrufe und Neustarts erhalten.
- **Dateinamen**: Der Seed wird als reines Zahlen-Suffix angehängt
  (`praefix_1000.png` statt `praefix_seed1000.png`).
- **JPG-Qualität** einstellbar im Batch-Fenster und beim Export.
- **Maskenzuweisung**: Der Abschnitt in den Ebenen-Einstellungen heißt jetzt
  so und aktualisiert seinen Titel sofort bei Änderungen (vorher blieb
  fälschlich „ohne Maske" stehen).
- **Projekt schließen** im Datei-Menü, mit Sicherheitsabfrage bei
  ungespeicherten Änderungen (auch beim Beenden der App).
- **Splash-Screen** mit prozedural gezeichnetem Logo beim Start; das Logo
  erscheint auch im Über-Dialog und als Fenster-Icon.

---


## Neu in 2.0

### Masken-Bibliothek
Masken sind jetzt benannte, wiederverwendbare Objekte im Tab **Masken**
(Rechteck, Ellipse, Polygon, linearer/radialer Verlauf, Bildmaske) — mit
Graustufen-Thumbnail und Anzeige, wie oft sie verwendet werden. Effekt-Ebenen
*referenzieren* Masken statt sie zu besitzen: Änderst du die Geometrie einer
Maske, ziehen alle Ebenen mit, die sie benutzen. Referenzierte Masken sind
gegen versehentliches Löschen geschützt.

### Masken-Ketten pro Ebene
Jede Ebene kann mehrere Masken zu einem Wirkungsbereich verknüpfen, ausgewertet
von oben nach unten: **∪ Vereinigen** (Maximum), **∩ Schneiden** (Minimum),
**− Abziehen** (geklemmte Differenz). *Invertieren* und *weiche Kante* gehören
zur Referenz, nicht zur Maske — „Effekt A innen, Effekt B außen" ist damit
einfach zweimal dieselbe Maske, einmal mit Invert-Häkchen. Optional glättet
eine finale weiche Kante das kombinierte Ergebnis. Ein Beispiel:
`(Oben ∪ Verlauf) − Loch`.

Die Pipeline bleibt sequenziell: Ebenen laufen von oben nach unten, jede sieht
das Ergebnis der vorherigen.

### Neues Erscheinungsbild
Durchgängiges Theme-System mit semantischen Farbtokens: folgt automatisch dem
System (hell/dunkel, Live-Umschaltung ohne Neustart), manuell übersteuerbar
unter *Ansicht → Erscheinungsbild*. Magenta-Akzent in zwei Abstufungen,
monochrome SVG-Icons, Toolbar, Ebenen-Liste mit Sichtbarkeits-Auge und
Maskennamen, aufklappbare Einstellungs-Abschnitte, Statusleiste mit
Bildgröße/Zoom/Renderzeit/Seed. Die Arbeitsfläche hinter dem Bild bleibt in
beiden Themes dunkelneutral, damit der Bildeindruck nicht verfälscht wird.

Projekte der Version 1 (Maske inline an der Ebene) werden beim Öffnen
automatisch migriert: Aus jeder Ebenen-Maske wird ein Bibliothekseintrag mit
einer Referenz.
