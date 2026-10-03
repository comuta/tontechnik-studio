#!/usr/bin/env bash
# Mithoeren der Telefonuebertragung: waehlt sich mit einem zweiten Zugang wie
# ein Zuhoerer ueber die Teilnehmer-Rufnummer ein und legt den Ton in den Sink
# Mithoeren. Die Oberflaeche misst dort den Pegel - hoerbar wird nichts.
#
# Als Mikrofon dient ein stummer Sink, damit nichts in die Konferenz
# zurueckgeht. Die Standardgeraete bleiben unangetastet.
#
# Laeuft im Vordergrund. SIGTERM beendet baresip und raeumt auf.
set -euo pipefail

SKRIPTORDNER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_geheimnisse.sh
source "$SKRIPTORDNER/lib_geheimnisse.sh"

werkzeuge_pruefen pactl baresip
geheimnisse_laden
verlange SIP_HOST SIP_MITHOEREN_USER SIP_MITHOEREN_PASS TEILNEHMER_RUFNUMMER

MITHOEREN="${TONTECHNIK_SINK_MITHOEREN:-Mithoeren}"
STUMM="${TONTECHNIK_SINK_MITHOEREN_STUMM:-mithoeren_stumm}"
ZIEL="sip:${TEILNEHMER_RUFNUMMER}@${SIP_HOST}"

pulse_verbinden
verlange_sink "$MITHOEREN"
verlange_sink "$STUMM"

BS_ORDNER="$(mktemp -d)"
baresip_vorbereiten "$BS_ORDNER" "$STUMM.monitor" "$MITHOEREN" \
    "$SIP_MITHOEREN_USER" "$SIP_MITHOEREN_PASS"

aufraeumen() {
    echo "Beende Mithoeren."
    rm -rf "$BS_ORDNER"
}
trap aufraeumen EXIT INT TERM

echo "Waehle zum Mithoeren $ZIEL."
baresip -f "$BS_ORDNER" -e "/dial $ZIEL"
