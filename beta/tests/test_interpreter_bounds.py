# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise real pipe floods, quiet loops and child cleanup. Model-Author: Codex."""

import os
import subprocess
import sys
import time

import pytest

from linumert.programs._interpreter_process import InterpreterOutputLimit, run_bounded


def run(script, **limits):
    return run_bounded([sys.executable, "-c", script], cwd=None, env=os.environ.copy(),
                       timeout=limits.pop("timeout", 2), **limits)


def test_captures_both_pipes_and_exit_code():
    result = run("import sys; print('result'); print('diagnostic', file=sys.stderr); sys.exit(3)")
    assert result.stdout == "result\n" and result.stderr == "diagnostic\n"
    assert result.returncode == 3


@pytest.mark.parametrize("fd", [1, 2])
def test_flooding_either_pipe_is_bounded_and_reaped(fd):
    start = time.monotonic()
    with pytest.raises(InterpreterOutputLimit, match="pętla bez końca"):
        run(f"import os\nwhile True: os.write({fd}, b'x'*65536)", max_output=4096)
    assert time.monotonic() - start < 2


def test_total_limit_is_shared_by_stdout_and_stderr():
    with pytest.raises(InterpreterOutputLimit):
        run("import os; os.write(1,b'x'*3000); os.write(2,b'x'*3000)", max_output=4096)


def test_quiet_loop_times_out():
    with pytest.raises(subprocess.TimeoutExpired):
        run("while True: pass", timeout=0.2)


def test_timeout_kills_child_that_keeps_pipe_open(tmp_path):
    marker = tmp_path / "orphan"
    child = f"import time,pathlib; time.sleep(1); pathlib.Path({str(marker)!r}).touch()"
    parent = ("import subprocess,sys; "
              f"subprocess.Popen([sys.executable,'-c',{child!r}])")
    with pytest.raises(subprocess.TimeoutExpired):
        run(parent, timeout=0.2)
    time.sleep(1.1)
    assert not marker.exists(), "analysis left a descendant running"
