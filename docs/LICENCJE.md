# Licencje zależności

Własny kod linumeRT: **GPL-2.0-or-later** (patrz `LICENSE`). Całość z kodem QtDragon/LinuxCNC jest
rozpowszechniana na **GPL-2.0**. Każda nowa zależność lub zasób wymaga wpisu tutaj (zasoby graficzne i
kod z innych projektów także w `PROVENANCE.md`).

Licencja z katalogu nadrzędnego (`PythonProjects/LICENSE`, „Paid Reuse Source-Available”) **nie dotyczy**
tego projektu (D14).

## Zależności Pythona (stan: sesja 001)

| Zależność | Rola | Licencja | Zgodność z GPL-2.0 | Wprowadzona |
|---|---|---|---|---|
| numpy | obliczenia numeryczne (rdzeń, symulacja) | BSD-3-Clause | tak | sesja 001 |
| PyYAML (`pyyaml`) | `machine.yaml`, katalog alarmów, tokeny | MIT | tak | sesja 001 |
| pydantic | schemat i walidacja `machine.yaml` (wymagane v2) | MIT | tak | sesja 010 |
| pytest (dev) | testy | MIT | tak (tylko narzędzie dev) | sesja 001 |
| ruff (dev) | lint | MIT | tak (tylko narzędzie dev) | sesja 001 |

## Zależności planowane (jeszcze nie dodane)

| Zależność | Rola | Licencja | Sesja |
|---|---|---|---|
| LinuxCNC 2.9 | interpreter i planer ruchu | GPL-2.0-or-later | 003 |
| QtDragon / QtVCP | baza ekranu (kopia w `screens/linumert/`) | GPL-2.0-or-later | 005 |
| PyQt5 (przez `qtpy`) | GUI | GPL-3.0 / komercyjna (Riverbank) | 005 — do potwierdzenia zgodności przy dystrybucji |
| pyqtgraph | widok 3D symulacji | MIT | 057 |
| FastAPI, uPlot | panel web Plant | MIT / MIT | 022 |
| IgH EtherCAT Master, linuxcnc-ethercat | EtherCAT | GPL-2.0 | 063 |

Zgodność PyQt5 (GPL-3.0) z dystrybucją na GPL-2.0 jest do sprawdzenia w sesji 005 i 080; do tego czasu
wpis ma status „do potwierdzenia”.

## Narzędzia lokalnego pulpitu testowego (bez dołączania binariów)

Model-Author: Codex. Skrypty używają zainstalowanych w Ubuntu TigerVNC, XFCE, X11, D-Bus i util-linux. Nie kopiujemy ich kodu ani binariów do repozytorium. Właściwe licencje pakietów znajdują się w `/usr/share/doc/<pakiet>/copyright`; przy ewentualnej dystrybucji obrazu wymagany osobny przegląd. Runner używa stdlib Pythona oraz istniejących zależności dev: pytest i ruff.

## Środowisko budowy LinuxCNC — sesja 003

Model-Author: Codex. LinuxCNC 2.9 jest pobierany do cache z oficjalnego repozytorium (GPL-2.0-or-later); nie dołączamy binariów ani źródeł do tego repo. Pełna lista pakietów budowy, GUI i testów jest w tools/ci/build-linuxcnc.sh, wyprowadzona z upstream debian/configure i debian/control. Obejmuje toolchain GNU, biblioteki systemowe, Tcl/Tk, Python, Qt/PyQt5/QtPy, Xvfb, ImageMagick i narzędzia AsciiDoc/DocBook. Licencje konkretnych wersji pakietów: /usr/share/doc/<pakiet>/copyright. Są to zależności środowiska deweloperskiego; przegląd licencji obrazu dystrybucyjnego pozostaje do sesji 080.


Środowisko Debian 12: bootstrap przez systemowy debootstrap i debian-archive-keyring, podpisy oficjalnego repo Debian sprawdzane przed eksportem rootfs. To lokalne narzędzia środowiska, bez dołączania kodu lub obrazu do Git; licencje konkretnych pakietów w /usr/share/doc/<pakiet>/copyright. Instalacja VNC: TigerVNC, XFCE, D-Bus i X11 jak w poprzednim pulpicie testowym.
