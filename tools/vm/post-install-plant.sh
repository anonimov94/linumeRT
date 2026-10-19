#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · sesja 025
# VM-B (Plant) po instalacji Debiana 12: zależności, repozytorium, rdzeń C, venv z panelem,
# statyczny adres w sieci lrtnet, plik /etc/linumert/plant.yaml i usługa systemd linumert-plant.
# Użycie (w VM-B):  sudo bash tools/vm/post-install-plant.sh [--vfd] [--repo URL|ŚCIEŻKA] [--no-net]
#   --vfd     Plant z falownikiem (pty dla hy_vfd) i most socat TCP:$VFD_BRIDGE_PORT → pty
#   --repo    źródło klonu (domyślnie REPO_URL z vm.conf; może być katalog z udostępnionego folderu)
#   --no-net  bez konfiguracji kart lrtnet i host-only (np. adresy ustawione ręcznie)
# Skrypt można uruchomić ponownie (aktualizuje repozytorium i pliki usług).
set -euo pipefail
# shellcheck source=tools/vm/lib.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
load_conf

vfd=0 net=1 repo=$REPO_URL
while [[ $# -gt 0 ]]; do
    case $1 in
        --vfd) vfd=1 ;;
        --no-net) net=0 ;;
        --repo) repo=${2:?--repo wymaga argumentu}; shift ;;
        -h|--help) sed -n '4,10p' "$0"; exit 0 ;;
        *) die "nieznana opcja: $1" ;;
    esac
    shift
done
require_root "$@"
require_debian12
id "$VM_USER" >/dev/null 2>&1 || die "brak użytkownika $VM_USER (preseed tworzy go przy instalacji)"

log "pakiety Debiana"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q --no-install-recommends git ca-certificates python3 python3-venv \
    python3-pip gcc make libc6-dev socat ifupdown
if [[ $net == 1 ]]; then configure_networks "$LRTNET_PLANT_IP"; fi

fetch_repo "$repo"
make_venv "[panel]"
log "rdzeń C Plant (make -C plant/core shared)"
runuser -u "$VM_USER" -- make -s -C "$REPO_DIR/plant/core" shared

install -d /etc/linumert
plant_yaml "$vfd" >/etc/linumert/plant.yaml

log "usługa systemd linumert-plant"
cat >/etc/systemd/system/linumert-plant.service <<EOF
[Unit]
Description=linumeRT Plant (wirtualna obrabiarka, LRT-NET :$LRTNET_PORT, panel :$PANEL_PORT)
After=network-online.target
Wants=network-online.target

[Service]
User=$VM_USER
WorkingDirectory=$REPO_DIR
StateDirectory=linumert-plant
ExecStart=$REPO_DIR/.venv/bin/python -m linumert_plant panel --plant /etc/linumert/plant.yaml --state-dir /var/lib/linumert-plant
Restart=on-failure
RestartSec=2
# Plant odpowiada na każdą ramkę LinuxCNC: wyższy priorytet niż reszta systemu (nie RT).
Nice=-5

[Install]
WantedBy=multi-user.target
EOF
if [[ $vfd == 1 ]]; then
    cat >/etc/systemd/system/linumert-vfd-bridge.service <<EOF
[Unit]
Description=linumeRT: most falownika TCP:$VFD_BRIDGE_PORT ↔ pty Plant ($VFD_DEVICE)
After=linumert-plant.service
BindsTo=linumert-plant.service

[Service]
User=$VM_USER
ExecStartPre=/bin/sh -c 'for i in \$(seq 50); do [ -e $VFD_DEVICE ] && exit 0; sleep 0.2; done; exit 1'
ExecStart=/usr/bin/socat TCP-LISTEN:$VFD_BRIDGE_PORT,bind=$LRTNET_PLANT_IP,reuseaddr,fork FILE:$VFD_DEVICE,raw,echo=0
Restart=on-failure
RestartSec=2

[Install]
WantedBy=linumert-plant.service
EOF
else
    systemctl disable --now linumert-vfd-bridge.service 2>/dev/null || true
    rm -f /etc/systemd/system/linumert-vfd-bridge.service
fi
systemctl daemon-reload
systemctl enable -q linumert-plant.service
systemctl restart linumert-plant.service
if [[ $vfd == 1 ]]; then
    systemctl enable -q linumert-vfd-bridge.service
    systemctl restart linumert-vfd-bridge.service
fi
sleep 2
systemctl --no-pager --lines=5 status linumert-plant.service || die "usługa nie wystartowała: journalctl -u linumert-plant"
log "gotowe: LRT-NET $LRTNET_PLANT_IP:$LRTNET_PORT, panel http://<adres host-only>:$PANEL_PORT/"
log "adresy: $(hostname -I)"
