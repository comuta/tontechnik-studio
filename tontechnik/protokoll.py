"""Protokollierung in Datei und auf die Konsole."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from . import konfiguration as konf

_FORMAT = "%(asctime)s  %(levelname)-7s  %(name)-18s  %(message)s"
_ZEIT = "%Y-%m-%d %H:%M:%S"


def einrichten(stufe: int = logging.INFO) -> logging.Logger:
    konf.vorbereiten()
    wurzel = logging.getLogger("tontechnik")
    if wurzel.handlers:
        return wurzel

    wurzel.setLevel(stufe)
    formatierer = logging.Formatter(_FORMAT, _ZEIT)

    datei = RotatingFileHandler(
        konf.PROTOKOLL, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    datei.setFormatter(formatierer)
    wurzel.addHandler(datei)

    konsole = logging.StreamHandler()
    konsole.setFormatter(formatierer)
    wurzel.addHandler(konsole)
    return wurzel


def logger(name: str) -> logging.Logger:
    return logging.getLogger(f"tontechnik.{name}")
