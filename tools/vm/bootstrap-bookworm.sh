#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Codex
set -euo pipefail
[[ $EUID == 0 && $# == 1 ]] || { echo 'Run as root with output tar path'; exit 2; }
output=$1
[[ ! -e $output ]] || { echo "Output already exists: $output"; exit 2; }
apt-get update
apt-get install -y --no-install-recommends debootstrap debian-archive-keyring ca-certificates
rootfs=$(mktemp -d /var/tmp/linumert-bookworm.XXXXXXXX)
# debootstrap verifies Debian Release signatures with the archive keyring.
debootstrap --variant=minbase bookworm "$rootfs" https://deb.debian.org/debian
chmod 755 "$rootfs"
cat > "$rootfs/etc/wsl.conf" <<'EOF'
[automount]
options = "uid=1000,gid=1000"

[user]
default = codex
EOF
mkdir -p "$(dirname "$output")"
tar --numeric-owner -C "$rootfs" -cpf "$output" .
echo "Rootfs exported to $output; bootstrap directory retained: $rootfs"
