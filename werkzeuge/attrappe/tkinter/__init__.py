"""Attrappe von tkinter: nur zum Durchlaufen des Aufbaus ohne Bildschirm."""


class Stub:
    def __init__(self, *a, **k):
        self._kinder = []

    def __getattr__(self, name):
        def ruf(*a, **k):
            if name == "yview":
                return (0.0, 1.0)
            if name == "state":
                return []
            if name in ("get", "cget"):
                return ""
            if name == "families":
                return ["Inter", "JetBrains Mono"]
            if name == "winfo_children":
                return []
            return Stub()

        return ruf


class TclError(Exception):
    pass


class Tk(Stub):
    pass


class Frame(Stub):
    pass


class Canvas(Stub):
    def create_oval(self, *a, **k):
        return 1


class Text(Stub):
    def yview(self):
        return (0.0, 1.0)


class PhotoImage(Stub):
    pass


class BooleanVar:
    def __init__(self, value=False, **k):
        self._wert = bool(value)

    def get(self):
        return self._wert

    def set(self, wert):
        self._wert = bool(wert)


class StringVar(BooleanVar):
    def __init__(self, value="", **k):
        self._wert = value
