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
    streams.toml                 die Streams: Namen, Skripte, Pegelquellen
    ressourcen/                  Symbol als PNG und SVG
    vorlagen/
      pipewire/50-tontechnik.conf   Audiogeraete
      secrets.env.beispiel          Zugangsdaten
      system/                       snd-aloop laden und einstellen
    skripte/
      stream_telefon.sh          Telefonuebertragung (ffmpeg + baresip)
      stream_radio.sh            Radiouebertragung (ffmpeg -> Icecast)
      mitschnitt_mp3.sh          separater MP3-Mitschnitt
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
        streams.py               streams.toml lesen und pruefen
        audio.py                 PipeWire-Quellen pruefen
      gui/
        app.py                   Hauptfenster, zwei Haelften, Zustandsanzeige
        stil.py                  Farben, Schriften, ttk-Stile
        widgets.py               Lampe, Karte, Trennlinie
        karte_aufnahme.py        Aufnahme in REAPER starten und beenden
        karte_mitschnitt.py      MP3-Mitschnitt starten und beenden
        karte_ausgang.py         Pegel von REAPERs Ausgang
        pegelanzeige.py          LED-Kette mit Spitzenmarke
        ansicht_start.py         linke Haelfte: Projekt, REAPER, Aufnahme, Ausgang
        ansicht_uebertragung.py  rechte Haelfte: Streams, Mitschnitt
        ansicht_protokoll.py     Protokolle mitlesen

Keine Datei ueberschreitet rund 200 Zeilen. Die Oberflaeche kennt keine
Fachlogik, der Kern kein Tkinter.

## Uebertragungen und Pegel

Die App startet ausschliesslich die Skripte aus `skripte/`. Deren Ausgabe
steht im Protokoll (Knopf oben rechts), nicht auf den Karten. In der
Oberflaeche heissen die Uebertragungen "Streams".

baresip braucht keine eigene Konfiguration: Die Skripte erzeugen bei jedem
Start eine vollstaendige in einem temporaeren Ordner und loeschen sie beim
Beenden wieder. `~/.baresip/` wird nicht gelesen.

| Uebertragung | Senden | Testen |
|---|---|---|
| Telefon | `TelefonBruecke.monitor` (aufbereitet) | `Mithoeren.monitor`, die Mithoerleitung |
| Radio | `reaper_loopback` | der Icecast-Stream, wie ihn ein Zuhoerer bekommt |
| Mitschnitt | `reaper_loopback` (Pegel "Aufnahme") | - |

Die Pegel rechts messen nur, solange ihr Stream bzw. der Mitschnitt laeuft,
sonst steht dort "aus". Was aus REAPER kommt, zeigt die Karte
"REAPER-Ausgang" links dauerhaft (Pegel "Summe" auf `reaper_loopback`) - dort
ist schon vor jedem Start zu sehen, ob Ton da ist.

"Testen" laeuft automatisch mit der Uebertragung und endet mit ihr - auch
wenn die Uebertragung von selbst abbricht. Faellt nur die Testleitung aus,
sendet die Uebertragung weiter.

Die Pegel sind LED-Ketten mit einem Segment je dB von -60 bis 0: gruen bis
-12, gelb bis -3, darueber rot. Unbeleuchtete Segmente bleiben in ihrer Zone
schwach sichtbar, das einzelne helle Segment rechts ist die Spitze der
letzten Sekunden. Rechts neben jedem Pegel steht der hoechste Stand des
laufenden Streams, Tests oder Mitschnitts ("max -12 dB"). Er beginnt mit
jedem Start neu. Gemessen wird mit je einem eigenen ffmpeg, das nur
mitliest. Bricht eine Quelle waehrend der Messung weg, versucht sie es alle
drei Sekunden neu und zeigt so lange "kein Signal".

## Mithoeren der Telefonuebertragung

Die sendende Leitung laesst sich nicht selbst kontrollieren - eine Konferenz
spielt einem Teilnehmer den eigenen Ton nicht zurueck. Mit einer zweiten
Rufnummer geht es aber: `mithoeren_telefon.sh` waehlt die
Teilnehmer-Rufnummer an, genau wie ein Zuhoerer, und legt den Ton in den Sink
`Mithoeren`. In `streams.toml` ist sie als Testskript des Telefons
eingetragen und startet und endet deshalb automatisch mit ihm,
die Telefonkarte zeigt ihren Pegel als "Testen". Hoerbar
wird er nirgends, der Rechner bleibt im Live-Betrieb stumm. Als Mikrofon
dieser Leitung dient der stumme Sink `mithoeren_stumm`, damit nichts in die
Konferenz zurueckgeht.

Dafuer in der Fritz!Box ein zweites IP-Telefon anlegen und die Zugangsdaten als
`SIP_MITHOEREN_USER`, `SIP_MITHOEREN_PASS` und `TEILNEHMER_RUFNUMMER`
eintragen. Es sind dann zwei gleichzeitige Gespraeche: Die Fritz!Box schafft
das, es belegt aber zwei Leitungen und faellt je nach Tarif zweimal an.

## MP3-Mitschnitt

Rechts unten laesst sich ein MP3-Mitschnitt der Summe starten, unabhaengig von
REAPER und den Streams. Klang wie beim Radio, 192 kbit/s. Alle Mitschnitte
landen zentral im Musikordner unter `Mitschnitte` (auf Deutsch
`~/Musik/Mitschnitte`, ermittelt mit `xdg-user-dir MUSIC`), benannt nach Datum
und Uhrzeit. `TONTECHNIK_MITSCHNITTE` legt einen anderen Ordner fest. "Alle Streams
beenden" laesst den Mitschnitt weiterlaufen. Das Radio schneidet nicht mehr
selbst mit.

## Bedienung

Das Fenster oeffnet maximiert, Appleiste und Dock bleiben sichtbar. Es ist
zweigeteilt: links Projekt, REAPER,
Aufnahme und REAPERs Ausgang, rechts die Streams mit ihren Pegeln und darunter
der MP3-Mitschnitt. Beide Haelften halten ihren Hauptknopf am unteren Rand auf
gleicher Hoehe. Gescrollt wird nirgends, der Inhalt ist auf 1760 Punkte
Breite begrenzt und bleibt mittig. Der Knopf "Protokoll" oben rechts ersetzt
beide Haelften durch die Protokolle und fuehrt wieder zurueck.

F11 schaltet ins Vollbild und zurueck, Escape verlaesst es, Strg+Q beendet.

Ein zweiter Start oeffnet kein zweites Fenster, sondern holt das vorhandene
nach vorn. Das laeuft ueber einen Unix-Socket im abstrakten Namensraum, der
mit dem Prozess verschwindet - eine verwaiste Sperrdatei kann es nicht geben.

Die Lampen oben rechts zeigen REAPER, Aufnahme, jeden Stream und den Mitschnitt.

## Schnittstelle zwischen Python und den Skripten

Python startet jedes Skript in einer eigenen Prozessgruppe. Beim Stoppen geht
SIGTERM an die ganze Gruppe, damit auch ffmpeg und baresip enden. Nach sechs
Sekunden ohne Reaktion folgt SIGKILL. Die Variable `TONTECHNIK_GEHEIMNISSE`
wird dabei gesetzt.

## Einen Stream ergaenzen

Alle Streams stehen in `streams.toml` im Projektordner. Ein neuer Stream
braucht dort einen Eintrag und ein Skript in `skripte/`, am Code aendert sich
nichts. Die Felder sind in der Datei selbst erklaert. Beispiel:

    [[stream]]
    id = "youtube"                 # Protokoll: youtube.log
    name = "YouTube"               # Anzeige auf Karte und Lampe
    skript = "stream_youtube.sh"   # in skripte/
    senden = "reaper_loopback"     # Pegel "Senden"

    [stream.test]                  # optional
    adresse = "https://..."        # oder: quelle = "<pipewire-quelle>"

Das Skript laeuft im Vordergrund, liest seine Zugangsdaten mit
`geheimnisse_laden` aus `secrets.env` und endet sauber auf SIGTERM - als
Vorlage eignet sich `stream_radio.sh`. Ausfuehrbar muss es nicht sein, die
Oberflaeche startet es mit bash.

Bis zu zwei Streams bekommen grosse Karten, drei und vier kompakte mit dem
Knopf neben den Pegeln. Mehr passen nicht auf den Bildschirm, die Oberflaeche
meldet das. Ist `streams.toml` fehlerhaft, startet sie trotzdem - ohne Streams
und mit der Fehlermeldung rot in der Kopfzeile. `TONTECHNIK_STREAMS` zeigt auf
eine andere Datei.

Warum TOML und nicht JSON: Die Datei wird von Hand gepflegt, und TOML erlaubt
Kommentare. Python liest es ab Version 3.11 ohne Zusatzpaket.

## Pfade ueberschreiben

Oberflaeche: `TONTECHNIK_AUFNAHMEN`, `TONTECHNIK_ZUSTAND`,
`TONTECHNIK_GEHEIMNISSE`, `TONTECHNIK_VORLAGE`, `TONTECHNIK_REAPER`,
`TONTECHNIK_REAPER_WEB`, `TONTECHNIK_STREAMS`, `TONTECHNIK_MITSCHNITTE`,
`TONTECHNIK_PEGEL_MITSCHNITT`, `TONTECHNIK_PEGEL_REAPER`, `TONTECHNIK_VOLLBILD`
(auf 1 setzen, um im Vollbild zu starten). Die Pegelquellen der Streams stehen
in `streams.toml`.

Skripte: `TONTECHNIK_QUELLE_TELEFON`, `TONTECHNIK_QUELLE_RADIO`,
`TONTECHNIK_SINK_TELEFON`, `TONTECHNIK_SINK_STUMM`, `TONTECHNIK_SINK_MITHOEREN`,
`TONTECHNIK_SINK_MITHOEREN_STUMM`, `TONTECHNIK_MITSCHNITT`,
`TONTECHNIK_QUELLE_MITSCHNITT`, `TONTECHNIK_MITSCHNITT_BITRATE`.

## Fehlersuche

    skripte/diagnose.sh --schnell   Prozesse, Geraete, Loopback, Routing
    skripte/diagnose.sh             zusaetzlich Pegel und Serverton (ca. 15 s)

## Protokolle

    ~/.local/state/tontechnik/studio.log       Oberflaeche
    ~/.local/state/tontechnik/<id>.log         je Stream, etwa telefon.log
    ~/.local/state/tontechnik/<id>-test.log    Testleitung, etwa telefon-test.log
    ~/.local/state/tontechnik/mitschnitt.log   MP3-Mitschnitt
    ~/.local/state/tontechnik/reaper.log       REAPER

Ueber den Knopf "Protokoll" oben rechts sind sie ohne Terminal einsehbar.
