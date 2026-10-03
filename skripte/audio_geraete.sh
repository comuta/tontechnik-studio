#!/usr/bin/env bash
# Prueft die Audiogeraete, die die Uebertragung braucht. Aendert nichts.
#
# Die Geraete kommen aus vorlagen/pipewire/50-tontechnik.conf und entstehen
# beim Start von PipeWire. Nachgeladen wird hier bewusst nichts: Was
# "pactl load-module" anlegt, ist beim naechsten Neustart wieder weg, und
# doppelte Geraete lassen den Ton scheinbar ins Leere laufen.
#
# Aufruf: ./audio_geraete.sh   Rueckgabewert 1, wenn etwas fehlt
set -euo pipefail

export LC_ALL=C
# Name|Art - hier stehen alle Geraete, die die Uebertragung braucht.
GERAETE=(
    "reaper_loopback|sources"
    "TelefonBruecke|sinks"
    "baresip_silent|sinks"
)

command -v pactl >/dev/null || { echo "FEHLER: pactl fehlt." >&2; exit 1; }
export PULSE_SERVER="${PULSE_SERVER:-unix:/run/user/$(id -u)/pulse/native}"

PROBLEME=0
for eintrag in "${GERAETE[@]}"; do
    name="${eintrag%%|*}"
    art="${eintrag##*|}"
    anzahl="$(pactl list short "$art" | awk -v n="$name" '$2==n' | wc -l)"
    if [ "$anzahl" -eq 1 ]; then
        printf '%-18s %s\n' "$name" "vorhanden"
    elif [ "$anzahl" -eq 0 ]; then
        printf '%-18s %s\n' "$name" "FEHLT"
        PROBLEME=$((PROBLEME + 1))
    else
        printf '%-18s %s\n' "$name" "WARNUNG: $anzahl mal vorhanden"
        PROBLEME=$((PROBLEME + 1))
    fi
done

# Von Hand geladene Module sind Reste alter Einrichtungen.
RESTE="$(pactl list short modules \
    | awk '$2 ~ /^module-(null-sink|alsa-source|loopback)$/ {print "  " $1 "  " $2 "  " $3}')"
if [ -n "$RESTE" ]; then
    echo "WARNUNG: Von Hand geladene Module gefunden:"
    echo "$RESTE"
    echo "  Mit pactl unload-module <nummer> entfernen, am besten ohne laufende Uebertragung."
    PROBLEME=$((PROBLEME + 1))
fi

if [ "$PROBLEME" -gt 0 ]; then
    echo "Einrichtung unvollstaendig: ./installiere.sh ausfuehren, Details mit skripte/diagnose.sh --schnell."
    exit 1
fi
