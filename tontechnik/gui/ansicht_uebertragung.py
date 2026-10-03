"""Zweite Ansicht: Telefon und Radio schalten, messen und mitverfolgen.

Die App startet nur die Skripte aus skripte/ und liest deren Ausgabe mit.
Gemessen wird davon unabhaengig: Sobald eine Quelle existiert, laeuft die
Pegelanzeige - auch bei einem Stream, den jemand von Hand gestartet hat.
Der Knopf "Pruefen" schaltet die Messung zusaetzlich von Hand ein, auch fuer
den Serverton des Radiostreams.
"""

from __future__ import annotations

from tkinter import ttk

from .. import konfiguration as konf
from ..kern import audio, pegel
from ..kern.ausgabe import letzte_zeile
from ..protokoll import logger
from .pegelanzeige import Pegelanzeige
from .widgets import Karte, Lampe

log = logger("ansicht.uebertragung")


class _Schalter(Karte):
    """Eine Uebertragung: Schalter, Pruefknopf, Pegel, letzte Meldung.

    Der zweite Pegel ist optional und zeigt, was beim Zuhoerer ankommt: beim
    Radio der Icecast-Stream, beim Telefon die Mithoerleitung. Er misst, solange
    sein Dienst laeuft oder von Hand geprueft wird. Hoerbar wird dabei nichts.
    """

    def __init__(self, master, anwendung, aufbau: dict):
        super().__init__(master, aufbau["titel"], aufbau["beschreibung"])
        self.anwendung = anwendung
        self.schluessel = aufbau["schluessel"]
        self._titel = aufbau["titel"]
        self._protokoll = aufbau["protokoll"]
        self._quelle_aus = aufbau.get("quelle_aus")   # None = keine Pulse-Quelle
        self._zweit = aufbau.get("zweitdienst")        # eigener Dienst fuer den zweiten Pegel
        self._pruefen = False

        kopf = ttk.Frame(self.inhalt, style="Karte.TFrame")
        kopf.grid(row=0, column=0, sticky="ew")
        self.lampe = Lampe(kopf, "aus", stil_rahmen="Karte.TFrame")
        self.lampe.pack(side="left")

        self.messer_aus = pegel.Pegelmesser(f"{self.schluessel}-gesendet", aufbau["pegel_aus"])
        self.anzeige_aus = Pegelanzeige(self.inhalt, "gesendet")
        self.anzeige_aus.grid(row=1, column=0, sticky="ew", pady=(12, 2))
        self.messer_ein = self.anzeige_ein = None
        if aufbau.get("pegel_ein"):
            self.messer_ein = pegel.Pegelmesser(
                f"{self.schluessel}-empfangen", aufbau["pegel_ein"]
            )
            self.anzeige_ein = Pegelanzeige(self.inhalt, aufbau["beschriftung_ein"])
            self.anzeige_ein.grid(row=2, column=0, sticky="ew", pady=(2, 0))

        self.meldung = ttk.Label(self.inhalt, text="", style="KarteKlein.TLabel", anchor="w")
        self.meldung.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        knoepfe = ttk.Frame(self.inhalt, style="Karte.TFrame")
        knoepfe.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        knoepfe.columnconfigure(0, weight=1)

        self.knopf = ttk.Button(
            knoepfe,
            text=f"{self._titel} starten",
            style="Aktion.TButton",
            command=lambda: self.umschalten(self.schluessel),
        )
        self.knopf.grid(row=0, column=0, sticky="ew")

        self.knopf_pruefen = ttk.Button(
            knoepfe, text="Pruefen", style="Neben.TButton", command=self.pruefung_umschalten
        )
        self.knopf_pruefen.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        self.knopf_zweit = None
        if self._zweit:
            self.knopf_zweit = ttk.Button(
                knoepfe,
                text=f"{self._zweit['titel']} starten",
                style="Neben.TButton",
                command=lambda: self.umschalten(self._zweit["schluessel"]),
            )
            self.knopf_zweit.grid(row=0, column=2, sticky="ew", padx=(10, 0))

    # Bedienung ------------------------------------------------------------

    def umschalten(self, schluessel: str) -> None:
        try:
            self.anwendung.verwaltung.umschalten(schluessel)
        except OSError as fehler:
            log.warning("%s: %s", schluessel, fehler)
            self.anwendung.melde(str(fehler), fehler=True)
            return
        self.anwendung.aktualisieren()

    def pruefung_umschalten(self) -> None:
        """Messung von Hand ein- oder ausschalten, unabhaengig vom Dienst."""
        self._pruefen = not self._pruefen
        self.anwendung.aktualisieren()

    # Messung --------------------------------------------------------------

    def _messer_folgen(self, messer, anzeige, soll: bool) -> None:
        if soll and not messer.aktiv:
            messer.start()
        elif not soll and messer.aktiv:
            messer.stopp()
            anzeige.setze(pegel.STILLE_DB, pegel.STILLE_DB, False)

    def _paare(self) -> list:
        paare = [(self.messer_aus, self.anzeige_aus)]
        if self.messer_ein is not None:
            paare.append((self.messer_ein, self.anzeige_ein))
        return paare

    def pegel_zeichnen(self) -> None:
        for messer, anzeige in self._paare():
            if messer.aktiv:
                anzeige.setze(messer.db, messer.spitze, messer.verbunden)

    def aktualisieren(self) -> None:
        verwaltung = self.anwendung.verwaltung
        laeuft = verwaltung.laeuft(self.schluessel)
        zweit_laeuft = bool(self._zweit) and verwaltung.laeuft(self._zweit["schluessel"])

        self.lampe.setze(laeuft)
        self.lampe.beschrifte("auf Sendung" if laeuft else "aus")
        self.knopf.configure(
            text=f"{self._titel} beenden" if laeuft else f"{self._titel} starten",
            style="Stopp.TButton" if laeuft else "Aktion.TButton",
        )
        self.knopf_pruefen.configure(
            text="Pruefung beenden" if self._pruefen else "Pruefen"
        )
        if self.knopf_zweit is not None:
            self.knopf_zweit.configure(
                text=f"{self._zweit['titel']} beenden" if zweit_laeuft
                else f"{self._zweit['titel']} starten"
            )

        # Senderichtung: messen, sobald die Quelle existiert - egal, wer sendet.
        aus_soll = laeuft or self._pruefen or (
            bool(self._quelle_aus) and audio.quelle_vorhanden(self._quelle_aus)
        )
        self._messer_folgen(self.messer_aus, self.anzeige_aus, aus_soll)
        # Empfangsrichtung nur, wenn ihr Dienst laeuft oder von Hand geprueft
        # wird - Radiostream wie Mithoerleitung kosten Bandbreite bzw. eine
        # Leitung. Beim Telefon ist das die Mithoerleitung, sonst der Dienst selbst.
        if self.messer_ein is not None:
            ein_laeuft = zweit_laeuft if self._zweit else laeuft
            self._messer_folgen(self.messer_ein, self.anzeige_ein, ein_laeuft or self._pruefen)

        self.meldung.configure(text=letzte_zeile(self._protokoll)[:110])

    def beenden(self) -> None:
        for messer, _anzeige in self._paare():
            messer.stopp()


class AnsichtUebertragung(ttk.Frame):
    titel = "Uebertragen"

    def __init__(self, master, anwendung):
        super().__init__(master, style="TFrame", padding=(20, 18))
        self.anwendung = anwendung

        leiste = ttk.Frame(self, style="TFrame")
        leiste.pack(side="bottom", fill="x", pady=(16, 0))
        self.alles_aus = ttk.Button(
            leiste,
            text="Alle Uebertragungen beenden",
            style="Neben.TButton",
            command=self.alle_beenden,
        )
        self.alles_aus.pack(fill="x")

        self.schalter = [
            _Schalter(self, anwendung, aufbau) for aufbau in (
                {
                    "schluessel": "telefon",
                    "titel": "Telefon",
                    "beschreibung": "stream_telefon.sh",
                    "protokoll": konf.LOG_TELEFON,
                    "pegel_aus": pegel.quelle_pulse(konf.PEGEL_TELEFON_AUS),
                    "pegel_ein": pegel.quelle_pulse(konf.PEGEL_TELEFON_EIN),
                    "quelle_aus": konf.PEGEL_TELEFON_AUS,
                    "beschriftung_ein": "mitgehoert",
                    "zweitdienst": {"schluessel": "mithoeren", "titel": "Mithoeren"},
                },
                {
                    "schluessel": "radio",
                    "titel": "Radio",
                    "beschreibung": "stream_radio.sh",
                    "protokoll": konf.LOG_RADIO,
                    "pegel_aus": pegel.quelle_pulse(konf.PEGEL_RADIO_AUS),
                    "pegel_ein": pegel.quelle_netz(konf.RADIO_STREAM),
                    "quelle_aus": konf.PEGEL_RADIO_AUS,
                    "beschriftung_ein": "vom Server",
                },
            )
        ]
        for schalter in self.schalter:
            schalter.pack(fill="x", pady=(0, 12))

    def alle_beenden(self) -> None:
        self.anwendung.verwaltung.alle_stoppen()
        self.anwendung.aktualisieren()

    def pegel_zeichnen(self) -> None:
        for schalter in self.schalter:
            schalter.pegel_zeichnen()

    def aktualisieren(self) -> None:
        for schalter in self.schalter:
            schalter.aktualisieren()
        laeuft_etwas = any(
            self.anwendung.verwaltung.laeuft(s) for s in self.anwendung.verwaltung.schluessel()
        )
        self.alles_aus.state(["!disabled"] if laeuft_etwas else ["disabled"])

    def beenden(self) -> None:
        for schalter in self.schalter:
            schalter.beenden()