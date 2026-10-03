"""REAPER im Hintergrund starten und Laufzustand pruefen."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .. import konfiguration as konf
from ..protokoll import logger

log = logger("reaper")


def laeuft() -> bool:
    try:
        ergebnis = subprocess.run(
            ["pgrep", "-x", "reaper"], capture_output=True, text=True, timeout=3
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return ergebnis.returncode == 0


def starte(projekt: Path) -> None:
    """Startet REAPER abgekoppelt, damit die Oberflaeche bedienbar bleibt.

    Der Prozess laeuft in einer eigenen Sitzung weiter, auch wenn Tontechnik
    Studio beendet wird. Die Ausgabe landet im REAPER-Protokoll.
    """
    konf.LOG_REAPER.parent.mkdir(parents=True, exist_ok=True)
    with konf.LOG_REAPER.open("ab", buffering=0) as datei:
        subprocess.Popen(
            [konf.REAPER_BEFEHL, "-nosplash", str(projekt)],
            stdin=subprocess.DEVNULL,
            stdout=datei,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    log.info("REAPER gestartet mit %s", projekt.name)
