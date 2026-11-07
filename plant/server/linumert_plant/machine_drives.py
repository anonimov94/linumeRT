"""Zgodność wsteczna: moduł przeniesiony do `linumert.machine.drives.machine_drives`.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · scalenie lite 2026-11-05
"""

import sys

from linumert.machine.drives import machine_drives as _impl

sys.modules[__name__] = _impl
