"""Waagerechte Pegelanzeige im Stil einer LED-Kette.

Ein Segment je dB von -60 bis 0. Gruen bis -12, gelb bis -3, darueber rot.
Rechts daneben steht der hoechste Stand seit Beginn der Messung bzw. der
Uebertragung, nicht der aktuelle Wert - der ist an der LED-Kette abzulesen.
Unbeleuchtete Segmente bleiben in ihrer Zone schwach sichtbar, damit man die
Bereiche auch bei Stille erkennt. Das hellste Segment rechts ist die Spitze
der letzten Sekunden. Ohne Verbindung bleibt alles dunkel und die Beschriftung
sagt, warum.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..kern.pegel import STILLE_DB
from .stil import FARBEN

BALKEN = 24                   # Hoehe der LED-Kette
SKALA = 14                    # Hoehe der Skalenbeschriftung darunter
LUECKE = 2                    # Abstand zwischen Segmenten
SEGMENTE = int(-STILLE_DB)    # ein Segment je dB
MARKEN = (-60, -40, -30, -20, -12, -6, -3, 0)

GRUND = "#15191e"
# Zone: (leuchtet, dunkel)
ZONEN = {
    "gruen": ("#34c46a", "#1d3326"),
    "gelb": ("#f2c230", "#3a3320"),
    "rot": ("#ec4a35", "#3e2220"),
}


def _zone(db: float) -> str:
    if db > -3:
        return "rot"
    if db > -12:
        return "gelb"
    return "gruen"


class Pegelanzeige(ttk.Frame):
    def __init__(self, master, beschriftung: str, skala: bool = False):
        super().__init__(master, style="Karte.TFrame")
        self.columnconfigure(1, weight=1)
        self._skala = skala

        ttk.Label(self, text=beschriftung, style="Pegel.TLabel", width=9).grid(
            row=0, column=0, sticky="nw"
        )
        self._flaeche = tk.Canvas(
            self,
            height=BALKEN + (SKALA if skala else 0),
            highlightthickness=0,
            background=FARBEN["flaeche"],
        )
        self._flaeche.grid(row=0, column=1, sticky="ew", padx=10)
        self._wert = ttk.Label(self, text="--", style="PegelWert.TLabel", width=11, anchor="e")
        self._wert.grid(row=0, column=2, sticky="ne")

        self._db = STILLE_DB
        self._spitze = STILLE_DB
        self._hoechst = STILLE_DB
        self._verbunden = False
        self._segmente: list = []     # (Kennung, Zone, untere dB-Grenze)
        self._farben: list = []       # zuletzt gesetzte Fuellung je Segment
        self._flaeche.bind("<Configure>", lambda _e: self._aufbauen())

    def setze(self, db: float, spitze: float, verbunden: bool,
              hoechst: float = STILLE_DB) -> None:
        self._db, self._spitze, self._verbunden = db, spitze, verbunden
        self._hoechst = hoechst
        self._zeichnen()

    def _schrift(self):
        schriften = getattr(self.winfo_toplevel(), "schriften", None)
        return schriften["skala"] if schriften else None

    def _aufbauen(self) -> None:
        """Legt die Segmente einmal an. Danach wird nur noch umgefaerbt."""
        flaeche = self._flaeche
        flaeche.delete("all")
        breite = flaeche.winfo_width()
        self._segmente, self._farben = [], []
        if breite <= SEGMENTE * (LUECKE + 1):
            return

        flaeche.create_rectangle(0, 0, breite, BALKEN, fill=GRUND, outline="")
        schritt = (breite - 2) / SEGMENTE
        for i in range(SEGMENTE):
            unten = STILLE_DB + i
            x0 = 1 + i * schritt + LUECKE / 2
            x1 = 1 + (i + 1) * schritt - LUECKE / 2
            zone = _zone(unten + 0.5)
            kennung = flaeche.create_rectangle(
                x0, 4, x1, BALKEN - 4, fill=ZONEN[zone][1], outline=""
            )
            self._segmente.append((kennung, zone, unten))
            self._farben.append(ZONEN[zone][1])

        if self._skala:
            for marke in MARKEN:
                x = 1 + (marke - STILLE_DB) * schritt
                anker = "nw" if marke == MARKEN[0] else "ne" if marke == 0 else "n"
                flaeche.create_text(
                    x, BALKEN + 1, text=str(marke), anchor=anker,
                    fill=FARBEN["gedaempft"], font=self._schrift(),
                )
        self._zeichnen()

    def _zeichnen(self) -> None:
        if self._verbunden:
            # Bei Stille keine Spitzenmarke, sonst leuchtet links ein Segment.
            spitze = int(self._spitze - STILLE_DB) if self._spitze > STILLE_DB + 0.5 else -1
            for i, (kennung, zone, unten) in enumerate(self._segmente):
                an = unten < self._db or i == spitze
                self._faerben(i, kennung, ZONEN[zone][0 if an else 1])
            self._wert.configure(
                text="still" if self._hoechst <= STILLE_DB + 0.5
                else f"max {self._hoechst:.0f} dB"
            )
        else:
            for i, (kennung, zone, _unten) in enumerate(self._segmente):
                self._faerben(i, kennung, ZONEN[zone][1])
            self._wert.configure(text="kein Signal")

    def _faerben(self, i: int, kennung, farbe: str) -> None:
        if self._farben[i] != farbe:
            self._flaeche.itemconfigure(kennung, fill=farbe)
            self._farben[i] = farbe
