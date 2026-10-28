"""Usługa programów: lista, odczyt, zapis, kompilacja .lnx, limity, czas, ścieżka, edycja kroku.

SPDX-License-Identifier: GPL-2.0-or-later

Wszystko, co GUI pokazuje na stronie „Program", idzie przez tę usługę:

- katalog programów NC (``config/nc_files``) z ochroną przed wyjściem poza katalog,
- kompilacja ``.lnx`` → G-code (``linumert.programs.compiler``),
- sprawdzanie granic (``linumert.programs.limits``) — z INI maszyny albo z wartościami domyślnymi,
- szacowanie czasu i drogi (``linumert.programs.estimate``),
- ścieżka narzędzia do podglądu (``linumert.programs.toolpath``) — **punkty, nie obraz**:
  GUI rysuje je u siebie (SVG/canvas/WebGL), backend nie generuje grafiki,
- edycja kroku programu dialogowego (``linumert.programs.step_editor``).

LinuxCNC pozostaje jedynym interpreterem: ta usługa tylko przygotowuje i sprawdza program.
"""

from __future__ import annotations

import dataclasses
import logging
import math
import tempfile
from pathlib import Path

from linumert.generators.registry import GeneratorRegistry
from linumert.programs import compiler, estimate, limits, lnx, step_editor
from linumert.programs.files import read_editable, save_new_program
from linumert_sim.path import KIND_RAPID, InterpreterUnavailable, load_path

from ..errors import Conflict, InvalidRequest, NotFound
from ..schema import (
    CheckRequest,
    CompileOut,
    EstimateOut,
    EstimateRequest,
    LimitReportOut,
    LnxCompileRequest,
    Ok,
    ProgramList,
    ProgramName,
    ProgramRead,
    ProgramSummary,
    ProgramWriteRequest,
    StepEditRequest,
    ToolpathOut,
    ToolpathPoint,
    ToolpathRequest,
    ViolationOut,
)
from .paths import ProjectPaths

log = logging.getLogger("linumert.service.program")

RAPID_MM_S = 83.33  # 5000 mm/min — domyślne G0 do szacunku bez przyspieszeń


def toolpath_available() -> bool:
    """Czy jest moduł ``gcode`` LinuxCNC (pełny rs274) — inaczej interpreter podzbioru."""
    import importlib.util

    try:
        return importlib.util.find_spec("gcode") is not None
    except (ImportError, ValueError):
        return False


def _estimate_with_rs274(text: str, ini: Path):
    with tempfile.TemporaryDirectory(prefix="lrt-est-") as tmp:
        ngc = Path(tmp) / "program.ngc"
        ngc.write_text(text, encoding="utf-8")
        source = ini if ini.exists() else None
        if source is None:
            raise RuntimeError("brak INI z granicami")
        return estimate.estimate_ngc(ngc, source)


# Granice domyślne, gdy nie podano INI (maszyna DIY 500 mm/s, 500 mm/s²) — tylko do podglądu.
DEFAULT_LIMITS = {"X": (500.0, 500.0), "Y": (500.0, 500.0), "Z": (200.0, 200.0)}
_AXES_XYZ = ("X", "Y", "Z")


def _violations_from_moves(moves, table: dict[str, tuple[float, float]]) -> list:
    """Pierwsze przekroczenie każdej osi i strony limitu; ``count`` liczy punkty.

    Semantyka jak w ``limits.analyze_canon``: oś, która nie ruszyła się z zera, nie jest
    oceniana — interpreter startuje w zerze maszyny, które bywa poza granicami.
    """
    found: list[limits.Violation] = []
    seen: dict[tuple[str, str], int] = {}
    touched: set[str] = set()
    for index in range(len(moves)):
        end = moves.end[index]
        line = int(moves.line[index])
        for i, axis in enumerate(_AXES_XYZ):
            if axis not in table:
                continue
            value = float(end[i])
            if axis not in touched:
                if abs(value) < limits.EPS:
                    continue
                touched.add(axis)
            low, high = table[axis]
            for side, limit, bad in (("min", low, value < low - limits.EPS),
                                     ("max", high, value > high + limits.EPS)):
                if not bad:
                    continue
                key = (axis, side)
                if key not in seen:
                    seen[key] = len(found)
                    found.append(limits.Violation(line, axis, value, limit, side))
                else:
                    first = found[seen[key]]
                    found[seen[key]] = dataclasses.replace(first, count=first.count + 1)
    return found


def _violation_out(violation) -> ViolationOut:
    """``message`` jest metodą ``Violation``, nie polem — trzeba ją wywołać."""
    return ViolationOut(
        axis=violation.axis, line=violation.line, value=round(violation.value, 4),
        limit=violation.limit, side=violation.side, count=violation.count,
        message=violation.message(),
    )
KINDS = {".ngc": "ngc", ".nc": "ngc", ".tap": "ngc", ".lnx": "lnx"}


class ProgramService:
    """Operacje domeny ``program``."""

    domain = "program"

    def __init__(self, paths: ProjectPaths, default_ini: Path | None = None,
                 registry: GeneratorRegistry | None = None):
        self.paths = paths
        self.default_ini = default_ini or paths.default_ini
        # Rejestr generatorów jest zapełniany przez load_generators(), który woła
        # CamService. Poleganie na tym skutku ubocznym sprawiało, że kompilacja .lnx
        # zależała od kolejności tworzenia usług: bez CamService DEFAULT_REGISTRY jest
        # pusty i każdy krok dostaje "brak generatora X". Ładujemy go jawnie.
        from .cam import load_generators

        self.registry = load_generators(registry)

    # ---- katalog -----------------------------------------------------------
    def list(self) -> ProgramList:
        root = self.paths.programs
        root.mkdir(parents=True, exist_ok=True)
        items = []
        for path in sorted(root.iterdir()):
            if not path.is_file():
                continue  # katalogi (np. macros) nie są programami
            stat = path.stat()
            items.append(ProgramSummary(
                name=path.name, path=str(path), kind=KINDS.get(path.suffix.lower(), "other"),
                size=stat.st_size, modified=stat.st_mtime))
        return ProgramList(root=str(root), programs=items)

    def read(self, request: ProgramName) -> ProgramRead:
        path = self.paths.program(request.name)
        return ProgramRead(name=path.name, path=str(path), text=read_editable(path))

    def write(self, request: ProgramWriteRequest) -> Ok:
        root = self.paths.programs
        root.mkdir(parents=True, exist_ok=True)
        path = self.paths.resolve(request.name, root, must_exist=False)
        if path.suffix.lower() not in {".ngc", ".nc", ".tap", ".lnx"}:
            raise InvalidRequest("program musi mieć rozszerzenie .ngc, .nc, .tap albo .lnx",
                                 details={"name": request.name})
        if path.exists() and not request.overwrite:
            raise Conflict(f"program {request.name} już istnieje (użyj overwrite=true)")
        if path.exists():
            path.write_text(request.text, encoding="utf-8")
        else:
            save_new_program(path, request.text)
        return Ok(message=f"zapisano {path.name}", details={"path": str(path)})

    def delete(self, request: ProgramName) -> Ok:
        path = self.paths.program(request.name)
        path.unlink()
        return Ok(message=f"usunięto {path.name}")

    # ---- kompilacja .lnx ---------------------------------------------------
    def compile_lnx(self, request: LnxCompileRequest) -> CompileOut:
        path = self.paths.program(request.name)
        if path.suffix.lower() != ".lnx":
            raise InvalidRequest("kompilacja dotyczy programów .lnx",
                                 details={"name": path.name})
        try:
            out = compiler.compile_file(path, None if not request.save else
                                        path.with_suffix(".ngc"), registry=self.registry)
        except (compiler.CompileError, lnx.LnxError) as exc:
            # LnxError (uszkodzony/zły schemat .lnx) nie jest podklasą CompileError,
            # a to błąd wejścia użytkownika — bez niego GUI dostałoby błąd wewnętrzny.
            raise InvalidRequest(f"kompilacja {path.name} nie powiodła się: {exc}",
                                 details={"program": path.name}) from exc
        text = Path(out).read_text(encoding="utf-8") if Path(out).exists() else ""
        return CompileOut(name=path.name, gcode=text, path=str(out),
                          message="skompilowano" if request.save else "kompilacja w pamięci")

    def compile_text(self, text: str) -> str:
        """Kompilacja programu .lnx z tekstu (bez zapisu na dysk)."""
        with tempfile.TemporaryDirectory(prefix="lrt-lnx-") as tmp:
            source = Path(tmp) / "program.lnx"
            source.write_text(text, encoding="utf-8")
            target = Path(tmp) / "program.ngc"
            try:
                compiler.compile_file(source, target, registry=self.registry)
            except (compiler.CompileError, lnx.LnxError) as exc:
                raise InvalidRequest(f"kompilacja nie powiodła się: {exc}") from exc
            return target.read_text(encoding="utf-8")

    # ---- granice -----------------------------------------------------------
    def check(self, request: CheckRequest) -> LimitReportOut:
        """Granice osi programu.

        Liczymy z ruchów interpretera (``linumert_sim.path.load_path``), więc działa
        też bez LinuxCNC. ``limits.analyze_canon`` odpada w tym miejscu z dwóch
        powodów: oczekuje **tekstu canon** (wyjścia rs274), a nie surowego G-code —
        karmiony G-code nie znajdował nic i meldował "program w granicach" — a jego
        ``Violation.limit`` to pojedynczy float z osobnym ``side``, nie para min/max.
        """
        text = self._text(request.name, request.text)
        table = self._limits(request.ini)
        with tempfile.TemporaryDirectory(prefix="lrt-chk-") as tmp:
            path = Path(tmp) / "program.ngc"
            path.write_text(text, encoding="utf-8")
            try:
                moves = load_path(path)
            except (InterpreterUnavailable, ValueError) as exc:
                raise InvalidRequest(f"nie udało się sprawdzić granic: {exc}") from exc
        found = _violations_from_moves(moves, table)
        return LimitReportOut(
            ok=not found,
            violations=[_violation_out(v) for v in found],
            lines=len(text.splitlines()),
            program=request.name,
            moves=len(moves),
            interpreter=str(getattr(moves, "source", "")),
        )

    # ---- czas i droga ------------------------------------------------------
    def estimate(self, request: EstimateRequest) -> EstimateOut:
        """Czas i droga programu.

        Z modułem ``gcode`` LinuxCNC idzie pełny model czasu z ``rs274``
        (``estimate_ngc`` → ``estimate_canon``). Bez LinuxCNC liczymy z listy ruchów
        interpretera podzbioru: długość G0/G1 i czas z posuwów F — bez przyspieszeń,
        więc to szacunek dolny (tak samo jak w symulacji ``sim.run``).
        """
        text = self._text(request.name, request.text)
        ini = Path(request.ini) if request.ini else self.default_ini
        if toolpath_available():
            try:
                result = _estimate_with_rs274(text, ini)
            except Exception as exc:  # rs274 odmówił — liczmy z listy ruchów
                log.debug("rs274 niedostępny (%s), szacunek z listy ruchów", exc)
            else:
                return EstimateOut(
                    seconds=round(result.total, 3),
                    distance_mm=round(result.rapid_length + result.feed_length, 3),
                    rapid_mm=round(result.rapid_length, 3),
                    feed_mm=round(result.feed_length, 3),
                    tools=sorted(result.per_tool),
                    source="rs274",
                    message=f"czas ~{result.total / 60:.1f} min",
                )
        return self._estimate_from_moves(text, ini)

    def _estimate_from_moves(self, text: str, ini: Path) -> EstimateOut:
        with tempfile.TemporaryDirectory(prefix="lrt-est-") as tmp:
            path = Path(tmp) / "program.ngc"
            path.write_text(text, encoding="utf-8")
            try:
                moves = load_path(path)
            except (InterpreterUnavailable, ValueError) as exc:
                raise InvalidRequest(f"nie udało się policzyć czasu: {exc}") from exc
        if not len(moves):
            return EstimateOut(ok=True, source=moves.source, message="program bez ruchu")

        rapid_mm = moves.length(KIND_RAPID)
        feed_mm = moves.length() - rapid_mm
        rapid_s = rapid_mm / RAPID_MM_S if rapid_mm else 0.0
        feed_s = 0.0
        for index in range(len(moves)):
            if int(moves.kind[index]) == KIND_RAPID:
                continue
            speed = float(moves.feed[index])  # mm/min
            length = float(moves.lengths[index])
            if speed > 0:
                feed_s += length / speed * 60.0
        limits_note = ""
        if ini.exists():
            try:
                spec = estimate.limits_from_ini(ini)
                limits_note = (f"; granice z {ini.name}: "
                               f"{spec.max_linear:g} mm/s")
            except Exception:
                limits_note = ""
        total = rapid_s + feed_s
        return EstimateOut(
            seconds=round(total, 3),
            distance_mm=round(rapid_mm + feed_mm, 3),
            rapid_mm=round(rapid_mm, 3),
            feed_mm=round(feed_mm, 3),
            tools=sorted({int(t) for t in moves.tool if int(t) > 0}),
            source=moves.source,
            message=f"czas ~{total / 60:.1f} min (bez przyspieszeń){limits_note}",
        )

    # ---- ścieżka narzędzia -------------------------------------------------
    def toolpath(self, request: ToolpathRequest) -> ToolpathOut:
        """Punkty ścieżki dla GUI.

        Używamy ``linumert_sim.path.load_path``: z modułem ``gcode`` LinuxCNC idzie pełny
        rs274, a bez niego interpreter podzbioru — więc podgląd działa też poza maszyną.
        Zwracamy **liczby**, nie obraz: GUI rysuje polilinię u siebie (SVG/canvas/WebGL).
        """
        text = self._text(request.name, request.text)
        with tempfile.TemporaryDirectory(prefix="lrt-path-") as tmp:
            path = Path(tmp) / "program.ngc"
            path.write_text(text, encoding="utf-8")
            try:
                moves = load_path(path)
            except (InterpreterUnavailable, ValueError) as exc:
                raise InvalidRequest(f"nie udało się wczytać ścieżki: {exc}") from exc

        total = len(moves)
        if total == 0:
            return ToolpathOut(points=[], bounds={}, unit="mm", source=moves.source,
                               notes=list(moves.notes), message="program bez ruchu")
        step = max(1, math.ceil(total / max(1, request.max_points)))
        points: list[ToolpathPoint] = []
        for index in range(0, total, step):
            end = moves.end[index]
            points.append(ToolpathPoint(
                line=int(moves.line[index]),
                x=round(float(end[0]), 4), y=round(float(end[1]), 4), z=round(float(end[2]), 4),
                rapid=int(moves.kind[index]) == KIND_RAPID, feed=float(moves.feed[index]),
            ))
        low, high = moves.bounds()
        bounds = {
            "min_x": round(float(low[0]), 4), "max_x": round(float(high[0]), 4),
            "min_y": round(float(low[1]), 4), "max_y": round(float(high[1]), 4),
            "min_z": round(float(low[2]), 4), "max_z": round(float(high[2]), 4),
        }
        return ToolpathOut(
            points=points, bounds=bounds, unit="mm", source=moves.source,
            length_mm=round(moves.length(), 3), notes=list(moves.notes),
            message=f"{len(points)} pkt z {total} odcinków ({moves.source})",
        )

    # ---- edycja kroku ------------------------------------------------------
    def edit_step(self, request: StepEditRequest) -> CompileOut:
        path = self.paths.program(request.name)
        if path.suffix.lower() != ".lnx":
            raise InvalidRequest("edycja kroku dotyczy programów .lnx",
                                 details={"name": path.name})
        program = lnx.load_lnx(path)
        if not 1 <= request.line <= len(program.steps):
            raise NotFound(f"program {path.name} nie ma kroku {request.line}",
                           details={"line": request.line, "steps": len(program.steps)})
        step = program.steps[request.line - 1]
        params = dict(step.params)
        params.update(request.changes)
        editor = step_editor.StepEditor(program, None)
        new_step = lnx.Step(**{**step.model_dump(), "params": params}) \
            if hasattr(step, "model_dump") else step
        editor.edit("replace", request.line - 1, new_step)
        text = lnx.dump_lnx(editor.program if hasattr(editor, "program") else program)
        return CompileOut(name=path.name, gcode=text, message=f"zmieniono krok {request.line}")

    # ---- pomocnicze --------------------------------------------------------
    def _text(self, name: str, text: str) -> str:
        if text:
            return text
        if not name:
            raise InvalidRequest("podaj name albo text")
        return read_editable(self.paths.program(name))

    def _limits(self, ini: str) -> dict[str, tuple[float, float]]:
        source = Path(ini) if ini else self.default_ini
        if not source.exists():
            return dict(DEFAULT_LIMITS)
        try:
            table = limits.limits_from_ini(source)
        except Exception:
            return dict(DEFAULT_LIMITS)
        return table or dict(DEFAULT_LIMITS)


def _default_spec() -> estimate.Limits:
    return estimate.Limits(
        max_vel={axis: value[0] for axis, value in DEFAULT_LIMITS.items()},
        max_acc={axis: value[1] for axis, value in DEFAULT_LIMITS.items()},
    )


__all__ = ["DEFAULT_LIMITS", "ProgramService"]
