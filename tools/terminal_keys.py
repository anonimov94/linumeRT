"""Nonblocking POSIX terminal keys, restored on every exit. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import contextlib
import os
import select
import sys


@contextlib.contextmanager
def keyboard(enabled):
    if not enabled or not sys.stdin.isatty():
        yield lambda: ""
        return
    import termios
    import tty

    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)

        def read():
            if select.select([sys.stdin], [], [], 0)[0]:
                return os.read(fd, 1).decode("ascii", errors="ignore").lower()
            return ""

        yield read
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original)
