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
        echo "Einrichtung pruefen: skripte/diagnose.sh --schnell" >&2
        exit 1
    fi
}

# Geraete werden nie per "pactl load-module" nachgeladen - so angelegte Sinks
# verschwinden beim naechsten Neustart von PipeWire. Sie kommen aus
# vorlagen/pipewire/50-tontechnik.conf.
verlange_sink() {
    if ! hat_sink "$1"; then
        echo "FEHLER: Sink $1 fehlt. Ist vorlagen/pipewire/50-tontechnik.conf" \
             "installiert (./installiere.sh)?" >&2
        exit 1
    fi
}

baresip_module() {
    local ordner
    for ordner in /usr/lib/baresip/modules /usr/lib/*/baresip/modules \
                  /usr/local/lib/baresip/modules; do
        [ -f "$ordner/pulse.so" ] && { echo "$ordner"; return 0; }
    done
    echo "FEHLER: baresip-Modul pulse.so fehlt (Paket baresip installieren)." >&2
    exit 1
}

# Schreibt eine vollstaendige baresip-Konfiguration nach <ordner>, damit keine
# ~/.baresip/config noetig ist. Nur was fuer einen Anruf ohne Terminal noetig
# ist: stdio.so fehlt mit Absicht, ohne Terminal beendet es baresip sofort.
# menu.so fuehrt "/dial" aus.
# Aufruf: baresip_vorbereiten <ordner> <quelle> <ausgabe-sink> <benutzer> <passwort>
baresip_vorbereiten() {
    local ordner="$1" quelle="$2" ausgabe="$3" benutzer="$4" passwort="$5" module
    module="$(baresip_module)"
    chmod 700 "$ordner"
    cat > "$ordner/config" << KONFIG_ENDE
poll_method             epoll
sip_cafile              /etc/ssl/certs/ca-certificates.crt
call_local_timeout      120
call_max_calls          1
audio_source            pulse,$quelle
audio_player            pulse,$ausgabe
audio_alert             pulse,$ausgabe
audio_level             no
audio_buffer            20-160
module_path             $module
module                  g711.so
module                  pulse.so
module_tmp              uuid.so
module_tmp              account.so
module_app              menu.so
KONFIG_ENDE
    printf '<sip:%s@%s>;auth_user=%s;auth_pass=%s;regint=600\n' \
        "$benutzer" "$SIP_HOST" "$benutzer" "$passwort" > "$ordner/accounts"
    chmod 600 "$ordner/accounts"
}

werkzeuge_pruefen() {
    local werkzeug fehlt=0
    for werkzeug in "$@"; do
        command -v "$werkzeug" >/dev/null 2>&1 || { echo "FEHLER: $werkzeug fehlt." >&2; fehlt=1; }
    done
    [ "$fehlt" -eq 0 ] || exit 1
}
