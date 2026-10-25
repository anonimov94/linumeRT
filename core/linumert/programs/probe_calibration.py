"""Kalibracja sondy na wzorcu: stała poprawka na oś i kierunek dojazdu.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-25 · sesja 033.

Odczyt sondy (`stat.probed_position`) różni się od prawdziwej płaszczyzny o wartość zależną od osi
i kierunku dojazdu (luz, sprężystość, opóźnienie zadziałania), zwykle stałą przy tej samej
procedurze (ten sam posuw dokładny). Kalibracja mierzy wzorzec o znanym położeniu ścian tą samą
procedurą i zapisuje
poprawkę `prawdziwe − zmierzone` dla każdej pary oś/kierunek. Poprawka nie zmienia sterownika ani
modelu napędów, a odczyt z innym posuwem lub innym kierunkiem bez własnej poprawki jest odrzucany.

Klucz: litera osi i kierunek ruchu sondy, np. `X+` (sonda jedzie w stronę +X), `Z-`.
Jednostki: mm. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path

VERSION = 1
AXES = "XYZABC"
MAX_CORRECTION = 0.1        # mm; więcej to usterka (zły wzorzec, sonda), nie kalibracja
MAX_SPREAD = 0.005          # mm; większy rozrzut powtórzeń = kalibracja odrzucona


class CalibrationError(ValueError):
    """Niepoprawna kalibracja albo brak poprawki dla żądanej osi/kierunku."""


def key(axis: str, direction: int) -> str:
    axis = axis.upper()
    if axis not in AXES or len(axis) != 1:
        raise CalibrationError(f"nieznana oś: {axis!r}")
    if direction not in (-1, 1):
        raise CalibrationError("kierunek sondowania to +1 albo −1")
    return f"{axis}{'+' if direction > 0 else '-'}"


def _number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise CalibrationError(f"{name}: oczekiwano skończonej liczby")
    return float(value)


@dataclass
class ProbeCalibration:
    """Poprawki odczytu sondy. `feed` to posuw dokładnego przejazdu, dla którego je wyznaczono."""

    feed: float
    corrections: dict[str, float] = field(default_factory=dict)
    spread: dict[str, float] = field(default_factory=dict)

    def calibrate(self, axis: str, direction: int, measured: list[float], true: float) -> float:
        """Dodaje poprawkę z powtórzonych odczytów `measured` wzorca o ścianie w `true`."""
        k = key(axis, direction)
        if not measured:
            raise CalibrationError(f"{k}: brak odczytów")
        values = [_number(v, f"{k}: odczyt") for v in measured]
        true = _number(true, f"{k}: położenie wzorca")
        spread = max(values) - min(values)
        if spread > MAX_SPREAD:
            raise CalibrationError(f"{k}: rozrzut odczytów {spread:.4f} mm > {MAX_SPREAD} mm")
        correction = true - sum(values) / len(values)
        if abs(correction) > MAX_CORRECTION:
            raise CalibrationError(f"{k}: poprawka {correction:.4f} mm poza ±{MAX_CORRECTION} mm")
        self.corrections[k] = correction
        self.spread[k] = spread
        return correction

    def apply(self, axis: str, direction: int, measured: float) -> float:
        """Odczyt sondy po poprawce; bez wyznaczonej poprawki dla tej pary rzuca wyjątek."""
        k = key(axis, direction)
        if k not in self.corrections:
            raise CalibrationError(f"brak kalibracji sondy dla {k}")
        return _number(measured, f"{k}: odczyt") + self.corrections[k]

    def check_feed(self, feed: float) -> None:
        if abs(_number(feed, "posuw") - self.feed) > 1e-9:
            raise CalibrationError(f"kalibracja dla posuwu {self.feed}, użyto {feed}")

    def to_json(self) -> str:
        return json.dumps({"version": VERSION, "units": "mm", "feed": self.feed,
                           "corrections": self.corrections, "spread": self.spread},
                          sort_keys=True, indent=1)

    @classmethod
    def from_json(cls, text: str) -> ProbeCalibration:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CalibrationError(f"plik kalibracji nie jest JSON: {exc}") from exc
        if (not isinstance(data, dict) or data.get("version") != VERSION
                or data.get("units") != "mm"):
            raise CalibrationError("nieobsługiwana wersja albo jednostki kalibracji")
        extra = set(data) - {"version", "units", "feed", "corrections", "spread"}
        if extra:
            raise CalibrationError(f"nieznane pola kalibracji: {sorted(extra)}")
        cal = cls(_number(data.get("feed"), "feed"))
        for name in ("corrections", "spread"):
            raw = data.get(name)
            if not isinstance(raw, dict):
                raise CalibrationError(f"{name}: oczekiwano słownika")
            for k, v in raw.items():
                if len(k) != 2 or k[0] not in AXES or k[1] not in "+-":
                    raise CalibrationError(f"{name}: nieprawidłowy klucz {k!r}")
                v = _number(v, f"{name}[{k}]")
                if name == "corrections" and abs(v) > MAX_CORRECTION:
                    raise CalibrationError(f"{k}: poprawka poza ±{MAX_CORRECTION} mm")
                getattr(cal, name)[k] = v
        return cal

    def save(self, path: Path | str) -> None:
        """Zapis atomowy (plik tymczasowy w tym samym katalogu, potem zamiana)."""
        path = Path(path)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(self.to_json())
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, path: Path | str) -> ProbeCalibration:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
