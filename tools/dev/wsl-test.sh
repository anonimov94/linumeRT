#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · sesja 008 (podział 022–025).
# Testy zatwierdzonego HEAD bieżącej gałęzi w WSL, na świeżym klonie w systemie plików Linuksa
# (checkout na dysku Windows ma core.symlinks=false i psuje dowiązania ekranu). Każda gałąź ma
# własny klon i venv w ~/linumert-test/<gałąź>, więc równoległe sesje się nie mieszają.
# Uruchomienie z Git Bash na Windows, z katalogu checkoutu (także worktree):
#   MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash tools/dev/wsl-test.sh            # lint, test, test-c
#   MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash tools/dev/wsl-test.sh --linuxcnc # + testy LinuxCNC
# --linuxcnc zajmuje blokadę `linuxcnc` (jedna instancja LinuxCNC w WSL naraz; kod 75 = zajęta).
# MODEL=Codex zmienia autora blokady; LINUXCNC_DIR wskazuje RIP (domyślnie ~/.cache/linuxcnc-2.9).
set -uo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
branch=$(git -C "$repo" rev-parse --abbrev-ref HEAD)
base=$HOME/linumert-test
work=$base/${branch//\//-}
export LINUMERT_LOCK_DIR=$base/locks
rm -rf "$work/src" && mkdir -p "$work" "$LINUMERT_LOCK_DIR" || exit 3
git clone -q --branch "$branch" "$repo" "$work/src" || exit 3
cd "$work/src" || exit 3
echo "== $branch @ $(git rev-parse --short HEAD) → $work/src"
if [ ! -x "$work/venv/bin/python" ]; then
    python3 -m venv --system-site-packages "$work/venv" || exit 3
fi
PY=$work/venv/bin/python
"$PY" -m pip install -q -e ".[dev]" >/dev/null || { echo "pip install nieudany" >&2; exit 3; }
export PYTHONPATH=$PWD/core:$PWD/plant/server:$PWD/simulation
status=0
echo "== lint"; make -s lint PYTHON="$PY" || status=1
echo "== test"; make -s test PYTHON="$PY" >"$work/test.log" 2>&1 || status=1; tail -3 "$work/test.log"
echo "== test-c"; make -s test-c >"$work/test-c.log" 2>&1 || status=1; grep -E "^# testy" "$work/test-c.log"
if [ "${1:-}" = "--linuxcnc" ]; then
    if ! "$PY" tools/lock.py acquire linuxcnc --model "${MODEL:-Claude}" --note "$branch"; then
        echo "blokada linuxcnc zajęta: $("$PY" tools/lock.py status)" >&2
        exit 75
    fi
    trap '"$PY" tools/lock.py release linuxcnc --model "${MODEL:-Claude}" >/dev/null' EXIT
    echo "== linuxcnc"
    make -s -C plant/core shared || status=1
    make -s test-linuxcnc PYTHON="$PY" >"$work/linuxcnc.log" 2>&1 || status=1
    grep -E "^(FAILED|ERROR)|^=+ .* =+$" "$work/linuxcnc.log" | tail -8
    pgrep -l -x 'linuxcnc|linuxcncsvr|milltask|rtapi_app' && { echo "zostały procesy LinuxCNC" >&2; status=1; }
fi
echo "== wynik: $([ $status -eq 0 ] && echo OK || echo BŁĄD) (logi: $work/*.log)"
exit $status
