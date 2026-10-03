#!/usr/bin/env bash
# Richtet Tontechnik Studio auf diesem Rechner ein:
#   - Menueeintrag, Symbol und Fensterklasse
#   - PipeWire-Konfiguration aus vorlagen/pipewire/
#   - secrets.env aus der Vorlage, falls noch keine da ist
#   - ALSA-Loopback und Gruppe audio (fragt nach dem sudo-Passwort)
#
# Wiederholbar: Was schon stimmt, bleibt unangetastet. Ersetzte Dateien
# landen in ~/.config/tontechnik/alte-konfiguration/.
#
# Aufruf: ./installiere.sh [--entfernen]
set -euo pipefail

ORDNER="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
VORLAGEN="$ORDNER/vorlagen"
ANWENDUNGEN="$HOME/.local/share/applications"
SYMBOLE="$HOME/.local/share/icons/hicolor/scalable/apps"
EINTRAG="$ANWENDUNGEN/tontechnik-studio.desktop"
SYMBOL="$SYMBOLE/tontechnik-studio.svg"
PW_ORDNER="$HOME/.config/pipewire"
PW_DATEI="$PW_ORDNER/pipewire.conf.d/50-tontechnik.conf"
EIGENES="$HOME/.config/tontechnik"
GEHEIMNISSE="$EIGENES/secrets.env"
ABLAGE="$EIGENES/alte-konfiguration/$(date +%Y%m%d-%H%M%S)"

if [ "${1:-}" = "--entfernen" ]; then
    rm -f "$EINTRAG" "$SYMBOL"
    update-desktop-database "$ANWENDUNGEN" 2>/dev/null || true
    echo "Menueeintrag entfernt. Audiokonfiguration und secrets.env bleiben erhalten."
    exit 0
fi

schritt() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
NEUSTART_NOETIG=0

# Legt eine Datei beiseite, statt sie zu loeschen.
beiseite() {
    mkdir -p "$ABLAGE"
    mv "$1" "$ABLAGE/"
    echo "  beiseitegelegt: $1 -> $ABLAGE/"
}

# --- Menueeintrag -------------------------------------------------------------
schritt "Menueeintrag"
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
echo "  eingetragen: $EINTRAG"

# --- Programme ----------------------------------------------------------------
schritt "Programme"
FEHLEN=()
command -v pactl   >/dev/null || FEHLEN+=(pulseaudio-utils)
command -v ffmpeg  >/dev/null || FEHLEN+=(ffmpeg)
command -v python3 >/dev/null || FEHLEN+=(python3)
python3 -c "import tkinter" 2>/dev/null || FEHLEN+=(python3-tk)
# pulse.so steckt im Paket baresip, nicht in baresip-core.
if ! command -v baresip >/dev/null || ! ls /usr/lib/baresip/modules/pulse.so \
        /usr/lib/*/baresip/modules/pulse.so >/dev/null 2>&1; then
    FEHLEN+=(baresip)
fi
if [ "${#FEHLEN[@]}" -eq 0 ]; then
    echo "  alles vorhanden"
else
    echo "  FEHLT: ${FEHLEN[*]}"
    echo "  Nachinstallieren mit: sudo apt install ${FEHLEN[*]}"
fi

# --- Zugangsdaten -------------------------------------------------------------
schritt "Zugangsdaten"
if [ -f "$ORDNER/skripte/secrets.env" ]; then
    echo "  verwendet: $ORDNER/skripte/secrets.env"
elif [ -f "$GEHEIMNISSE" ]; then
    echo "  vorhanden: $GEHEIMNISSE"
else
    mkdir -p "$EIGENES"
    install -m 600 "$VORLAGEN/secrets.env.beispiel" "$GEHEIMNISSE"
    echo "  angelegt: $GEHEIMNISSE"
    echo "  Bitte die Zugangsdaten dort eintragen."
fi

# --- PipeWire -----------------------------------------------------------------
schritt "PipeWire"
# Reste frueherer Einrichtungen. Sie legen dieselben Geraete noch einmal an.
for alt in \
    "$PW_ORDNER/pipewire.conf.d/50-tontechnik-sinks.conf" \
    "$PW_ORDNER/pipewire-pulse.conf.d/10-tontechnik.conf"; do
    if [ -f "$alt" ]; then
        beiseite "$alt"
        NEUSTART_NOETIG=1
    fi
done

if [ -f "$PW_DATEI" ] && cmp -s "$VORLAGEN/pipewire/50-tontechnik.conf" "$PW_DATEI"; then
    echo "  aktuell: $PW_DATEI"
else
    [ -f "$PW_DATEI" ] && beiseite "$PW_DATEI"
    install -D -m 644 "$VORLAGEN/pipewire/50-tontechnik.conf" "$PW_DATEI"
    echo "  installiert: $PW_DATEI"
    NEUSTART_NOETIG=1
fi

# Frueherer Hilfsdienst fuer Kartenprofil und Bruecken - wird nicht mehr gebraucht.
ALTER_DIENST="$HOME/.config/systemd/user/tontechnik-audio.service"
if [ -f "$ALTER_DIENST" ]; then
    systemctl --user disable --now tontechnik-audio.service 2>/dev/null || true
    beiseite "$ALTER_DIENST"
    systemctl --user daemon-reload
fi

# --- System (sudo) ------------------------------------------------------------
schritt "ALSA-Loopback und Gruppe audio"
SYSTEM_NOETIG=0
cmp -s "$VORLAGEN/system/snd-aloop-laden.conf" /etc/modules-load.d/snd-aloop.conf || SYSTEM_NOETIG=1
cmp -s "$VORLAGEN/system/snd-aloop-optionen.conf" /etc/modprobe.d/snd-aloop.conf || SYSTEM_NOETIG=1
grep -q "^snd_aloop " /proc/modules || SYSTEM_NOETIG=1
# Die Gruppe macht den Zugriff auf den Loopback unabhaengig vom Anmeldezeitpunkt.
# Sonst kann PipeWire vor der Freigabe starten und die Quelle fehlt.
GRUPPE_NEU=0
id -nG "$USER" | tr ' ' '\n' | grep -qx audio || { SYSTEM_NOETIG=1; GRUPPE_NEU=1; }

if [ "$SYSTEM_NOETIG" -eq 0 ]; then
    echo "  alles eingerichtet"
else
    echo "  Dafuer sind Administratorrechte noetig."
    if sudo install -m 644 "$VORLAGEN/system/snd-aloop-laden.conf" /etc/modules-load.d/snd-aloop.conf \
        && sudo install -m 644 "$VORLAGEN/system/snd-aloop-optionen.conf" /etc/modprobe.d/snd-aloop.conf \
        && { grep -q "^snd_aloop " /proc/modules || sudo modprobe snd-aloop; } \
        && { [ "$GRUPPE_NEU" -eq 0 ] || sudo usermod -aG audio "$USER"; }; then
        echo "  eingerichtet"
        NEUSTART_NOETIG=1
        [ "$GRUPPE_NEU" -eq 1 ] && echo "  Die Gruppe audio wirkt erst nach Ab- und Anmelden."
    else
        echo "  FEHLER: nicht vollstaendig eingerichtet. Von Hand:"
        echo "    sudo install -m 644 $VORLAGEN/system/snd-aloop-laden.conf /etc/modules-load.d/snd-aloop.conf"
        echo "    sudo install -m 644 $VORLAGEN/system/snd-aloop-optionen.conf /etc/modprobe.d/snd-aloop.conf"
        echo "    sudo modprobe snd-aloop"
        echo "    sudo usermod -aG audio $USER"
    fi
fi

# --- Abschluss ----------------------------------------------------------------
schritt "Fertig"
if [ "$NEUSTART_NOETIG" -eq 1 ]; then
    echo "PipeWire muss neu starten, damit die Geraete entstehen. Dabei bricht"
    echo "laufender Ton kurz ab - nicht waehrend einer Uebertragung."
    antwort=""
    if [ -t 0 ]; then
        read -r -p "Jetzt neu starten? [j/N] " antwort
    fi
    if [ "$antwort" = "j" ] || [ "$antwort" = "J" ]; then
        systemctl --user restart pipewire pipewire-pulse wireplumber
        sleep 2
        "$ORDNER/skripte/audio_geraete.sh" || true
    else
        echo "Spaeter: systemctl --user restart pipewire pipewire-pulse wireplumber"
    fi
fi
cat << HINWEIS

In REAPER unter Optionen -> Einstellungen -> Audio -> Device einstellen:
  Audio system: ALSA, Output device: hw:Loopback, 48000 Hz, 32 Bit
Fuer die Aufnahmesteuerung unter Control/OSC/web ein "Web browser interface"
auf Port 8080 anlegen.
Pruefen: skripte/diagnose.sh --schnell
HINWEIS
