#!/usr/bin/env bash
# Sucht im Git-Checkout nach Zugangsdaten, die dort nicht hingehoeren.
set -euo pipefail

BASIS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MUSTER='auth_pass|ICECAST_PASS=|SIP_PASS=|password=|icecast://[^"$]*:'
TREFFER=0

while IFS= read -r datei; do
    if grep -nEI "$MUSTER" "$datei" | grep -vE '\$\{?[A-Z_]+' >/dev/null; then
        echo "VERDACHT in ${datei#$BASIS/}:"
        grep -nEI "$MUSTER" "$datei" | grep -vE '\$\{?[A-Z_]+' | sed 's/^/  /'
        TREFFER=1
    fi
done < <(git -C "$BASIS" ls-files 2>/dev/null || find "$BASIS" -type f -not -path '*/.git/*')

if [ "$TREFFER" -eq 0 ]; then
    echo "Sauber: keine Zugangsdaten im Checkout gefunden."
else
    echo "Bitte pruefen und nach ~/.config/tontechnik/secrets.env auslagern." >&2
    exit 1
fi
