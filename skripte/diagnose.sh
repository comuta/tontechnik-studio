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
LOOP_QUELLE="reaper_loopback"
SINKS=(TelefonBruecke baresip_silent Mithoeren mithoeren_stumm)
MESSPUNKTE=(reaper_loopback TelefonBruecke Mithoeren)
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

# --- 3. Loopback -------------------------------------------------------------
loopback() {
    titel "ALSA-Loopback"
    if grep -q "^snd_aloop " /proc/modules; then
        zeile "Modul snd_aloop" "geladen"
    else
        zeile "Modul snd_aloop" "NICHT geladen  -> ./installiere.sh"
        return
    fi

    if id -nG | tr ' ' '\n' | grep -qx audio; then
        zeile "Gruppe audio" "ja"
    else
        zeile "Gruppe audio" "nein  -> Quelle fehlt evtl. nach dem Anmelden"
    fi

    if pactl list short sources | awk '{print $2}' | grep -Fxq "$LOOP_QUELLE"; then
        zeile "$LOOP_QUELLE" "vorhanden"
    else
        zeile "$LOOP_QUELLE" "FEHLT  -> systemctl --user restart pipewire"
    fi

    if pgrep -x reaper >/dev/null; then
        zeile "REAPER-Ausgabe" "$(grep -m1 '^alsa_outdev=' "$HOME/.config/REAPER/reaper.ini" 2>/dev/null \
            | cut -d= -f2) (erwartet: hw:Loopback)"
    fi
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
        if ! pactl list short sources | awk '{print $2}' | grep -Fxq -e "$name" -e "$name.monitor"; then
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
  reaper_loopback STILL        -> REAPER läuft nicht oder gibt nicht auf hw:Loopback aus
  reaper_loopback FEHLT        -> snd-aloop / Gruppe audio prüfen, PipeWire neu starten
  Sink FEHLT                   -> vorlagen/pipewire/50-tontechnik.conf nicht installiert
  Gerät mehrfach vorhanden     -> Rest alter Einrichtung, pactl unload-module <id>
  gesendet ok, Server still    -> Verbindung zum Icecast prüfen
HINWEIS
echo