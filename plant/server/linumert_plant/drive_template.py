"""Zgodność wsteczna: moduł przeniesiony do `linumert.machine.drives.drive_template`.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · scalenie lite 2026-11-05
"""

import sys

from linumert.machine.drives import drive_template as _impl

sys.modules[__name__] = _impl
