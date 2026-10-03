#!/usr/bin/env bash
# Startet Tontechnik Studio direkt aus dem Git-Checkout.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
# Virtuelle Geraete pruefen und fehlende anlegen. Schlaegt das fehl, startet
# die Oberflaeche trotzdem - sie zeigt den Fehler dann in den Pegelanzeigen.
if [ -x skripte/audio_geraete.sh ]; then
    ./skripte/audio_geraete.sh || echo "Achtung: Audiogeraete unvollstaendig." >&2
fi

exec python3 -m tontechnik "$@"