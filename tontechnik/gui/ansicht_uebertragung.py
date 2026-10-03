"""Rechte Haelfte: die Streams aus streams.toml schalten und messen, darunter
der separate MP3-Mitschnitt.

Die App startet nur die Skripte der Streams. Deren Ausgabe steht im
Protokoll, nicht auf den Karten. Jeder Stream hat bis zu zwei Pegel:

  Senden  was hinausgeht. Misst nur, solange der Stream laeuft. REAPERs
          Ausgang zeigt die linke Haelfte dauerhaft.
  Testen  (optional) was beim Zuhoerer ankommt, etwa der Icecast-Stream oder
          eine Mithoerleitung. Laeuft automatisch mit dem Stream und endet
          mit ihm. Hoerbar wird dabei nichts.

Neben jedem Pegel steht der hoechste Stand des laufenden Streams bzw. Tests.
Er beginnt mit jedem Start neu, weil die Messung dann neu startet.

Bis zu zwei Streams bekommen grosse Karten mit dem Knopf unter den Pegeln,
ab drei werden die Karten kompakt und der Knopf steht daneben.
"""

from __future__ import annotations

from tkinter import ttk

from ..kern import pegel
from ..kern.streams import Stream
from ..protokoll import logger
from .karte_mitschnitt import KarteMitschnitt
from .pegelanzeige import Pegelanzeige
from .widgets import Karte, Lampe

log = logger("ansicht.uebertragung")

KOMPAKT_AB = 3


class _Schalter(Karte):
    """Ein Stream: Lampe, Senden- und ggf. Testpegel, Knopf."""

    def __init__(self, master, anwendung, stream: Stream, kompakt: bool):
        super().__init__(master, stream.name)
        self.anwendung = anwendung
        self.stream = stream
        self.schluessel = stream.id

        self.lampe = Lampe(self.kopf_rechts, "aus", stil_rahmen="Karte.TFrame")
        self.lampe.pack(side="right")

        self.messer_aus = pegel.Pegelmesser(f"{stream.id}-senden", pegel.quelle_pulse(stream.senden))
        self.anzeige_aus = Pegelanzeige(self.inhalt, "Senden", skala=stream.test is None)
        self.anzeige_aus.grid(row=0, column=0, sticky="ew")
        self.messer_ein = self.anzeige_ein = None
        if stream.test:
            eingabe = (pegel.quelle_pulse(stream.test.quelle) if stream.test.quelle
                       else pegel.quelle_netz(stream.test.adresse))
            self.messer_ein = pegel.Pegelmesser(f"{stream.id}-testen", eingabe)
            self.anzeige_ein = Pegelanzeige(self.inhalt, "Testen", skala=True)
            self.anzeige_ein.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        self.knopf = ttk.Button(
            self.inhalt,
            text=f"{stream.name} starten",
            style="Aktion.TButton",
            command=self.umschalten,
            width=16 if kompakt else 0,
        )
        if kompakt:
            self.knopf.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(16, 0))
        else:
            self.knopf.grid(row=2, column=0, sticky="ew", pady=(12, 0))

    # Bedienung ------------------------------------------------------------

    def umschalten(self) -> None:
        """Startet oder beendet den Stream samt Testleitung."""
        verwaltung = self.anwendung.verwaltung
        test_id = self.stream.test_id
        if verwaltung.laeuft(self.schluessel):
            if test_id:
                verwaltung.stopp(test_id)
            verwaltung.stopp(self.schluessel)
        else:
            try:
                verwaltung.start(self.schluessel)
            except OSError as fehler:
                log.warning("%s: %s", self.schluessel, fehler)
                self.anwendung.melde(str(fehler), fehler=True)
                return
            # Faellt die Testleitung aus, laeuft der Stream trotzdem.
            if test_id:
                try:
                    verwaltung.start(test_id)
                except OSError as fehler:
                    log.warning("%s: %s", test_id, fehler)
                    self.anwendung.melde(f"Testleitung: {fehler}", fehler=True)
        self.anwendung.aktualisieren()

    # Messung --------------------------------------------------------------

    def _messer_folgen(self, messer, anzeige, soll: bool) -> None:
        if soll and not messer.aktiv:
            messer.start()
        elif not soll and messer.aktiv:
            messer.stopp()
            anzeige.ruhe()

    def _paare(self) -> list:
        paare = [(self.messer_aus, self.anzeige_aus)]
        if self.messer_ein is not None:
            paare.append((self.messer_ein, self.anzeige_ein))
        return paare

    def pegel_zeichnen(self) -> None:
        for messer, anzeige in self._paare():
            if messer.aktiv:
                anzeige.setze(messer.db, messer.spitze, messer.verbunden, messer.hoechst)

    def aktualisieren(self) -> None:
        verwaltung = self.anwendung.verwaltung
        laeuft = verwaltung.laeuft(self.schluessel)
        test_id = self.stream.test_id
        test_laeuft = bool(test_id) and verwaltung.laeuft(test_id)

        # Endet der Stream von selbst, endet auch die Testleitung.
        if test_laeuft and not laeuft:
            verwaltung.stopp(test_id)
            test_laeuft = False

        self.lampe.setze(laeuft)
        self.lampe.beschrifte("auf Sendung" if laeuft else "aus")
        self.knopf.configure(
            text=f"{self.stream.name} {'beenden' if laeuft else 'starten'}",
            style="Stopp.TButton" if laeuft else "Aktion.TButton",
        )

        self._messer_folgen(self.messer_aus, self.anzeige_aus, laeuft)
        if self.messer_ein is not None:
            # Mit eigener Testleitung misst der Test, solange diese laeuft.
            self._messer_folgen(
                self.messer_ein, self.anzeige_ein, test_laeuft if test_id else laeuft
            )

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

        kompakt = len(anwendung.streams) >= KOMPAKT_AB
        self.schalter = [_Schalter(self, anwendung, s, kompakt) for s in anwendung.streams]
        for schalter in self.schalter:
            schalter.pack(fill="x", pady=(0, 12))
        if not self.schalter:
            ttk.Label(
                self, text="Keine Streams eingerichtet (streams.toml).", style="Gedaempft.TLabel"
            ).pack(anchor="w")

    def _dienste(self) -> list:
        """Was "Alle Streams beenden" stoppt: Streams und ihre Testleitungen.
        Der Mitschnitt gehoert nicht dazu, er hat seinen eigenen Knopf."""
        dienste = []
        for stream in self.anwendung.streams:
            dienste.append(stream.id)
            if stream.test_id:
                dienste.append(stream.test_id)
        return dienste

    def alle_beenden(self) -> None:
        for schluessel in self._dienste():
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
        laeuft_etwas = any(self.anwendung.verwaltung.laeuft(s) for s in self._dienste())
        self.alles_aus.state(["!disabled"] if laeuft_etwas else ["disabled"])

    def beenden(self) -> None:
        for schalter in self.schalter:
            schalter.beenden()
        self.mitschnitt.beenden()
