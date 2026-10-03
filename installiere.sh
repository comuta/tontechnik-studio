#!/usr/bin/env bash
# Traegt Tontechnik Studio ins Anwendungsmenue ein, mit Symbol und
# passender Fensterklasse. Aufruf: ./installiere.sh [--entfernen]
set -euo pipefail

ORDNER="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
ANWENDUNGEN="$HOME/.local/share/applications"
SYMBOLE="$HOME/.local/share/icons/hicolor/scalable/apps"
EINTRAG="$ANWENDUNGEN/tontechnik-studio.desktop"
SYMBOL="$SYMBOLE/tontechnik-studio.svg"

if [ "${1:-}" = "--entfernen" ]; then
    rm -f "$EINTRAG" "$SYMBOL"
    update-desktop-database "$ANWENDUNGEN" 2>/dev/null || true
    echo "Eintrag entfernt."
    exit 0
fi

mkdir -p "$ANWENDUNGEN" "$SYMBOLE"
install -m 644 "$ORDNER/ressourcen/tontechnik-studio.svg" "$SYMBOL"

cat > "$EINTRAG" << EINTRAG_ENDE
[Desktop Entry]
Type=Application
Name=Tontechnik Studio
Comment=Aufnahme und Uebertragung fuer Gottesdienste
Exec=$ORDNER/start.sh
Icon=tontechnik-studio
Terminal=false
Categories=AudioVideo;Audio;
StartupNotify=true
StartupWMClass=TontechnikStudio
SingleMainWindow=true
EINTRAG_ENDE

chmod 644 "$EINTRAG"
update-desktop-database "$ANWENDUNGEN" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Eingetragen: $EINTRAG"
echo "Das Symbol laesst sich jetzt aus dem Anwendungsmenue ans Dock heften."
