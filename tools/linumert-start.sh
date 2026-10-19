#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · starter aplikacji (2026-10-19).
# linumeRT jednym poleceniem na Linuksie z podmanem (EndeavourOS/Arch, także Fedora, Debian, Ubuntu):
# pobiera albo aktualizuje main z GitHuba, instaluje zależności, buduje kontener Debian 12 z LinuxCNC 2.9
# (pakiety linuxcnc.org) i otwiera okno LinuxCNC z ekranem linumeRT.
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/anonimov94/linumeRT/main/tools/linumert-start.sh)
#   ~/linumeRT/tools/linumert-start.sh            # symulator LinuxCNC + ekran linumeRT
#   ~/linumeRT/tools/linumert-start.sh --plant    # + wirtualna obrabiarka Plant (LRT-NET) i jej panel w przeglądarce
#   ~/linumeRT/tools/linumert-start.sh --plant --vfd   # wrzeciono przez falownik (hy_vfd)
#   ~/linumeRT/tools/linumert-start.sh --desktop  # skróty „linumeRT” w menu aplikacji, bez uruchamiania
# Opcje: --no-update (bez git pull), --rebuild (nowy obraz kontenera), --shell (powłoka w kontenerze),
#        --dir KATALOG (repozytorium, domyślnie ~/linumeRT albo repozytorium, w którym leży skrypt),
#        --classic (czysty QtDragon, LINUMERT_SHELL=0).
# Pierwsze uruchomienie: kilka minut (obraz ok. 1,5 GB); kolejne: kilkanaście sekund.
# NIEZWERYFIKOWANE NA SPRZĘCIE: to symulacja, bez połączenia z prawdziwą maszyną.
set -euo pipefail

REPO_URL=https://github.com/anonimov94/linumeRT.git
IMG_REV=2  # zmień przy każdej zmianie Containerfile niżej (wymusza przebudowę obrazu)
IMG=linumert-app:bookworm-$IMG_REV
PANEL_PORT=8080

say() { printf '\033[1;36m[linumeRT]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[linumeRT] BŁĄD:\033[0m %s\n' "$*" >&2; exit 1; }

mode=sim vfd=0 update=1 rebuild=0 shell=0 desktop=0 classic=0 dir=""
while [ $# -gt 0 ]; do
    case $1 in
        --plant) mode=plant ;;
        --vfd) vfd=1 ;;
        --no-update) update=0 ;;
        --rebuild) rebuild=1 ;;
        --shell) shell=1 ;;
        --desktop) desktop=1 ;;
        --classic) classic=1 ;;
        --dir) dir=${2:?--dir wymaga katalogu}; shift ;;
        -h|--help) sed -n '5,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "nieznana opcja: $1 (--help)" ;;
    esac
    shift
done
[ "$vfd" = 1 ] && [ "$mode" != plant ] && die "--vfd działa z --plant"

# ---- 1. zależności gospodarza -------------------------------------------------------------------
need=()
command -v git >/dev/null || need+=(git)
command -v podman >/dev/null || need+=(podman)
if [ ${#need[@]} -gt 0 ]; then
    say "instaluję: ${need[*]} (potrzebne sudo)"
    if command -v pacman >/dev/null; then sudo pacman -S --needed --noconfirm "${need[@]}"
    elif command -v dnf >/dev/null; then sudo dnf install -y "${need[@]}"
    elif command -v apt-get >/dev/null; then sudo apt-get update && sudo apt-get install -y "${need[@]}"
    else die "zainstaluj ręcznie: ${need[*]}"; fi
fi

# ---- 2. repozytorium (main z GitHuba) ------------------------------------------------------------
if [ -z "$dir" ]; then
    here=""
    if src=$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd); then
        here=$(git -C "$src" rev-parse --show-toplevel 2>/dev/null) || here=""
    fi
    if [ -n "$here" ] && [ -f "$here/tools/linumert-start.sh" ]; then dir=$here; else dir=$HOME/linumeRT; fi
fi
if [ ! -d "$dir/.git" ]; then
    say "pobieram $REPO_URL → $dir"
    git clone "$REPO_URL" "$dir"
fi
cd "$dir"
# Pliki robocze LinuxCNC (zmieniane przy każdym uruchomieniu) nie blokują aktualizacji.
for f in config/*/*/linumert.var config/*/*/linumert.pref config/*/*/linumert.log; do
    git ls-files --error-unmatch "$f" >/dev/null 2>&1 && git update-index --skip-worktree "$f"
done
if [ "$update" = 1 ]; then
    branch=$(git rev-parse --abbrev-ref HEAD)
    if [ "$branch" != main ]; then
        say "gałąź $branch (nie main): bez aktualizacji"
    elif ! git pull --ff-only -q origin main; then
        say "UWAGA: nie udało się zaktualizować (lokalne zmiany albo brak sieci): uruchamiam bieżącą wersję"
    fi
fi
say "wersja: $(git log -1 --format='%h %s' | cut -c1-80)"

# ---- 3. skróty w menu aplikacji -------------------------------------------------------------------
install_desktop() {
    local apps=${XDG_DATA_HOME:-$HOME/.local/share}/applications
    mkdir -p "$apps"
    local name args
    for entry in "linumeRT|" "linumeRT + Plant|--plant"; do
        name=${entry%%|*} args=${entry#*|}
        cat >"$apps/linumert${args:+-plant}.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$name
Comment=Ekran operatora linumeRT na LinuxCNC (symulacja${args:+ z wirtualną obrabiarką Plant})
Exec=$dir/tools/linumert-start.sh $args
Icon=$dir/docs/design/marka/znak.svg
Terminal=true
Categories=Development;Engineering;
EOF
    done
    say "skróty: $apps/linumert.desktop, linumert-plant.desktop (menu aplikacji: linumeRT)"
}
if [ "$desktop" = 1 ]; then install_desktop; exit 0; fi
[ -f "${XDG_DATA_HOME:-$HOME/.local/share}/applications/linumert.desktop" ] || install_desktop

# ---- 4. obraz kontenera Debian 12 + LinuxCNC 2.9 --------------------------------------------------
if [ "$rebuild" = 1 ] || ! podman image exists "$IMG"; then
    say "buduję obraz $IMG (Debian 12, LinuxCNC 2.9 z linuxcnc.org) — pierwszy raz kilka minut"
    podman build -t "$IMG" -f - . <<'CONTAINERFILE'
FROM docker.io/library/debian:bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
 && curl -sfL 'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3CB9FD148F374FEF' \
    | gpg --dearmor -o /usr/share/keyrings/linuxcnc.gpg \
 && gpg --show-keys --with-colons /usr/share/keyrings/linuxcnc.gpg \
    | grep -q '^fpr:::::::::EEDD0D29F81DCAA0D258661F3CB9FD148F374FEF:' \
 && echo 'deb [signed-by=/usr/share/keyrings/linuxcnc.gpg] http://www.linuxcnc.org/ bookworm base 2.9-uspace' \
    > /etc/apt/sources.list.d/linuxcnc.list \
 && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    linuxcnc-uspace linuxcnc-uspace-dev python3-pyqt5 python3-pyqt5.qsci python3-pyqt5.qtsvg \
    python3-pyqt5.qtopengl python3-dbus.mainloop.pyqt5 python3-opengl python3-numpy python3-yaml \
    python3-venv python3-pip build-essential mesa-utils fonts-dejavu xdg-utils python3-pyqtgraph \
 && rm -rf /var/lib/apt/lists/*
# Symulator bez RT jako zwykły użytkownik (keep-id): rtapi_app bez setuid (inaczej shmget EACCES),
# katalog modułów zapisywalny dla halcompile --install komponentów linumeRT (lrt_net, lrt_cia402).
RUN chmod u-s /usr/bin/rtapi_app && chmod 1777 /usr/lib/linuxcnc/modules
# Plant (wirtualna obrabiarka) i panel web: pydantic 2, FastAPI, Uvicorn
RUN python3 -m venv --system-site-packages /opt/linumert \
 && /opt/linumert/bin/pip install -q "pydantic>=2" "fastapi>=0.100" "uvicorn>=0.23" "websockets>=11"
CONTAINERFILE
fi

# ---- 4a. układ detalu symulatora: G54 nad przygotówką (machine.yaml), gdy brak albo zerowy ---------
simcfg=config/sim/linumert_xyz
if ! awk '$1 ~ /^522[123]$/ && $2+0 != 0 {found=1} END {exit !found}' "$simcfg/linumert.var" 2>/dev/null; then
    cp "$simcfg/linumert.var.default" "$simcfg/linumert.var"
    say "układ detalu G54 symulatora: X100 Y100 Z-150 (wierzch przygotówki na stole)"
fi

# ---- 5. okno na pulpicie (X11 / Xwayland) ----------------------------------------------------------
[ -n "${DISPLAY:-}" ] || die "brak DISPLAY: uruchom z sesji graficznej (X11 albo Wayland z Xwayland)"
if command -v xhost >/dev/null; then xhost "+SI:localuser:$(id -un)" >/dev/null 2>&1 || true; fi
X=(-e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:ro -e QT_X11_NO_MITSHM=1)
if [ -n "${XAUTHORITY:-}" ] && [ -f "$XAUTHORITY" ]; then
    X+=(-e XAUTHORITY=/tmp/.Xauthority -v "$XAUTHORITY:/tmp/.Xauthority:ro")
fi
[ -e /dev/dri ] && X+=(--device /dev/dri)
HOME_DIR=${XDG_DATA_HOME:-$HOME/.local/share}/linumert/home  # ustawienia ekranu między uruchomieniami
mkdir -p "$HOME_DIR"
TTY=()
[ -t 0 ] && [ -t 1 ] && TTY=(-t)
RUN=(podman run --rm -i "${TTY[@]}" --userns=keep-id --security-opt label=disable
     -e HOME=/home/lcnc -e XDG_CACHE_HOME=/home/lcnc/.cache -e LINUMERT_SHELL="$((1 - classic))"
     -v "$HOME_DIR:/home/lcnc" -v "$PWD:/work" -w /work "${X[@]}")

if [ "$shell" = 1 ]; then exec "${RUN[@]}" "$IMG" bash; fi

if [ "$mode" = sim ]; then
    say "start: symulator LinuxCNC z ekranem linumeRT (zamknij okno, aby zakończyć)"
    exec "${RUN[@]}" "$IMG" linuxcnc /work/config/sim/linumert_xyz/linumert_xyz.ini
fi

cfg=config/plant/linumert_plant_xyz ini=linumert_plant_xyz.ini yaml=plant.yaml
if [ "$vfd" = 1 ]; then ini=linumert_plant_xyz_vfd.ini yaml=plant_vfd.yaml; fi
say "start: Plant (LRT-NET) + LinuxCNC z ekranem linumeRT; panel Plant: http://127.0.0.1:$PANEL_PORT/"
( sleep 25; command -v xdg-open >/dev/null && xdg-open "http://127.0.0.1:$PANEL_PORT/" >/dev/null 2>&1 ) &
# shellcheck disable=SC2016 # skrypt wykonuje bash w kontenerze; argumenty przez $1…$4
exec "${RUN[@]}" -p "127.0.0.1:$PANEL_PORT:$PANEL_PORT" "$IMG" bash -c '
set -e
cfg=$1 ini=$2 yaml=$3 port=$4
make -s -C plant/core shared >/dev/null
T=$(mktemp -d)
cp hal/lrt_net.comp hal/lrt_net_proto.h hal/lrt_cia402.comp hal/lrt_hardstop_home.comp hal/lrt_estop2.comp "$T"/
(cd "$T" && for c in lrt_net lrt_cia402 lrt_hardstop_home lrt_estop2; do halcompile --install $c.comp >/dev/null; done)
PYTHONPATH=/work/core:/work/plant/server /opt/linumert/bin/python -m linumert_plant serve \
    --plant "$cfg/$yaml" --panel "$port" --panel-listen 0.0.0.0 --state-dir /home/lcnc/plant-state \
    > /home/lcnc/plant.log 2>&1 &
plant=$!
trap "kill $plant 2>/dev/null; wait $plant 2>/dev/null; tail -3 /home/lcnc/plant.log" EXIT
sleep 3
kill -0 $plant 2>/dev/null || { cat /home/lcnc/plant.log; exit 1; }
linuxcnc "/work/$cfg/$ini"' _ "$cfg" "$ini" "$yaml" "$PANEL_PORT"
