"""Ścieżki projektu beta — jedno miejsce na layout katalogów.

SPDX-License-Identifier: GPL-2.0-or-later

Aplikacja headless nie ma ekranu, więc cały „interfejs" do danych to katalogi: programy NC,
maszyny (``machine.yaml``), scenariusze Plant, baza narzędzi, raporty. Ten moduł rozwiązuje
nazwy na ścieżki i pilnuje, że nazwa nie wychodzi poza swój katalog (``..``, ścieżka
bezwzględna) — inaczej dowolny klient API mógłby czytać i pisać poza projektem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..errors import InvalidRequest, NotFound

ROOT = Path(__file__).resolve().parents[3]  # beta/


@dataclass
class ProjectPaths:
    """Katalogi projektu; ``root`` pozwala wskazać inne miejsce (testy, wdrożenie)."""

    root: Path = field(default_factory=lambda: ROOT)

    # ---- katalogi ----------------------------------------------------------
    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def programs(self) -> Path:
        return self.config / "nc_files"

    @property
    def machines(self) -> Path:
        return self.config / "machines"

    @property
    def sim(self) -> Path:
        return self.config / "sim" / "linumert_xyz"

    @property
    def plant_config(self) -> Path:
        return self.config / "plant" / "linumert_plant_xyz"

    @property
    def drives(self) -> Path:
        return self.root / "library" / "drives"

    @property
    def scenarios(self) -> Path:
        return self.root / "scenarios"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def reports(self) -> Path:
        return self.state / "raporty"

    @property
    def default_ini(self) -> Path:
        return self.sim / "linumert_xyz.ini"

    @property
    def tools_db(self) -> Path:
        return self.plant_config / "linumert_tools.db"

    # ---- rozwiązywanie nazw ------------------------------------------------
    def resolve(self, name: str, root: Path, *, must_exist: bool = True,
                extensions: tuple[str, ...] = ()) -> Path:
        """Bezpieczne przekształcenie nazwy w ścieżkę wewnątrz ``root``."""
        if not name or name in {".", ".."}:
            raise InvalidRequest("pusta nazwa")
        candidate = (root / name).resolve()
        base = root.resolve()
        if base not in candidate.parents and candidate != base:
            raise InvalidRequest(f"nazwa wychodzi poza katalog {root.name}",
                                 details={"name": name})
        if not candidate.exists() and extensions:
            for ext in extensions:
                with_ext = candidate.with_suffix(ext)
                if with_ext.exists():
                    return with_ext
        if must_exist and not candidate.exists():
            raise NotFound(f"nie znaleziono {name}", details={"name": name, "root": str(root)})
        return candidate

    def program(self, name: str) -> Path:
        return self.resolve(name, self.programs, extensions=(".ngc", ".lnx"))

    def machine(self, name: str) -> Path:
        return self.resolve(name, self.machines, extensions=(".yaml", ".yml"))

    def scenario(self, name: str) -> Path:
        path = Path(name)
        if path.is_absolute() or "/" in name:
            candidate = path.resolve()
            if candidate.exists():
                return candidate
            raise NotFound(f"nie znaleziono scenariusza {name}", details={"name": name})
        return self.resolve(name, self.scenarios, extensions=(".yaml", ".yml"))

    def ensure_state(self) -> Path:
        self.reports.mkdir(parents=True, exist_ok=True)
        return self.reports


__all__ = ["ROOT", "ProjectPaths"]
