# SPDX-License-Identifier: GPL-2.0-or-later
"""Transactional editing of dialog programs, without Qt or CNC commands.

Model-Author: Codex.
"""
from __future__ import annotations

from .compiler import compile_program
from .lnx import LnxProgram, Step


class StepEditor:
    """Validate before replacing a program; retain at most 100 undo states."""

    def __init__(self, program: LnxProgram, registry):
        self.program = program.model_copy(deep=True)
        self.registry = registry
        self.selected = -1
        self._undo: list[tuple[LnxProgram, int]] = []
        self._redo: list[tuple[LnxProgram, int]] = []

    @property
    def can_undo(self):
        return bool(self._undo)

    @property
    def can_redo(self):
        return bool(self._redo)

    def _snapshot(self):
        return self.program.model_copy(deep=True), self.selected

    def _commit(self, program, selected):
        compile_program(program, self.registry)
        if program == self.program:
            return False
        self._undo.append(self._snapshot())
        self._undo = self._undo[-100:]
        self._redo.clear()
        self.program, self.selected = program, selected
        return True

    def edit(self, operation: str, index: int = -1, step: Step | None = None):
        candidate = self.program.model_copy(deep=True)
        steps = candidate.steps
        if operation == "add":
            if step is None:
                raise ValueError("Brak parametrów kroku.")
            steps.append(step.model_copy(deep=True))
            index = len(steps) - 1
        else:
            if not 0 <= index < len(steps):
                raise ValueError("Wybierz krok z listy.")
            if operation == "update":
                if step is None:
                    raise ValueError("Brak parametrów kroku.")
                steps[index] = step.model_copy(deep=True)
            elif operation == "duplicate":
                steps.insert(index + 1, steps[index].model_copy(deep=True))
                index += 1
            elif operation == "toggle":
                steps[index].enabled = not steps[index].enabled
            elif operation == "delete":
                steps.pop(index)
                index = min(index, len(steps) - 1)
            elif operation in ("up", "down"):
                target = index + (-1 if operation == "up" else 1)
                if not 0 <= target < len(steps):
                    return False
                steps[index], steps[target] = steps[target], steps[index]
                index = target
            else:
                raise ValueError(f"Nieznana operacja: {operation}")
        unit_step = steps[index] if operation == "toggle" else step
        if unit_step is not None and unit_step.enabled and unit_step.generator == "header":
            candidate.units = "inch" if unit_step.params.get("units") == "G20" else "mm"
        return self._commit(candidate, index)

    def undo(self):
        if not self._undo:
            return False
        self._redo.append(self._snapshot())
        self.program, self.selected = self._undo.pop()
        return True

    def redo(self):
        if not self._redo:
            return False
        self._undo.append(self._snapshot())
        self.program, self.selected = self._redo.pop()
        return True
