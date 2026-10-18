#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Codex
set -eo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
target=${LINUXCNC_DIR:-$HOME/.cache/linuxcnc-2.9}
if [[ ! -f $target/.linumert-built ]]; then
    echo 'Build LinuxCNC first: bash tools/ci/build-linuxcnc.sh' >&2
    exit 2
fi
source "$target/scripts/rip-environment"
export LINUXCNC_DIR="$target"
export QT_QPA_PLATFORM=xcb LIBGL_ALWAYS_SOFTWARE=1
unset WAYLAND_DISPLAY
cd "$repo"
exec "${PYTHON:-python3}" -m pytest -o addopts= -m linuxcnc -v "$@"
