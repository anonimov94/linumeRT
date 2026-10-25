#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · uruchamia polecenie pod rip-environment LinuxCNC (WSL), rdzeń w PYTHONPATH.
R=${LINUXCNC_DIR:-$HOME/.cache/linuxcnc-2.9}
source "$R/scripts/rip-environment"
export PYTHONPATH=$PWD/core:$PYTHONPATH
exec "$@"
