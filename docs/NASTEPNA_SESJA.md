# Przekazanie — stan bieżący

Model-Author: Codex · 2026-10-18

## Podział pracy zatwierdzony przez właściciela

Codex: dokończenie PR #3 (LinuxCNC 2.9, Debian 12, CI, VNC) i `nextPROMPT.md`.
Osobny worktree `../linumeRT-codex-003`, gałąź `codex/sesja-003`.
Claude: rdzeń i Plant, otwarte PR #13 (015), #14 (039), #15 (044), #16 (032).
Checkout `linumeRT` na `wip/sesja-032` pozostaje dla Claude. Nie przełączać go.
Właściciel zezwolił teraz na niezależną pracę równoległą; używać osobnych checkoutów
i instancji LinuxCNC. Poprzednie ograniczenie do jednej tury jest zastąpione
w tym zakresie. Nie zmieniać plików roboczych drugiego modelu.

## Stan i bieżące zadania Codexa

Main zawiera sesje 001, 002, 006, 007, 009–014 (scalenie Claude d53aa04).
PR #3 nadal otwarty. Wyniki Ubuntu: 47 testów bazowych + 2 integracyjne,
pełny build 50 s; log w state/test-runs/20261018T060319.515034Z-Codex/report.json.
CI po ponowieniu zielone, ale wystąpił niestabilny segfault QtDragon przy
zamykaniu. Nie usuwać asercji wykrywającej awarię.

Przed scaleniem #3:
1. Zintegrować main z zachowaniem wpisów obu modeli i make test-c w CI.
2. Wykonać wymaganie Debian 12 z komentarza Claude w PR #3: dedykowana
   dystrybucja WSL, setup-debian12-wsl.ps1, guard builda (obejście tylko jawne),
   job CI w debian:bookworm, Python 3.11, venv --system-site-packages, D27.
3. Pełna budowa i runner w Debian 12, testy w VNC, powtórzenie zamykania GUI;
   raport, autokontrola/przegląd aktualnego SHA, zielone kontrole, merge.
4. Dopiero po spełnieniu kryteriów wpis 003 do DONE i zwolnienie własnej blokady.

## Kolejne zadania (nie są wykonywane równolegle z domknięciem 003)

- Codex: 004 (własna konfiguracja sim XYZ i HAL), 005 (kopia QtDragon), potem 008.
- Przegląd wsteczny d53aa04: machine.c (forward, NC/NO, E-4207, E-STOP),
  PRESET_CHAINS (znaki trunnion), 7 szablonów, model krokowca, mapowanie awarii,
  lrt_drive_set_live i live.c; make test shared i ASan/UBSan. Usterki jako issue/PR.
- Sesja 018: znaki A/B/C wobec xyzac-trt-kins i xyzbc-trt-kins.
- Czytnik stanu z 006: sprawdzić prawdziwy RIP (gcodes/mcodes, axis, limit, spindle).
- Claude: kontynuacja swoich PR; sprawdzić ich aktualny stan przed wyborem pracy.

## Środowisko i instrukcje

Repo Windows: `C:/Users/pc/Documents/PythonProjects/linumeRT/.collaboration/linumeRT`.
Repo Codexa: sąsiedni `linumeRT-codex-003`. Katalog nadrzędny to stara kopia.
Dotychczasowy Ubuntu RIP: /home/pc/.cache/linuxcnc-2.9, SHA
a33293f46575c809e082e0806e79ab996f982513. Nie modyfikować kodu upstream.
VNC poprzedniej sesji: localhost:5911, DISPLAY=:11,
XAUTHORITY=/tmp/linumert-vnc.rSYjwuGM/Xauthority — sprawdzić proces przed użyciem.
Nie zabijać obcych sesji. tools/agent_tests jest wspólną paczką.
Budowa: bash tools/ci/build-linuxcnc.sh; zależności: --install-deps.
Testy: .venv/bin/python tools/agent_tests/run.py --model Codex --linuxcnc.
API poll wymaga gotowej pamięci narzędzi; fixture sprawdza gotowość osobnym procesem.
Tymczasowe shutdown_check=False wyłącza dialog potwierdzenia w teście.
W przykładzie upstream są ostrzeżenia opcjonalnego PDF/NGCGUI/PROGRAM_PREFIX;
uporządkować ścieżki w 004. Plant jest już obecny na main.

WSL2 nie jest PREEMPT_RT. NIEZWERYFIKOWANE NA SPRZĘCIE; pomiary RT wymagają
VM lub sprzętu z właściwym jądrem. Historia poprzednich przekazań jest w Git:
f0227f3 (Codex) oraz adcc7bb (Claude). Wyniki i pochodzenie są też w DZIENNIK,
PROVENANCE i docs/raporty/SPIKE_LINUXCNC.md; przy scaleniu zachowano oba zestawy.
