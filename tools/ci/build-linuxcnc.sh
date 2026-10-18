#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Codex
set -euo pipefail

source /etc/os-release
if [[ $ID != debian || $VERSION_ID != 12 ]]; then
    if [[ ${LINUMERT_ALLOW_NON_DEBIAN:-0} != 1 ]]; then
        echo 'Debian 12 required; explicit exploratory override: LINUMERT_ALLOW_NON_DEBIAN=1' >&2
        exit 2
    fi
    echo "Exploratory non-target build: $ID $VERSION_ID" >&2
fi

# RIP/uspace only. Dependencies derived from upstream debian/configure no-docs
# and debian/control (2.9, a33293f46575c809e082e0806e79ab996f982513).
packages=(ca-certificates python3-venv git build-essential autoconf automake libtool pkg-config gettext intltool
    asciidoc-base xsltproc docbook-xsl docbook-xml libxml2-utils groff-base
    libudev-dev libboost-python-dev libepoxy-dev libgl-dev libglu1-mesa-dev
    libgtk2.0-dev libgtk-3-dev libmodbus-dev libgpiod-dev libeditreadline-dev
    libtirpc-dev libusb-1.0-0-dev libxmu-dev python3-dev python3-tk python3-xlib
    tcl8.6-dev tk8.6-dev tclx bwidget yapps2 python3-yapps python3-serial
    python3-pyqt5 python3-pyqt5.qsci python3-pyqt5.qtsvg python3-pyqt5.qtopengl
    python3-pyqt5.qtwebengine python3-opengl python3-numpy python3-qtpy
    python3-pil python3-pil.imagetk python3-dbus python3-dbus.mainloop.pyqt5
    python3-gi python3-cairo python3-gi-cairo python3-gst-1.0 python3-espeak
    python3-opencv espeak espeak-ng gstreamer1.0-tools gstreamer1.0-plugins-base
    pyqt5-dev-tools sound-theme-freedesktop xvfb xauth imagemagick
    netcat-openbsd netpbm procps psmisc desktop-file-utils)
if [[ ${1:-} == --install-deps ]]; then
    export PATH="/usr/sbin:/sbin:$PATH"
    if (( EUID == 0 )); then admin=(); else admin=(sudo); fi
    "${admin[@]}" apt-get update
    "${admin[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${packages[@]}"
    exit
fi
if (( EUID == 0 )); then echo 'Build as an ordinary user.' >&2; exit 2; fi
target=${LINUXCNC_DIR:-$HOME/.cache/linuxcnc-2.9}
if [[ ! -d $target ]]; then
    git clone --depth 1 --branch 2.9 https://github.com/LinuxCNC/linuxcnc.git "$target"
fi
cd "$target"
revision=$(git rev-parse HEAD)
signature="$revision $ID $VERSION_ID $(uname -m) $(python3 --version)"
if [[ -f .linumert-built && $(cat .linumert-built) == "$signature" && -x bin/linuxcnc ]]; then
    echo "Reusing LinuxCNC $revision in $target"
    exit
fi
start=$SECONDS
cd src
./autogen.sh
./configure --with-realtime=uspace --disable-check-runtime-deps
make -j"${LINUXCNC_JOBS:-$(nproc)}"
cd ..
printf '%s\n' "$signature" > .linumert-built
printf 'revision=%s\nbuild_seconds=%s\n' "$revision" "$((SECONDS-start))" | tee .linumert-build-info
