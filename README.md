# Tontechnik Studio

Bedienoberflaeche fuer Aufnahme und Uebertragung bei Gottesdiensten und
aehnlichen Veranstaltungen. Laeuft direkt aus dem Git-Checkout, `git pull`
genuegt zum Aktualisieren.

## Einrichtung

    ./installiere.sh        # Symbol und Menueeintrag anlegen
    ./start.sh              # oder ueber das Anwendungsmenue starten

Danach die eigenen Skripte nach `skripte/` legen (siehe
`skripte/PLATZHALTER.md`) und `secrets.env` entweder dorthin oder nach
`~/.config/tontechnik/secrets.env`.

Fuer die Aufnahmesteuerung in REAPER einmalig unter Einstellungen ->
Control/OSC/web ein "Web browser interface" auf Port 8080 anlegen. Ohne das
bleibt der Aufnahmeknopf grau und die Karte sagt, was fehlt.

## Aufbau

    installiere.sh               Menueeintrag, Symbol, Fensterklasse
    start.sh                     Starter (python3 -m tontechnik)
    ressourcen/                  Symbol als PNG und SVG
    skripte/                     eigene stream_telefon.sh, stream_radio.sh
      vorlagen/                  Beispiele, mithoeren_telefon.sh, secrets.env.beispiel
    werkzeuge/probelauf.py       baut die Oberflaeche ohne Bildschirm auf
    tontechnik/
      konfiguration.py           alle Pfade und Konstanten an einer Stelle
      protokoll.py               Protokollierung
      einzelinstanz.py           zweiter Start holt das Fenster nach vorn
      kern/
        prozesse.py              startet und stoppt die Skripte
        reaper.py                REAPER im Hintergrund starten, Zustand pruefen
        aufnahme.py              Transportsteuerung ueber das Webinterface
        pegel.py                 Pegelmessung ueber ffmpeg
        ausgabe.py               letzte Zeile einer Protokolldatei
        projekte.py              Projektordner und Namensschema
        audio.py                 PipeWire-Quellen pruefen
      gui/
        app.py                   Hauptfenster, Reiter, Zustandsanzeige
        stil.py                  Farben, Schriften, ttk-Stile
        widgets.py               Lampe, Karte, Trennlinie
        karte_aufnahme.py        Aufnahme starten und beenden
        pegelanzeige.py          Balken mit Spitzenmarke
        ansicht_start.py         Projekt anlegen
        ansicht_uebertragung.py  Telefon und Radio schalten
        ansicht_protokoll.py     Protokolle mitlesen

Keine Datei ueberschreitet rund 200 Zeilen. Die Oberflaeche kennt keine
Fachlogik, der Kern kein Tkinter.

## Pruefen ohne Bildschirm

    python3 werkzeuge/probelauf.py

Baut alle Ansichten gegen eine Tkinter-Attrappe auf und durchlaeuft jeden
Bedienpfad. Faengt Tippfehler und falsche Aufrufe ab, bevor sie vor dem
Gottesdienst auffallen. Meldungen ueber fehlende Skripte oder fehlendes
REAPER sind dabei normal.

## Uebertragungen und Pegel

Die App startet ausschliesslich die Skripte aus `skripte/` und liest deren
Ausgabe mit. Sie prueft weder Quellen noch Zugangsdaten - was im Skript
passiert, ist dessen Sache. Unter jeder Karte steht die letzte Zeile, die das
Skript geschrieben hat.

Je Uebertragung gibt es zwei Pegelanzeigen:

| Uebertragung | gesendet | empfangen |
|---|---|---|
| Telefon | `TelefonBruecke.monitor` | `Mithoeren.monitor`, sobald die Mithoerleitung laeuft |
| Radio | `reaper_sip.monitor` | der Icecast-Stream, wie ihn ein Zuhoerer bekommt |

Gemessen wird mit je einem eigenen ffmpeg, das nur mitliest. Die Skala reicht
von -60 bis 0 dB, der dunkle Strich ist die Spitze der letzten Sekunden. Bricht
eine Quelle weg, versucht die Messung alle drei Sekunden neu und zeigt so
lange "kein Signal".

## Mithoeren der Telefonuebertragung

Die sendende Leitung laesst sich nicht selbst abhoeren - eine Konferenz spielt
einem Teilnehmer den eigenen Ton nicht zurueck. Mit einer zweiten Rufnummer
geht es aber: `mithoeren_telefon.sh` waehlt die Teilnehmer-Rufnummer an,
genau wie ein Zuhoerer, und legt den Ton in den Sink `Mithoeren`.

Dafuer in der Fritz!Box ein zweites IP-Telefon anlegen und die Zugangsdaten als
`SIP_MITHOEREN_USER`, `SIP_MITHOEREN_PASS` und `TEILNEHMER_RUFNUMMER`
eintragen. Mit `MITHOEREN_AUSGANG` geht der Ton zusaetzlich auf einen
Kopfhoerer. Als Mikrofon dieser Leitung dient ein stummer Sink, damit nichts in
die Konferenz zurueckgeht.

Drei Punkte dazu:

* Es sind dann zwei gleichzeitige Gespraeche. Die Fritz!Box schafft das, es
  belegt aber zwei Leitungen und faellt je nach Tarif zweimal an.
* Auf dem Kopfhoerer hoerst du dich selbst um die Laufzeit der Konferenz
  verzoegert. Zum Kontrollieren taugt das, zum Mitarbeiten nicht.
* Den Mithoerton niemals auf die TF1 legen.

## Bedienung

Das Fenster oeffnet im Vollbild. F11 schaltet um, Escape verlaesst das
Vollbild, Strg+Q beendet. Gescrollt wird nirgends: jede Ansicht haelt ihre
Schaltflaeche am unteren Rand fest, der Inhalt ist auf 900 mal 820 Punkte
begrenzt und bleibt mittig, damit er im Vollbild nicht auseinanderfaellt.

Ein zweiter Start oeffnet kein zweites Fenster, sondern holt das vorhandene
nach vorn. Das laeuft ueber einen Unix-Socket im abstrakten Namensraum, der
mit dem Prozess verschwindet - eine verwaiste Sperrdatei kann es nicht geben.

Die Lampen oben rechts zeigen REAPER, Aufnahme, Telefon und Radio.

## Schnittstelle zwischen Python und den Skripten

Python startet jedes Skript in einer eigenen Prozessgruppe. Beim Stoppen geht
SIGTERM an die ganze Gruppe, damit auch ffmpeg und baresip enden. Nach sechs
Sekunden ohne Reaktion folgt SIGKILL. Die Variable `TONTECHNIK_GEHEIMNISSE`
wird dabei gesetzt.

Ein drittes Skript wird in `gui/app.py` in `baue_verwaltung()` eingetragen und
in `ansicht_uebertragung.py` als weiterer Schalter ergaenzt. Sonst aendert sich
nichts.

## Pfade ueberschreiben

`TONTECHNIK_AUFNAHMEN`, `TONTECHNIK_ZUSTAND`, `TONTECHNIK_GEHEIMNISSE`,
`TONTECHNIK_VORLAGE`, `TONTECHNIK_REAPER`, `TONTECHNIK_REAPER_WEB`,
`TONTECHNIK_PEGEL_TELEFON_AUS`, `TONTECHNIK_PEGEL_TELEFON_EIN`,
`TONTECHNIK_PEGEL_RADIO_AUS`, `TONTECHNIK_RADIO_STREAM`, `TONTECHNIK_VOLLBILD`
(auf 0 setzen fuer Fensterbetrieb).

## Protokolle

    ~/.local/state/tontechnik/studio.log    Oberflaeche
    ~/.local/state/tontechnik/telefon.log   Telefonuebertragung
    ~/.local/state/tontechnik/radio.log     Radiouebertragung
    ~/.local/state/tontechnik/mithoeren.log Mithoerleitung
    ~/.local/state/tontechnik/reaper.log    REAPER

Im Reiter "Protokoll" sind sie ohne Terminal einsehbar.
