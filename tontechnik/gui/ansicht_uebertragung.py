"""Rechte Haelfte: Telefon und Radio schalten, messen und mitverfolgen,
darunter der separate MP3-Mitschnitt.

Die App startet nur die Skripte aus skripte/ und liest deren Ausgabe mit.
Jede Uebertragung hat zwei Pegel:

  Senden  was hinausgeht. Misst, sobald die Quelle existiert - auch bei einem
          Stream, den jemand von Hand gestartet hat.
  Testen  was beim Zuhoerer ankommt: beim Radio der Icecast-Stream, beim
          Telefon die Mithoerleitung. Laeuft automatisch mit der Uebertragung
          und endet mit ihr. Hoerbar wird dabei nichts.
"""

from __future__ import annotations

from tkinter import ttk

from .. import konfiguration as konf
from ..kern import audio, pegel
from ..kern.ausgabe import letzte_zeile
from ..protokoll import logger
from .karte_mitschnitt import KarteMitschnitt
from .pegelanzeige import Pegelanzeige
from .widgets import Karte, Lampe

log = logger("ansicht.uebertragung")

# Was "Alle Streams beenden" stoppt. Der Mitschnitt gehoert nicht dazu,
# er hat seinen eigenen Knopf.
UEBERTRAGUNGEN = ("telefon", "radio", "mithoeren")


class _Schalter(Karte):
    """Eine Uebertragung: Lampe, Senden- und Testpegel, letzte Meldung, Knopf."""

    def __init__(self, master, anwendung, aufbau: dict):
        super().__init__(master, aufbau["titel"])
        self.anwendung = anwendung
        self.schluessel = aufbau["schluessel"]
        self._titel = aufbau["titel"]
        self._protokoll = aufbau["protokoll"]
        self._quelle_aus = aufbau["quelle_aus"]
        # Eigener Dienst fuer den Testpegel (Mithoerleitung), sonst None.
        self._testdienst = aufbau.get("testdienst")

        self.lampe = Lampe(self.kopf_rechts, "aus", stil_rahmen="Karte.TFrame")
        self.lampe.pack(side="right")

        self.messer_aus = pegel.Pegelmesser(f"{self.schluessel}-senden", aufbau["pegel_aus"])
        self.messer_ein = pegel.Pegelmesser(f"{self.schluessel}-testen", aufbau["pegel_ein"])
        self.anzeige_aus = Pegelanzeige(self.inhalt, "Senden")
        self.anzeige_aus.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.anzeige_ein = Pegelanzeige(self.inhalt, "Testen", skala=True)
        self.anzeige_ein.grid(row=1, column=0, sticky="ew")

        self.meldung = ttk.Label(self.inhalt, text="", style="KarteKlein.TLabel", anchor="w")
        self.meldung.grid(row=2, column=0, sticky="ew", pady=(6, 0))

        self.knopf = ttk.Button(
            self.inhalt,
            text=f"{self._titel} starten",
            style="Aktion.TButton",
            command=self.umschalten,
        )
        self.knopf.grid(row=3, column=0, sticky="ew", pady=(10, 0))

    # Bedienung ------------------------------------------------------------

    def umschalten(self) -> None:
        """Startet oder beendet die Uebertragung samt Testleitung."""
        verwaltung = self.anwendung.verwaltung
        if verwaltung.laeuft(self.schluessel):
            if self._testdienst:
                verwaltung.stopp(self._testdienst)
            verwaltung.stopp(self.schluessel)
        else:
            try:
                verwaltung.start(self.schluessel)
            except OSError as fehler:
                log.warning("%s: %s", self.schluessel, fehler)
                self.anwendung.melde(str(fehler), fehler=True)
                return
            # Faellt die Testleitung aus, laeuft die Uebertragung trotzdem.
            if self._testdienst:
                try:
                    verwaltung.start(self._testdienst)
                except OSError as fehler:
                    log.warning("%s: %s", self._testdienst, fehler)
                    self.anwendung.melde(f"Testleitung: {fehler}", fehler=True)
        self.anwendung.aktualisieren()

    # Messung --------------------------------------------------------------

    def _messer_folgen(self, messer, anzeige, soll: bool) -> None:
        if soll and not messer.aktiv:
            messer.start()
        elif not soll and messer.aktiv:
            messer.stopp()
            anzeige.setze(pegel.STILLE_DB, pegel.STILLE_DB, False)

    def _paare(self) -> list:
        return [(self.messer_aus, self.anzeige_aus), (self.messer_ein, self.anzeige_ein)]

    def pegel_zeichnen(self) -> None:
        for messer, anzeige in self._paare():
            if messer.aktiv:
                anzeige.setze(messer.db, messer.spitze, messer.verbunden)

    def aktualisieren(self) -> None:
        verwaltung = self.anwendung.verwaltung
        laeuft = verwaltung.laeuft(self.schluessel)
        test_laeuft = bool(self._testdienst) and verwaltung.laeuft(self._testdienst)

        # Endet die Uebertragung von selbst, endet auch die Testleitung.
        if test_laeuft and not laeuft:
            verwaltung.stopp(self._testdienst)
            test_laeuft = False

        self.lampe.setze(laeuft)
        self.lampe.beschrifte("auf Sendung" if laeuft else "aus")
        self.knopf.configure(
            text=f"{self._titel} beenden" if laeuft else f"{self._titel} starten",
            style="Stopp.TButton" if laeuft else "Aktion.TButton",
        )

        aus_soll = laeuft or audio.quelle_vorhanden(self._quelle_aus)
        ein_soll = test_laeuft if self._testdienst else laeuft
        self._messer_folgen(self.messer_aus, self.anzeige_aus, aus_soll)
        self._messer_folgen(self.messer_ein, self.anzeige_ein, ein_soll)

        self.meldung.configure(text=letzte_zeile(self._protokoll)[:110])

    def beenden(self) -> None:
        for messer, _anzeige in self._paare():
            messer.stopp()


class AnsichtUebertragung(ttk.Frame):
    def __init__(self, master, anwendung):
        super().__init__(master, style="TFrame")
        self.anwendung = anwendung

        leiste = ttk.Frame(self, style="TFrame")
        leiste.pack(side="bottom", fill="x", pady=(12, 0))
        self.alles_aus = ttk.Button(
            leiste,
            text="Alle Streams beenden",
            style="Neben.TButton",
            command=self.alle_beenden,
        )
        self.alles_aus.pack(fill="x")

        self.mitschnitt = KarteMitschnitt(self, anwendung)
        self.mitschnitt.pack(side="bottom", fill="x")

        self.schalter = [
            _Schalter(self, anwendung, aufbau) for aufbau in (
                {
                    "schluessel": "telefon",
                    "titel": "Telefon",
                    "protokoll": konf.LOG_TELEFON,
                    "pegel_aus": pegel.quelle_pulse(konf.PEGEL_TELEFON_AUS),
                    "pegel_ein": pegel.quelle_pulse(konf.PEGEL_TELEFON_EIN),
                    "quelle_aus": konf.PEGEL_TELEFON_AUS,
                    "testdienst": "mithoeren",
                },
                {
                    "schluessel": "radio",
                    "titel": "Radio",
                    "protokoll": konf.LOG_RADIO,
                    "pegel_aus": pegel.quelle_pulse(konf.PEGEL_RADIO_AUS),
                    "pegel_ein": pegel.quelle_netz(konf.RADIO_STREAM),
                    "quelle_aus": konf.PEGEL_RADIO_AUS,
                },
            )
        ]
        for schalter in self.schalter:
            schalter.pack(fill="x", pady=(0, 12))

    def alle_beenden(self) -> None:
        for schluessel in UEBERTRAGUNGEN:
            self.anwendung.verwaltung.stopp(schluessel)
        self.anwendung.aktualisieren()

    def pegel_zeichnen(self) -> None:
        for schalter in self.schalter:
            schalter.pegel_zeichnen()
        self.mitschnitt.pegel_zeichnen()

    def aktualisieren(self) -> None:
        for schalter in self.schalter:
            schalter.aktualisieren()
        self.mitschnitt.aktualisieren()
        laeuft_etwas = any(self.anwendung.verwaltung.laeuft(s) for s in UEBERTRAGUNGEN)
        self.alles_aus.state(["!disabled"] if laeuft_etwas else ["disabled"])

    def beenden(self) -> None:
        for schalter in self.schalter:
            schalter.beenden()
        self.mitschnitt.beenden()
