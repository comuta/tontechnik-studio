"""Hauptfenster: Kopfzeile mit Zustandsanzeige, darunter zwei Haelften.

Links Projekt, REAPER und Aufnahme, rechts die Uebertragungen mit Pegeln und
darunter der MP3-Mitschnitt. Alles Wichtige ist gleichzeitig sichtbar, es wird
nirgends gescrollt. Das Protokoll ersetzt auf Knopfdruck beide Haelften.
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
BUEHNE_BREIT = 1760
RAND = 24


class Anwendung(tk.Tk):
    def __init__(self, verwaltung: Dienstverwaltung, horcher=None):
        # WM_CLASS besteht aus zwei Teilen. baseName setzt den ersten, der
        # sonst "python3" hiesse - genau daran scheitert die Zuordnung im Dock,
        # und das Fenster bekommt dann das allgemeine Symbol.
        super().__init__(baseName="tontechnik-studio", className="TontechnikStudio")
        self.verwaltung = verwaltung
        self.log = protokoll.logger("gui")

        self.title("Tontechnik Studio")
        self.geometry("1600x1000")
        self.minsize(1280, 980)
        self.schriften = stil.anwenden(self)
        self._fenstersymbol()
        self._vollbild = False

        self.transport = None
        self.projekt = None          # zuletzt angelegte .RPP, Ziel des Mitschnitts
        self._weckruf = threading.Event()
        if horcher is not None:
            einzelinstanz.lauschen(horcher, self._weckruf)

        self._takte = 0
        self._reaper_laeuft = False
        self._protokoll_offen = False

        self._baue_kopf()
        self._baue_inhalt()

        self.protocol("WM_DELETE_WINDOW", self.beenden)
        self.bind("<Control-q>", lambda _e: self.beenden())
        self.bind("<F11>", lambda _e: self.vollbild_umschalten())
        self.bind("<Escape>", lambda _e: self.vollbild_umschalten(False))
        self._pegel_takt()
        if konf.VOLLBILD:
            self.vollbild_umschalten(True)
        else:
            self.maximieren()
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

    def maximieren(self) -> None:
        """Fenster auf die volle Arbeitsflaeche, Appleiste und Dock bleiben frei."""
        try:
            self.attributes("-zoomed", True)
        except tk.TclError:
            # Fenstermanager ohne Maximieren: wenigstens die Bildschirmgroesse.
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

    def vollbild_umschalten(self, an: bool | None = None) -> None:
        """F11: Vollbild ueber alles. Zurueck geht es ins maximierte Fenster."""
        self._vollbild = (not self._vollbild) if an is None else an
        try:
            self.attributes("-fullscreen", self._vollbild)
        except tk.TclError:
            return
        if not self._vollbild:
            self.maximieren()

    def nach_vorn(self) -> None:
        """Holt das Fenster in den Vordergrund, auch aus dem Symbolzustand."""
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))
        self.focus_force()

    # Aufbau ---------------------------------------------------------------

    def _baue_kopf(self) -> None:
        kopf = ttk.Frame(self, style="Kopf.TFrame", padding=(RAND, 14))
        kopf.pack(fill="x")
        kopf.columnconfigure(0, weight=1)

        ttk.Label(kopf, text="Tontechnik Studio", style="Titel.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        lampen = ttk.Frame(kopf, style="Kopf.TFrame")
        lampen.grid(row=0, column=1, sticky="e")
        self.lampe_reaper = Lampe(lampen, "REAPER")
        self.lampe_aufnahme = Lampe(lampen, "Aufnahme")
        self.lampe_telefon = Lampe(lampen, "Telefon")
        self.lampe_radio = Lampe(lampen, "Radio")
        self.lampe_mitschnitt = Lampe(lampen, "Mitschnitt")
        for lampe in (self.lampe_reaper, self.lampe_aufnahme, self.lampe_telefon,
                      self.lampe_radio, self.lampe_mitschnitt):
            lampe.pack(side="left", padx=(0, 16))

        self.knopf_protokoll = ttk.Button(
            kopf, text="Protokoll", style="Neben.TButton", command=self.protokoll_umschalten
        )
        self.knopf_protokoll.grid(row=0, column=2, sticky="e", padx=(8, 0))

        self.meldung = ttk.Label(kopf, text="", style="KopfKlein.TLabel")
        self.meldung.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
        trennlinie(self)

    def _baue_inhalt(self) -> None:
        self._buehne = ttk.Frame(self, style="TFrame")
        self._buehne.pack(fill="both", expand=True)
        self._inhalt = ttk.Frame(self._buehne, style="TFrame", padding=(0, 18, 0, RAND))
        self._inhalt.place(relx=0.5, y=0, anchor="n", width=BUEHNE_BREIT, relheight=1.0)
        self._buehne.bind("<Configure>", self._buehne_anpassen)

        # Zwei gleich breite Haelften mit einer Linie dazwischen.
        self._uebersicht = ttk.Frame(self._inhalt, style="TFrame")
        self._uebersicht.columnconfigure(0, weight=1, uniform="haelfte")
        self._uebersicht.columnconfigure(2, weight=1, uniform="haelfte")
        self._uebersicht.rowconfigure(1, weight=1)

        ttk.Label(self._uebersicht, text="Vorbereitung", style="Spaltentitel.TLabel").grid(
            row=0, column=0, sticky="w", padx=RAND, pady=(0, 10)
        )
        ttk.Label(self._uebersicht, text="Uebertragung", style="Spaltentitel.TLabel").grid(
            row=0, column=2, sticky="w", padx=RAND, pady=(0, 10)
        )
        self.links = AnsichtStart(self._uebersicht, self)
        self.links.grid(row=1, column=0, sticky="nsew", padx=RAND)
        tk.Frame(self._uebersicht, width=1, background=stil.FARBEN["linie"]).grid(
            row=0, column=1, rowspan=2, sticky="ns"
        )
        self.rechts = AnsichtUebertragung(self._uebersicht, self)
        self.rechts.grid(row=1, column=2, sticky="nsew", padx=RAND)
        self._uebersicht.pack(fill="both", expand=True)

        self.protokoll = AnsichtProtokoll(self._inhalt, self)

    def _buehne_anpassen(self, ereignis) -> None:
        """Haelt den Inhalt mittig und begrenzt seine Breite, damit er auf
        breiten Bildschirmen nicht auseinandergezogen wird."""
        self._inhalt.place_configure(width=min(BUEHNE_BREIT, ereignis.width))

    # Bedienung ------------------------------------------------------------

    def protokoll_umschalten(self) -> None:
        self._protokoll_offen = not self._protokoll_offen
        if self._protokoll_offen:
            self._uebersicht.pack_forget()
            self.protokoll.pack(fill="both", expand=True, padx=RAND)
            self.knopf_protokoll.configure(text="Zurueck zur Uebersicht")
        else:
            self.protokoll.pack_forget()
            self._uebersicht.pack(fill="both", expand=True)
            self.knopf_protokoll.configure(text="Protokoll")
        self.aktualisieren()

    def melde(self, text: str, fehler: bool = False) -> None:
        self.meldung.configure(
            text=text, style="KopfFehler.TLabel" if fehler else "KopfKlein.TLabel"
        )

    def aktualisieren(self) -> None:
        self.lampe_telefon.setze(self.verwaltung.laeuft("telefon"))
        self.lampe_radio.setze(self.verwaltung.laeuft("radio"))
        self.lampe_mitschnitt.setze(self.verwaltung.laeuft("mitschnitt"))
        self.lampe_reaper.setze(self._reaper_laeuft, farbe="bereit")
        self.lampe_aufnahme.setze(bool(self.transport and self.transport["nimmt_auf"]))
        if self._protokoll_offen:
            self.protokoll.aktualisieren()
        else:
            self.links.aktualisieren()
            self.rechts.aktualisieren()

    def _pegel_takt(self) -> None:
        """Eigener, schneller Takt: nur die Pegelanzeigen werden neu gezeichnet."""
        if not self._protokoll_offen:
            self.rechts.pegel_zeichnen()
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
            "Es laeuft noch eine Uebertragung oder ein Mitschnitt. Wirklich beenden?",
            parent=self,
        ):
            return
        self.verwaltung.alle_stoppen()
        self.rechts.beenden()
        self.log.info("Oberflaeche beendet")
        self.destroy()


def baue_verwaltung() -> Dienstverwaltung:
    verwaltung = Dienstverwaltung()
    umgebung = {"TONTECHNIK_GEHEIMNISSE": str(konf.GEHEIMNISSE)}
    for schluessel, titel, skript, log in (
        ("telefon", "Telefonuebertragung", konf.SKRIPT_TELEFON, konf.LOG_TELEFON),
        ("radio", "Radiouebertragung", konf.SKRIPT_RADIO, konf.LOG_RADIO),
        ("mithoeren", "Mithoeren", konf.SKRIPT_MITHOEREN, konf.LOG_MITHOEREN),
        ("mitschnitt", "MP3-Mitschnitt", konf.SKRIPT_MITSCHNITT, konf.LOG_MITSCHNITT),
    ):
        verwaltung.registriere(Dienst(schluessel, titel, skript, log, umgebung))
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
