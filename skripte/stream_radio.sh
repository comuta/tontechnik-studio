#!/usr/bin/env bash
# Radiouebertragung: REAPER-Summe an Icecast senden und gleichzeitig als
# MP3 mitschneiden.
#
# Laeuft im Vordergrund. SIGTERM beendet ffmpeg und schliesst die Datei.
set -euo pipefail

SKRIPTORDNER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_geheimnisse.sh
source "$SKRIPTORDNER/lib_geheimnisse.sh"

werkzeuge_pruefen pactl ffmpeg
geheimnisse_laden
verlange ICECAST_HOST ICECAST_PORT ICECAST_MOUNT ICECAST_USER ICECAST_PASS

QUELLE="${TONTECHNIK_QUELLE_RADIO:-reaper_radio}"
MITSCHNITT_ORDNER="${TONTECHNIK_MITSCHNITT:-$HOME/Aufnahmen/Mitschnitte}"
BITRATE="${ICECAST_BITRATE:-128k}"
NAME="${ICECAST_NAME:-Uebertragung}"

pulse_verbinden
verlange_quelle "$QUELLE"
mkdir -p "$MITSCHNITT_ORDNER"
DATEI="$MITSCHNITT_ORDNER/$(date +%Y-%m-%d_%H-%M)_$NAME.mp3"

ZIEL="icecast://${ICECAST_USER}:${ICECAST_PASS}@${ICECAST_HOST}:${ICECAST_PORT}${ICECAST_MOUNT}"

echo "Sende an ${ICECAST_HOST}:${ICECAST_PORT}${ICECAST_MOUNT}, Mitschnitt: ${DATEI##*/}"

# exec: ffmpeg uebernimmt die Prozess-ID, damit SIGTERM direkt ankommt und
# die MP3-Datei sauber abgeschlossen wird.
exec ffmpeg -hide_banner -loglevel warning -nostdin \
    -f pulse -i "$QUELLE" \
    -af "highpass=f=30,acompressor=threshold=0.08:ratio=3:attack=15:release=400:makeup=2,alimiter=limit=0.95" \
    -c:a libmp3lame -b:a "$BITRATE" -ar 44100 -ac 2 \
    -f tee -map 0:a \
    "[f=mp3]${DATEI}|[f=mp3:content_type=audio/mpeg:ice_name=${NAME}]${ZIEL}"
