"""Usługa maszyny: stan, tryby, bazowanie, JOG, MDI, AUTO, wrzeciono, offsety.

SPDX-License-Identifier: GPL-2.0-or-later

To jest warstwa, którą GUI steruje maszyną. Zasady:

- **stan z migawki**, nie z odpytywania backendu przez GUI (``MachineState``),
- **deadman jogu** i limiter poleceń z ``session.py`` obowiązują każdy transport,
- polecenia zatrzymujące (``estop``, ``stop``, ``pause``, ``jog_stop``, ``power_off``)
  przechodzą zawsze — limiter ich nie blokuje,
- błędy backendu wracają jako ``Conflict``/``SafetyRefused`` z komunikatem po polsku,
  więc GUI może go pokazać bez tłumaczenia wyjątków.

Usługa nie wie, czy pod spodem jest atrapa, LinuxCNC czy Plant — widzi tylko ``MachinePort``.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from linumert.cnc.model import AXIS_LETTERS, MachineSnapshot, Mode

from ..errors import Conflict, NotImplementedCapability, SafetyRefused
from ..ports import MachinePort
from ..schema import (
    AxisState,
    HomeRequest,
    JogIncrementRequest,
    JogRequest,
    JogStopRequest,
    MachineState,
    MdiRequest,
    ModeRequest,
    Ok,
    OverrideRequest,
    RunRequest,
    SpindleRequest,
    SpindleState,
    WorkOffsetRequest,
    finite,
)
from ..session import SessionManager

MODES = {m.value: m for m in Mode}
MAX_JOG_SPEED = 50.0  # mm/s (3000 mm/min) — górna granica z GUI


class MachineService:
    """Operacje domeny ``machine``."""

    domain = "machine"

    def __init__(self, backend: MachinePort, sessions: SessionManager,
                 clock: Callable[[], float] = time.monotonic,
                 sink: Callable[[str, dict], None] | None = None):
        self.backend = backend
        self.sessions = sessions
        self._clock = clock
        self._sink = sink

    def _now(self) -> float:
        """Zegar do liczenia wieku migawki — zegar backendu, nie czas systemowy.

        Atrapa stempluje migawki czasem symulowanym (start 0.0); liczonym czasem
        systemowym każda migawka byłaby "nieświeża" (wiek = uptime hosta).
        Starsze atrapy bez ``now()`` dostają zegar serwisu.
        """
        backend_now = getattr(self.backend, "now", None)
        return backend_now() if callable(backend_now) else self._clock()

    # ---- stan --------------------------------------------------------------
    def state(self) -> MachineState:
        snap = self.backend.snapshot()
        axes = [
            AxisState(
                name=a.name,
                position=round(a.position, 4),
                commanded=round(a.commanded, 4),
                work_position=round(snap.work_position(a.name), 4),
                following_error=round(a.following_error, 6),
                homed=a.homed,
                soft_min=finite(a.soft_min),
                soft_max=finite(a.soft_max),
                limit_hit=a.limit_hit,
            )
            for a in snap.axes
        ]
        state = MachineState(
            fresh=snap.is_fresh(self._now()),
            age_s=round(snap.age(self._now()), 4),
            task_state=snap.task_state.value,
            mode=snap.mode.value,
            interp_state=snap.interp_state.value,
            axes=axes,
            all_homed=snap.all_homed,
            current_line=snap.current_line,
            program=snap.program_file,
            feed_override=snap.feed_override,
            rapid_override=snap.rapid_override,
            spindle=SpindleState(
                speed=snap.spindle_speed,
                direction=snap.spindle_direction,
                override=snap.spindle_override,
                running=snap.spindle_running,
            ),
            tool_number=snap.tool_number,
            work_offset_name=snap.work_offset_name,
            work_offset=dict(snap.work_offset),
            gcodes=list(snap.active_gcodes),
            mcodes=list(snap.active_mcodes),
            errors=list(snap.errors),
            backend=getattr(self.backend, "name", "unknown"),
        )
        return state

    def publish_state(self) -> MachineState:
        """Odświeża stan i publikuje go w magazynie (robi to pętla aplikacji)."""
        state = self.state()
        if self._sink is not None:
            self._sink("machine", state.model_dump())
        return state

    # ---- zasilanie i E-STOP ------------------------------------------------
    def estop(self) -> Ok:
        self.sessions.jog_stop(None)
        self.backend.estop()
        return Ok(message="E-STOP aktywny")

    def estop_reset(self) -> Ok:
        """Reset E-STOP z API — wymaga roli serwisu (sprawdza kontrakt operacji)."""
        self.backend.estop_reset()
        return Ok(message="E-STOP zresetowany; wymagane włączenie zasilania")

    def power_on(self) -> Ok:
        self.backend.power_on()
        return Ok(message="zasilanie włączone")

    def power_off(self) -> Ok:
        self.sessions.jog_stop(None)
        self.backend.power_off()
        return Ok(message="zasilanie wyłączone")

    # ---- tryby -------------------------------------------------------------
    def set_mode(self, request: ModeRequest) -> Ok:
        self.backend.set_mode(MODES[request.mode])
        return Ok(message=f"tryb {request.mode}")

    def home(self, request: HomeRequest) -> Ok:
        self._require_power("bazowanie")
        self.backend.home(request.axis)
        return Ok(message="bazowanie " + (request.axis or "wszystkich osi"))

    # ---- MDI / AUTO --------------------------------------------------------
    def mdi(self, request: MdiRequest) -> Ok:
        self._require_power("MDI")
        self.backend.mdi(request.text)
        return Ok(message=f"MDI: {request.text}")

    def load_program(self, name: str, text: str) -> Ok:
        self.backend.load_program(name, text)
        return Ok(message=f"wczytano program {name}")

    def run(self, request: RunRequest) -> Ok:
        self._require_power("start programu")
        self.backend.run(request.from_line)
        return Ok(message="program uruchomiony")

    def pause(self) -> Ok:
        self.backend.pause()
        return Ok(message="pauza")

    def resume(self) -> Ok:
        self.backend.resume()
        return Ok(message="wznowiono")

    def stop(self) -> Ok:
        self.sessions.jog_stop(None)
        self.backend.stop()
        return Ok(message="ruch zatrzymany")

    # ---- nastawy -----------------------------------------------------------
    def set_override(self, request: OverrideRequest) -> Ok:
        self.backend.set_override(feed=request.feed, rapid=request.rapid,
                                  spindle=request.spindle)
        return Ok(message="nastawy zaktualizowane")

    def spindle(self, request: SpindleRequest) -> Ok:
        self._require_power("wrzeciono")
        self.backend.spindle(request.speed, request.direction)
        if request.speed == 0 or request.direction == 0:
            return Ok(message="wrzeciono zatrzymane")
        return Ok(message=f"wrzeciono {request.speed:g} obr/min")

    def set_work_offset(self, request: WorkOffsetRequest) -> Ok:
        self.backend.set_work_offset(request.name, dict(request.values))
        return Ok(message=f"offset {request.name} ustawiony")

    # ---- JOG ---------------------------------------------------------------
    def jog(self, request: JogRequest) -> Ok:
        """Jog ciągły z deadmanem: klient odświeża co ~100 ms, inaczej ruch stanie."""
        self._require_power("jog")
        session = request.session or "local"
        if abs(request.speed) > MAX_JOG_SPEED:
            raise SafetyRefused(f"prędkość jogu ponad {MAX_JOG_SPEED:g} mm/s")
        if request.speed == 0.0:
            self.sessions.jog_stop(request.axis)
            self.backend.jog_stop(request.axis)
            return Ok(message=f"jog {request.axis} zatrzymany")
        if self.sessions.owned_by_other(request.axis, session):
            raise Conflict("jog tej osi należy do innej sesji")
        self.sessions.jog_start(request.axis, session)
        self.backend.jog(request.axis, request.speed)
        return Ok(message=f"jog {request.axis} {request.speed:+g} mm/s")

    def jog_increment(self, request: JogIncrementRequest) -> Ok:
        self._require_power("jog przyrostowy")
        self.sessions.jog_increment(request.axis)
        self.backend.jog_increment(request.axis, request.speed, request.distance)
        return Ok(message=f"jog {request.axis} o {request.distance:g} mm")

    def jog_stop(self, request: JogStopRequest) -> Ok:
        self.sessions.jog_stop(request.axis)
        self.backend.jog_stop(request.axis)
        return Ok(message="jog zatrzymany")

    def expired_jog(self) -> list[str]:
        """Osie po wygaśnięciu deadmana — aplikacja wysyła stop i ponawia."""
        axes = self.sessions.expired_jog()
        for axis in axes:
            try:
                self.backend.jog_stop(axis)
            except Exception:  # ponowimy w następnym cyklu
                self.sessions.jog_start(axis, "watchdog")
        return axes

    # ---- funkcje planowane -------------------------------------------------
    def tool_change(self) -> Ok:
        """Ręczna/automatyczna zmiana narzędzia: wymaga sekwencji HAL i potwierdzeń GUI."""
        raise NotImplementedCapability(
            "machine.tool_change",
            "wdrożenie po podpięciu ATC: makro M6 (machine.atc_macro) + potwierdzenia operatora",
        )

    # ---- pomocnicze --------------------------------------------------------
    def _require_power(self, what: str) -> None:
        snap: MachineSnapshot = self.backend.snapshot()
        if snap.task_state.value in {"estop", "estop_reset", "off"}:
            raise SafetyRefused(f"{what} wymaga włączonego zasilania",
                                details={"task_state": snap.task_state.value})

    @staticmethod
    def known_axes() -> tuple[str, ...]:
        return AXIS_LETTERS


__all__ = ["MAX_JOG_SPEED", "MachineService"]
