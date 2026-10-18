#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · D27: wyniki testów liczą się tylko z Debiana 12 (bookworm).
# Uruchamia polecenie w kontenerze debian:bookworm z katalogiem repo jako /work (Podman albo Docker).
#   tools/dev/debian-container.sh make lint test test-c test-san
#   tools/dev/debian-container.sh bash          # powłoka interaktywna
# Pierwsze uruchomienie buduje obraz linumert-dev:bookworm (gcc, make, python3 + venv, git, pytest, ruff).
set -euo pipefail
cd "$(dirname "$0")/../.."
RT=$(command -v podman || command -v docker || { echo "brak podman/docker" >&2; exit 2; })
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
