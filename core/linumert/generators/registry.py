"""Rejestr generatorów: nazwa + wersja → klasa (sesja 039).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 039

Program .lnx zapisuje wersję generatora każdego kroku. Kompilator bierze dokładnie tę wersję,
nigdy „najnowszą”, więc stary program daje po aktualizacji ten sam G-code; brak wersji = błąd
P-5011. Nowa wersja generatora to nowa klasa z wyższym `version` (stara zostaje w rejestrze).
"""

from __future__ import annotations

import re

from .base import BaseMacroGenerator

NAME = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


class RegistryError(ValueError):
    """Niepoprawna rejestracja generatora (błąd programisty, komunikat po polsku)."""


class GeneratorRegistry:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, int], type[BaseMacroGenerator]] = {}

    def register(self, cls: type[BaseMacroGenerator]) -> type[BaseMacroGenerator]:
        """Rejestruje klasę (można użyć jako dekoratora)."""
        name = getattr(cls, "name", None)
        version = getattr(cls, "version", None)
        if not isinstance(name, str) or not NAME.match(name):
            raise RegistryError(f"{cls.__name__}: nazwa generatora {name!r} "
                                "(dozwolone: małe litery, cyfry, _)")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise RegistryError(f"{cls.__name__}: wersja musi być liczbą całkowitą >= 1")
        names = [f.name for f in cls.fields]
        if len(names) != len(set(names)):
            raise RegistryError(f"{name}: powtórzone nazwy pól")
        key = (name, version)
        if key in self._by_key and self._by_key[key] is not cls:
            raise RegistryError(f"{name} v{version} jest już zarejestrowany")
        self._by_key[key] = cls
        return cls

    def get(self, name: str, version: int) -> BaseMacroGenerator | None:
        cls = self._by_key.get((name, version))
        return cls() if cls is not None else None

    def latest(self, name: str) -> BaseMacroGenerator | None:
        """Najnowsza wersja (dla nowych kroków w edytorze, nie dla kompilacji)."""
        versions = [v for (n, v) in self._by_key if n == name]
        return self.get(name, max(versions)) if versions else None

    def names(self) -> list[str]:
        return sorted({n for (n, _) in self._by_key})

    def __contains__(self, key: object) -> bool:
        return key in self._by_key


# Rejestr domyślny: generatory wbudowane rejestrują się tu w sesjach 040–043.
DEFAULT_REGISTRY = GeneratorRegistry()
