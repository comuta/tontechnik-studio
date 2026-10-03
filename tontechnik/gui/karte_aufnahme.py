"""Aufnahmekarte: startet und stoppt die Aufnahme in REAPER.

Sichtbar ist sie immer, bedienbar erst, wenn REAPER laeuft und sein
Webinterface antwortet. So erklaert die Karte selbst, was noch fehlt.
"""

from __future__ import annotations

import time
from tkinter import ttk

from ..kern import aufnahme, reaper
from .widgets import Karte, Lampe


def dauer(sekunden: float) -> str:
    sekunden = int(sekunden)
    return f"{sekunden // 3600:02d}:{sekunden % 3600 // 60:02d}:{sekunden % 60:02d}"


class KarteAufnahme(Karte):
    def __init__(self, master, anwendung):
        super().__init__(master, "Aufnahme", "Steuert den Transport in REAPER.")
        self.anwendung = anwendung
        self._beginn: float | None = None
        self._bereit = False
        self._nimmt_auf = False

        self.uhr = ttk.Label(self.kopf_rechts, text="00:00:00", style="Uhr.TLabel")
        self.uhr.pack(side="right")
        self.lampe = Lampe(self.kopf_rechts, "gestoppt", stil_rahmen="Karte.TFrame")
        self.lampe.pack(side="right", padx=(0, 18))

        self.hinweis = ttk.Label(self.inhalt, text="", style="KarteKlein.TLabel")
        self.hinweis.grid(row=1, column=0, sticky="w")

        self.knopf = ttk.Button(
            self.inhalt,
            text="Aufnahme starten",
            style="Aktion.TButton",
            command=self.umschalten,
        )
        self.knopf.grid(row=2, column=0, sticky="ew", pady=(12, 0))

    def umschalten(self) -> None:
        erfolg = aufnahme.stoppen() if self._nimmt_auf else aufnahme.starten()
        if not erfolg:
            self.hinweis.configure(
                text="REAPER hat nicht geantwortet.", style="KarteFehler.TLabel"
            )
            return
        self.anwendung.aktualisieren()

    def aktualisieren(self) -> None:
        zustand = self.anwendung.transport
        self._bereit = zustand is not None
        self._nimmt_auf = bool(zustand and zustand["nimmt_auf"])

        if self._nimmt_auf and self._beginn is None:
            self._beginn = time.monotonic()
        if not self._nimmt_auf:
            self._beginn = None

        self.lampe.setze(self._nimmt_auf)
        self.lampe.beschrifte("Aufnahme" if self._nimmt_auf else "gestoppt")
        self.uhr.configure(
            text=dauer(time.monotonic() - self._beginn) if self._beginn else "00:00:00"
        )

        if self._bereit:
            self.hinweis.configure(text="", style="KarteKlein.TLabel")
        elif reaper.laeuft():
            self.hinweis.configure(
                text="Webinterface antwortet nicht. In REAPER unter Einstellungen -> "
                "Control/OSC/web die Weboberflaeche aktivieren.",
                style="KarteFehler.TLabel",
            )
        else:
            self.hinweis.configure(
                text="REAPER laeuft noch nicht.", style="KarteKlein.TLabel"
            )

        self.knopf.configure(
            text="Aufnahme beenden" if self._nimmt_auf else "Aufnahme starten",
            style="Stopp.TButton" if self._nimmt_auf else "Aktion.TButton",
        )
        self.knopf.state(["!disabled"] if self._bereit else ["disabled"])
