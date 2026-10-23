#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Test tworzenia konta przez Debian Live, w jednorazowym kontenerze bookworm.
# docker run --rm -v "$PWD:/work:ro" debian:bookworm sh /work/tools/iso/test-live-login.sh
# Model-Author: Codex
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    live-config live-config-systemd user-setup sudo python3 >/dev/null
LIVE_USERNAME=$(sed -n 's/.* username=\([^ ]*\) .*/\1/p' /work/tools/iso/build.sh)
test -n "$LIVE_USERNAME"
export LIVE_USERNAME
export LIVE_CONFIG_CMDLINE="boot=live components username=$LIVE_USERNAME"
export LIVE_USER_FULLNAME=linumeRT LIVE_USER_DEFAULT_GROUPS=sudo
mkdir -p /var/lib/live/config
/usr/lib/live/config/0030-user-setup
getent passwd "$LIVE_USERNAME" >/dev/null
python3 -W ignore::DeprecationWarning - <<'PY'
import crypt
import os
import pwd
import spwd

name = os.environ['LIVE_USERNAME']
account = pwd.getpwnam(name)
assert account.pw_uid == 1000
assert os.path.isdir(account.pw_dir)
stored = spwd.getspnam(name).sp_pwdp
assert crypt.crypt('live', stored) == stored, 'Live password does not match'
print('PASS: Live user exists, UID=1000, home exists, password verified')
PY
id -nG "$LIVE_USERNAME" | tr ' ' '\n' | grep -qx sudo
# Drugie uruchomienie nie może usunąć konta lub zmienić jego UID.
/usr/lib/live/config/0030-user-setup
test "$(id -u "$LIVE_USERNAME")" = 1000
