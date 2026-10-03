#!/usr/bin/env bash
# MP3-Mitschnitt der REAPER-Summe, unabhaengig von den Uebertragungen.
#
# Die Datei landet in TONTECHNIK_MITSCHNITT. Die Oberflaeche setzt dort den
# Ordner "Mitschnitt" des aktuellen Projekts ein, sonst gilt der Standard.
# Klang wie beim Radio, damit der Mitschnitt so klingt wie die Sendung.
#
# Laeuft im Vordergrund. SIGTERM beendet ffmpeg und schliesst die Datei sauber.
set -euo pipefail

SKRIPTORDNER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_geheimnisse.sh
source "$SKRIPTORDNER/lib_geheimnisse.sh"

werkzeuge_pruefen pactl ffmpeg

QUELLE="${TONTECHNIK_QUELLE_MITSCHNITT:-reaper_loopback}"
ORDNER="${TONTECHNIK_MITSCHNITT:-$HOME/Aufnahmen/Mitschnitte}"
BITRATE="${TONTECHNIK_MITSCHNITT_BITRATE:-192k}"

pulse_verbinden
verlange_quelle "$QUELLE"
mkdir -p "$ORDNER"
DATEI="$ORDNER/$(date +%Y-%m-%d_%H-%M-%S)_Mitschnitt.mp3"

echo "Ordner: $ORDNER"
echo "Datei: ${DATEI##*/}"

# exec: ffmpeg uebernimmt die Prozess-ID, damit SIGTERM direkt ankommt und
# die MP3-Datei sauber abgeschlossen wird.
exec ffmpeg -hide_banner -loglevel error -nostdin \
    -f pulse -i "$QUELLE" \
    -af "highpass=f=30,acompressor=threshold=0.08:ratio=3:attack=15:release=400:makeup=2,alimiter=limit=0.95" \
    -c:a libmp3lame -b:a "$BITRATE" -ar 48000 -ac 2 \
    "$DATEI"
