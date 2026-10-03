"""Pegelmessung ueber ffmpeg.

ffmpeg liefert rohe 16-Bit-Abtastwerte auf die Standardausgabe, der Effektivwert
wird hier gerechnet. Das ist stabiler als Logzeilen von astats zu lesen und
kostet bei 8 kHz mono kaum Rechenzeit.

Gemessen wird, was ohnehin schon laeuft: eine PulseAudio-Quelle oder ein
Netzwerkstream. Die Uebertragung selbst wird dabei nicht angefasst.
"""

from __future__ import annotations

import array
import math
import subprocess
import threading
import time

from ..protokoll import logger

log = logger("pegel")

ABTASTRATE = 8000
BLOCK = ABTASTRATE // 5          # 200 ms
STILLE_DB = -60.0
SPITZE_FALL_DB = 3.0             # Rueckgang der Spitzenanzeige je Block
NEUSTART_WARTEN = 3.0


def quelle_pulse(name: str) -> list:
    return ["-f", "pulse", "-i", name]


def quelle_netz(adresse: str) -> list:
    return [
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", adresse,
    ]


def _dezibel(werte: array.array) -> float:
    if not werte:
        return STILLE_DB
    summe = sum(wert * wert for wert in werte)
    effektiv = math.sqrt(summe / len(werte)) / 32768.0
    if effektiv <= 0:
        return STILLE_DB
    return max(STILLE_DB, 20.0 * math.log10(effektiv))


class Pegelmesser:
    """Misst dauerhaft eine Quelle, bis sie gestoppt wird."""

    def __init__(self, name: str, eingabe: list):
        self.name = name
        self._eingabe = eingabe
        self._faden: threading.Thread | None = None
        self._laeuft = False
        self._prozess: subprocess.Popen | None = None
        self.db = STILLE_DB
        self.spitze = STILLE_DB
        self.hoechst = STILLE_DB     # hoechster Stand seit Start bzw. neu_beginnen()
        self.verbunden = False

    @property
    def aktiv(self) -> bool:
        return self._laeuft

    def start(self) -> None:
        if self._laeuft:
            return
        self._laeuft = True
        self.hoechst = STILLE_DB
        self._faden = threading.Thread(target=self._schleife, daemon=True)
        self._faden.start()

    def stopp(self) -> None:
        self._laeuft = False
        self._prozess_beenden()
        self.db = STILLE_DB
        self.spitze = STILLE_DB
        self.hoechst = STILLE_DB
        self.verbunden = False

    def neu_beginnen(self) -> None:
        """Hoechststand zuruecksetzen, etwa wenn eine Uebertragung beginnt."""
        self.hoechst = STILLE_DB

    def _prozess_beenden(self) -> None:
        prozess, self._prozess = self._prozess, None
        if prozess and prozess.poll() is None:
            prozess.terminate()
            try:
                prozess.wait(timeout=2)
            except subprocess.TimeoutExpired:
                prozess.kill()

    def _schleife(self) -> None:
        while self._laeuft:
            befehl = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                *self._eingabe,
                "-ac", "1", "-ar", str(ABTASTRATE), "-f", "s16le", "-",
            ]
            try:
                self._prozess = subprocess.Popen(
                    befehl, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                )
            except OSError as fehler:
                log.warning("%s: ffmpeg nicht startbar (%s)", self.name, fehler)
                self.verbunden = False
                time.sleep(NEUSTART_WARTEN)
                continue

            self.verbunden = True
            self._lesen(self._prozess)
            self.verbunden = False
            self.db = STILLE_DB
            self.spitze = STILLE_DB
            if self._laeuft:
                time.sleep(NEUSTART_WARTEN)

    def _lesen(self, prozess: subprocess.Popen) -> None:
        bytes_je_block = BLOCK * 2
        while self._laeuft:
            rohdaten = prozess.stdout.read(bytes_je_block)
            if not rohdaten or len(rohdaten) < bytes_je_block:
                return
            werte = array.array("h")
            werte.frombytes(rohdaten)
            self.db = _dezibel(werte)
            self.spitze = max(self.db, self.spitze - SPITZE_FALL_DB)
            self.hoechst = max(self.hoechst, self.db)
