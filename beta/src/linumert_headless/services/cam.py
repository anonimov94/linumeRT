"""Usługa CAM: katalog generatorów cykli i generowanie G-code z parametrów.

SPDX-License-Identifier: GPL-2.0-or-later

Generatory (``linumert.generators``) rejestrują się przez ``register()`` w każdym module —
``load_generators()`` robi to raz dla całego procesu. Dzięki temu GUI dostaje **katalog
operacji CAM razem ze schematem parametrów** (``cam.operations``) i może zbudować formularze
bez wiedzy o Pythonie: nazwa, wersja, pola, wartości domyślne.

Backend zwraca wyłącznie tekst G-code. Podgląd, walidacja wizualna i rysowanie pozostają
w GUI — serwer nie generuje grafiki.
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any

from linumert.generators.registry import DEFAULT_REGISTRY, GeneratorRegistry, RegistryError

from ..errors import InvalidRequest, NotFound
from ..schema import CamCatalog, CamGenerateOut, CamGenerateRequest, CamOperation

GENERATOR_MODULES = (
    "basic", "shapes", "contours", "pockets", "pockets_v1", "drilling",
    "surfacing", "engraving", "relief", "stl_trace", "subroutines",
)

_loaded = False


def load_generators(registry: GeneratorRegistry | None = None) -> GeneratorRegistry:
    """Rejestruje wszystkie generatory (idempotentne)."""
    global _loaded
    target = registry or DEFAULT_REGISTRY
    for name in GENERATOR_MODULES:
        module = importlib.import_module(f"linumert.generators.{name}")
        register = getattr(module, "register", None)
        if callable(register):
            try:
                register(target)
            except RegistryError:
                continue  # już zarejestrowane
    _loaded = True
    return target


def _summary(generator: Any) -> str:
    """Opis generatora dla GUI.

    Generatory nie mają pola ``summary`` ani docstringu klasy — mają polski ``title``
    (np. "Kieszeń okrągła"). Czytanie ``summary`` przez ``getattr`` z domyślną wartością
    oddawało pusty opis dla wszystkich 16 generatorów, więc menu GUI nie miało etykiet.
    """
    text = str(getattr(generator, "summary", "")
               or getattr(generator, "title", "")
               or inspect.getdoc(generator)
               or "").strip()
    return text.splitlines()[0] if text else ""


def _parameters(generator: Any) -> dict[str, Any]:
    """Schemat parametrów generatora — podstawa formularza w GUI.

    Generatory opisują pola krotką dataklas ``Field`` (``linumert.generators.base``):
    nazwa, rodzaj, etykieta po polsku, jednostka, wartość domyślna, zakres i lista
    wyborów. Z tego GUI buduje formularz bez wiedzy o Pythonie.
    """
    params: dict[str, Any] = {}
    fields = getattr(generator, "fields", None) or getattr(generator, "PARAMETERS", None)
    if isinstance(fields, (tuple, list)) and fields:
        for field in fields:
            name = getattr(field, "name", None)
            if not name:
                continue
            default = getattr(field, "default", None)
            params[name] = {
                "label": getattr(field, "label", name),
                "type": getattr(field, "kind", "float"),
                "unit": getattr(field, "unit", ""),
                "default": default,
                "required": default is None,
                "min": getattr(field, "minimum", None),
                "max": getattr(field, "maximum", None),
                "choices": list(getattr(field, "choices", ()) or ()),
            }
        if params:
            return params
    if isinstance(fields, dict):
        for key, spec in fields.items():
            if isinstance(spec, dict):
                params[key] = {
                    "label": spec.get("label", key),
                    "type": spec.get("type", "float"),
                    "default": spec.get("default"),
                    "unit": spec.get("unit", ""),
                    "min": spec.get("min"),
                    "max": spec.get("max"),
                }
            else:
                params[key] = {"label": key, "type": "float", "default": spec}
        return params
    init = getattr(generator, "__init__", None)
    if init is None:
        return params
    try:
        signature = inspect.signature(init)
    except (TypeError, ValueError):
        return params
    for name, parameter in signature.parameters.items():
        if name in {"self", "cls"}:
            continue
        default = parameter.default
        params[name] = {
            "label": name,
            "type": "float" if isinstance(default, (int, float)) else "any",
            "default": None if default is inspect.Parameter.empty else default,
            "required": default is inspect.Parameter.empty,
        }
    return params


class CamService:
    """Operacje domeny ``cam``."""

    domain = "cam"

    def __init__(self, registry: GeneratorRegistry | None = None):
        self.registry = load_generators(registry)

    def operations(self) -> CamCatalog:
        items: list[CamOperation] = []
        for name in self.registry.names():
            generator = self.registry.latest(name)
            if generator is None:
                continue
            items.append(CamOperation(
                name=name,
                version=int(getattr(generator, "version", 1)),
                summary=_summary(generator),
                parameters=_parameters(generator),
            ))
        return CamCatalog(operations=sorted(items, key=lambda o: o.name))

    def generate(self, request: CamGenerateRequest) -> CamGenerateOut:
        generator = (self.registry.get(request.operation, request.version)
                     if request.version else self.registry.latest(request.operation))
        if generator is None:
            known = self.registry.names()
            if request.operation not in known:
                raise NotFound(f"nieznana operacja CAM {request.operation!r}",
                               details={"known": known})
            raise NotFound(f"brak wersji {request.version} generatora {request.operation}",
                           details={"operation": request.operation})
        # Rejestr zwraca INSTANCJE generatorów (nie klasy): parametry walidujemy
        # i generujemy przez API generatora, a nie przez konstruktor.
        validate = getattr(generator, "validate", None)
        if callable(validate):
            issues = list(validate(request.parameters))
            if issues:
                # Błędy polowe z kodami z katalogu alarmów — GUI podświetla pola.
                raise InvalidRequest(
                    f"parametry operacji {request.operation} są niepoprawne",
                    details={"operation": request.operation,
                             "errors": [{"code": i.code, "field": i.field,
                                         "message": i.message()} for i in issues],
                             "parameters": _parameters(generator)})
            values, _issues = generator.normalize(request.parameters)
        else:
            values = dict(request.parameters)
        try:
            lines = generator.generate(values)
        except Exception as exc:
            raise InvalidRequest(f"generator {request.operation} zgłosił błąd: {exc}",
                                 details={"operation": request.operation}) from exc
        text = "\n".join(lines) if isinstance(lines, (list, tuple)) else str(lines)
        return CamGenerateOut(
            operation=request.operation,
            version=int(getattr(generator, "version", 1)),
            gcode=text if isinstance(text, str) else "\n".join(text),
            message="wygenerowano G-code",
        )


__all__ = ["CamService", "load_generators"]
