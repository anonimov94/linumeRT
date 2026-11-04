# SPDX-License-Identifier: GPL-2.0-or-later
"""Program edits preserve source, undo state and compilation. Model-Author: Codex."""
import pytest

from linumert.generators import basic
from linumert.generators.registry import GeneratorRegistry
from linumert.programs.compiler import CompileError, compile_program
from linumert.programs.lnx import LnxProgram, Step, load_lnx, save_lnx
from linumert.programs.step_editor import StepEditor


def editor():
    registry = GeneratorRegistry()
    basic.register(registry)
    return StepEditor(LnxProgram(name="Próba"), registry)


def header(title):
    return Step(generator="header", version=1, params={"title": title})


def test_operations_undo_redo_and_roundtrip(tmp_path):
    model = editor()
    model.edit("add", step=header("A"))
    model.edit("add", step=header("B"))
    model.edit("up", 1)
    assert [s.params["title"] for s in model.program.steps] == ["B", "A"]
    model.edit("duplicate", 0)
    model.program.steps[1].params["title"] = "kopia"
    assert model.program.steps[0].params["title"] == "B"
    model.edit("toggle", 1)
    text = compile_program(model.program, model.registry)
    assert "( kopia )" not in text and "pominiety" in text
    model.edit("delete", 0)
    assert model.undo() and len(model.program.steps) == 3
    assert model.redo() and len(model.program.steps) == 2
    path = tmp_path / "test.lnx"
    save_lnx(model.program, path)
    assert load_lnx(path) == model.program


def test_invalid_edit_is_atomic_and_keeps_redo():
    model = editor()
    model.edit("add", step=header("A"))
    model.undo()
    before = model.program.model_copy(deep=True)
    with pytest.raises(CompileError):
        model.edit("add", step=Step(generator="tool_change", version=1, params={"tool": -1}))
    assert model.program == before and model.can_redo
    assert model.redo()
    with pytest.raises(ValueError):
        model.edit("delete", -1)
    assert len(model.program.steps) == 1
    assert not model.edit("up", 0)


def test_update_units_and_undo_are_snapshots():
    model = editor()
    source = header("A")
    model.edit("add", step=source)
    source.params["title"] = "outside"
    replacement = header("B")
    replacement.params["units"] = "G20"
    model.edit("update", 0, replacement)
    assert model.program.units == "inch"
    model.undo()
    assert model.program.units == "mm" and model.program.steps[0].params["title"] == "A"
    model.edit("toggle", 0)
    assert not model.can_redo


def test_editing_disabled_header_does_not_change_program_units():
    model = editor()
    step = header("Nagłówek pomijany")
    step.enabled = False
    step.params["units"] = "G20"
    model.edit("add", step=step)
    assert model.program.units == "mm"
    model.edit("update", 0, step.model_copy(update={"comment": "zmiana opisu"}))
    assert model.program.units == "mm"
    model.edit("toggle", 0)
    assert model.program.units == "inch"
    model.undo()
    assert model.program.units == "mm"
