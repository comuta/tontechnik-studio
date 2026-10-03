"""Protokolle mitlesen, ohne ein Terminal zu oeffnen. Ersetzt auf Knopfdruck
beide Haelften des Hauptfensters."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import konfiguration as konf
from .stil import FARBEN

ZEILEN = 400


class AnsichtProtokoll(ttk.Frame):
    def __init__(self, master, anwendung):
        super().__init__(master, style="TFrame")
        self.anwendung = anwendung
        self._letzter_stand = ""

        leiste = ttk.Frame(self, style="TFrame")
        leiste.pack(side="bottom", fill="x", pady=(12, 0))
        ttk.Button(
            leiste, text="Ans Ende springen", style="Neben.TButton", command=self._ans_ende
        ).pack(fill="x")

        auswahl = ttk.Frame(self, style="TFrame")
        auswahl.pack(fill="x", pady=(0, 10))
        ttk.Label(auswahl, text="Quelle").pack(side="left", padx=(0, 10))
        self.quelle = ttk.Combobox(
            auswahl,
            values=[titel for titel, _ in konf.PROTOKOLLE.values()],
            state="readonly",
        )
        self.quelle.current(0)
        self.quelle.bind("<<ComboboxSelected>>", lambda _e: self._neu_laden())
        self.quelle.pack(side="left", fill="x", expand=True)

        rahmen = ttk.Frame(self, style="TFrame")
        rahmen.pack(fill="both", expand=True)
        self.text = tk.Text(
            rahmen,
            wrap="none",
            background="#12161a",
            foreground="#d6dce3",
            insertbackground="#d6dce3",
            relief="flat",
            padx=10,
            pady=8,
            font=self.anwendung.schriften["fest"],
            state="disabled",
            highlightthickness=1,
            highlightbackground=FARBEN["linie"],
        )
        schieber = ttk.Scrollbar(rahmen, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=schieber.set)
        schieber.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

    def _datei(self):
        titel = self.quelle.get()
        for anzeige, pfad in konf.PROTOKOLLE.values():
            if anzeige == titel:
                return pfad
        return konf.PROTOKOLL

    def _neu_laden(self) -> None:
        self._letzter_stand = ""
        self.aktualisieren()

    def aktualisieren(self) -> None:
        pfad = self._datei()
        try:
            zeilen = pfad.read_text(encoding="utf-8", errors="replace").splitlines()
            inhalt = "\n".join(zeilen[-ZEILEN:])
        except FileNotFoundError:
            inhalt = f"Noch nichts protokolliert ({pfad.name})."
        except OSError as fehler:
            inhalt = f"Protokoll nicht lesbar: {fehler}"

        if inhalt == self._letzter_stand:
            return
        self._letzter_stand = inhalt

        am_ende = self.text.yview()[1] > 0.99
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", inhalt)
        self.text.configure(state="disabled")
        if am_ende:
            self.text.see("end")

    def _ans_ende(self) -> None:
        self.text.see("end")
