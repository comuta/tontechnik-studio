#!/usr/bin/env bash
# Gemeinsame Funktionen fuer alle Uebertragungsskripte.
# Wird mit "source" eingebunden, nicht direkt ausgefuehrt.

GEHEIMNISSE_DATEI="${TONTECHNIK_GEHEIMNISSE:-$HOME/.config/tontechnik/secrets.env}"

geheimnisse_laden() {
    if [ ! -r "$GEHEIMNISSE_DATEI" ]; then
        echo "FEHLER: $GEHEIMNISSE_DATEI ist nicht lesbar." >&2
        exit 1
    fi
    local rechte
    rechte="$(stat -c '%a' "$GEHEIMNISSE_DATEI")"
    case "$rechte" in
        600|400) ;;
        *) echo "WARNUNG: $GEHEIMNISSE_DATEI hat Rechte $rechte. Besser: chmod 600." >&2 ;;
    esac
    set -a
    # shellcheck source=/dev/null
    source "$GEHEIMNISSE_DATEI"
    set +a
}

verlange() {
    local name fehlt=0
    for name in "$@"; do
        if [ -z "${!name:-}" ]; then
            echo "FEHLER: $name fehlt in $GEHEIMNISSE_DATEI" >&2
            fehlt=1
        fi
    done
    [ "$fehlt" -eq 0 ] || exit 1
}

pulse_verbinden() {
    export PULSE_SERVER="unix:/run/user/$(id -u)/pulse/native"
}

# Ein Null-Sink heisst bei den Quellen "<name>.monitor". PulseAudio nimmt beim
# Aufnehmen aber auch den Sink-Namen an - deshalb zaehlen alle drei Schreibweisen.
hat_quelle() {
    local namen
    namen="$(pactl list short sources | awk '{print $2}')"
    grep -Fxq "$1" <<< "$namen" && return 0
    grep -Fxq "$1.monitor" <<< "$namen" && return 0
    pactl list short sinks | awk '{print $2}' | grep -Fxq "$1"
}
hat_sink()   { pactl list short sinks   | awk '{print $2}' | grep -Fxq "$1"; }

verlange_quelle() {
    if ! hat_quelle "$1"; then
        echo "FEHLER: Quelle $1 nicht gefunden. Vorhanden:" >&2
        pactl list short sources | awk '{print "  " $2}' >&2
        exit 1
    fi
}

sichere_sink() {
    local name="$1" beschreibung="${2:-$1}"
    hat_sink "$name" && return 0
    echo "Lege Sink $name an."
    pactl load-module module-null-sink \
        sink_name="$name" \
        sink_properties=device.description="$beschreibung" \
        rate=48000 channels=2 >/dev/null
}

werkzeuge_pruefen() {
    local werkzeug fehlt=0
    for werkzeug in "$@"; do
        command -v "$werkzeug" >/dev/null 2>&1 || { echo "FEHLER: $werkzeug fehlt." >&2; fehlt=1; }
    done
    [ "$fehlt" -eq 0 ] || exit 1
}
