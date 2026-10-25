#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · N4: odbiór Classic × Neon na LinuxCNC sim (WSL). Użycie: bash tools/dev/neon_accept.sh [KATALOG]
# Wymaga venv z pytest (python -m venv --system-site-packages) w $VENV oraz RIP LinuxCNC 2.9.
PY=${VENV:-$HOME/linumert-test/venv}/bin/python
export LINUMERT_LOCK_DIR=${LINUMERT_LOCK_DIR:-$HOME/linumert-test/locks}
mkdir -p "$LINUMERT_LOCK_DIR"
exec xvfb-run -a -s '-screen 0 1440x1100x24' bash tools/dev/neon_rip.sh "$PY" tools/dev/neon_accept.py "${1:-/tmp/neon-out}"
