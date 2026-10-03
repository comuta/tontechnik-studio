"""Letzte Zeile einer Protokolldatei lesen, ohne sie ganz einzulesen."""

from __future__ import annotations

from pathlib import Path

PUFFER = 4096


def letzte_zeile(pfad: Path) -> str:
    try:
        groesse = pfad.stat().st_size
        with pfad.open("rb") as datei:
            datei.seek(max(0, groesse - PUFFER))
            zeilen = datei.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for zeile in reversed(zeilen):
        text = zeile.strip()
        if text and not text.startswith("==="):
            return text
    return ""
