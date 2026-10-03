#!/usr/bin/env bash
# Diagnose der Übertragungskette. Ändert nichts - weder Routing noch Module,
# noch laufende Prozesse. Gefahrlos im laufenden Betrieb aufzurufen.
#
#   ./diagnose.sh            alles, mit Pegelmessung (ca. 15 Sekunden)
#   ./diagnose.sh --schnell  ohne Pegelmessung, sofort fertig
#   ./diagnose.sh --pegel    nur die Pegel
set -uo pipefail

export LC_ALL=C   # pactl antwortet sonst auf Deutsch und Filter greifen nicht
export PULSE_SERVER="${PULSE_SERVER:-unix:/run/user/$(id -u)/pulse/native}"

MESSDAUER=3
KARTE="alsa_card.platform-snd_aloop.0"
LOOP_QUELLE="alsa_input.platform-snd_aloop.0.analog-stereo"
SINKS=(reaper_sip reaper_radio TelefonBruecke baresip_silent Mithoeren mithoeren_stumm)
MESSPUNKTE=(reaper_sip reaper_radio TelefonBruecke Mithoeren)
STREAM="${TONTECHNIK_RADIO_STREAM:-http://segenswelle.de:8000/ECBG-Gelsenkirchen}"

MODUS="alles"
case "${1:-}" in
    --schnell) MODUS="schnell" ;;
    --pegel)   MODUS="pegel" ;;
esac

titel() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
zeile() { printf '  %-34s %s\n' "$1" "$2"; }

# --- 1. Prozesse -------------------------------------------------------------
prozesse() {
    titel "Prozesse"
    if pgrep -x reaper >/dev/null; then
        zeile "REAPER" "läuft (PID $(pgrep -x reaper | tr '\n' ' '))"
    else
        zeile "REAPER" "läuft NICHT"
    fi

    local anzahl
    anzahl="$(pgrep -cx baresip || true)"
    zeile "baresip" "${anzahl:-0} Prozess(e)"

    echo "  ffmpeg:"
    if ! pgrep -a ffmpeg >/dev/null; then
        echo "      keiner"
        return
    fi
    # Nur das Wesentliche zeigen: Ein- und Ausgang je Prozess.
    pgrep -a ffmpeg | while read -r pid rest; do
        local ein aus
        ein="$(grep -oP '(?<=-i )[^ ]+' <<< "$rest" | head -1)"
        aus="$(grep -oP '(?<=-device )[^ ]+' <<< "$rest" | head -1)"
        [ -z "$aus" ] && aus="$(grep -oP 'icecast://[^ "]+' <<< "$rest" | sed 's|:[^:@]*@|:***@|' | head -1)"
        [ -z "$aus" ] && aus="(Messung)"
        printf '      %-7s %-46s -> %s\n' "$pid" "${ein:-?}" "$aus"
    done
}

# --- 2. Geräte ---------------------------------------------------------------
geraete() {
    titel "Virtuelle Geräte"
    local liste name zustand anzahl
    liste="$(pactl list short sinks)"
    for name in "${SINKS[@]}"; do
        anzahl="$(awk -v n="$name" '$2==n' <<< "$liste" | wc -l)"
        if [ "$anzahl" -eq 0 ]; then
            zeile "$name" "FEHLT"
        elif [ "$anzahl" -gt 1 ]; then
            zeile "$name" "WARNUNG: $anzahl mal vorhanden"
        else
            zustand="$(awk -v n="$name" '$2==n {print $NF}' <<< "$liste")"
            case "$zustand" in
                RUNNING) zeile "$name" "RUNNING  (es wird hineingeschrieben)" ;;
                IDLE)    zeile "$name" "IDLE     (verbunden, aber still)" ;;
                *)       zeile "$name" "$zustand" ;;
            esac
        fi
    done
}

# --- 3. Loopback-Karte -------------------------------------------------------
loopback() {
    titel "ALSA-Loopback"
    if grep -q "^snd_aloop " /proc/modules; then
        zeile "Modul snd_aloop" "geladen ($(awk '$1=="snd_aloop"{print $3}' /proc/modules) Nutzer)"
    else
        zeile "Modul snd_aloop" "NICHT geladen"
        return
    fi

    local profil
    profil="$(pactl list cards \
        | sed -n "/Name: $KARTE\$/,/^Card #/p" \
        | sed -n 's/^[[:space:]]*Active Profile:[[:space:]]*//p' | head -1)"
    if [ -z "$profil" ]; then
        zeile "Kartenprofil" "Karte nicht gefunden"
    elif [ "$profil" = "off" ]; then
        zeile "Kartenprofil" "off  -> PipeWire sieht REAPER nicht"
    else
        zeile "Kartenprofil" "$profil"
    fi

    if pactl list short sources | awk '{print $2}' | grep -Fxq "$LOOP_QUELLE"; then
        zeile "Loopback-Quelle" "vorhanden"
    else
        zeile "Loopback-Quelle" "FEHLT"
    fi

    local bruecken
    bruecken="$(pactl list short modules | grep -c "module-loopback.*$LOOP_QUELLE" || true)"
    zeile "Brücken zu den Sinks" "$bruecken (erwartet: 2)"
}

# --- 4. Wer sendet wohin ----------------------------------------------------
routing() {
    titel "Routing der Clients"
    local ausgaben
    ausgaben="$(pactl list source-outputs 2>/dev/null)"
    if [ -z "$ausgaben" ]; then
        echo "  keine Aufnahme-Clients"
    else
        awk '
            /Source:/ {q=$2}
            /application.name = / {gsub(/"/,""); printf "      %-22s liest Quelle %s\n", $3, q}
        ' <<< "$ausgaben"
    fi

    local eingaben
    eingaben="$(pactl list sink-inputs 2>/dev/null)"
    if [ -n "$eingaben" ]; then
        awk '
            /Sink:/ {s=$2}
            /application.name = / {gsub(/"/,""); printf "      %-22s schreibt in Sink %s\n", $3, s}
        ' <<< "$eingaben"
    fi
    echo "  (Nummern über: pactl list short sources | short sinks)"
}

# --- 5. Pegel ----------------------------------------------------------------
messen() {
    titel "Pegel (je $MESSDAUER s)"
    command -v ffmpeg >/dev/null || { echo "  ffmpeg fehlt"; return; }

    local name ausgabe mittel spitze
    for name in "${MESSPUNKTE[@]}"; do
        if ! pactl list short sinks | awk '{print $2}' | grep -Fxq "$name"; then
            zeile "$name" "nicht vorhanden"
            continue
        fi
        ausgabe="$(ffmpeg -nostdin -hide_banner -f pulse -i "$name" -t "$MESSDAUER" \
                   -af volumedetect -f null - 2>&1)"
        mittel="$(grep -oE 'mean_volume: [-0-9.a-z]+ dB' <<< "$ausgabe" | grep -oE '[-0-9.a-z]+ dB')"
        spitze="$(grep -oE 'max_volume: [-0-9.a-z]+ dB' <<< "$ausgabe" | grep -oE '[-0-9.a-z]+ dB')"
        if [ -z "$mittel" ]; then
            zeile "$name" "keine Messung möglich"
        elif [[ "$mittel" == *inf* ]]; then
            zeile "$name" "STILL"
        else
            zeile "$name" "Mittel $mittel, Spitze ${spitze:-?}"
        fi
    done
}

# --- 6. Radiostream vom Server ----------------------------------------------
serverton() {
    titel "Radiostream vom Server"
    command -v ffmpeg >/dev/null || { echo "  ffmpeg fehlt"; return; }
    local ausgabe
    echo "  (verbinde, bitte kurz warten)"
    ausgabe="$(timeout -k 2 $((MESSDAUER + 9)) ffmpeg -nostdin -hide_banner \
               -rw_timeout 5000000 -i "$STREAM" -t "$MESSDAUER" \
               -af volumedetect -f null - 2>&1)"
    if grep -q "mean_volume" <<< "$ausgabe"; then
        zeile "$STREAM" "$(grep -oE 'mean_volume: -?[0-9.]+ dB|mean_volume: -inf dB' <<< "$ausgabe" | head -1)"
    else
        zeile "$STREAM" "nicht erreichbar oder kein Ton"
    fi
}

# --- 7. Dienste --------------------------------------------------------------
dienste() {
    titel "Dienste"
    local zustand
    zustand="$(systemctl --user is-active tontechnik-audio.service 2>/dev/null)"
    zeile "tontechnik-audio.service" "${zustand:-nicht eingerichtet}"
    for dienst in pipewire pipewire-pulse wireplumber; do
        zeile "$dienst" "$(systemctl --user is-active "$dienst" 2>/dev/null)"
    done
}

case "$MODUS" in
    pegel)
        messen
        serverton
        ;;
    schnell)
        prozesse; geraete; loopback; routing; dienste
        ;;
    *)
        prozesse; geraete; loopback; routing; dienste; messen; serverton
        ;;
esac

titel "Kurzdeutung"
cat << 'HINWEIS'
  Sink IDLE statt RUNNING      -> REAPER schreibt nicht hinein (Zuweisung prüfen)
  Sink FEHLT                   -> PipeWire neu gestartet, Geräte weg
  Sink mehrfach vorhanden      -> Duplikat, entladen mit pactl unload-module <id>
  Kartenprofil off             -> pactl set-card-profile, siehe audio_aufbau.sh
  Brücken 0 statt 2            -> systemctl --user restart tontechnik-audio
  gesendet ok, Server still    -> Verbindung zum Icecast prüfen
HINWEIS
echo