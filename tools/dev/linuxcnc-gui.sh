#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · podgląd GUI na laptopie (nie zastępuje budowy RIP z sesji 003, zakres Codexa).
# LinuxCNC 2.9 (pakiety linuxcnc.org, bookworm 2.9-uspace) w podmanie, okno na pulpicie gospodarza (X11/Xwayland).
#   tools/dev/linuxcnc-gui.sh                    # symulator QtDragon (XYZ, metryczny)
#   tools/dev/linuxcnc-gui.sh linuxcnc <plik.ini> # dowolna konfiguracja (repo widoczne jako /work)
#   tools/dev/linuxcnc-gui.sh bash                # powłoka w kontenerze
# Przed użyciem: python tools/lock.py acquire linuxcnc --model ... (docs/WSPOLPRACA_MODELI.md §2a).
# Konfiguracje i ustawienia ekranu: ~/.cache/linumert/linuxcnc-home (trwałe między uruchomieniami).
set -euo pipefail
cd "$(dirname "$0")/../.."
RT=$(command -v podman || { echo "brak podman (sudo pacman -S --needed podman)" >&2; exit 2; })
IMG=linumert-cnc:bookworm-3
if ! "$RT" image inspect "$IMG" >/dev/null 2>&1; then
  "$RT" build -t "$IMG" -f - . <<'DOCKER'
FROM debian:bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
 && curl -sfL 'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3CB9FD148F374FEF' \
    | gpg --dearmor -o /usr/share/keyrings/linuxcnc.gpg \
 && gpg --show-keys --with-colons /usr/share/keyrings/linuxcnc.gpg \
    | grep -q '^fpr:::::::::EEDD0D29F81DCAA0D258661F3CB9FD148F374FEF:' \
 && echo 'deb [signed-by=/usr/share/keyrings/linuxcnc.gpg] http://www.linuxcnc.org/ bookworm base 2.9-uspace' \
    > /etc/apt/sources.list.d/linuxcnc.list \
 && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    linuxcnc-uspace python3-pyqt5 python3-pyqt5.qsci python3-pyqt5.qtsvg python3-pyqt5.qtopengl \
    python3-dbus.mainloop.pyqt5 python3-opengl python3-numpy python3-yaml mesa-utils fonts-dejavu \
 && rm -rf /var/lib/apt/lists/*
# Symulator bez RT: rtapi_app bez setuid, wszystkie procesy jako uid gospodarza (keep-id);
# setuid root w przestrzeni użytkownika rozdziela właścicieli pamięci HAL (shmget EACCES).
RUN chmod u-s /usr/bin/rtapi_app
RUN apt-get update && apt-get install -y --no-install-recommends python3-pytest \
 && rm -rf /var/lib/apt/lists/*
DOCKER
fi
HOME_DIR=$HOME/.cache/linumert/linuxcnc-home
mkdir -p "$HOME_DIR"
[ -n "${DISPLAY:-}" ] || { echo "brak DISPLAY (uruchom z sesji graficznej)" >&2; exit 2; }
X=(-e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:ro)
if [ -n "${XAUTHORITY:-}" ] && [ -f "$XAUTHORITY" ]; then
  X+=(-e XAUTHORITY=/tmp/.Xauthority -v "$XAUTHORITY:/tmp/.Xauthority:ro")
fi
[ -e /dev/dri ] && X+=(--device /dev/dri)
TTY=(); [ -t 0 ] && [ -t 1 ] && TTY=(-t)
if [ $# -eq 0 ]; then
  set -- sh -c 'C=$HOME/linuxcnc/configs/sim-qtdragon; if [ ! -d "$C" ]; then mkdir -p "$C" &&
    cp -r /usr/share/doc/linuxcnc/examples/sample-configs/sim/qtdragon/qtdragon_xyz/. "$C"/; fi
    exec linuxcnc "$C/qtdragon_metric.ini"'
fi
exec "$RT" run --rm -i "${TTY[@]}" --userns=keep-id --security-opt label=disable \
  -e HOME=/home/lcnc -e XDG_CACHE_HOME=/home/lcnc/.cache -e QT_X11_NO_MITSHM=1 -v "$HOME_DIR:/home/lcnc" -v "$PWD:/work" -w /work "${X[@]}" "$IMG" "$@"
