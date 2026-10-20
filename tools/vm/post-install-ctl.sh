#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · sesja 025
# VM-A (LinuxCNC 2.9 + ekran linumeRT) po instalacji z obrazu LinuxCNC 2.9 (Debian 12):
# narzędzia, repozytorium, venv rdzenia, komponenty HAL (halcompile --install), statyczny adres
# w sieci lrtnet i konfiguracje LinuxCNC wskazujące Plant w VM-B.
# Użycie (w VM-A):  sudo bash tools/vm/post-install-ctl.sh [--vfd] [--repo URL|ŚCIEŻKA] [--no-net]
#   --vfd     także most socat: lokalny pty $VFD_DEVICE ↔ TCP VM-B:$VFD_BRIDGE_PORT (dla hy_vfd)
#   --repo    źródło klonu (domyślnie REPO_URL z vm.conf)
#   --no-net  bez konfiguracji kart lrtnet i host-only
# Skrypt można uruchomić ponownie.
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
        -h|--help) sed -n '5,11p' "$0"; exit 0 ;;
        *) die "nieznana opcja: $1" ;;
    esac
    shift
done
require_root "$@"
require_debian12
id "$VM_USER" >/dev/null 2>&1 || die "brak użytkownika $VM_USER (VM_USER=<login> sudo -E bash $0)"
command -v linuxcnc >/dev/null || die "brak LinuxCNC: VM-A instaluje się z obrazu LinuxCNC 2.9 (docs/VM.md §3)"

log "pakiety Debiana"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q --no-install-recommends git ca-certificates python3-venv python3-pip \
    linuxcnc-uspace-dev socat
if [[ $net == 1 ]]; then configure_networks "$LRTNET_CTL_IP"; fi

fetch_repo "$repo"
# --system-site-packages: moduły linuxcnc, qtvcp i PyQt5 pochodzą z pakietów Debiana/LinuxCNC.
make_venv "" --system-site-packages

log "komponenty HAL (halcompile --install)"
for comp in lrt_net lrt_cia402 lrt_hardstop_home lrt_estop2; do
    (cd "$REPO_DIR/hal" && halcompile --install "$comp.comp" >/dev/null) || die "halcompile $comp.comp"
done

log "konfiguracje LinuxCNC z [PLANT]IP = $LRTNET_PLANT_IP"
cfg=$REPO_DIR/config/plant/linumert_plant_xyz
for ini in linumert_plant_xyz linumert_plant_xyz_vfd; do
    # Kopia obok oryginału: ścieżki względne INI (HAL, tool.tbl, ekran) działają bez zmian.
    sed -e "/^\[PLANT\]/,/^\[/ s/^IP = .*/IP = $LRTNET_PLANT_IP/" \
        -e "/^\[PLANT\]/,/^\[/ s/^PORT = .*/PORT = $LRTNET_PORT/" \
        "$cfg/$ini.ini" >"$cfg/${ini}_vm.ini"
    chown "$VM_USER:$VM_USER" "$cfg/${ini}_vm.ini"
done

if [[ $vfd == 1 ]]; then
    log "most falownika: $VFD_DEVICE ↔ $LRTNET_PLANT_IP:$VFD_BRIDGE_PORT (usługa linumert-vfd-link)"
    cat >/etc/systemd/system/linumert-vfd-link.service <<EOF
[Unit]
Description=linumeRT: pty $VFD_DEVICE dla hy_vfd ↔ Plant VM-B $LRTNET_PLANT_IP:$VFD_BRIDGE_PORT
After=network-online.target
Wants=network-online.target

[Service]
User=$VM_USER
ExecStart=/usr/bin/socat PTY,link=$VFD_DEVICE,raw,echo=0 TCP:$LRTNET_PLANT_IP:$VFD_BRIDGE_PORT
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable -q --now linumert-vfd-link.service
fi

log "gotowe. Start (jako $VM_USER, na pulpicie VM-A):"
log "  linuxcnc $cfg/linumert_plant_xyz_vm.ini"
[[ $vfd == 1 ]] && log "  linuxcnc $cfg/linumert_plant_xyz_vfd_vm.ini   (wrzeciono przez hy_vfd)"
log "test łącza: $REPO_DIR/.venv/bin/python $REPO_DIR/tools/vm/lrtnet_probe.py --host $LRTNET_PLANT_IP"
