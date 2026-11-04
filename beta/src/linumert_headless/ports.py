"""Porty (interfejsy) domen — granica między aplikacją a światem zewnętrznym.

SPDX-License-Identifier: GPL-2.0-or-later

Usługi mówią do portów, nie do LinuxCNC, Plant ani plików. Dzięki temu:

- backend maszyny można wymienić (atrapa → LinuxCNC → Plant) bez zmian w usługach i GUI,
- testy podpinają atrapy portów i sprawdzają logikę bez sprzętu,
- przyszłe GUI nie wie, co jest po drugiej stronie — widzi tylko operacje kontraktu.

Porty to ``typing.Protocol``: implementacja nie musi dziedziczyć, wystarczy że ma metody
(strukturalne typowanie). Atrapy testowe i backend LinuxCNC spełniają ten sam kontrakt.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from linumert.cnc.model import MachineSnapshot, Mode


@runtime_checkable
class MachinePort(Protocol):
    """Sterowanie maszyną. Jedyny port, który realnie porusza osią."""

    name: str

    def tick(self) -> None:
        """Odśwież stan (backend, który sam nie płynie, np. atrapa z zegarem wirtualnym)."""

    def snapshot(self) -> MachineSnapshot: ...

    def now(self) -> float:
        """Zegar backendu — ten sam, którym stemplowana jest migawka.

        Atrapa stempluje migawki czasem symulowanym (``FakeMachine.time``), więc wiek
        migawki trzeba liczyć tym samym zegarem; inaczej GUI widziałoby dane jako
        trwale nieświeże. LinuxCNC stempluje czasem systemowym i ten zegar oddaje.
        """

    def estop(self) -> None: ...

    def estop_reset(self) -> None: ...

    def power_on(self) -> None: ...

    def power_off(self) -> None: ...

    def set_mode(self, mode: Mode) -> None: ...

    def home(self, axis: str | None) -> None: ...

    def mdi(self, text: str) -> None: ...

    def load_program(self, name: str, text: str) -> None: ...

    def run(self, from_line: int = 1) -> None: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def stop(self) -> None: ...

    def set_override(self, feed: float | None = None, rapid: float | None = None,
                     spindle: float | None = None) -> None: ...

    def spindle(self, speed: float, direction: int) -> None: ...

    def jog(self, axis: str, speed: float) -> None: ...

    def jog_increment(self, axis: str, speed: float, distance: float) -> None: ...

    def jog_stop(self, axis: str | None) -> None: ...

    def set_work_offset(self, name: str, values: dict[str, float]) -> None: ...


@runtime_checkable
class Clock(Protocol):
    def __call__(self) -> float: ...


@runtime_checkable
class EventSink(Protocol):
    """Odbiorca zdarzeń (magazyn stanu, WebSocket, dziennik)."""

    def publish(self, topic: str, payload: dict[str, Any]) -> None: ...


class PathResolver(Protocol):
    """Rozwiązywanie nazw programów/maszyn na ścieżki w katalogach projektu."""

    def program(self, name: str) -> Any: ...

    def program_root(self) -> Any: ...

    def machine(self, name: str) -> Any: ...

    def machine_root(self) -> Any: ...


__all__ = ["Clock", "EventSink", "MachinePort", "PathResolver"]
