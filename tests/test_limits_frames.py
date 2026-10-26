"""Regression: arc starts retain their machine position across modal changes.

Model-Author: Codex. LIMITS-PREFLIGHT review #172.
"""

import pytest
from linumert.programs.limits import check_canon
from linumert.programs.linuxcnc_check import run_interpreter


def canon(*calls):
    return '\n'.join(f'{i} N{i} {call}' for i, call in enumerate(calls, 1))


@pytest.mark.parametrize('offset', [
    'SET_G92_OFFSET(10, 0, 0)',
    'SET_G5X_OFFSET(1, 10, 0, 0)',
    'USE_TOOL_LENGTH_OFFSET(10, 0, 0)',
])
def test_arc_start_rebased_after_offset(offset):
    got = check_canon(canon('STRAIGHT_TRAVERSE(10, 0, 0)', offset,
                            'ARC_FEED(-20, 0, -10, 0, 1, 0)'), {'Y': (-5, 5)})
    assert [(v.axis, v.side, v.value) for v in got] == [('Y', 'max', 10)]


def test_unit_switch_rescales_existing_offsets_and_arc_start():
    got = check_canon(canon(
        'SET_G5X_OFFSET(1, 25.4, 0, 0)', 'STRAIGHT_TRAVERSE(25.4, 0, 0)',
        'USE_LENGTH_UNITS(CANON_UNITS_INCHES)', 'ARC_FEED(-1, 0, 0, 0, 1, 0)',
    ), {'X': (0, 51), 'Y': (-5, 5)})
    assert [(v.axis, v.side) for v in got] == [('Y', 'max')]
    assert got[0].value == pytest.approx(25.4)


@pytest.mark.linuxcnc
@pytest.mark.parametrize('change', ['G92 X0', 'G10 L2 P1 X10'])
def test_real_interpreter_arc_after_frame_change(tmp_path, change):
    program = tmp_path / 'frame.ngc'
    program.write_text(f'G21 G90 G17\nG0 X10 Y0\n{change}\n'
                       'G3 X-20 Y0 I-10 J0 F100\nM2\n')
    run = run_interpreter(program)
    assert run.returncode == 0 and 'PROGRAM_END()' in run.stdout, run.stderr
    got = check_canon(run.stdout, {'Y': (-5, 5)})
    assert [(v.axis, v.side, v.value) for v in got] == [('Y', 'max', 10)]


def test_unit_switch_does_not_scale_rotary_position_or_offsets():
    got = check_canon(canon(
        'SET_G5X_OFFSET(1, 25.4, 0, 0, 90, 0, 0)',
        'STRAIGHT_TRAVERSE(25.4, 0, 0, 10, 0, 0)',
        'USE_LENGTH_UNITS(CANON_UNITS_INCHES)',
        'STRAIGHT_FEED(1, 0, 0, 10, 0, 0)',
    ), {'X': (0, 51), 'A': (95, 105)})
    assert got == []
