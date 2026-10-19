# shellcheck shell=bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · sesja 025. Wspólne funkcje post-install-ctl.sh i post-install-plant.sh.

VM_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

log() { printf '\033[1m[linumeRT]\033[0m %s\n' "$*"; }
die() { printf '[linumeRT] BŁĄD: %s\n' "$*" >&2; exit 1; }

# Wczytuje tools/vm/vm.conf (KLUCZ=wartość) do zmiennych powłoki; zmienne środowiska wygrywają.
load_conf() {
    local file=${1:-$VM_DIR/vm.conf} key value
    [[ -r $file ]] || die "brak pliku $file"
    while IFS='=' read -r key value; do
        [[ $key =~ ^[A-Z][A-Z0-9_]*$ ]] || continue
        [[ -n ${!key:-} ]] || printf -v "$key" '%s' "$value"
        export "${key?}"
    done <"$file"
}

require_root() { [[ $EUID == 0 ]] || die "uruchom przez sudo: sudo bash $0 $*"; }

require_debian12() {
    local id version
    # shellcheck disable=SC1091
    id=$(. /etc/os-release && echo "$ID") version=$(. /etc/os-release && echo "${VERSION_ID:-}")
    [[ $id == debian && $version == 12 ]] || die "oczekiwano Debiana 12, jest $id $version"
}

# Druga karta Ethernet (pierwsza to NAT): w VirtualBox karta 2 = lrtnet, np. enp0s8.
second_nic() {
    local nics=() path
    for path in /sys/class/net/en* /sys/class/net/eth*; do
        [[ -e $path ]] && nics+=("${path##*/}")
    done
    mapfile -t nics < <(printf '%s\n' "${nics[@]}" | sort)
    [[ ${#nics[@]} -ge 2 ]] || die "brak drugiej karty sieciowej (lrtnet); sprawdź ustawienia VM"
    echo "${nics[1]}"
}

# Statyczny adres w sieci lrtnet (ifupdown, domyślny w Debianie 12 bez NetworkManagera).
configure_lrtnet() {
    local ip=$1 nic=${LRTNET_NIC:-$(second_nic)} file=/etc/network/interfaces.d/lrtnet
    if command -v nmcli >/dev/null && systemctl is-active -q NetworkManager; then
        log "NetworkManager: $nic → $ip/$LRTNET_PREFIX (połączenie lrtnet)"
        nmcli -t -f NAME con show | grep -qx lrtnet && nmcli con delete lrtnet >/dev/null
        nmcli con add type ethernet ifname "$nic" con-name lrtnet ipv4.method manual \
            ipv4.addresses "$ip/$LRTNET_PREFIX" ipv6.method disabled >/dev/null
        nmcli con up lrtnet >/dev/null
        return
    fi
    log "ifupdown: $nic → $ip/$LRTNET_PREFIX ($file)"
    printf 'auto %s\niface %s inet static\n    address %s/%s\n' "$nic" "$nic" "$ip" "$LRTNET_PREFIX" >"$file"
    ifdown "$nic" 2>/dev/null || true
    ifup "$nic"
}

# Klon albo aktualizacja repozytorium w $REPO_DIR (właściciel: $VM_USER).
fetch_repo() {
    local src=${1:-$REPO_URL}
    if [[ -d $REPO_DIR/.git ]]; then
        log "repozytorium istnieje: $REPO_DIR (git pull)"
        runuser -u "$VM_USER" -- git -C "$REPO_DIR" pull --ff-only
    else
        log "klonowanie $src → $REPO_DIR"
        install -d -o "$VM_USER" -g "$VM_USER" "$REPO_DIR"
        runuser -u "$VM_USER" -- git clone --depth 1 "$src" "$REPO_DIR"
    fi
}

# venv z pakietem linumert; $1 = dodatki pip (np. "[panel]"), $2 = --system-site-packages albo puste.
make_venv() {
    local extras=$1 site=${2:-}
    log "venv $REPO_DIR/.venv (pip install -e .$extras)"
    # shellcheck disable=SC2086
    runuser -u "$VM_USER" -- python3 -m venv $site "$REPO_DIR/.venv"
    runuser -u "$VM_USER" -- "$REPO_DIR/.venv/bin/pip" install -q -e "$REPO_DIR$extras"
}

# plant.yaml dla VM-B (stdout); $1 = 1: z falownikiem (pty dla hy_vfd, Modbus TCP).
# Wzór: config/plant/linumert_plant_xyz/plant.yaml i plant_vfd.yaml (te same pola, tryb realtime).
plant_yaml() {
    local vfd=${1:-0}
    cat <<EOF
# linumeRT · VM-B: Plant w trybie realtime (wygenerowane przez tools/vm/post-install-plant.sh).
# Zmiany ręczne znikną po ponownym uruchomieniu skryptu.
machine: $REPO_DIR/config/machines/mill_servo_table.yaml
network: {listen: $LRTNET_PLANT_IP, port: $LRTNET_PORT, panel_listen: 0.0.0.0, panel_port: $PANEL_PORT}
timing: {cycle_ns: 1000000, substeps: 1, watchdog_ms: 50}
mode: realtime
seed: 1
state_file: /var/lib/linumert-plant/plant_state.json
oracle: {arm_bit: 31}
EOF
    if [[ $vfd == 1 ]]; then
        echo "vfd: {device: $VFD_DEVICE, modbus_listen: $LRTNET_PLANT_IP, modbus_port: 1502, slave: 1}"
    fi
}
