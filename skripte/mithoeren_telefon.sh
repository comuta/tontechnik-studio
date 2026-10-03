#!/usr/bin/env bash
set -euo pipefail

SKRIPTORDNER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_geheimnisse.sh
source "$SKRIPTORDNER/lib_geheimnisse.sh"

werkzeuge_pruefen pactl baresip
geheimnisse_laden
verlange SIP_HOST SIP_MITHOEREN_USER SIP_MITHOEREN_PASS TEILNEHMER_RUFNUMMER

MITHOEREN="${TONTECHNIK_SINK_MITHOEREN:-Mithoeren}"
STUMM="mithoeren_stumm"
ZIEL="sip:${TEILNEHMER_RUFNUMMER}@${SIP_HOST}"

pulse_verbinden
sichere_sink "$MITHOEREN" "Mithoeren"
sichere_sink "$STUMM" "Mithoeren stumm"

BS_ORDNER="$(mktemp -d)"
chmod 700 "$BS_ORDNER"
[ -f "$HOME/.baresip/config" ] && cp "$HOME/.baresip/config" "$BS_ORDNER/config"
printf '<sip:%s@%s>;auth_user=%s;auth_pass=%s;regint=600\n' \
    "$SIP_MITHOEREN_USER" "$SIP_HOST" "$SIP_MITHOEREN_USER" "$SIP_MITHOEREN_PASS" \
    > "$BS_ORDNER/accounts"
chmod 600 "$BS_ORDNER/accounts"

if [ -f "$BS_ORDNER/config" ]; then
    sed -i -E "s|^audio_player.*|audio_player             pulse,$MITHOEREN|" "$BS_ORDNER/config"
    sed -i -E "s|^audio_alert.*|audio_alert              pulse,$MITHOEREN|" "$BS_ORDNER/config"
    sed -i -E "s|^audio_source.*|audio_source             pulse,$STUMM.monitor|" "$BS_ORDNER/config"
    # Ohne Terminal darf stdio.so nicht laden, sonst beendet sich baresip sofort.
    [ -t 0 ] || sed -i 's/^module[[:space:]]\+stdio\.so/#&/' "$BS_ORDNER/config"
fi

aufraeumen() {
    echo "Beende Mithoeren."
    rm -rf "$BS_ORDNER"
}
trap aufraeumen EXIT INT TERM

echo "Waehle zum Mithoeren $ZIEL."
baresip -f "$BS_ORDNER" -e "/dial $ZIEL"