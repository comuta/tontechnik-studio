"""Mitschnittkarte: separate MP3-Aufnahme der Summe, unabhaengig von REAPER.

Alle Mitschnitte landen zentral in konf.MITSCHNITTE (~/Musik/Mitschnitte).
"""

from __future__ import annotations

import time
from tkinter import ttk

from .. import konfiguration as konf
from ..kern import pegel
from ..kern.ausgabe import letzte_zeile
from ..protokoll import logger
from .karte_aufnahme import dauer
from .pegelanzeige import Pegelanzeige
from .widgets import Karte, Lampe

log = logger("ansicht.mitschnitt")

SCHLUESSEL = "mitschnitt"


class KarteMitschnitt(Karte):
    def __init__(self, master, anwendung):
        super().__init__(master, "MP3-Mitschnitt")
        self.anwendung = anwendung
        self._beginn: float | None = None

        self.uhr = ttk.Label(self.kopf_rechts, text="00:00:00", style="Uhr.TLabel")
        self.uhr.pack(side="right")
        self.lampe = Lampe(self.kopf_rechts, "gestoppt", stil_rahmen="Karte.TFrame")
        self.lampe.pack(side="right", padx=(0, 18))

        # Misst nur waehrend des Mitschnitts. REAPERs Ausgang zeigt die linke Haelfte.
        self.messer = pegel.Pegelmesser("mitschnitt", pegel.quelle_pulse(konf.PEGEL_MITSCHNITT))
        self.anzeige = Pegelanzeige(self.inhalt, "Aufnahme", skala=True)
        self.anzeige.grid(row=0, column=0, sticky="ew")

        self.ziel = ttk.Label(self.inhalt, text="", style="KarteKlein.TLabel", anchor="w")
        self.ziel.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.knopf = ttk.Button(
            self.inhalt, text="Mitschnitt starten", style="Aktion.TButton",
            command=self.umschalten,
        )
        self.knopf.grid(row=2, column=0, sticky="ew", pady=(10, 0))

    def umschalten(self) -> None:
        umgebung = {"TONTECHNIK_MITSCHNITT": str(konf.MITSCHNITTE)}
        try:
            self.anwendung.verwaltung.umschalten(SCHLUESSEL, umgebung)
        except OSError as fehler:
            log.warning("%s: %s", SCHLUESSEL, fehler)
            self.anwendung.melde(str(fehler), fehler=True)
            return
        self.anwendung.aktualisieren()

    def pegel_zeichnen(self) -> None:
        if self.messer.aktiv:
            self.anzeige.setze(
                self.messer.db, self.messer.spitze, self.messer.verbunden, self.messer.hoechst
            )

    def beenden(self) -> None:
        self.messer.stopp()

    def aktualisieren(self) -> None:
        laeuft = self.anwendung.verwaltung.laeuft(SCHLUESSEL)
        if laeuft and not self.messer.aktiv:
            self.messer.start()
        elif not laeuft and self.messer.aktiv:
            self.messer.stopp()
            self.anzeige.ruhe()
        if laeuft and self._beginn is None:
            self._beginn = time.monotonic()
        if not laeuft:
            self._beginn = None

        self.lampe.setze(laeuft)
        self.lampe.beschrifte("nimmt auf" if laeuft else "gestoppt")
        self.uhr.configure(
            text=dauer(time.monotonic() - self._beginn) if self._beginn else "00:00:00"
        )
        if laeuft:
            text = letzte_zeile(konf.LOG_MITSCHNITT)
        else:
            ordner = konf.MITSCHNITTE
            try:
                ordner = "~/" + str(ordner.relative_to(konf.HEIM))
            except ValueError:
                pass
            text = f"Ziel: {ordner}"
        self.ziel.configure(text=text[:110])
        self.knopf.configure(
            text="Mitschnitt beenden" if laeuft else "Mitschnitt starten",
            style="Stopp.TButton" if laeuft else "Aktion.TButton",
        )
