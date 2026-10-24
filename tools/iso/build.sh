#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# linumeRT · obraz live USB / ISO: Debian 12 + jądro PREEMPT_RT + LinuxCNC 2.9 + linumeRT.
# Tryb live (próba bez instalacji: symulator i Plant) + instalator na dysk (Calamares).
# Uruchamiać jako root w debian:bookworm z --privileged (GitHub Actions: .github/workflows/iso.yml):
#   docker run --rm --privileged -v "$PWD:/work" debian:bookworm bash /work/tools/iso/build.sh
# Wynik: /work/build/iso/linumert-<wersja>-amd64.iso + .sha256. Model-Author: Claude · 2026-10-19.
# NIEZWERYFIKOWANE NA SPRZĘCIE (przed pracą na maszynie: test latencji, docs/HMI_SYMULACJA.md).
set -euo pipefail
SRC=/work
OUT=$SRC/build/iso
VERSION=${LINUMERT_VERSION:-$(git -C "$SRC" describe --tags --always 2>/dev/null || echo dev)}
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq live-build curl gnupg git ca-certificates \
    >/dev/null
W=$(mktemp -d)
cd "$W"
lb config --distribution bookworm --archive-areas "main contrib non-free non-free-firmware" \
    --linux-flavours rt-amd64 --debian-installer none --binary-images iso-hybrid \
    --bootloaders "syslinux,grub-efi" --memtest none --apt-recommends false \
    --iso-application linumeRT --iso-publisher "linumeRT (GPL-2.0)" --iso-volume "linumeRT" \
    --bootappend-live "boot=live components quiet splash locales=pl_PL.UTF-8 keyboard-layouts=pl username=linumert hostname=linumert" \
    >/dev/null
cp -r "$SRC/tools/iso/config/." config/
mkdir -p config/archives
# Repozytorium LinuxCNC 2.9 (jak tools/linumert-start.sh: klucz ze sprawdzeniem odcisku)
curl -sfL 'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3CB9FD148F374FEF' \
    | gpg --dearmor > config/archives/linuxcnc.key.chroot
gpg --show-keys --with-colons config/archives/linuxcnc.key.chroot \
    | grep -q '^fpr:::::::::EEDD0D29F81DCAA0D258661F3CB9FD148F374FEF:'
cp config/archives/linuxcnc.key.chroot config/archives/linuxcnc.key.binary
echo 'deb http://www.linuxcnc.org/ bookworm base 2.9-uspace' > config/archives/linuxcnc.list.chroot
cp config/archives/linuxcnc.list.chroot config/archives/linuxcnc.list.binary
# Repo zamontowane z hosta ma innego właściciela niż root w kontenerze (git: dubious ownership).
git config --global --add safe.directory "$SRC"
# Kod linumeRT (bez historii git i katalogów roboczych) do /opt/linumeRT
mkdir -p config/includes.chroot/opt/linumeRT
git -C "$SRC" archive HEAD | tar -x -C config/includes.chroot/opt/linumeRT
echo "$VERSION" > config/includes.chroot/opt/linumeRT/VERSION
# Pełny dziennik lb w build/lb-build.log (poza build/iso, które idzie do wydania); na konsoli koniec, przy błędzie dłuższy.
mkdir -p "$OUT"
if ! lb build > "$SRC/build/lb-build.log" 2>&1; then
    tail -n 200 "$SRC/build/lb-build.log"
    exit 1
fi
tail -n 40 "$SRC/build/lb-build.log"
ISO="$OUT/linumert-$VERSION-amd64.iso"
mv live-image-amd64.hybrid.iso "$ISO"
(cd "$OUT" && sha256sum "$(basename "$ISO")" > "$(basename "$ISO").sha256")
ls -lh "$OUT"
