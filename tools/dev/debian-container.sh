#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · D27: wyniki testów liczą się tylko z Debiana 12 (bookworm).
# Uruchamia polecenie w kontenerze debian:bookworm z katalogiem repo jako /work (Podman albo Docker;
# bez nich: rootfs Debiana 12 przez unshare -r + chroot, patrz niżej).
#   tools/dev/debian-container.sh make lint test test-c test-san
#   tools/dev/debian-container.sh bash          # powłoka interaktywna
# Pierwsze uruchomienie buduje obraz linumert-dev:bookworm (gcc, make, python3 + venv, git, pytest, ruff).
set -euo pipefail
cd "$(dirname "$0")/../.."
RT=$(command -v podman || command -v docker || true)
if [ -z "$RT" ]; then
  # Bez podman/docker (np. laptop z Archem bez sudo): rootfs Debiana 12 z linuxcontainers.org,
  # uruchamiany przez unshare -r + chroot (przestrzeń nazw użytkownika, nic nie instaluje w systemie).
  ROOT=${LINUMERT_DEB12_ROOT:-$HOME/.cache/linumert/debian12}
  IN=(unshare -rm --propagation private bash -c '
    R=$1; shift; mkdir -p "$R/work"; mount --rbind /dev "$R/dev"; mount --rbind /proc "$R/proc"
    mount --rbind /sys "$R/sys"; mount --bind "$PWD" "$R/work"; rm -f "$R/etc/resolv.conf"
    cp -L /etc/resolv.conf "$R/etc/resolv.conf"
    exec chroot "$R" /usr/bin/env -i HOME=/root LANG=C.UTF-8 TERM="${TERM:-dumb}" PYTHONPATH=/work/core \
      PATH=/opt/venv/bin:/usr/sbin:/usr/bin:/sbin:/bin bash -c "cd /work && \"\$@\"" _ "$@"' _ "$ROOT")
  if [ ! -x "$ROOT/opt/venv/bin/pytest" ]; then
    B=https://images.linuxcontainers.org/images/debian/bookworm/amd64/default
    D=$(curl -sfL "$B/" | grep -o '[0-9]\{8\}_[0-9][0-9]:[0-9][0-9]' | sort -u | tail -1)
    T=$(mktemp -d); U="$B/${D/:/%3A}"
    curl -sfL -o "$T/rootfs.tar.xz" "$U/rootfs.tar.xz"
    (cd "$T" && curl -sfL "$U/SHA256SUMS" | grep ' rootfs.tar.xz$' | sha256sum -c --quiet)
    mkdir -p "$ROOT"; unshare -r tar -xJf "$T/rootfs.tar.xz" -C "$ROOT" 2>/dev/null || true; rm -rf "$T"
    echo 'APT::Sandbox::User "root";' > "$ROOT/etc/apt/apt.conf.d/99sandbox"
    "${IN[@]}" sh -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      --no-install-recommends build-essential make git python3 python3-venv python3-pip ca-certificates \
      >/dev/null && python3 -m venv /opt/venv && /opt/venv/bin/pip install -q numpy pydantic pyyaml pytest ruff \
      && git config --global --add safe.directory /work'
  fi
  exec "${IN[@]}" "$@"
fi
IMG=linumert-dev:bookworm
if ! "$RT" image inspect "$IMG" >/dev/null 2>&1; then
  "$RT" build -t "$IMG" -f - . <<'DOCKER'
FROM debian:bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential make git python3 python3-venv python3-pip ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install -q numpy pydantic pyyaml pytest ruff
ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/work/core
WORKDIR /work
DOCKER
fi
exec "$RT" run --rm -it -v "$PWD:/work:Z" -w /work "$IMG" "$@"
