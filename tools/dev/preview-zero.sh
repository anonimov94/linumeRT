#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Codex · wyłącznie edytor offline, bez startowania LinuxCNC.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
if python3 -c 'import PyQt5.QtWidgets, numpy' >/dev/null 2>&1; then
    exec python3 "$repo/tools/dev/preview-zero.py" "$@"
fi
command -v podman >/dev/null || { echo 'Brak PyQt5/numpy i Podmana.' >&2; exit 2; }
revision=$(sed -n 's/^IMG_REV=\([0-9]*\).*/\1/p' "$repo/tools/linumert-start.sh")
image="linumert-app:bookworm-$revision"
podman image exists "$image" || {
    echo "Brak obrazu $image. Zbuduj go starterem linumeRT." >&2; exit 2; }
[ -n "${DISPLAY:-}" ] || { echo 'Uruchom z terminala na pulpicie.' >&2; exit 2; }
x=(-e DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix:ro)
if [ -n "${XAUTHORITY:-}" ] && [ -f "$XAUTHORITY" ]; then
    x+=(-e XAUTHORITY=/tmp/.Xauthority -v "$XAUTHORITY:/tmp/.Xauthority:ro")
fi
exec podman run --rm --userns=keep-id --security-opt label=disable --network=none \
    --read-only --tmpfs /tmp:rw,exec,mode=1777 -e HOME=/tmp/home \
    -v "$repo:/work:ro" -w /work "${x[@]}" "$image" bash -c '
mkdir -p /tmp/home
exec /opt/linumert/bin/python /work/tools/dev/preview-zero.py "$@"
' _ "$@"
