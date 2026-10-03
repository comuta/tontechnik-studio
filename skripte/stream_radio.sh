#!/usr/bin/env bash
# Radiouebertragung: REAPER-Summe an Icecast senden.
#
# Den MP3-Mitschnitt uebernimmt mitschnitt_mp3.sh, damit er sich unabhaengig
# von der Uebertragung starten und beenden laesst.
#
# Laeuft im Vordergrund. SIGTERM beendet ffmpeg.
set -euo pipefail

SKRIPTORDNER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_geheimnisse.sh
source "$SKRIPTORDNER/lib_geheimnisse.sh"

werkzeuge_pruefen pactl ffmpeg
geheimnisse_laden
verlange ICECAST_HOST ICECAST_PORT ICECAST_MOUNT ICECAST_USER ICECAST_PASS

QUELLE="${TONTECHNIK_QUELLE_RADIO:-reaper_loopback}"
BITRATE="${ICECAST_BITRATE:-128k}"
NAME="${ICECAST_NAME:-Uebertragung}"

pulse_verbinden
verlange_quelle "$QUELLE"

ZIEL="icecast://${ICECAST_USER}:${ICECAST_PASS}@${ICECAST_HOST}:${ICECAST_PORT}${ICECAST_MOUNT}"

echo "Sende an ${ICECAST_HOST}:${ICECAST_PORT}${ICECAST_MOUNT}."

# exec: ffmpeg uebernimmt die Prozess-ID, damit SIGTERM direkt ankommt.
exec ffmpeg -hide_banner -loglevel warning -nostdin \
    -f pulse -i "$QUELLE" \
    -af "highpass=f=30,acompressor=threshold=0.08:ratio=3:attack=15:release=400:makeup=2,alimiter=limit=0.95" \
    -c:a libmp3lame -b:a "$BITRATE" -ar 44100 -ac 2 \
    -f mp3 -content_type audio/mpeg -ice_name "$NAME" \
    "$ZIEL"
