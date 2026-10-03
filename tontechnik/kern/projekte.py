"""Projektordner nach festem Namensschema anlegen."""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path

from ..protokoll import logger

log = logger("projekte")

ANLAESSE = (
    "Gottesdienst",
    "Bibelstunde",
    "Jugendstunde",
    "Taufe",
    "Hochzeit",
    "Beerdigung",
    "Weihnachten",
    "Ostern",
    "Sonstiges",
)

_UMLAUTE = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}


def bereinige(text: str) -> str:
    for zeichen, ersatz in _UMLAUTE.items():
        text = text.replace(zeichen, ersatz)
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return text


def projektname(tag: date, anlass: str, zusatz: str = "") -> str:
    teile = [tag.strftime("%Y-%m-%d"), bereinige(anlass)]
    if zusatz.strip():
        teile.append(bereinige(zusatz))
    return "_".join(teil for teil in teile if teil)


def lege_an(tag: date, anlass: str, zusatz: str, basis: Path, vorlage: Path) -> Path:
    """Legt Ordner und Projektdatei an und gibt den Pfad der .RPP zurueck."""
    if not vorlage.is_file():
        raise FileNotFoundError(f"Projektvorlage fehlt: {vorlage}")

    name = projektname(tag, anlass, zusatz)
    ordner = basis / tag.strftime("%Y") / name
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "Mitschnitt").mkdir(exist_ok=True)

    projekt = ordner / f"{name}.RPP"
    if not projekt.exists():
        shutil.copy2(vorlage, projekt)
        log.info("Projekt angelegt: %s", name)
    else:
        log.info("Projekt bestand bereits: %s", name)
    return projekt
