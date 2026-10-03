"""REAPER-Ausgang: Pegel des ALSA-Loopbacks, aus dem alle Streams und der
Mitschnitt lesen.

Misst dauerhaft, solange die Quelle existiert. So ist schon vor jedem Start
zu sehen, ob aus REAPER Ton kommt. Die Pegel rechts messen dagegen nur, was
tatsaechlich hinausgeht.
"""

from __future__ import annotations

from .. import konfiguration as konf
from ..kern import audio, pegel
from .pegelanzeige import Pegelanzeige
from .widgets import Karte


class KarteAusgang(Karte):
    def __init__(self, master, anwendung):
        super().__init__(
            master, "REAPER-Ausgang", "Quelle fuer alle Streams und den Mitschnitt."
        )
        self.anwendung = anwendung
        self.messer = pegel.Pegelmesser("reaper", pegel.quelle_pulse(konf.PEGEL_REAPER))
        self.anzeige = Pegelanzeige(self.inhalt, "Summe", skala=True)
        self.anzeige.grid(row=0, column=0, sticky="ew")

    def pegel_zeichnen(self) -> None:
        if self.messer.aktiv:
            self.anzeige.setze(
                self.messer.db, self.messer.spitze, self.messer.verbunden, self.messer.hoechst
            )

    def aktualisieren(self) -> None:
        soll = audio.quelle_vorhanden(konf.PEGEL_REAPER)
        if soll and not self.messer.aktiv:
            self.messer.start()
        elif not soll and self.messer.aktiv:
            self.messer.stopp()
            self.anzeige.ruhe()

    def beenden(self) -> None:
        self.messer.stopp()
