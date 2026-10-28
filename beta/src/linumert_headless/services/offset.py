"""Usługa offsetów: przygotówka, zero detalu, sondowanie i kalibracja sondy.

SPDX-License-Identifier: GPL-2.0-or-later

Domena ``offset`` obejmuje to, co w ekranie Qt było osobnymi stronami (przygotówka, zero
detalu, korekcje). Backend liczy i waliduje, **nie rysuje**: definicja przygotówki wraca
jako dane (``Stock``/``Workpiece``), a GUI decyduje, jak je pokazać.

Kalibracja sondy (``linumert.programs.probe_calibration``) działa na liczbach: pomiar →
współczynnik → zapis JSON. Samo sondowanie (ruch G38.x) wymaga maszyny i jest osobną
operacją ``offset.probe_run`` — w kontrakcie jako ``planned``, bo potrzebuje sprzętu.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from linumert.programs.probe_calibration import (
    CalibrationError,
    ProbeCalibration,
    key,
)
from linumert.programs.stock import Stock, StockError, format_stock_line, parse_stock_line
from linumert.programs.workpiece import Workpiece

from ..errors import InvalidRequest, NotImplementedCapability
from ..schema import Model, Ok
from .paths import ProjectPaths

PROBE_FEED_MM_MIN = 100.0  # posuw dokładnego przejazdu sondy [mm/min]


class StockOut(Model):
    line: str = ""
    shape: str = ""
    x: float | None = None
    y: float | None = None
    z: float | None = None
    d: float | None = None
    h: float | None = None
    origin: str = ""
    offset: str = ""
    top: float = 0.0
    material: str | None = None


class StockIn(Model):
    line: str = ""
    shape: str = "BOX"
    x: float | None = None
    y: float | None = None
    z: float | None = None
    d: float | None = None
    h: float | None = None
    origin: str = "TOP_FRONT_LEFT"
    offset: str = "G54"
    top: float = 0.0
    material: str | None = None


class WorkpieceOut(Model):
    shape: str = ""
    x: float = 0.0
    y: float = 0.0
    height: float = 0.0
    diameter: float = 0.0
    bore: float = 0.0
    anchor: str = ""
    offset: str = ""
    material: str = ""
    position: list[float] = []
    gcode: str = ""


class ProbeCalibrateIn(Model):
    axis: str
    direction: int
    measured: list[float]
    true_value: float


class ProbeApplyIn(Model):
    axis: str
    direction: int
    measured: float


class ProbeOut(Model):
    """Wynik kalibracji albo zastosowania poprawki sondy.

    ``correction`` to poprawka w mm wyznaczona z powtórzonych odczytów wzorca
    (``true_value - średnia(odczytów)``) — tak liczy ją rdzeń, więc nie udajemy
    współczynnika. ``value`` wypełnia tylko ``probe_apply`` (odczyt po poprawce).
    """

    ok: bool = True
    axis: str = ""
    direction: int = 0
    correction: float = 0.0
    spread: float = Field(0.0, description="rozrzut odczytów [mm] — miara powtarzalności")
    value: float = 0.0
    message: str = ""


class OffsetService:
    """Operacje domeny ``offset``."""

    domain = "offset"

    def __init__(self, paths: ProjectPaths, calibration_file: Path | None = None,
                 probe_feed: float = PROBE_FEED_MM_MIN):
        self.paths = paths
        self.calibration_file = calibration_file or (paths.state / "probe_calibration.json")
        self.probe_feed = probe_feed
        self._stock: Stock | None = None
        self._workpiece: Workpiece | None = None

    # ---- przygotówka -------------------------------------------------------
    def stock_get(self) -> StockOut:
        if self._stock is None:
            return StockOut(line="", shape="")
        stock = self._stock
        return StockOut(line=format_stock_line(stock), shape=stock.shape, x=stock.x,
                        y=stock.y, z=stock.z, d=stock.d, h=stock.h, origin=stock.origin,
                        offset=stock.offset, top=stock.top, material=stock.material)

    def stock_set(self, request: StockIn) -> StockOut:
        try:
            if request.line:
                stock = parse_stock_line(request.line)
            else:
                stock = Stock(shape=request.shape.upper(), x=request.x, y=request.y,
                              z=request.z, d=request.d, h=request.h, origin=request.origin,
                              offset=request.offset, top=request.top, material=request.material)
        except (StockError, ValueError) as exc:
            raise InvalidRequest(f"niepoprawna przygotówka: {exc}") from exc
        self._stock = stock
        return self.stock_get()

    # ---- detal -------------------------------------------------------------
    def workpiece_get(self) -> WorkpieceOut:
        piece = self._workpiece or Workpiece()
        return self._workpiece_out(piece)

    def workpiece_set(self, values: dict) -> WorkpieceOut:
        current = self._workpiece or Workpiece()
        try:
            piece = Workpiece(**{**current.__dict__, **values})
        except (TypeError, ValueError) as exc:
            raise InvalidRequest(f"niepoprawny detal: {exc}") from exc
        self._workpiece = piece
        return self._workpiece_out(piece)

    def _workpiece_out(self, piece: Workpiece) -> WorkpieceOut:
        from linumert.programs.workpiece import offset_command

        try:
            gcode = offset_command(piece)
        except Exception:
            gcode = ""
        return WorkpieceOut(
            shape=piece.shape, x=piece.x, y=piece.y, height=piece.height,
            diameter=piece.diameter, bore=piece.bore, anchor=piece.anchor,
            offset=piece.offset, material=piece.material,
            position=[float(v) for v in piece.position], gcode=gcode,
        )

    # ---- sonda -------------------------------------------------------------
    def _calibration(self) -> ProbeCalibration:
        """Poprawki sondy; ``feed`` to posuw dokładnego przejazdu, dla którego je wyznaczono."""
        if self.calibration_file.exists():
            return ProbeCalibration.load(self.calibration_file)
        return ProbeCalibration(feed=self.probe_feed)

    def probe_calibrate(self, request: ProbeCalibrateIn) -> ProbeOut:
        calibration = self._calibration()
        try:
            correction = calibration.calibrate(request.axis, request.direction,
                                               request.measured, request.true_value)
            self.calibration_file.parent.mkdir(parents=True, exist_ok=True)
            calibration.save(self.calibration_file)
        except CalibrationError as exc:
            raise InvalidRequest(f"kalibracja sondy nie powiodła się: {exc}") from exc
        spread = calibration.spread.get(key(request.axis, request.direction), 0.0)
        return ProbeOut(axis=request.axis, direction=request.direction,
                        correction=round(correction, 6), spread=round(spread, 6),
                        message=f"poprawka {correction:+.4f} mm; zapisano")

    def probe_apply(self, request: ProbeApplyIn) -> ProbeOut:
        calibration = self._calibration()
        try:
            value = calibration.apply(request.axis, request.direction, request.measured)
        except CalibrationError as exc:
            raise InvalidRequest(f"zastosowanie kalibracji nie powiodło się: {exc}") from exc
        return ProbeOut(axis=request.axis, direction=request.direction, value=value,
                        message="skorygowany pomiar")

    def probe_run(self) -> Ok:
        """Sondowanie G38.x: wymaga maszyny, potwierdzeń i nadzoru posuwu."""
        raise NotImplementedCapability(
            "offset.probe_run",
            "sekwencja G38.2 + check_feed() + zapis do .var; wymaga backendu maszyny i HAL",
        )


__all__ = ["OffsetService", "ProbeApplyIn", "ProbeCalibrateIn", "ProbeOut",
           "StockIn", "StockOut", "WorkpieceOut"]
