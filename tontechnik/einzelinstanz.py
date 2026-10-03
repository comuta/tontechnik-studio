"""Nur ein Fenster: ein zweiter Start holt das bestehende nach vorn.

Benutzt einen Unix-Socket im abstrakten Namensraum. Der belegt keinen Platz
im Dateisystem und wird vom Kernel freigegeben, sobald der Prozess endet -
eine verwaiste Sperrdatei nach einem Absturz kann es also nicht geben.
"""

from __future__ import annotations

import hashlib
import os
import socket
import threading
from pathlib import Path


def name_fuer(ordner: Path) -> str:
    """Eigener Name je Installationsordner.

    So sperren sich zwei Kopien - etwa eine laufende und eine neue zum Testen -
    nicht gegenseitig aus. Innerhalb eines Ordners bleibt es bei einem Fenster.
    """
    kennung = hashlib.sha1(str(ordner.resolve()).encode()).hexdigest()[:12]
    return f"\0tontechnik-studio-{kennung}"


def abgeschaltet() -> bool:
    return os.environ.get("TONTECHNIK_EINZELINSTANZ", "1") == "0"


def belegen(name: str) -> socket.socket | None:
    """Belegt den Namen. None bedeutet: es laeuft bereits eine Instanz."""
    if abgeschaltet():
        return None
    horcher = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        horcher.bind(name)
    except OSError:
        horcher.close()
        return None
    horcher.listen(1)
    return horcher


def wecken(name: str) -> bool:
    """Bittet die laufende Instanz, ihr Fenster zu zeigen."""
    if abgeschaltet():
        return False
    verbindung = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        verbindung.connect(name)
        verbindung.sendall(b"zeigen")
        return True
    except OSError:
        return False
    finally:
        verbindung.close()


def lauschen(horcher: socket.socket, signal: threading.Event) -> threading.Thread:
    """Startet einen Hintergrundfaden, der Weckrufe entgegennimmt."""

    def schleife() -> None:
        while True:
            try:
                verbindung, _ = horcher.accept()
            except OSError:
                return
            with verbindung:
                try:
                    verbindung.recv(16)
                except OSError:
                    pass
            signal.set()

    faden = threading.Thread(target=schleife, daemon=True)
    faden.start()
    return faden