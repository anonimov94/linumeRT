"""Przygotówka: model i linia `;@STOCK` w nagłówku `.ngc` (NARZEDZIA_I_KOLIZJE.md §2).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 039

Składnia (jedna linia, słowa rozdzielone spacją, kolejność dowolna po typie):
    ;@STOCK BOX X120 Y80 Z30 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 TOP=1.0 MAT="aluminium"
    ;@STOCK CYL D60 H40 ORIGIN=TOP_CENTER OFFSET=G54
Wymiary w mm. ORIGIN = położenie zera układu detalu na przygotówce, OFFSET = układ detalu
(G54…G59.3), TOP = naddatek na górze [mm], MAT = materiał (tekst w cudzysłowie).
`format_stock_line(parse_stock_line(s))` daje postać kanoniczną; ponowne parsowanie jest
bezstratne (test).
"""

from __future__ import annotations

import re
import shlex
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PREFIX = ";@STOCK"
ORIGINS = tuple(f"{z}_{xy}" for z in ("TOP", "BOTTOM")
                for xy in ("FRONT_LEFT", "FRONT_RIGHT", "BACK_LEFT", "BACK_RIGHT", "CENTER"))
OFFSETS = ("G54", "G55", "G56", "G57", "G58", "G59", "G59.1", "G59.2", "G59.3")
_NUM = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")


class StockError(ValueError):
    """Niepoprawna przygotówka (komunikat po polsku)."""


class Stock(BaseModel):
    """Przygotówka: prostopadłościan (BOX: x, y, z) albo walec (CYL: d, h). Wymiary w mm."""

    model_config = ConfigDict(extra="forbid")

    shape: Literal["BOX", "CYL"]
    x: float | None = Field(default=None, gt=0)
    y: float | None = Field(default=None, gt=0)
    z: float | None = Field(default=None, gt=0)
    d: float | None = Field(default=None, gt=0)
    h: float | None = Field(default=None, gt=0)
    origin: Literal[ORIGINS] = "TOP_FRONT_LEFT"  # type: ignore[valid-type]
    offset: Literal[OFFSETS] = "G54"  # type: ignore[valid-type]
    top: float = Field(default=0.0, ge=0)
    material: str | None = Field(default=None, min_length=1, max_length=60)

    @model_validator(mode="after")
    def _dimensions(self) -> Stock:
        need, forbid = (("x", "y", "z"), ("d", "h")) if self.shape == "BOX" else \
            (("d", "h"), ("x", "y", "z"))
        missing = [n for n in need if getattr(self, n) is None]
        extra = [n for n in forbid if getattr(self, n) is not None]
        if missing:
            raise ValueError(f"{self.shape} wymaga wymiarów: {', '.join(missing).upper()}")
        if extra:
            raise ValueError(f"{self.shape} nie ma wymiarów: {', '.join(extra).upper()}")
        if self.material is not None and ('"' in self.material or "\n" in self.material):
            raise ValueError("materiał nie może zawierać cudzysłowu ani nowej linii")
        if self.shape == "CYL" and self.origin.endswith(("_LEFT", "_RIGHT")):
            raise ValueError("walec ma zero tylko w środku: ORIGIN=TOP_CENTER albo BOTTOM_CENTER")
        return self


def fmt_mm(value: float) -> str:
    """Liczba w zapisie stałym, do 4 miejsc po przecinku, bez zbędnych zer (deterministycznie)."""
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def format_stock_line(stock: Stock) -> str:
    """Postać kanoniczna linii `;@STOCK`."""
    words = [PREFIX, stock.shape]
    dims = ("x", "y", "z") if stock.shape == "BOX" else ("d", "h")
    words += [f"{n.upper()}{fmt_mm(getattr(stock, n))}" for n in dims]
    words += [f"ORIGIN={stock.origin}", f"OFFSET={stock.offset}"]
    if stock.top:
        words.append(f"TOP={fmt_mm(stock.top)}")
    if stock.material is not None:
        words.append(f'MAT="{stock.material}"')
    return " ".join(words)


def parse_stock_line(line: str) -> Stock:
    """Parsuje linię `;@STOCK …` (StockError z opisem po polsku)."""
    text = line.strip()
    if not text.upper().startswith(PREFIX):
        raise StockError(f"linia nie zaczyna się od {PREFIX}")
    try:
        words = shlex.split(text[len(PREFIX):], posix=True)
    except ValueError as exc:
        raise StockError(f"niezamknięty cudzysłów ({exc})") from None
    if not words:
        raise StockError("brak typu przygotówki (BOX albo CYL)")
    data: dict[str, object] = {"shape": words[0].upper()}
    for word in words[1:]:
        key, sep, value = word.partition("=")
        if sep:
            name = {"ORIGIN": "origin", "OFFSET": "offset", "TOP": "top",
                    "MAT": "material"}.get(key.upper())
            if name is None:
                raise StockError(f"nieznane słowo {key}=")
            data[name] = value.upper() if name in ("origin", "offset") else value
        else:
            letter, number = word[:1].upper(), word[1:]
            if letter not in "XYZDH" or not _NUM.match(number):
                raise StockError(f"niepoprawne słowo {word!r}")
            data[letter.lower()] = float(number)
        if "top" in data and isinstance(data["top"], str):
            if not _NUM.match(data["top"]):
                raise StockError(f"TOP={data['top']} nie jest liczbą")
            data["top"] = float(data["top"])
    try:
        return Stock.model_validate(data)
    except ValueError as exc:
        raise StockError(_first_error(exc)) from None


def _first_error(exc: ValueError) -> str:
    errors = getattr(exc, "errors", None)
    if callable(errors):
        first = errors()[0]
        where = ".".join(str(p) for p in first.get("loc", ()) if p != "__root__")
        message = str(first.get("msg", exc)).removeprefix("Value error, ")
        return f"{where}: {message}" if where else message
    return str(exc)
