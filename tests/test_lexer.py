"""Lekser G-code LinuxCNC (sesja 044): próbki z tests/data/gcode_samples.yaml i zgodność z rs274.

Model-Author: Claude
Testy bez LinuxCNC sprawdzają werdykt i kod pierwszego błędu każdej próbki, kolumny, strukturę
słów O i komunikaty. Test z markerem `linuxcnc` porównuje werdykty z interpreterem rs274
LinuxCNC 2.9 (`oracle`: same / strict / semantic — opis w pliku próbek).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml
from linumert.programs.lexer import check, lex

SAMPLES = yaml.safe_load((Path(__file__).parent / "data" / "gcode_samples.yaml")
                         .read_text(encoding="utf-8"))


def test_enough_samples():
    assert len(SAMPLES) >= 20
    assert len({s["id"] for s in SAMPLES}) == len(SAMPLES)
    assert {s.get("oracle", "same") for s in SAMPLES} == {"same", "strict", "semantic"}


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s["id"])
def test_sample_verdict_and_code(sample):
    issues = check(sample["text"])
    if sample["ok"]:
        assert issues == [], [i.message() for i in issues]
    else:
        assert issues, "oczekiwano błędu"
        assert issues[0].code == sample["code"], issues[0].message()


def test_positions_are_original_columns():
    (issue,) = check("G0 X1 (abc")
    assert (issue.code, issue.line, issue.col) == ("P-5101", 1, 7)
    (issue,) = check("G1  X 1.2.3")
    assert (issue.code, issue.col) == ("P-5105", 7)       # kolumna mimo spacji
    assert issue.params["text"] == "1.2.3"
    (issue,) = check("N1\nG0 N10 X1")
    assert (issue.code, issue.line, issue.col) == ("P-5111", 2, 4)
    (issue,) = check("G0 X[1+2")
    assert (issue.code, issue.col) == ("P-5106", 5)       # wskazuje otwierający nawias


def test_messages_both_languages():
    (issue,) = check("G0 X[FOO[1]]")
    assert issue.message() == "Linia 1, kolumna 6: nieznana funkcja albo operator FOO."
    assert issue.message("en") == "Line 1, column 6: unknown function or operator FOO."


def test_every_line_and_structure_reported():
    text = "G0 X\nG0 $1\no1 if [1]\no2 endif\nM2"
    issues = check(text)
    assert [(i.line, i.code) for i in issues] == [(1, "P-5104"), (2, "P-5103"),
                                                  (3, "P-5109"), (4, "P-5109")]


def test_lexed_structure():
    result = lex("/N10 g1 x[1+#2] y#<dl> f100 (ruch) ; uwaga\n#<dl>=[2*3]\n"
                 "o<frez> call [1] [2.5]\n%")
    first, second, third, fourth = result.lines
    assert first.block_delete and [w.letter for w in first.words] == ["N", "G", "X", "Y", "F"]
    assert first.words[2].value == "[1+#2]" and first.words[3].value == "#<DL>"
    assert first.comments == ["ruch", " uwaga"]
    assert second.assignments == [("#<DL>", "[2*3]")]
    assert third.oword is not None and third.oword.label == "<FREZ>"
    assert third.oword.keyword == "CALL" and third.oword.args == ["[1]", "[2.5]"]
    assert fourth.percent and result.ok


def test_o_word_rules():
    assert check("o1 sub\no1 return\no1 endsub") == []
    assert [i.code for i in check("o1 return\nM2")] == ["P-5109"]          # poza sub
    assert [i.code for i in check("o2 break\nM2")] == ["P-5109"]           # poza pętlą
    assert check("o3 if\no3 endif")[0].code == "P-5109"                    # if bez warunku
    assert [i.code for i in check("o4 endif [1]\nM2")][0] == "P-5109"      # argument
    assert check("o5 sub X1\no5 endsub")[0].code == "P-5109"                # słowo po sub
    nested = "o1 sub\no2 if [1]\no2 endif\no1 endsub\no1 call"
    assert check(nested) == []
    crossed = "o1 sub\no2 if [1]\no1 endsub\no2 endif"
    assert len(check(crossed)) >= 2


def test_expressions():
    good = ["G0 X[1 2]",  # spacje są pomijane jak w rs274ngc: [12]
            "G0 X[1+2*3-4/5]", "G0 X[[1]]", "G0 X[ABS[-1]+SQRT[4]**2]",
            "G0 X[#1 LE 2 AND #2 GE 1]", "G0 X[-SIN[30]]", "#[1+1]=3"]
    for text in good:
        assert check(text) == [], text
    bad = {"G0 X[1+]": "P-5110", "G0 X[ABS 1]": "P-5110", "G0 X[ATAN[1]/2]": "P-5110",
           "G0 X[1#2]": "P-5110", "#1.5=2": "P-5108", "G0 X#": "P-5108"}
    for text, code in bad.items():
        assert [i.code for i in check(text)][:1] == [code], text


@pytest.mark.linuxcnc
@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s["id"])
def test_verdict_matches_linuxcnc(sample, tmp_path):
    from linumert.programs.linuxcnc_check import InterpreterUnavailable, check_with_linuxcnc

    ngc = tmp_path / f"{sample['id']}.ngc"
    ngc.write_text(sample["text"] + "\n", encoding="utf-8")
    root = os.environ.get("LINUXCNC_DIR", str(Path.home() / ".cache" / "linuxcnc-2.9"))
    try:
        result = check_with_linuxcnc(ngc, root=root, timeout=10)
    except InterpreterUnavailable as exc:
        pytest.skip(str(exc))
    lexer_ok = not check(sample["text"])
    oracle = sample.get("oracle", "same")
    if oracle == "same":
        assert lexer_ok == result.ok, result.messages
    elif oracle == "strict":
        assert not lexer_ok
    else:  # semantic: składnia poprawna, błąd zgłasza interpreter
        assert lexer_ok and not result.ok


@pytest.mark.parametrize("name", ["linumert_demo.ngc", "linumert_kolizja.ngc"])
def test_shipped_simulation_programs_have_no_lexical_errors(name):
    # The nested M4 comment formerly aborted the demo before its final tool.
    program = Path(__file__).parents[1] / "config/sim/nc_files" / name
    issues = check(program.read_text(encoding="utf-8"))
    assert not issues, [issue.message() for issue in issues]
