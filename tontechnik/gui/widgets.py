"""Wiederverwendbare Bausteine der Oberflaeche."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .stil import FARBEN


class Lampe(ttk.Frame):
    """Punkt mit Beschriftung. Zeigt den Zustand eines Dienstes.

    gross=True fuer die Kopfzeile: groesserer Punkt und kraeftigere Schrift,
    damit der Zustand auch aus einigen Metern Abstand erkennbar ist.
    """

    def __init__(self, master, text: str, stil_rahmen: str = "Kopf.TFrame",
                 gross: bool = False, **kw):
        super().__init__(master, style=stil_rahmen, **kw)
        hell = {"Kopf.TFrame", "Karte.TFrame"}
        hintergrund = FARBEN["flaeche"] if stil_rahmen in hell else FARBEN["grund"]
        durchmesser = 18 if gross else 12
        self._punkt = tk.Canvas(
            self,
            width=durchmesser,
            height=durchmesser,
            highlightthickness=0,
            background=hintergrund,
        )
        self._kreis = self._punkt.create_oval(
            2, 2, durchmesser - 1, durchmesser - 1, fill=FARBEN["aus"], outline=""
        )
        self._punkt.pack(side="left", padx=(0, 8 if gross else 6))
        if gross:
            stil_text = "LampeGross.TLabel"
        else:
            stil_text = "KarteKlein.TLabel" if stil_rahmen in hell else "Gedaempft.TLabel"
        self._text = ttk.Label(self, text=text, style=stil_text)
        self._text.pack(side="left")

    def beschrifte(self, text: str) -> None:
        self._text.configure(text=text)

    def setze(self, aktiv: bool, farbe: str = "sendung") -> None:
        self._punkt.itemconfigure(
            self._kreis, fill=FARBEN[farbe] if aktiv else FARBEN["aus"]
        )


class Karte(ttk.Frame):
    """Weisse Flaeche mit Titel und Platz fuer Inhalt.

    kopf_rechts liegt in der Titelzeile rechts, etwa fuer Lampe und Uhr.
    """

    def __init__(self, master, titel: str, untertitel: str = "", **kw):
        super().__init__(master, style="Karte.TFrame", padding=(18, 14), **kw)
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=titel, style="Abschnitt.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.kopf_rechts = ttk.Frame(self, style="Karte.TFrame")
        self.kopf_rechts.grid(row=0, column=1, sticky="e")
        if untertitel:
            ttk.Label(self, text=untertitel, style="KarteKlein.TLabel").grid(
                row=1, column=0, columnspan=2, sticky="w", pady=(2, 0)
            )
        self.inhalt = ttk.Frame(self, style="Karte.TFrame")
        self.inhalt.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.inhalt.columnconfigure(0, weight=1)


def trennlinie(master, **kw) -> tk.Frame:
    linie = tk.Frame(master, height=1, background=FARBEN["linie"])
    linie.pack(fill="x", **kw)
    return linie
