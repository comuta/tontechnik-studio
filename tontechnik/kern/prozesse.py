"""Start und Stopp der externen Dienste.

Jeder Dienst ist ein Bash-Skript, das im Vordergrund laeuft und sich per
SIGTERM sauber beendet. Gestartet wird es in einer eigenen Prozessgruppe,
damit auch Kindprozesse wie ffmpeg oder baresip mit beendet werden.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..protokoll import logger

log = logger("prozesse")


@dataclass(frozen=True)
class Dienst:
    schluessel: str
    titel: str
    skript: Path
    protokoll: Path
    umgebung: dict = field(default_factory=dict)


class Dienstverwaltung:
    """Haelt fuer jeden Dienst hoechstens einen laufenden Prozess."""

    def __init__(self) -> None:
        self._dienste: dict[str, Dienst] = {}
        self._prozesse: dict[str, subprocess.Popen] = {}

    def registriere(self, dienst: Dienst) -> None:
        self._dienste[dienst.schluessel] = dienst

    def dienst(self, schluessel: str) -> Dienst:
        return self._dienste[schluessel]

    def schluessel(self) -> list:
        return list(self._dienste)

    def laeuft(self, schluessel: str) -> bool:
        prozess = self._prozesse.get(schluessel)
        if prozess is None:
            return False
        if prozess.poll() is None:
            return True
        self._prozesse.pop(schluessel, None)
        log.info("%s wurde beendet (Rueckgabewert %s)", schluessel, prozess.returncode)
        return False

    def start(self, schluessel: str) -> None:
        if self.laeuft(schluessel):
            return
        dienst = self._dienste[schluessel]
        if not dienst.skript.is_file():
            raise FileNotFoundError(f"Skript fehlt: {dienst.skript}")

        dienst.protokoll.parent.mkdir(parents=True, exist_ok=True)
        with dienst.protokoll.open("ab", buffering=0) as datei:
            kopf = f"\n=== {dienst.titel} gestartet {datetime.now():%d.%m.%Y %H:%M:%S} ===\n"
            datei.write(kopf.encode("utf-8"))
            self._prozesse[schluessel] = subprocess.Popen(
                ["bash", str(dienst.skript)],
                stdin=subprocess.DEVNULL,
                stdout=datei,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, **dienst.umgebung},
                close_fds=True,
            )
        log.info("%s gestartet", dienst.titel)

    def stopp(self, schluessel: str, frist: float = 6.0) -> None:
        prozess = self._prozesse.get(schluessel)
        if prozess is None:
            return
        if prozess.poll() is not None:
            self._prozesse.pop(schluessel, None)
            return

        self._signal(prozess, signal.SIGTERM)
        ende = time.monotonic() + frist
        while time.monotonic() < ende:
            if prozess.poll() is not None:
                break
            time.sleep(0.1)
        else:
            log.warning("%s reagiert nicht, erzwinge Ende", schluessel)
            self._signal(prozess, signal.SIGKILL)
            try:
                prozess.wait(timeout=2)
            except subprocess.TimeoutExpired:
                log.error("%s liess sich nicht beenden", schluessel)

        self._prozesse.pop(schluessel, None)
        log.info("%s beendet", self._dienste[schluessel].titel)

    def umschalten(self, schluessel: str) -> bool:
        """Startet oder stoppt den Dienst. Gibt den neuen Zustand zurueck."""
        if self.laeuft(schluessel):
            self.stopp(schluessel)
            return False
        self.start(schluessel)
        return True

    def alle_stoppen(self) -> None:
        for schluessel in list(self._prozesse):
            self.stopp(schluessel)

    @staticmethod
    def _signal(prozess: subprocess.Popen, zeichen: int) -> None:
        try:
            os.killpg(os.getpgid(prozess.pid), zeichen)
        except (ProcessLookupError, PermissionError):
            try:
                prozess.send_signal(zeichen)
            except ProcessLookupError:
                pass
