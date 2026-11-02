# SPDX-License-Identifier: GPL-2.0-or-later
"""Bound interpreter output and lifetime without a preexec hook in Qt threads.

Model-Author: Codex.
"""

import os
import selectors
import signal
import subprocess
import time

MAX_OUTPUT_BYTES = 8 * 1024 * 1024


class InterpreterOutputLimit(RuntimeError):
    pass


def run_bounded(args, *, cwd, env, timeout, max_output=MAX_OUTPUT_BYTES):
    """Capture at most max_output bytes across both pipes; reap the owned process group."""
    if timeout <= 0 or max_output <= 0:
        raise ValueError("Limity interpretera muszą być dodatnie.")
    output = {"stdout": bytearray(), "stderr": bytearray()}
    total = 0
    deadline = time.monotonic() + timeout
    with subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          start_new_session=True) as proc, selectors.DefaultSelector() as selector:
        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(args, timeout)
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fileobj.fileno(), min(65536, max_output - total + 1))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    total += len(chunk)
                    if total > max_output:
                        raise InterpreterOutputLimit(
                            "Przekroczono limit danych analizy programu "
                            f"({max_output} bajtów): możliwa pętla bez końca "
                            "lub zbyt długi program.")
                    output[key.data].extend(chunk)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(args, timeout)
            code = proc.wait(timeout=remaining)
        finally:
            # Only this invocation owns the session/process group, never the live CNC.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
    return subprocess.CompletedProcess(args, code,
                                       output["stdout"].decode("utf-8", errors="replace"),
                                       output["stderr"].decode("utf-8", errors="replace"))
