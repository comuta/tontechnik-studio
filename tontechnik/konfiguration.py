"""Zentrale Pfade und Konstanten.

Jeder Pfad laesst sich ueber eine Umgebungsvariable ueberschreiben, damit
Tests und ein zweiter Rechner ohne Codeaenderung laufen.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

HEIM = Path.home()
BASIS = Path(__file__).resolve().parent.parent
SKRIPTE = BASIS / "skripte"


def _pfad(variable: str, standard: Path) -> Path:
    wert = os.environ.get(variable)
    return Path(wert).expanduser() if wert else standard


RESSOURCEN = BASIS / "ressourcen"
ICON = RESSOURCEN / "tontechnik-studio.png"

def _musikordner() -> Path:
    """Musikordner laut Desktop (auf Deutsch ~/Musik), sonst ~/Musik."""
    try:
        ergebnis = subprocess.run(
            ["xdg-user-dir", "MUSIC"], capture_output=True, text=True, timeout=3
        )
        ordner = ergebnis.stdout.strip()
        # Ohne Eintrag antwortet xdg-user-dir mit dem Heimordner selbst.
        if ergebnis.returncode == 0 and ordner and Path(ordner) != HEIM:
            return Path(ordner)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return HEIM / "Musik"


AUFNAHMEN = _pfad("TONTECHNIK_AUFNAHMEN", HEIM / "Aufnahmen")
ZUSTAND = _pfad("TONTECHNIK_ZUSTAND", HEIM / ".local/state/tontechnik")
def _geheimnisse_standard() -> Path:
    """Bevorzugt die Datei neben den Skripten, sonst die im Benutzerprofil."""
    neben_skripten = SKRIPTE / "secrets.env"
    return neben_skripten if neben_skripten.is_file() else HEIM / ".config/tontechnik/secrets.env"


GEHEIMNISSE = _pfad("TONTECHNIK_GEHEIMNISSE", _geheimnisse_standard())
REAPER_VORLAGE = _pfad(
    "TONTECHNIK_VORLAGE",
    HEIM / ".config/REAPER/ProjectTemplates/Yamaha_TF1_GE_Live_Stereo.RPP",
)
REAPER_BEFEHL = os.environ.get("TONTECHNIK_REAPER", "reaper")
REAPER_WEB = os.environ.get("TONTECHNIK_REAPER_WEB", "http://127.0.0.1:8080")
# Standard ist ein maximiertes Fenster, Appleiste und Dock bleiben sichtbar.
VOLLBILD = os.environ.get("TONTECHNIK_VOLLBILD", "0") == "1"

# Die Streams selbst stehen in streams.toml (Namen, Skripte, Pegelquellen).
STREAMS = _pfad("TONTECHNIK_STREAMS", BASIS / "streams.toml")

PROTOKOLL = ZUSTAND / "studio.log"
LOG_REAPER = ZUSTAND / "reaper.log"
LOG_MITSCHNITT = ZUSTAND / "mitschnitt.log"

SKRIPT_MITSCHNITT = SKRIPTE / "mitschnitt_mp3.sh"

# Alle MP3-Mitschnitte an einem Ort, unabhaengig vom Projekt.
MITSCHNITTE = _pfad("TONTECHNIK_MITSCHNITTE", _musikordner() / "Mitschnitte")

# Quellen fuer die Pegelanzeigen. Gemessen wird nur mitgehoert, nie eingegriffen.
# REAPERs Ausgang, dauerhaft gemessen in der linken Haelfte.
PEGEL_REAPER = os.environ.get("TONTECHNIK_PEGEL_REAPER", "reaper_loopback")
PEGEL_MITSCHNITT = os.environ.get("TONTECHNIK_PEGEL_MITSCHNITT", "reaper_loopback")


def vorbereiten() -> None:
    """Legt die Verzeichnisse an, die beim Start vorhanden sein muessen."""
    ZUSTAND.mkdir(parents=True, exist_ok=True)
    AUFNAHMEN.mkdir(parents=True, exist_ok=True)
