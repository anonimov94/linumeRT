# SPDX-License-Identifier: GPL-2.0-or-later
"""Text remains a reproducible path snapshot. Model-Author: Codex."""
import json

from linumert.generators.engraving import EngraveText, register
from linumert.generators.registry import GeneratorRegistry
from linumert.programs.compiler import compile_program
from linumert.programs.lnx import LnxProgram, Step, load_lnx, save_lnx


def test_text_metadata_is_not_executed_and_font_is_not_needed_to_compile(tmp_path):
    gen = EngraveText()
    v, issues = gen.normalize({"text": "(M2)\nŻÓŁĆ", "font_family": "Missing Font",
                               "paths": json.dumps([[[0, 0], [1, 1], [2, 0]]])})
    assert not issues and not gen.check(v, 0)
    registry = GeneratorRegistry()
    register(registry)
    program = LnxProgram(name="Napis", steps=[Step(generator=gen.name, version=1, params=v)])
    output = compile_program(program, registry)
    assert "ŻÓŁĆ" not in output and output.count("M2") == 1
    save_lnx(program, tmp_path / "text.lnx")
    assert compile_program(load_lnx(tmp_path / "text.lnx"), registry) == output


def test_text_validation_and_placement():
    gen = EngraveText()
    assert gen.validate({"text": "x" * 129})
    assert gen.validate({"text": "\x00"})
    v, issues = gen.normalize({"paths": "[[[0,0],[1,0]]]", "angle": 90, "x": 10,
                               "y": 20, "scale": 2, "reverse": True})
    assert not issues and not gen.check(v, 0)
    assert gen.preview_2d(v) == [[(10.0, 22.0), (10.0, 20.0)]]
