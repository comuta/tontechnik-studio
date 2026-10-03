#!/usr/bin/env python3
"""Baut die gesamte Oberflaeche gegen eine Tkinter-Attrappe auf.

Laeuft ohne Bildschirm, also auch ueber SSH, und faengt Tippfehler und
falsche Aufrufe ab, bevor sie vor dem Gottesdienst auffallen. Aufruf aus dem
Projektordner: python3 werkzeuge/probelauf.py
"""

import sys
from pathlib import Path

BASIS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASIS / "werkzeuge" / "attrappe"))
sys.path.insert(0, str(BASIS))

from tontechnik.gui.app import Anwendung, baue_verwaltung  # noqa: E402

app = Anwendung(baue_verwaltung(), None)
print("Fenster aufgebaut")

for ansicht in ("uebertragung", "protokoll", "start"):
    app.wechsle(ansicht)
    print("Ansicht ok:", ansicht)

app.aktualisieren()
app.vollbild_umschalten(True)
app.vollbild_umschalten(False)
app.nach_vorn()
app._takt()

start = app._ansichten["start"]
start.anlegen()
start.aufnahme.umschalten()
uebertragung = app._ansichten["uebertragung"]
for schalter in uebertragung.schalter:
    schalter.umschalten(schalter.schluessel)
    if schalter.knopf_zweit is not None:
        schalter.umschalten("mithoeren")
uebertragung.pegel_zeichnen()
app._pegel_takt()
uebertragung.alle_beenden()
uebertragung.beenden()
app._ansichten["protokoll"]._neu_laden()

print("Alle Bedienpfade durchlaufen.")
print("Meldungen oben sind erwartet, solange Skripte oder REAPER fehlen.")
