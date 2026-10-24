# shellcheck shell=bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · sesja 025. Wspólne funkcje post-install-ctl.sh i post-install-plant.sh.

VM_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

log() { printf '\033[1m[linumeRT]\033[0m %s\n' "$*"; }
die() { printf '[linumeRT] BŁĄD: %s\n' "$*" >&2; exit 1; }

# Wczytuje vm.conf (KLUCZ=wartość; inny plik: VM_CONF=ścieżka) do zmiennych; zmienne środowiska wygrywają.
load_conf() {
    local file=${VM_CONF:-$VM_DIR/vm.conf} key value
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

# Karty Ethernet według nazwy; w VirtualBox: 1 = NAT, 2 = lrtnet, 3 = host-only (np. enp0s3/8/9).
nics() {
    local found=() path
    for path in /sys/class/net/en* /sys/class/net/eth*; do
        [[ -e $path ]] && found+=("${path##*/}")
    done
    printf '%s\n' "${found[@]}" | sort
}

# Karta 2: statyczny adres w lrtnet; karta 3 (jeśli jest): DHCP z sieci host-only VirtualBox.
configure_networks() {
    local ip=$1 all lrt host file=/etc/network/interfaces.d/linumert
    mapfile -t all < <(nics)
    [[ ${#all[@]} -ge 2 ]] || die "brak drugiej karty sieciowej (lrtnet); sprawdź ustawienia VM"
    lrt=${LRTNET_NIC:-${all[1]}} host=${HOSTONLY_NIC:-${all[2]:-}}
    if command -v nmcli >/dev/null && systemctl is-active -q NetworkManager; then
        log "NetworkManager: $lrt → $ip/$LRTNET_PREFIX (połączenie lrtnet); host-only: DHCP NetworkManagera"
        if nmcli -t -f NAME con show | grep -qx lrtnet; then nmcli con delete lrtnet >/dev/null; fi
        nmcli con add type ethernet ifname "$lrt" con-name lrtnet ipv4.method manual \
            ipv4.addresses "$ip/$LRTNET_PREFIX" ipv6.method disabled >/dev/null
        nmcli con up lrtnet >/dev/null
        return
    fi
    log "ifupdown: $lrt → $ip/$LRTNET_PREFIX${host:+, $host → DHCP (host-only)} ($file)"
    {
        printf 'auto %s\niface %s inet static\n    address %s/%s\n' "$lrt" "$lrt" "$ip" "$LRTNET_PREFIX"
        [[ -z $host ]] || printf '\nauto %s\niface %s inet dhcp\n' "$host" "$host"
    } >"$file"
    local nic
    for nic in "$lrt" $host; do
        ifdown "$nic" 2>/dev/null || true
        ifup "$nic" || die "ifup $nic"
    done
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
timing: {cycle_ns: 1000000, substeps: 4, watchdog_ms: 50}
mode: realtime
seed: 1
state_file: /var/lib/linumert-plant/plant_state.json
oracle: {arm_bit: 31}
EOF
    if [[ $vfd == 1 ]]; then
        echo "vfd: {device: $VFD_DEVICE, modbus_listen: $LRTNET_PLANT_IP, modbus_port: 1502, slave: 1}"
    fi
}
