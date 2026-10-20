#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · 2026-10-19.
# Test end-to-end symulacji HMI w obrazie startera (linumert-app, tools/linumert-start.sh) pod Xvfb:
# LinuxCNC + ekran linumeRT (obszar Symulacja) + proces linumert_sim.live; bazowanie, program demo,
# program kolizji (oczekiwane K-302 bez zmiany stanu LinuxCNC). Kopia konfiguracji w /tmp z HMI_ESTOP_BYPASS = 1
# (bez operatora nie ma kto zwolnić grzyba). Zrzuty i dziennik zdarzeń: build/sim-e2e/.
#   tools/dev/sim-e2e.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
IMG=$(grep -o '^IMG_REV=[0-9]*' tools/linumert-start.sh | cut -d= -f2)
IMG=linumert-app:bookworm-$IMG
mkdir -p build/sim-e2e
TEST_IMG=$IMG-test
podman image exists "$TEST_IMG" || podman build -t "$TEST_IMG" -f - . <<DOCKER
FROM $IMG
RUN apt-get update -qq && apt-get install -y -qq xvfb x11-apps imagemagick procps >/dev/null \
 && rm -rf /var/lib/apt/lists/*
DOCKER
# jak starter: zwykły użytkownik (LinuxCNC nie startuje jako root)
exec podman run --rm -i --userns=keep-id --security-opt label=disable -e HOME=/tmp/home \
  -v "$PWD:/work" -w /work "$TEST_IMG" bash -c '
set -e
mkdir -p /tmp/home
rm -rf /tmp/t && mkdir -p /tmp/t && cp -r config/sim /tmp/t/ && cp -r config/hal /tmp/t/
mkdir -p /tmp/t/screens && ln -s /work/screens/linumert /tmp/t/screens/linumert
C=/tmp/t/sim/linumert_xyz
rm -f $C/linumert_tools.db $C/linumert.var*; cp config/sim/linumert_xyz/linumert.var.default $C/linumert.var
sed -i "s/^HMI_ESTOP_BYPASS = 0/HMI_ESTOP_BYPASS = 1/" $C/linumert_xyz.ini
rm -f $C/qtvcp/screens/linumert && ln -s /work/screens/linumert $C/qtvcp/screens/linumert
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp & sleep 2
export DISPLAY=:99 LINUMERT_SIM_LOG=/work/build/sim-e2e/events.jsonl LINUMERT_START_AREA=sim
rm -f $LINUMERT_SIM_LOG
linuxcnc $C/linumert_xyz.ini > /work/build/sim-e2e/linuxcnc.log 2>&1 &
python3 /work/tools/dev/sim_e2e_driver.py /work/build/sim-e2e $C/../nc_files
'
