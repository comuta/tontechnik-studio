"""Zentrale Pfade und Konstanten.

Jeder Pfad laesst sich ueber eine Umgebungsvariable ueberschreiben, damit
Tests und ein zweiter Rechner ohne Codeaenderung laufen.
"""

from __future__ import annotations

import os
from pathlib import Path

HEIM = Path.home()
BASIS = Path(__file__).resolve().parent.parent
SKRIPTE = BASIS / "skripte"


def _pfad(variable: str, standard: Path) -> Path:
    wert = os.environ.get(variable)
    return Path(wert).expanduser() if wert else standard


RESSOURCEN = BASIS / "ressourcen"
ICON = RESSOURCEN / "tontechnik-studio.png"

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

PROTOKOLL = ZUSTAND / "studio.log"
LOG_TELEFON = ZUSTAND / "telefon.log"
LOG_RADIO = ZUSTAND / "radio.log"
LOG_REAPER = ZUSTAND / "reaper.log"
LOG_MITHOEREN = ZUSTAND / "mithoeren.log"
LOG_MITSCHNITT = ZUSTAND / "mitschnitt.log"

SKRIPT_TELEFON = SKRIPTE / "stream_telefon.sh"
SKRIPT_RADIO = SKRIPTE / "stream_radio.sh"
SKRIPT_MITHOEREN = SKRIPTE / "mithoeren_telefon.sh"
SKRIPT_MITSCHNITT = SKRIPTE / "mitschnitt_mp3.sh"

# Ziel des MP3-Mitschnitts, solange in dieser Sitzung kein Projekt angelegt wurde.
MITSCHNITTE = AUFNAHMEN / "Mitschnitte"

# Quellen fuer die Pegelanzeigen. Gemessen wird nur mitgehoert, nie eingegriffen.
# REAPERs Ausgang, dauerhaft gemessen in der linken Haelfte.
PEGEL_REAPER = os.environ.get("TONTECHNIK_PEGEL_REAPER", "reaper_loopback")
PEGEL_TELEFON_AUS = os.environ.get("TONTECHNIK_PEGEL_TELEFON_AUS", "TelefonBruecke.monitor")
PEGEL_TELEFON_EIN = os.environ.get("TONTECHNIK_PEGEL_TELEFON_EIN", "Mithoeren.monitor")
PEGEL_RADIO_AUS = os.environ.get("TONTECHNIK_PEGEL_RADIO_AUS", "reaper_loopback")
PEGEL_MITSCHNITT = os.environ.get("TONTECHNIK_PEGEL_MITSCHNITT", "reaper_loopback")
RADIO_STREAM = os.environ.get(
    "TONTECHNIK_RADIO_STREAM", "http://segenswelle.de:8000/ECBG-Gelsenkirchen"
)

PROTOKOLLE = {
    "studio": ("Studio", PROTOKOLL),
    "telefon": ("Telefon", LOG_TELEFON),
    "radio": ("Radio", LOG_RADIO),
    "mithoeren": ("Mithoeren", LOG_MITHOEREN),
    "mitschnitt": ("Mitschnitt", LOG_MITSCHNITT),
    "reaper": ("REAPER", LOG_REAPER),
}


def vorbereiten() -> None:
    """Legt die Verzeichnisse an, die beim Start vorhanden sein muessen."""
    ZUSTAND.mkdir(parents=True, exist_ok=True)
    AUFNAHMEN.mkdir(parents=True, exist_ok=True)
