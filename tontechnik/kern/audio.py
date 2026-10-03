"""Pruefungen der PipeWire- bzw. PulseAudio-Umgebung."""

from __future__ import annotations

import subprocess
import time

from ..protokoll import logger

log = logger("audio")


_ZWISCHENSPEICHER: dict = {}
_HALTBAR = 3.0


def _kurzliste(art: str) -> list:
    stand = _ZWISCHENSPEICHER.get(art)
    if stand and time.monotonic() - stand[0] < _HALTBAR:
        return stand[1]
    try:
        ergebnis = subprocess.run(
            ["pactl", "list", "short", art], capture_output=True, text=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as fehler:
        log.warning("pactl nicht verfuegbar: %s", fehler)
        return []
    if ergebnis.returncode != 0:
        return []
    namen = [
        zeile.split("\t")[1]
        for zeile in ergebnis.stdout.splitlines()
        if len(zeile.split("\t")) > 1
    ]
    _ZWISCHENSPEICHER[art] = (time.monotonic(), namen)
    return namen


def quelle_vorhanden(name: str) -> bool:
    """Ein Null-Sink heisst bei den Quellen "<name>.monitor" - beides zaehlt."""
    quellen = _kurzliste("sources")
    if name in quellen or f"{name}.monitor" in quellen:
        return True
    return name in _kurzliste("sinks")


def pruefe(namen: dict) -> list:
    """Erwartet {Anzeigename: Quellenname} und meldet den Zustand je Eintrag."""
    vorhandene = set(_kurzliste("sources"))
    return [(anzeige, quelle in vorhandene) for anzeige, quelle in namen.items()]