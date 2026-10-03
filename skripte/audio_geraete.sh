#!/usr/bin/env bash
# Prueft die virtuellen Audiogeraete und legt fehlende an.
#
# Idempotent: Was schon da ist, bleibt unangetastet. Doppelt geladene Module
# werden gemeldet und bis auf eines entfernt - Duplikate sind die haeufigste
# Ursache dafuer, dass Ton scheinbar ins Leere laeuft.
#
# Aufruf:
#   ./audio_geraete.sh            pruefen und fehlende anlegen
#   ./audio_geraete.sh --pruefen  nur berichten, nichts aendern
set -euo pipefail

# Name|Beschreibung - hier stehen alle Geraete, die die Uebertragung braucht.
GERAETE=(
    "reaper_sip|REAPER Telefon"
    "reaper_radio|REAPER Radio"
    "TelefonBruecke|Telefonbruecke"
    "baresip_silent|Baresip stumm"
    "Mithoeren|Mithoeren"
    "mithoeren_stumm|Mithoeren stumm"
)

NUR_PRUEFEN=0
[ "${1:-}" = "--pruefen" ] && NUR_PRUEFEN=1

command -v pactl >/dev/null || { echo "FEHLER: pactl fehlt." >&2; exit 1; }
export PULSE_SERVER="${PULSE_SERVER:-unix:/run/user/$(id -u)/pulse/native}"

modul_ids() {
    pactl list short modules \
        | awk -v name="sink_name=$1" '$2=="module-null-sink" && index($0, name) {print $1}'
}

vorhanden() {
    pactl list short sinks | awk '{print $2}' | grep -Fxq "$1"
}

anlegen() {
    pactl load-module module-null-sink \
        sink_name="$1" \
        sink_properties=device.description="$2" \
        rate=48000 channels=2 >/dev/null
}

FEHLT=0
ANGELEGT=0
ENTFERNT=0

for eintrag in "${GERAETE[@]}"; do
    name="${eintrag%%|*}"
    beschreibung="${eintrag##*|}"

    mapfile -t ids < <(modul_ids "$name")
    anzahl=${#ids[@]}

    if [ "$anzahl" -gt 1 ]; then
        if [ "$NUR_PRUEFEN" -eq 1 ]; then
            printf '%-18s %s\n' "$name" "WARNUNG: $anzahl Module geladen"
        else
            for id in "${ids[@]:1}"; do
                pactl unload-module "$id" 2>/dev/null || true
                ENTFERNT=$((ENTFERNT + 1))
            done
            printf '%-18s %s\n' "$name" "Duplikate entfernt ($((anzahl - 1)))"
        fi
    fi

    if vorhanden "$name"; then
        printf '%-18s %s\n' "$name" "vorhanden"
        continue
    fi

    if [ "$NUR_PRUEFEN" -eq 1 ]; then
        printf '%-18s %s\n' "$name" "FEHLT"
        FEHLT=$((FEHLT + 1))
        continue
    fi

    if anlegen "$name" "$beschreibung" && vorhanden "$name"; then
        printf '%-18s %s\n' "$name" "angelegt"
        ANGELEGT=$((ANGELEGT + 1))
    else
        printf '%-18s %s\n' "$name" "FEHLER beim Anlegen"
        FEHLT=$((FEHLT + 1))
    fi
done

echo "---"
if [ "$NUR_PRUEFEN" -eq 1 ]; then
    echo "Nur geprueft: $FEHLT fehlend."
else
    echo "Angelegt: $ANGELEGT, Duplikate entfernt: $ENTFERNT, ungeloest: $FEHLT."
    echo "Hinweis: Diese Geraete verschwinden beim Neustart von PipeWire."
fi
exit $(( FEHLT > 0 ? 1 : 0 ))