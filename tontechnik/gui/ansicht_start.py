"""Linke Haelfte: Projekt anlegen, REAPER starten, Aufnahme steuern und
REAPERs Ausgang beobachten.

Die Aktionsleiste liegt fest am unteren Rand.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

from .. import konfiguration as konf
from ..kern import projekte, reaper
from ..protokoll import logger
from .karte_aufnahme import KarteAufnahme
from .karte_ausgang import KarteAusgang
from .widgets import Karte

log = logger("ansicht.start")


class AnsichtStart(ttk.Frame):
    def __init__(self, master, anwendung):
        super().__init__(master, style="TFrame")
        self.anwendung = anwendung

        # Rueckmeldung ueber dem Knopf, damit der Knopf auf einer Hoehe mit
        # "Alle Streams beenden" in der rechten Haelfte liegt.
        leiste = ttk.Frame(self, style="TFrame")
        leiste.pack(side="bottom", fill="x", pady=(12, 0))
        self.rueckmeldung = ttk.Label(leiste, text="Bereit.", style="Gedaempft.TLabel")
        self.rueckmeldung.pack(anchor="w", pady=(0, 8))
        self.knopf = ttk.Button(
            leiste,
            text="Projekt anlegen und REAPER starten",
            style="Aktion.TButton",
            command=self.anlegen,
        )
        self.knopf.pack(fill="x")

        karte = Karte(self, "Projekt", "Datum und Anlass bestimmen den Ordnernamen.")
        karte.pack(fill="x")
        formular = karte.inhalt
        formular.columnconfigure(1, weight=1)

        ttk.Label(formular, text="Datum", style="KarteText.TLabel").grid(
            row=0, column=0, sticky="w", pady=6, padx=(0, 12)
        )
        self.datum = ttk.Entry(formular)
        self.datum.insert(0, date.today().strftime("%d.%m.%Y"))
        self.datum.grid(row=0, column=1, sticky="ew", pady=6)

        ttk.Label(formular, text="Anlass", style="KarteText.TLabel").grid(
            row=1, column=0, sticky="w", pady=6, padx=(0, 12)
        )
        self.anlass = ttk.Combobox(
            formular, values=list(projekte.ANLAESSE), state="readonly"
        )
        self.anlass.current(0)
        self.anlass.grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(formular, text="Zusatz", style="KarteText.TLabel").grid(
            row=2, column=0, sticky="w", pady=6, padx=(0, 12)
        )
        self.zusatz = ttk.Entry(formular)
        self.zusatz.grid(row=2, column=1, sticky="ew", pady=6)
        ttk.Label(
            formular,
            text="Optional, zum Beispiel ein Name oder eine Uhrzeit.",
            style="KarteKlein.TLabel",
        ).grid(row=3, column=1, sticky="w")

        self.mit_reaper = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            formular,
            text="REAPER anschliessend starten",
            variable=self.mit_reaper,
            command=self.aktualisieren,
        ).grid(row=4, column=1, sticky="w", pady=(12, 0))

        self.aufnahme = KarteAufnahme(self, self.anwendung)
        self.aufnahme.pack(fill="x", pady=(12, 0))

        self.ausgang = KarteAusgang(self, self.anwendung)
        self.ausgang.pack(fill="x", pady=(12, 0))

    def pegel_zeichnen(self) -> None:
        self.ausgang.pegel_zeichnen()

    def beenden(self) -> None:
        self.ausgang.beenden()

    def aktualisieren(self) -> None:
        self.aufnahme.aktualisieren()
        self.ausgang.aktualisieren()
        self.knopf.configure(
            text="Projekt anlegen und REAPER starten"
            if self.mit_reaper.get()
            else "Projekt anlegen"
        )

    def anlegen(self) -> None:
        try:
            tag = datetime.strptime(self.datum.get().strip(), "%d.%m.%Y").date()
        except ValueError:
            self._melde("Datum bitte als TT.MM.JJJJ eingeben.", fehler=True)
            return

        try:
            projekt = projekte.lege_an(
                tag,
                self.anlass.get(),
                self.zusatz.get(),
                konf.AUFNAHMEN,
                konf.REAPER_VORLAGE,
            )
        except OSError as fehler:
            log.exception("Projekt konnte nicht angelegt werden")
            self._melde(str(fehler), fehler=True)
            return

        if self.mit_reaper.get():
            try:
                reaper.starte(projekt)
            except OSError as fehler:
                self._melde(f"Projekt angelegt, REAPER fehlt: {fehler}", fehler=True)
                return
            self._melde(f"{projekt.stem} angelegt, REAPER startet.")
        else:
            self._melde(f"{projekt.stem} angelegt.")

    def _melde(self, text: str, fehler: bool = False) -> None:
        self.rueckmeldung.configure(
            text=text, style="Fehler.TLabel" if fehler else "Gedaempft.TLabel"
        )
