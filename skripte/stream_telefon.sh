#!/usr/bin/env bash
# Telefonuebertragung: REAPER-Summe telefontauglich aufbereiten und die
# Moderator-Rufnummer ueber den eigenen SIP-Zugang anrufen.
#
# Laeuft im Vordergrund. SIGTERM beendet ffmpeg, baresip und raeumt auf.
set -euo pipefail

SKRIPTORDNER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_geheimnisse.sh
source "$SKRIPTORDNER/lib_geheimnisse.sh"

werkzeuge_pruefen pactl ffmpeg baresip
geheimnisse_laden
verlange SIP_HOST SIP_USER SIP_PASS MODERATOR_RUFNUMMER

QUELLE="${TONTECHNIK_QUELLE_TELEFON:-reaper_sip}"
BRUECKE="${TONTECHNIK_SINK_TELEFON:-TelefonBruecke}"
STUMM="${TONTECHNIK_SINK_STUMM:-baresip_stumm}"
ZIEL="sip:${MODERATOR_RUFNUMMER}@${SIP_HOST}"

pulse_verbinden
verlange_quelle "$QUELLE"
verlange_sink "$BRUECKE"
verlange_sink "$STUMM"

# baresip nimmt die Standardgeraete: Eingang ist die aufbereitete Bruecke,
# Ausgang ein stummer Sink, damit der Konferenzton nicht in die Mischung faellt.
pactl set-default-source "$BRUECKE.monitor"
pactl set-default-sink "$STUMM"
pactl set-sink-volume "$BRUECKE" 100%
pactl set-source-volume "$BRUECKE.monitor" 100%

BS_ORDNER="$(mktemp -d)"
chmod 700 "$BS_ORDNER"
[ -f "$HOME/.baresip/config" ] && cp "$HOME/.baresip/config" "$BS_ORDNER/config"
printf '<sip:%s@%s>;auth_user=%s;auth_pass=%s;regint=600\n' \
    "$SIP_USER" "$SIP_HOST" "$SIP_USER" "$SIP_PASS" > "$BS_ORDNER/accounts"
chmod 600 "$BS_ORDNER/accounts"
# Ohne Terminal darf das stdio-Modul nicht laden, sonst beendet sich baresip sofort.
if [ ! -t 0 ] && [ -f "$BS_ORDNER/config" ]; then
    sed -i 's/^module[[:space:]]\+stdio\.so/#&/' "$BS_ORDNER/config"
fi

FFMPEG_PID=""
aufraeumen() {
    echo "Beende Telefonuebertragung."
    [ -n "$FFMPEG_PID" ] && kill "$FFMPEG_PID" 2>/dev/null || true
    rm -rf "$BS_ORDNER"
}
trap aufraeumen EXIT INT TERM

echo "Bereite Telefonsumme auf ($QUELLE -> $BRUECKE)."
ffmpeg -hide_banner -loglevel warning -nostdin \
    -f pulse -i "$QUELLE" \
    -af "pan=mono|c0=0.5*c0+0.5*c1,highpass=f=100,lowpass=f=3400,acompressor=threshold=0.05:ratio=5:attack=8:release=300:makeup=3,volume=8dB,alimiter=limit=0.95" \
    -ar 48000 -ac 1 \
    -f pulse -device "$BRUECKE" "stream_sip_telefon" &
FFMPEG_PID=$!

sleep 1
if ! kill -0 "$FFMPEG_PID" 2>/dev/null; then
    echo "FEHLER: ffmpeg ist sofort beendet worden." >&2
    exit 1
fi

echo "Waehle $ZIEL."
baresip -f "$BS_ORDNER" -e "/dial $ZIEL"
