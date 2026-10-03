"""Hauptfenster: Kopfzeile mit Zustandsanzeige, Reiter, Inhalt.

Es wird nirgends gescrollt. Jede Ansicht haelt ihre Schaltflaeche unten fest,
damit die naechste Handlung immer sichtbar ist.
"""

from __future__ import annotations

import tkinter as tk
import threading
from tkinter import messagebox, ttk

from .. import einzelinstanz
from .. import konfiguration as konf
from .. import protokoll
from ..kern.prozesse import Dienst, Dienstverwaltung
from ..kern import aufnahme, reaper
from . import stil
from .ansicht_protokoll import AnsichtProtokoll
from .ansicht_start import AnsichtStart
from .ansicht_uebertragung import AnsichtUebertragung
from .widgets import Lampe, trennlinie

TAKT_MS = 1500
PEGEL_MS = 200
REAPER_TAKTE = 4
BUEHNE_BREIT = 900
BUEHNE_HOCH = 820


class Anwendung(tk.Tk):
    def __init__(self, verwaltung: Dienstverwaltung, horcher=None):
        # WM_CLASS besteht aus zwei Teilen. baseName setzt den ersten, der
        # sonst "python3" hiesse - genau daran scheitert die Zuordnung im Dock,
        # und das Fenster bekommt dann das allgemeine Symbol.
        super().__init__(baseName="tontechnik-studio", className="TontechnikStudio")
        self.verwaltung = verwaltung
        self.log = protokoll.logger("gui")

        self.title("Tontechnik Studio")
        self.geometry("900x700")
        self.minsize(560, 540)
        self.schriften = stil.anwenden(self)
        self._fenstersymbol()
        self._vollbild = False

        self.transport = None
        self._weckruf = threading.Event()
        if horcher is not None:
            einzelinstanz.lauschen(horcher, self._weckruf)

        self._ansichten: dict = {}
        self._reiter: dict = {}
        self._takte = 0
        self._reaper_laeuft = False

        self._baue_kopf()
        self._baue_reiter()
        self._baue_inhalt()

        self.protocol("WM_DELETE_WINDOW", self.beenden)
        self.bind("<Control-q>", lambda _e: self.beenden())
        self.bind("<F11>", lambda _e: self.vollbild_umschalten())
        self.bind("<Escape>", lambda _e: self.vollbild_umschalten(False))
        self.wechsle("start")
        self._pegel_takt()
        if konf.VOLLBILD:
            self.vollbild_umschalten(True)
        self.nach_vorn()
        self._takt()

    def _fenstersymbol(self) -> None:
        if not konf.ICON.is_file():
            return
        try:
            self._symbol = tk.PhotoImage(file=str(konf.ICON))
            self.iconphoto(True, self._symbol)
        except tk.TclError:
            pass

    def vollbild_umschalten(self, an: bool | None = None) -> None:
        self._vollbild = (not self._vollbild) if an is None else an
        try:
            self.attributes("-fullscreen", self._vollbild)
        except tk.TclError:
            # Fenstermanager ohne Vollbildattribut: wenigstens maximieren.
            try:
                self.attributes("-zoomed", self._vollbild)
            except tk.TclError:
                pass

    def nach_vorn(self) -> None:
        """Holt das Fenster in den Vordergrund, auch aus dem Symbolzustand."""
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))
        self.focus_force()

    # Aufbau ---------------------------------------------------------------

    def _baue_kopf(self) -> None:
        kopf = ttk.Frame(self, style="Kopf.TFrame", padding=(20, 16))
        kopf.pack(fill="x")
        kopf.columnconfigure(0, weight=1)

        ttk.Label(kopf, text="Tontechnik Studio", style="Titel.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        lampen = ttk.Frame(kopf, style="Kopf.TFrame")
        lampen.grid(row=0, column=1, sticky="e")
        self.lampe_reaper = Lampe(lampen, "REAPER")
        self.lampe_reaper.pack(side="left", padx=(0, 16))
        self.lampe_aufnahme = Lampe(lampen, "Aufnahme")
        self.lampe_aufnahme.pack(side="left", padx=(0, 16))
        self.lampe_telefon = Lampe(lampen, "Telefon")
        self.lampe_telefon.pack(side="left", padx=(0, 16))
        self.lampe_radio = Lampe(lampen, "Radio")
        self.lampe_radio.pack(side="left")

        self.meldung = ttk.Label(kopf, text="", style="KopfKlein.TLabel")
        self.meldung.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        reiterleiste = ttk.Frame(self, style="Kopf.TFrame", padding=(12, 0))
        reiterleiste.pack(fill="x")
        self._reiterleiste = reiterleiste
        trennlinie(self)

    def _baue_reiter(self) -> None:
        for schluessel, klasse in (
            ("start", AnsichtStart),
            ("uebertragung", AnsichtUebertragung),
            ("protokoll", AnsichtProtokoll),
        ):
            knopf = ttk.Button(
                self._reiterleiste,
                text=klasse.titel,
                style="Reiter.TButton",
                command=lambda s=schluessel: self.wechsle(s),
            )
            knopf.pack(side="left")
            self._reiter[schluessel] = (knopf, klasse)

    def _baue_inhalt(self) -> None:
        self._buehne = ttk.Frame(self, style="TFrame")
        self._buehne.pack(fill="both", expand=True)
        self._inhalt = ttk.Frame(self._buehne, style="TFrame")
        self._inhalt.place(relx=0.5, y=0, anchor="n", width=BUEHNE_BREIT, height=BUEHNE_HOCH)
        self._buehne.bind("<Configure>", self._buehne_anpassen)
        self._aktiv = None

    def _buehne_anpassen(self, ereignis) -> None:
        """Haelt den Inhalt mittig und begrenzt ihn, damit er im Vollbild
        nicht ueber die ganze Flaeche auseinandergezogen wird."""
        self._inhalt.place_configure(
            width=min(BUEHNE_BREIT, ereignis.width),
            height=min(BUEHNE_HOCH, ereignis.height),
        )

    # Bedienung ------------------------------------------------------------

    def wechsle(self, schluessel: str) -> None:
        if schluessel == self._aktiv:
            return
        if self._aktiv is not None:
            self._ansichten[self._aktiv].pack_forget()
            self._reiter[self._aktiv][0].configure(style="Reiter.TButton")

        if schluessel not in self._ansichten:
            klasse = self._reiter[schluessel][1]
            self._ansichten[schluessel] = klasse(self._inhalt, self)

        self._ansichten[schluessel].pack(fill="both", expand=True)
        self._reiter[schluessel][0].configure(style="ReiterAktiv.TButton")
        self._aktiv = schluessel
        self.aktualisieren()

    def melde(self, text: str, fehler: bool = False) -> None:
        self.meldung.configure(
            text=text, style="KopfFehler.TLabel" if fehler else "KopfKlein.TLabel"
        )

    def aktualisieren(self) -> None:
        self.lampe_telefon.setze(self.verwaltung.laeuft("telefon"))
        self.lampe_radio.setze(self.verwaltung.laeuft("radio"))
        self.lampe_reaper.setze(self._reaper_laeuft, farbe="bereit")
        self.lampe_aufnahme.setze(bool(self.transport and self.transport["nimmt_auf"]))
        if self._aktiv is not None:
            self._ansichten[self._aktiv].aktualisieren()

    def _pegel_takt(self) -> None:
        """Eigener, schneller Takt: nur die Pegelanzeigen werden neu gezeichnet."""
        ansicht = self._ansichten.get(self._aktiv)
        if hasattr(ansicht, "pegel_zeichnen"):
            ansicht.pegel_zeichnen()
        self.after(PEGEL_MS, self._pegel_takt)

    def _takt(self) -> None:
        if self._weckruf.is_set():
            self._weckruf.clear()
            self.nach_vorn()
        if self._takte % REAPER_TAKTE == 0:
            self._reaper_laeuft = reaper.laeuft()
        self.transport = aufnahme.transport() if self._reaper_laeuft else None
        self._takte += 1
        self.aktualisieren()
        self.after(TAKT_MS, self._takt)

    def beenden(self) -> None:
        laeuft = [s for s in self.verwaltung.schluessel() if self.verwaltung.laeuft(s)]
        if laeuft and not messagebox.askyesno(
            "Tontechnik Studio",
            "Es laeuft noch eine Uebertragung. Wirklich beenden?",
            parent=self,
        ):
            return
        self.verwaltung.alle_stoppen()
        for ansicht in self._ansichten.values():
            if hasattr(ansicht, "beenden"):
                ansicht.beenden()
        self.log.info("Oberflaeche beendet")
        self.destroy()


def baue_verwaltung() -> Dienstverwaltung:
    verwaltung = Dienstverwaltung()
    umgebung = {"TONTECHNIK_GEHEIMNISSE": str(konf.GEHEIMNISSE)}
    verwaltung.registriere(
        Dienst("telefon", "Telefonuebertragung", konf.SKRIPT_TELEFON, konf.LOG_TELEFON, umgebung)
    )
    verwaltung.registriere(
        Dienst("radio", "Radiouebertragung", konf.SKRIPT_RADIO, konf.LOG_RADIO, umgebung)
    )
    verwaltung.registriere(
        Dienst("mithoeren", "Mithoeren", konf.SKRIPT_MITHOEREN, konf.LOG_MITHOEREN, umgebung)
    )
    return verwaltung


def starte() -> None:
    protokoll.einrichten()
    konf.vorbereiten()

    sperrname = einzelinstanz.name_fuer(konf.BASIS)
    horcher = einzelinstanz.belegen(sperrname)
    if horcher is None and einzelinstanz.wecken(sperrname):
        # Es laeuft bereits eine Instanz. Sie holt ihr Fenster nach vorn.
        return

    Anwendung(baue_verwaltung(), horcher).mainloop()