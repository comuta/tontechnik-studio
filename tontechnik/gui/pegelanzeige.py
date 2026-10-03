"""Waagerechte Pegelanzeige mit Spitzenmarke.

Die Skala reicht von -60 dB bis 0 dB. Gruen bis -12, gelb bis -3, darueber rot.
Ohne Verbindung bleibt der Balken leer und die Beschriftung sagt, warum.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..kern.pegel import STILLE_DB
from .stil import FARBEN

HOEHE = 12
MARKEN = (-40, -20, -12, -6)


def _farbe(db: float) -> str:
    if db >= -3:
        return FARBEN["sendung"]
    if db >= -12:
        return "#c8912b"
    return FARBEN["bereit"]


class Pegelanzeige(ttk.Frame):
    def __init__(self, master, beschriftung: str):
        super().__init__(master, style="Karte.TFrame")
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text=beschriftung, style="KarteKlein.TLabel", width=11).grid(
            row=0, column=0, sticky="w"
        )
        self._flaeche = tk.Canvas(
            self,
            height=HOEHE,
            highlightthickness=0,
            background=FARBEN["flaeche"],
        )
        self._flaeche.grid(row=0, column=1, sticky="ew", padx=8)
        self._wert = ttk.Label(self, text="--", style="KarteKlein.TLabel", width=8, anchor="e")
        self._wert.grid(row=0, column=2, sticky="e")

        self._db = STILLE_DB
        self._spitze = STILLE_DB
        self._verbunden = False
        self._flaeche.bind("<Configure>", lambda _e: self._zeichnen())

    def setze(self, db: float, spitze: float, verbunden: bool) -> None:
        self._db, self._spitze, self._verbunden = db, spitze, verbunden
        self._zeichnen()

    def _anteil(self, db: float) -> float:
        return max(0.0, min(1.0, (db - STILLE_DB) / (0 - STILLE_DB)))

    def _zeichnen(self) -> None:
        flaeche = self._flaeche
        flaeche.delete("all")
        breite = flaeche.winfo_width()
        if breite <= 1:
            return

        flaeche.create_rectangle(0, 0, breite, HOEHE, fill="#e4e7eb", outline="")
        for marke in MARKEN:
            x = breite * self._anteil(marke)
            flaeche.create_line(x, 0, x, HOEHE, fill="#ffffff")

        if not self._verbunden:
            self._wert.configure(text="kein Signal")
            return

        balken = breite * self._anteil(self._db)
        if balken > 1:
            flaeche.create_rectangle(0, 0, balken, HOEHE, fill=_farbe(self._db), outline="")
        x = breite * self._anteil(self._spitze)
        flaeche.create_line(x, 0, x, HOEHE, fill=FARBEN["text"], width=2)
        self._wert.configure(
            text="still" if self._db <= STILLE_DB + 0.5 else f"{self._db:.0f} dB"
        )
