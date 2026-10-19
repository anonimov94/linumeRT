#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Codex
# Local test desktop. Run from Ubuntu WSL, keep this process alive.
set -euo pipefail

display_number=${LRT_VNC_DISPLAY:-9}
model=${LRT_TEST_MODEL:-Manual}
case "$model" in Codex|Claude|Manual) ;; *) echo 'Invalid LRT_TEST_MODEL' >&2; exit 2 ;; esac
if [[ ! $display_number =~ ^[1-9][0-9]{0,2}$ ]]; then
    echo 'LRT_VNC_DISPLAY must be an integer from 1 to 999.' >&2
    exit 2
fi
for command in Xtigervnc xauth mcookie xdpyinfo dbus-run-session xfce4-session \
    xfce4-terminal setsid timeout python3; do
    command -v "$command" >/dev/null || { echo "Missing: $command" >&2; exit 2; }
done
password_file=${LRT_VNC_PASSWORD_FILE:-$HOME/.vnc/passwd}
if [[ ! -r $password_file ]]; then
    echo 'Create a VNC password using tigervncpasswd first.' >&2
    exit 2
fi
viewer_display=${DISPLAY:-:0}
viewer_authority=${XAUTHORITY:-$HOME/.Xauthority}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
# Prefer the project's development environment, while keeping system GUI packages available.
if [[ -x $repo/.venv/bin/python ]]; then export PATH="$repo/.venv/bin:$PATH"; fi
runtime=$(mktemp -d "${TMPDIR:-/tmp}/linumert-vnc.XXXXXXXX")
server_pid='' desktop_pid='' terminal_pid='' viewer_pid=''
cleanup() {
    trap - EXIT INT TERM
    for pid in "$viewer_pid" "$terminal_pid" "$server_pid"; do
        [[ -z $pid ]] || kill "$pid" 2>/dev/null || true
    done
    [[ -z $desktop_pid ]] || kill -- "-$desktop_pid" 2>/dev/null || true
    wait 2>/dev/null || true
    echo "Session stopped. Diagnostic logs retained in $runtime"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
export DISPLAY=:$display_number
export XAUTHORITY=$runtime/Xauthority
export GDK_BACKEND=x11 QT_QPA_PLATFORM=xcb XDG_SESSION_TYPE=x11 XDG_CURRENT_DESKTOP=XFCE
unset WAYLAND_DISPLAY SESSION_MANAGER DBUS_SESSION_BUS_ADDRESS
touch "$XAUTHORITY"
chmod 600 "$XAUTHORITY"
xauth -f "$XAUTHORITY" add "$DISPLAY" . "$(mcookie)"
port=$((5900 + display_number))
Xtigervnc "$DISPLAY" -localhost=1 -rfbport "$port" -SecurityTypes VncAuth \
    -PasswordFile "$password_file" -auth "$XAUTHORITY" -desktop linumeRT-Ubuntu-testy \
    -geometry 1440x900 -depth 24 -nolisten unix -noreset >"$runtime/server.log" 2>&1 &
server_pid=$!
ready=0
for ((attempt=0; attempt<20; attempt++)); do
    if ! kill -0 "$server_pid" 2>/dev/null; then
        cat "$runtime/server.log" >&2
        exit 1
    fi
    if timeout 1 xdpyinfo >/dev/null 2>&1; then ready=1; break; fi
    sleep 0.25
done
if [[ $ready != 1 ]]; then
    echo "X11 did not become ready. See $runtime/server.log" >&2
    exit 1
fi
setsid dbus-run-session -- xfce4-session >"$runtime/desktop.log" 2>&1 &
desktop_pid=$!
xfce4-terminal --disable-server --title=linumeRT-testy --working-directory="$repo" \
    --hold --command="python3 tools/agent_tests/run.py --model $model" \
    >"$runtime/terminal.log" 2>&1 &
terminal_pid=$!
echo "VNC: 127.0.0.1:$port; DISPLAY=$DISPLAY; XAUTHORITY=$XAUTHORITY"
echo "Logs: $runtime. Stop with Ctrl+C in this launching console."
if [[ ${LRT_VNC_VIEWER:-1} == 1 ]] && command -v vncviewer >/dev/null; then
    DISPLAY=$viewer_display XAUTHORITY=$viewer_authority \
        vncviewer -passwd "$password_file" "127.0.0.1:$port" >"$runtime/viewer.log" 2>&1 &
    viewer_pid=$!
fi
wait "$server_pid"
