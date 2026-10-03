"""Streams aus streams.toml lesen und pruefen.

Die Datei beschreibt jeden Stream: Anzeigename, Skript, Pegelquellen. Daraus
entstehen Dienste, Karten und Lampen - ein neuer Stream braucht also nur
einen Eintrag und sein Skript, keine Codeaenderung.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .. import konfiguration as konf
from ..protokoll import logger
from .prozesse import Dienst, Dienstverwaltung

log = logger("streams")

_ID = re.compile(r"^[a-z0-9_]+$")
_RESERVIERT = {"mitschnitt", "studio", "reaper"}
MAX_STREAMS = 4


class StreamFehler(Exception):
    """streams.toml fehlt oder ist fehlerhaft. Die Meldung ist fuer Menschen."""


@dataclass(frozen=True)
class Test:
    quelle: str | None = None       # PipeWire-Quelle
    adresse: str | None = None      # Netzwerkstream
    skript: Path | None = None      # eigene Testleitung


@dataclass(frozen=True)
class Stream:
    id: str
    name: str
    skript: Path
    senden: str
    test: Test | None = None
    umgebung: dict = field(default_factory=dict)

    @property
    def protokoll(self) -> Path:
        return konf.ZUSTAND / f"{self.id}.log"

    @property
    def test_id(self) -> str | None:
        """Dienstname der Testleitung, None ohne eigenes Testskript."""
        return f"{self.id}-test" if self.test and self.test.skript else None

    @property
    def test_protokoll(self) -> Path:
        return konf.ZUSTAND / f"{self.id}-test.log"


def _skript(wert, wo: str) -> Path:
    if not isinstance(wert, str) or not wert.strip():
        raise StreamFehler(f"{wo}: 'skript' fehlt")
    pfad = Path(wert).expanduser()
    return pfad if pfad.is_absolute() else konf.SKRIPTE / pfad


def _text(eintrag: dict, schluessel: str, wo: str) -> str:
    wert = eintrag.get(schluessel)
    if not isinstance(wert, str) or not wert.strip():
        raise StreamFehler(f"{wo}: '{schluessel}' fehlt")
    return wert.strip()


def _test(eintrag, wo: str) -> Test | None:
    if eintrag is None:
        return None
    if not isinstance(eintrag, dict):
        raise StreamFehler(f"{wo}: [stream.test] ist keine Tabelle")
    quelle, adresse = eintrag.get("quelle"), eintrag.get("adresse")
    if bool(quelle) == bool(adresse):
        raise StreamFehler(f"{wo}: im Test genau eins von 'quelle' oder 'adresse' angeben")
    skript = _skript(eintrag["skript"], f"{wo}, Test") if "skript" in eintrag else None
    return Test(quelle=quelle, adresse=adresse, skript=skript)


def _stream(eintrag, nummer: int) -> Stream:
    wo = f"Stream {nummer}"
    if not isinstance(eintrag, dict):
        raise StreamFehler(f"{wo}: kein gueltiger Eintrag")
    kennung = _text(eintrag, "id", wo)
    wo = f"Stream '{kennung}'"
    if not _ID.match(kennung) or kennung in _RESERVIERT:
        raise StreamFehler(f"{wo}: id nur aus a-z, 0-9 und _, nicht {sorted(_RESERVIERT)}")
    umgebung = eintrag.get("umgebung", {})
    if not isinstance(umgebung, dict) or not all(
        isinstance(wert, str) for wert in umgebung.values()
    ):
        raise StreamFehler(f"{wo}: 'umgebung' braucht Text als Werte")
    return Stream(
        id=kennung,
        name=_text(eintrag, "name", wo),
        skript=_skript(eintrag.get("skript"), wo),
        senden=_text(eintrag, "senden", wo),
        test=_test(eintrag.get("test"), wo),
        umgebung=dict(umgebung),
    )


def laden(pfad: Path | None = None) -> list:
    """Liest alle Streams. Wirft StreamFehler mit einer lesbaren Meldung."""
    pfad = pfad or konf.STREAMS
    try:
        daten = tomllib.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise StreamFehler(f"{pfad} fehlt") from None
    except (OSError, tomllib.TOMLDecodeError) as fehler:
        raise StreamFehler(f"{pfad.name}: {fehler}") from None

    eintraege = daten.get("stream", [])
    if not isinstance(eintraege, list):
        raise StreamFehler(f"{pfad.name}: Streams als [[stream]] angeben")
    streams = [_stream(eintrag, nummer) for nummer, eintrag in enumerate(eintraege, 1)]

    doppelt = {s.id for s in streams if [t.id for t in streams].count(s.id) > 1}
    if doppelt:
        raise StreamFehler(f"{pfad.name}: id mehrfach vergeben: {', '.join(sorted(doppelt))}")
    if len(streams) > MAX_STREAMS:
        raise StreamFehler(
            f"{pfad.name}: hoechstens {MAX_STREAMS} Streams, mehr passen nicht auf den Bildschirm"
        )
    return streams


def protokolle(streams: list) -> list:
    """(Anzeige, Pfad) fuer die Protokollansicht, Streams in ihrer Reihenfolge."""
    liste = [("Studio", konf.PROTOKOLL)]
    for stream in streams:
        liste.append((stream.name, stream.protokoll))
        if stream.test_id:
            liste.append((f"{stream.name} Test", stream.test_protokoll))
    return liste + [("Mitschnitt", konf.LOG_MITSCHNITT), ("REAPER", konf.LOG_REAPER)]


def baue_verwaltung(streams: list) -> Dienstverwaltung:
    verwaltung = Dienstverwaltung()
    umgebung = {"TONTECHNIK_GEHEIMNISSE": str(konf.GEHEIMNISSE)}
    for stream in streams:
        verwaltung.registriere(Dienst(
            stream.id, stream.name, stream.skript, stream.protokoll,
            {**umgebung, **stream.umgebung},
        ))
        if stream.test_id:
            verwaltung.registriere(Dienst(
                stream.test_id, f"{stream.name} Test", stream.test.skript,
                stream.test_protokoll, umgebung,
            ))
    verwaltung.registriere(Dienst(
        "mitschnitt", "MP3-Mitschnitt", konf.SKRIPT_MITSCHNITT, konf.LOG_MITSCHNITT, umgebung
    ))
    return verwaltung


def streams_laden() -> tuple:
    """(Streams, Fehlermeldung). Bei einem Fehler startet die Oberflaeche ohne
    Streams und zeigt die Meldung in der Kopfzeile."""
    try:
        return laden(), None
    except StreamFehler as fehler:
        log.error("streams.toml: %s", fehler)
        return [], str(fehler)
