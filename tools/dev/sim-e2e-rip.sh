#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · 2026-10-25.
# Odpowiednik tools/dev/sim-e2e.sh bez kontenera: LinuxCNC RIP (~/.cache/linuxcnc-2.9) + ekran linumeRT pod Xvfb
# (TCP, bo /tmp/.X11-unix w WSL nie ma uprawnień do gniazd). Wymaga: imagemagick (import/convert), xvfb,
# PyQt5 systemowy oraz pyyaml, pydantic i pyqtgraph 0.13 w katalogu $PGPATH (domyślnie /tmp/pgpath):
#   pip install --no-deps --target /tmp/pgpath pyqtgraph==0.13.7 pyyaml pydantic pydantic-core \
#       annotated-types typing-extensions typing-inspection
# Zajmuje blokadę `linuxcnc`. Wynik: zrzuty i wynik.json w katalogu z argumentu (domyślnie build/sim-e2e).
# HMI_ESTOP_BYPASS = 1 tylko w kopii konfiguracji w /tmp (próba bez operatora, bez fizycznej maszyny).
set -uo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
OUT=${1:-$ROOT/build/sim-e2e}
PGPATH=${PGPATH:-/tmp/pgpath}
PY=${PYTHON:-python3}
export LINUMERT_LOCK_DIR=${LINUMERT_LOCK_DIR:-$HOME/linumert-test/locks}
mkdir -p "$LINUMERT_LOCK_DIR" "$OUT"
$PY tools/lock.py acquire linuxcnc --model "${MODEL:-Claude}" --note "sim-e2e-rip" || exit 75
cleanup() {
    for n in linuxcnc linuxcncsvr milltask io iov2 halui rtapi_app Xvfb; do pkill -KILL -x $n 2>/dev/null; done
    rm -f /tmp/.X99-lock
    $PY tools/lock.py release linuxcnc --model "${MODEL:-Claude}" >/dev/null
}
trap cleanup EXIT
T=/tmp/t-shots; rm -rf $T "$OUT"/*.png; mkdir -p $T/screens
cp -r config/sim $T/; cp -r config/hal $T/
ln -s "$ROOT/screens/linumert" $T/screens/linumert
C=$T/sim/linumert_xyz
rm -f $C/linumert_tools.db $C/linumert.var*; cp config/sim/linumert_xyz/linumert.var.default $C/linumert.var
sed -i "s/^HMI_ESTOP_BYPASS = 0/HMI_ESTOP_BYPASS = 1/" $C/linumert_xyz.ini
sed -i "s/^DISPLAY = qtvcp linumert/DISPLAY = qtvcp -g 1920x1080+0+0 linumert/" $C/linumert_xyz.ini
rm -f $C/qtvcp/screens/linumert; ln -s "$ROOT/screens/linumert" $C/qtvcp/screens/linumert
source "${LINUXCNC_DIR:-$HOME/.cache/linuxcnc-2.9}/scripts/rip-environment"
halrun -U >/dev/null 2>&1
for n in linuxcnc linuxcncsvr milltask io iov2 halui rtapi_app Xvfb; do pkill -KILL -x $n 2>/dev/null; done
rm -f /tmp/linuxcnc.lock /tmp/.X99-lock; sleep 2
export PYTHONPATH=$ROOT/core:$ROOT/simulation:$PGPATH:${PYTHONPATH:-}
Xvfb :99 -screen 0 1920x1080x24 -ac -nolisten unix -listen tcp & sleep 2
export DISPLAY=127.0.0.1:99 LINUMERT_SIM_LOG=$OUT/events.jsonl LINUMERT_START_AREA=sim
rm -f "$LINUMERT_SIM_LOG"
linuxcnc $C/linumert_xyz.ini > "$OUT/linuxcnc.log" 2>&1 &
python3 "$ROOT/tools/dev/sim_e2e_driver.py" "$OUT" $C/../nc_files
