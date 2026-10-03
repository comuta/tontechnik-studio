# Lessons learned — Umbau der Übertragung, September 2026

Auslöser: Der Telefonkonferenz-Anbieter hat die SIP-Zugangsdaten abgeschaltet,
zwei Wochen vor dem angekündigten Termin. Aus der Umstellung wurde ein langer
Abend Fehlersuche. Was dabei hängen geblieben ist.

---

## Audio unter PipeWire

### Ein Sink heißt bei den Quellen anders

`pactl list short sinks` zeigt `reaper_sip`, `pactl list short sources` zeigt
`reaper_sip.monitor`. Eine Prüfung, die den exakten Namen in den Sources sucht,
schlägt deshalb fehl, obwohl alles vorhanden ist.

Verwirrend wird es, weil ffmpeg beim Aufnehmen auch den **Sink**-Namen annimmt
und selbst dessen Monitor wählt. `ffmpeg -i reaper_sip` funktioniert also,
während das eigene Prüfskript "Quelle fehlt" meldet. Eine Prüfung muss alle
drei Schreibweisen akzeptieren: den Namen, `<name>.monitor` und den Sink.

### `pactl load-module` überlebt nichts

Per `load-module` angelegte Geräte verschwinden bei jedem Neustart von
PipeWire. Das war die eigentliche Ursache dafür, dass `reaper_sip` "plötzlich
weg" war. Dauerhaft gehören solche Geräte nach
`~/.config/pipewire/pipewire.conf.d/`.

### Doppelte Module sind still und gefährlich

`load-module` zweimal aufgerufen erzeugt zwei Geräte mit demselben Namen. Es
gibt keine Warnung. Danach bedient man womöglich das falsche, und der Ton läuft
ins Leere. Vor dem Anlegen prüfen, nach dem Aufräumen zählen:

    pactl list short sinks | grep reaper_sip    # genau eine Zeile

Und: Wird ein Duplikat entladen, an dem ein laufender Stream hängt, bricht
dessen Ton ab.

### Der ALSA-Loopback braucht ein aktives Kartenprofil

`snd-aloop` war geladen, die Karte stand in `/proc/asound/cards`, WirePlumber
hatte sie geöffnet — trotzdem erschien keine Quelle. Grund: **Aktives Profil:
off**. Erst

    pactl set-card-profile alsa_card.platform-snd_aloop.0 \
        output:analog-stereo+input:analog-stereo

macht `alsa_input.platform-snd_aloop.0.analog-stereo` sichtbar. Das Profil wird
nicht automatisch gemerkt und gehört in ein Startskript.

### Wer hält das Modul fest?

`rmmod snd-aloop` meldete "in use", obwohl REAPER beendet war. Der Halter war
WirePlumber. Der Benutzungszähler in `lsmod` zeigt, wie viele Öffner es gibt;
`sudo fuser -v /dev/snd/*` nennt sie beim Namen. Zum Entladen muss der ganze
Stack weg — **Sockets zuerst**, sonst startet PipeWire sofort neu:

    systemctl --user stop pipewire.socket pipewire-pulse.socket
    systemctl --user stop wireplumber pipewire-pulse pipewire

### REAPER verliert seine Zuweisung

War ein Sink beim Start von REAPER nicht da oder wurde zwischendurch neu
angelegt, zeigt REAPERs Hardware-Ausgabezuweisung ins Leere. Symptom: Sink
existiert, steht aber auf IDLE statt RUNNING. Der Zustand in
`pactl list short sinks` ist die schnellste Diagnose — RUNNING heißt, es wird
wirklich etwas hineingeschrieben.

### Die Schichtung war das Grundproblem

REAPER gab über ALSA direkt auf `hw:Loopback` aus, nicht an PipeWire. Dazwischen
brauchte es eine Brücke vom Loopback in die Sinks. Jede dieser Schichten konnte
einzeln ausfallen, und keine meldete sich, wenn sie es tat. Der direkte Weg
(REAPER als PipeWire-Client, Output device `pulse`) hätte die halbe Fehlersuche
erspart.

---

## SIP und Telefonie

### Die Fritz!Box telefoniert nicht kostenlos

Sie ist nur das Endgerät und reicht an den Telefonanbieter weiter. Ob Minuten
anfallen, entscheidet der Tarif und die Art der Zielrufnummer: geografische
Nummern fallen meist unter die Flat, 0180 und 0900 nicht.

### 401 Unauthorized heißt immer Zugangsdaten

Nicht Routing, nicht Sink, nicht Skript. Der Benutzername ist der eigene
Anmeldename des IP-Telefons, nicht der Anzeigename des Geräts. Der Grund steht
in der Fritz!Box unter System → Ereignisse → Telefonie im Klartext.

### Sonderzeichen in `secrets.env`

`SIP_PASS=ab$cd` wird von der Shell zerlegt. Immer in einfache
Anführungszeichen. Gegenprobe:

    set -a; source ~/.config/tontechnik/secrets.env; set +a
    echo "[$SIP_PASS]"

### "Call in-progress" ist nicht "Call established"

Bei `183 Session Progress` baut die Gegenstelle schon einen Medienkanal auf —
man hört die Ansage, sendet aber noch nicht in die Konferenz. Die Weboberfläche
zeigt trotzdem einen verbundenen, nicht stummen Teilnehmer. Wer nur auf die
Weboberfläche schaut, sucht den Fehler an der falschen Stelle.

### baresip ohne Terminal

Mit `stdin` auf `/dev/null` beendet sich baresip sofort, solange `stdio.so`
geladen ist. In der temporären Konfiguration auskommentieren, wenn kein
Terminal vorhanden ist (`[ -t 0 ] || sed -i ...`).

`baresip -f <ordner>` ersetzt das **komplette** Konfigurationsverzeichnis.
Änderungen in `~/.baresip/config` wirken dann nur, wenn das Skript die Datei
dorthin kopiert.

### Geräte fest eintragen statt Standard setzen

`pactl set-default-source` legt nur fest, was neue Clients bekommen *sollen*.
Verlässlich ist `audio_source pulse,<gerät>` in der baresip-Konfiguration.
Kontrolle im laufenden Anruf:

    LC_ALL=C pactl list source-outputs | grep -E "Source:|application.name"

### Mithören braucht eine zweite Leitung

Eine Konferenz spielt dem eigenen Teilnehmer den Ton nicht zurück. Zum
Kontrollieren wählt man sich mit einer zweiten Nummer über die
**Teilnehmer**-Rufnummer ein, nicht noch einmal über die Moderator-Nummer.
Als Mikrofon dieser Leitung dient ein stummer Sink — sonst Rückkopplung.

---

## Werkzeuge und Vorgehen

### `pactl` spricht Deutsch

`grep "Source:"` findet nichts, wenn dort "Quelle:" steht. Bei Skripten und
Diagnosebefehlen immer `LC_ALL=C` voranstellen.

### `timeout` verschluckt die Auswertung

`timeout 10 ffmpeg ... -af volumedetect` schickt SIGTERM, bevor ffmpeg die
Werte ausgibt. Stattdessen `-t 10` verwenden, dann beendet ffmpeg sich selbst
und schreibt das Ergebnis.

### Pegel messen, statt hören

`volumedetect` beantwortet im laufenden Betrieb die Frage "kommt hier Signal
an?", ohne etwas umzurouten und ohne Wiedergabe:

    ffmpeg -f pulse -i <quelle> -t 10 -af volumedetect -f null - 2>&1 \
      | grep -E "mean_volume|max_volume"

Richtwerte: Mittelwert um −25 dB, Spitze unter −3 dB. Unter −80 dB oder `-inf`
heißt Stille.

### Heruntergeladene Skripte sind nicht ausführbar

Nach jedem Download `chmod +x`. Eine systemd-Unit quittiert das mit
`status=203/EXEC`, ein `[ -x datei ]` in einem Startskript überspringt den
Aufruf dagegen kommentarlos.

### Icecast: "Broken pipe" direkt nach dem Header

Der Server hat aufgelegt. Zu prüfen in dieser Reihenfolge: Mountpoint schon
belegt, neueres ffmpeg spricht HTTP PUT statt der alten `SOURCE`-Methode
(`-legacy_icecast 1`), Zugangsdaten falsch. Der Grund steht in der `error.log`
des Servers.

### Zugangsdaten nicht in Chats kopieren

Beim Einfügen eines Skripts ist das Icecast-Quellpasswort mitgegangen. Solche
Passwörter danach wechseln.

---

## Software

### Ein Patch, der nicht greift, sagt nichts

Zweimal wurde eine Codeänderung nicht angewendet, weil der gesuchte Text sich
vorher geändert hatte — und zweimal fiel es erst beim Anwender auf. Jede
automatische Ersetzung muss prüfen, ob sie etwas getroffen hat, und sonst
abbrechen.

### Ohne Bildschirm testen

Eine Tkinter-Attrappe reicht, um die gesamte Oberfläche aufzubauen und jeden
Bedienpfad durchzulaufen. `werkzeuge/probelauf.py` findet Tippfehler und
falsche Aufrufe in einer Sekunde — vor dem Gottesdienst, nicht während.

### Eigene Berechnungen gegenprüfen

Die selbst gerechnete RMS-Anzeige liefert exakt dieselben Werte wie ffmpegs
`volumedetect`. So ein Vergleich kostet eine Minute und macht aus "sieht
plausibel aus" ein belastbares Ergebnis.

### WM_CLASS besteht aus zwei Teilen

Ohne Angabe heißt das Fenster nach dem Programm, also `python3`. Damit findet
GNOME keinen Menüeintrag, zeigt das allgemeine Zahnrad und legt einen zweiten
Dock-Eintrag an.

Nachtrag: `baseName` hilft dabei nicht. Beide Teile entstehen allein aus
`className`, und Tk normalisiert die Schreibweise: Aus `TontechnikStudio`
wurde `("tontechnikStudio", "Tontechnikstudio")` - passend zu keinem
`StartupWMClass`. Verlässlich ist `Tk(className="<name des .desktop>")`, hier
`tontechnik-studio`. Prüfen statt vermuten:

    xwininfo -root -tree | grep -i tontechnik

### Sperren gehören an den Ordner, nicht an den Benutzer

Eine Einzelinstanz-Sperre pro Benutzer verhindert, dass eine zweite Kopie zum
Testen startet — sie holt stattdessen das alte Fenster nach vorn. Der
Installationspfad ist die bessere Grundlage.

---

## Was daraus folgt

1. **Zustand sichtbar machen.** RUNNING/IDLE, Pegel, letzte Logzeile. Fast jeder
   Fehler dieses Abends war in einer Zeile Ausgabe erkennbar — man musste nur
   wissen, wo man hinschaut.
2. **Nichts von Hand laden, was in eine Konfiguration gehört.** Alles, was
   `load-module` anlegt, ist bis zum nächsten Neustart geborgt.
3. **Schichten reduzieren.** Der ALSA-Loopback zwischen REAPER und PipeWire war
   die Ursache der meisten Ausfälle.
4. **Redundanz zahlt sich aus.** Während die Telefonübertragung nicht lief, ging
   der Ton über den Radio-Stream weiter raus. Das Wichtige war draußen.
