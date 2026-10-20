#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · sesja 018.
# LinuxCNC (RIP z tools/ci/build-linuxcnc.sh) + wirtualna obrabiarka Plant w jednym kontenerze
# Debian 12 (obraz linumert-rip:bookworm), okno ekranu linumert na pulpicie gospodarza.
#   tools/dev/plant-gui.sh                 # Plant + LinuxCNC z ekranem
#   HEADLESS=1 tools/dev/plant-gui.sh CMD  # bez ekranu: polecenie w gotowym środowisku (testy)
#   VFD=1 tools/dev/plant-gui.sh           # wariant _vfd: wrzeciono przez hy_vfd i falownik Plant
# Kroki w kontenerze: rdzeń Plant (make shared), halcompile --install lrt_net/lrt_cia402 do RIP,
# serwer Plant (plant.yaml konfiguracji), LinuxCNC. RIP: ~/.cache/linumert/rip-home.
set -euo pipefail
cd "$(dirname "$0")/../.."
RIPHOME=$HOME/.cache/linumert/rip-home
[ -f "$RIPHOME/.cache/linuxcnc-2.9/scripts/rip-environment" ] || {
  echo "brak RIP: zbuduj obraz i LinuxCNC (docs/PLANT_START.md)" >&2; exit 2; }
CFG=config/plant/linumert_plant_xyz
INI=linumert_plant_xyz.ini PLANT_YAML=plant.yaml
if [ -n "${VFD:-}" ]; then INI=linumert_plant_xyz_vfd.ini PLANT_YAML=plant_vfd.yaml; fi
X=()
if [ -z "${HEADLESS:-}" ]; then
  [ -n "${DISPLAY:-}" ] || { echo "brak DISPLAY" >&2; exit 2; }
  X=(-e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:ro -e QT_X11_NO_MITSHM=1)
  if [ -n "${XAUTHORITY:-}" ] && [ -f "$XAUTHORITY" ]; then
    X+=(-e XAUTHORITY=/tmp/.Xauthority -v "$XAUTHORITY:/tmp/.Xauthority:ro")
  fi
  [ -e /dev/dri ] && X+=(--device /dev/dri)
fi
TTY=(); [ -t 0 ] && [ -t 1 ] && TTY=(-t)
if [ $# -eq 0 ]; then set -- linuxcnc "/work/$CFG/$INI"; fi
exec podman run --rm -i "${TTY[@]}" --userns=keep-id --security-opt label=disable \
  -e HOME=/home/rip -e XDG_CACHE_HOME=/home/rip/.cache -v "$RIPHOME:/home/rip" -v "$PWD:/work" \
  -w /work "${X[@]}" linumert-rip:bookworm bash -c '
set -e
source /home/rip/.cache/linuxcnc-2.9/scripts/rip-environment >/dev/null
make -s -C plant/core shared >/dev/null
T=$(mktemp -d); cp hal/lrt_net.comp hal/lrt_net_proto.h hal/lrt_cia402.comp hal/lrt_estop2.comp "$T"/
( cd "$T" && halcompile --install lrt_net.comp >/dev/null && halcompile --install lrt_cia402.comp >/dev/null && halcompile --install lrt_estop2.comp >/dev/null )
PY=/home/rip/venv/bin/python
[ -x $PY ] || { python3 -m venv --system-site-packages /home/rip/venv && $PY -m pip install -q -e ".[dev]"; }
PYTHONPATH=/work/core:/work/plant/server $PY -m linumert_plant serve --plant '"$CFG/$PLANT_YAML"' \
  > /tmp/plant.log 2>&1 &
PLANT=$!
trap "kill $PLANT 2>/dev/null; wait $PLANT 2>/dev/null; tail -2 /tmp/plant.log" EXIT
sleep 2
"$@"' _ "$@"
