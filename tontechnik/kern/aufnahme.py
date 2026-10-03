"""Aufnahmesteuerung ueber das Webinterface von REAPER.

REAPER bringt eine eingebaute Fernsteuerung mit (Einstellungen ->
Control/OSC/web -> "Web browser interface"). Ueber sie laesst sich jede
Aktion per HTTP ausloesen und der Transportzustand abfragen. Das kommt ohne
zusaetzliche Bibliothek aus und funktioniert auch, wenn REAPER nicht von
dieser Oberflaeche gestartet wurde.
"""

from __future__ import annotations

import urllib.error
import urllib.request

from .. import konfiguration as konf
from ..protokoll import logger

log = logger("aufnahme")

AKTION_AUFNAHME = "1013"   # Transport: Record
AKTION_STOPP = "1016"      # Transport: Stop

# Zustaende laut REAPER: 0 gestoppt, 1 Wiedergabe, 2 Pause,
# 5 Aufnahme, 6 Aufnahme pausiert.
_AUFNAHME_ZUSTAENDE = {5, 6}


def _abrufen(pfad: str, frist: float = 1.0):
    adresse = f"{konf.REAPER_WEB.rstrip('/')}/_/{pfad}"
    try:
        with urllib.request.urlopen(adresse, timeout=frist) as antwort:
            return antwort.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return None


def transport() -> dict | None:
    """Liefert den Transportzustand oder None, wenn REAPER nicht antwortet."""
    text = _abrufen("TRANSPORT")
    if not text:
        return None
    for zeile in text.splitlines():
        felder = zeile.split("\t")
        if felder[0] != "TRANSPORT" or len(felder) < 3:
            continue
        try:
            zustand = int(felder[1])
            position = float(felder[2])
        except ValueError:
            return None
        return {
            "zustand": zustand,
            "position": position,
            "nimmt_auf": zustand in _AUFNAHME_ZUSTAENDE,
        }
    return None


def erreichbar() -> bool:
    return transport() is not None


def starten() -> bool:
    if _abrufen(AKTION_AUFNAHME) is None:
        log.warning("Aufnahme liess sich nicht starten")
        return False
    log.info("Aufnahme gestartet")
    return True


def stoppen() -> bool:
    if _abrufen(AKTION_STOPP) is None:
        log.warning("Aufnahme liess sich nicht stoppen")
        return False
    log.info("Aufnahme gestoppt")
    return True
