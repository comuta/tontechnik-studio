# Tontechnik Studio

Bedienoberflaeche fuer Aufnahme und Uebertragung bei Gottesdiensten und
aehnlichen Veranstaltungen. Laeuft direkt aus dem Git-Checkout, `git pull`
genuegt zum Aktualisieren.

## Einrichtung

    ./installiere.sh        # einmalig, wiederholbar
    ./start.sh              # oder ueber das Anwendungsmenue starten

`installiere.sh` richtet einen frischen Ubuntu-Rechner vollstaendig ein:

* Menueeintrag und Symbol
* PipeWire-Konfiguration aus `vorlagen/pipewire/` nach
  `~/.config/pipewire/pipewire.conf.d/`
* `~/.config/tontechnik/secrets.env` aus `vorlagen/secrets.env.beispiel`,
  falls noch keine da ist - danach die Zugangsdaten eintragen
* ALSA-Loopback beim Systemstart laden und den Benutzer in die Gruppe
  `audio` aufnehmen (fragt nach dem sudo-Passwort)

Fehlende Programme meldet das Skript mit passendem `apt install`. Reste
frueherer Einrichtungen legt es nach `~/.config/tontechnik/alte-konfiguration/`.

In REAPER danach unter Einstellungen -> Audio -> Device: ALSA, Output device
`hw:Loopback`, 48000 Hz, 32 Bit. Fuer die Aufnahmesteuerung unter
Control/OSC/web ein "Web browser interface" auf Port 8080 anlegen. Ohne das
bleibt der Aufnahmeknopf grau und die Karte sagt, was fehlt.

## Audiowege

REAPER erkennt das TF1 nur ueber ALSA und gibt deshalb auf den ALSA-Loopback
aus. PipeWire oeffnet dessen Gegenseite als Quelle `reaper_loopback`, beide
Uebertragungen lesen sie direkt:

    REAPER -> hw:Loopback -> reaper_loopback -+-> stream_radio.sh   -> Icecast
                                              +-> stream_telefon.sh -> TelefonBruecke -> baresip
    baresip (Ton der Konferenz) -> baresip_silent (stumm)
    Mithoerleitung (Konferenz wie ein Zuhoerer) -> Mithoeren (nur gemessen)

Alle Geraete entstehen beim Start von PipeWire aus
`vorlagen/pipewire/50-tontechnik.conf`. Kein Skript legt Geraete per
`pactl load-module` an - so angelegte Geraete sind beim naechsten Neustart von
PipeWire wieder weg. `skripte/audio_geraete.sh` prueft nur und meldet.

Waehrend der Telefonuebertragung sind Standardausgang und -eingang auf
`baresip_silent` und `TelefonBruecke.monitor` gestellt. Das ist Absicht: Im
Live-Betrieb soll vom Rechner nichts hoerbar werden, auch nicht der Ton der
Konferenz.

## Aufbau

    installiere.sh               Einrichtung, Menueeintrag, Symbol
    start.sh                     Starter (python3 -m tontechnik)
    ressourcen/                  Symbol als PNG und SVG
    vorlagen/
      pipewire/50-tontechnik.conf   Audiogeraete
      secrets.env.beispiel          Zugangsdaten
      system/                       snd-aloop laden und einstellen
    skripte/
      stream_telefon.sh          Telefonuebertragung (ffmpeg + baresip)
      stream_radio.sh            Radiouebertragung (ffmpeg -> Icecast + MP3)
      mithoeren_telefon.sh       Mithoerleitung zur Pegelkontrolle
      audio_geraete.sh           prueft die Audiogeraete
      diagnose.sh                zeigt die ganze Kette, aendert nichts
      pruefe_geheimnisse.sh      sucht Zugangsdaten im Checkout
      lib_geheimnisse.sh         gemeinsame Funktionen der Skripte
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

## Uebertragungen und Pegel

Die App startet ausschliesslich die Skripte aus `skripte/` und liest deren
Ausgabe mit. Unter jeder Karte steht die letzte Zeile, die das Skript
geschrieben hat.

baresip braucht keine eigene Konfiguration: Die Skripte erzeugen bei jedem
Start eine vollstaendige in einem temporaeren Ordner und loeschen sie beim
Beenden wieder. `~/.baresip/` wird nicht gelesen.

| Uebertragung | gesendet | empfangen |
|---|---|---|
| Telefon | `TelefonBruecke.monitor` (aufbereitet) | `Mithoeren.monitor`, solange die Mithoerleitung laeuft |
| Radio | `reaper_loopback` | der Icecast-Stream, wie ihn ein Zuhoerer bekommt |

Gemessen wird mit je einem eigenen ffmpeg, das nur mitliest. Die Skala reicht
von -60 bis 0 dB, der dunkle Strich ist die Spitze der letzten Sekunden. Bricht
eine Quelle weg, versucht die Messung alle drei Sekunden neu und zeigt so
lange "kein Signal".

## Mithoeren der Telefonuebertragung

Die sendende Leitung laesst sich nicht selbst kontrollieren - eine Konferenz
spielt einem Teilnehmer den eigenen Ton nicht zurueck. Mit einer zweiten
Rufnummer geht es aber: `mithoeren_telefon.sh` waehlt die
Teilnehmer-Rufnummer an, genau wie ein Zuhoerer, und legt den Ton in den Sink
`Mithoeren`. Die Telefonkarte zeigt dessen Pegel als "mitgehoert". Hoerbar
wird er nirgends, der Rechner bleibt im Live-Betrieb stumm. Als Mikrofon
dieser Leitung dient der stumme Sink `mithoeren_stumm`, damit nichts in die
Konferenz zurueckgeht.

Dafuer in der Fritz!Box ein zweites IP-Telefon anlegen und die Zugangsdaten als
`SIP_MITHOEREN_USER`, `SIP_MITHOEREN_PASS` und `TEILNEHMER_RUFNUMMER`
eintragen. Es sind dann zwei gleichzeitige Gespraeche: Die Fritz!Box schafft
das, es belegt aber zwei Leitungen und faellt je nach Tarif zweimal an.

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

Oberflaeche: `TONTECHNIK_AUFNAHMEN`, `TONTECHNIK_ZUSTAND`,
`TONTECHNIK_GEHEIMNISSE`, `TONTECHNIK_VORLAGE`, `TONTECHNIK_REAPER`,
`TONTECHNIK_REAPER_WEB`, `TONTECHNIK_PEGEL_TELEFON_AUS`,
`TONTECHNIK_PEGEL_TELEFON_EIN`, `TONTECHNIK_PEGEL_RADIO_AUS`, `TONTECHNIK_RADIO_STREAM`, `TONTECHNIK_VOLLBILD`
(auf 0 setzen fuer Fensterbetrieb).

Skripte: `TONTECHNIK_QUELLE_TELEFON`, `TONTECHNIK_QUELLE_RADIO`,
`TONTECHNIK_SINK_TELEFON`, `TONTECHNIK_SINK_STUMM`, `TONTECHNIK_SINK_MITHOEREN`,
`TONTECHNIK_SINK_MITHOEREN_STUMM`, `TONTECHNIK_MITSCHNITT`.

## Fehlersuche

    skripte/diagnose.sh --schnell   Prozesse, Geraete, Loopback, Routing
    skripte/diagnose.sh             zusaetzlich Pegel und Serverton (ca. 15 s)

## Protokolle

    ~/.local/state/tontechnik/studio.log    Oberflaeche
    ~/.local/state/tontechnik/telefon.log   Telefonuebertragung
    ~/.local/state/tontechnik/radio.log     Radiouebertragung
    ~/.local/state/tontechnik/mithoeren.log Mithoerleitung
    ~/.local/state/tontechnik/reaper.log    REAPER

Im Reiter "Protokoll" sind sie ohne Terminal einsehbar.
