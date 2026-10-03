"""Farben, Schriften und ttk-Stile.

Die Oberflaeche steht neben dem Mischpult und wird unter Zeitdruck bedient.
Darum: ruhige, kuehle Graustufen als Gehaeuse, eine einzige Aktionsfarbe und
Rot ausschliesslich fuer den Sendezustand - wie das Rotlicht im Studio.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

FARBEN = {
    "grund": "#e8eaed",
    "flaeche": "#ffffff",
    "linie": "#c9ced6",
    "text": "#15181c",
    "gedaempft": "#5c646e",
    "aktion": "#1f4f6f",
    "aktion_hell": "#2a6489",
    "sendung": "#b3291c",
    "bereit": "#2f7d4f",
    "aus": "#aab1ba",
}

_SCHRIFTEN = ("Inter", "Cantarell", "Ubuntu", "DejaVu Sans")
_FESTBREITE = ("JetBrains Mono", "Ubuntu Mono", "DejaVu Sans Mono", "Courier")


def _erste_vorhandene(root: tk.Misc, kandidaten) -> str:
    verfuegbar = {name.lower() for name in tkfont.families(root)}
    for kandidat in kandidaten:
        if kandidat.lower() in verfuegbar:
            return kandidat
    return "TkDefaultFont"


def anwenden(root: tk.Tk) -> dict:
    familie = _erste_vorhandene(root, _SCHRIFTEN)
    fest = _erste_vorhandene(root, _FESTBREITE)

    schriften = {
        "titel": (familie, 16, "bold"),
        "spalte": (familie, 13, "bold"),
        "abschnitt": (familie, 12, "bold"),
        "text": (familie, 11),
        "klein": (familie, 10),
        "knopf": (familie, 12, "bold"),
        "fest": (fest, 10),
    }

    root.configure(background=FARBEN["grund"])
    stil = ttk.Style(root)
    stil.theme_use("clam")

    stil.configure("TFrame", background=FARBEN["grund"])
    stil.configure("Karte.TFrame", background=FARBEN["flaeche"])
    stil.configure("Kopf.TFrame", background=FARBEN["flaeche"])

    stil.configure(
        "TLabel", background=FARBEN["grund"], foreground=FARBEN["text"], font=schriften["text"]
    )
    stil.configure("Titel.TLabel", font=schriften["titel"], background=FARBEN["flaeche"])
    stil.configure("Abschnitt.TLabel", font=schriften["abschnitt"], background=FARBEN["flaeche"])
    # Ueberschrift je Bildschirmhaelfte, auf dem Grund statt auf einer Karte.
    stil.configure(
        "Spaltentitel.TLabel",
        font=schriften["spalte"],
        foreground=FARBEN["gedaempft"],
        background=FARBEN["grund"],
    )
    stil.configure(
        "Gedaempft.TLabel", font=schriften["klein"], foreground=FARBEN["gedaempft"]
    )
    stil.configure(
        "KarteText.TLabel", background=FARBEN["flaeche"], font=schriften["text"]
    )
    stil.configure(
        "KarteKlein.TLabel",
        background=FARBEN["flaeche"],
        foreground=FARBEN["gedaempft"],
        font=schriften["klein"],
    )
    stil.configure(
        "Fehler.TLabel", font=schriften["klein"], foreground=FARBEN["sendung"]
    )
    stil.configure(
        "Uhr.TLabel",
        background=FARBEN["flaeche"],
        foreground=FARBEN["text"],
        font=(fest, 22),
    )
    stil.configure(
        "KarteFehler.TLabel",
        background=FARBEN["flaeche"],
        foreground=FARBEN["sendung"],
        font=schriften["klein"],
    )
    stil.configure(
        "KopfFehler.TLabel",
        background=FARBEN["flaeche"],
        foreground=FARBEN["sendung"],
        font=schriften["klein"],
    )
    stil.configure(
        "KopfKlein.TLabel",
        background=FARBEN["flaeche"],
        foreground=FARBEN["gedaempft"],
        font=schriften["klein"],
    )

    stil.configure(
        "Aktion.TButton",
        font=schriften["knopf"],
        foreground="#ffffff",
        background=FARBEN["aktion"],
        bordercolor=FARBEN["aktion"],
        focuscolor=FARBEN["aktion_hell"],
        padding=(16, 12),
        relief="flat",
    )
    stil.map(
        "Aktion.TButton",
        background=[("active", FARBEN["aktion_hell"]), ("disabled", FARBEN["aus"])],
        bordercolor=[("active", FARBEN["aktion_hell"])],
    )

    stil.configure(
        "Stopp.TButton",
        font=schriften["knopf"],
        foreground="#ffffff",
        background=FARBEN["sendung"],
        bordercolor=FARBEN["sendung"],
        padding=(16, 12),
        relief="flat",
    )
    stil.map("Stopp.TButton", background=[("active", "#8f2116")])

    stil.configure(
        "Neben.TButton",
        font=schriften["text"],
        foreground=FARBEN["text"],
        background=FARBEN["flaeche"],
        bordercolor=FARBEN["linie"],
        padding=(12, 8),
        relief="solid",
    )
    stil.map("Neben.TButton", background=[("active", FARBEN["grund"])])


    stil.configure(
        "TEntry",
        fieldbackground=FARBEN["flaeche"],
        bordercolor=FARBEN["linie"],
        insertcolor=FARBEN["text"],
        padding=6,
    )
    stil.configure(
        "TCombobox",
        fieldbackground=FARBEN["flaeche"],
        background=FARBEN["flaeche"],
        bordercolor=FARBEN["linie"],
        padding=6,
    )
    stil.configure(
        "TCheckbutton", background=FARBEN["flaeche"], font=schriften["text"]
    )

    return schriften
