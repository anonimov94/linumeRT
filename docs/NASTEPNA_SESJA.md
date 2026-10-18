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
Tura: Claude · od 2026-10-18T10:55Z · stan: oddana (sesja 016 → PR #17; #13–#17 czekają na przegląd Codexa)

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
## Stan main — 2026-10-18 (Model-Author: Claude)

W `main` są sesje 001, 002, 006, 007, 009, 010, 011, 012, 013, 014 (PR #1, #2, #4–#12).
#6–#12 scalił Claude w `d53aa04` jako **autokontrolę, bez niezależnego przeglądu** (Codex był
niedostępny; D26 wariant b). Kontrole na stanie scalonym (WSL Ubuntu 24.04): ruff czysty,
pytest 248 OK bez pominięć (test tablicy awarii z katalogiem alarmów już nie jest pomijany),
`make test-c` OK (osie, napęd, maszyna). Konflikty były tylko w plikach dziennikowych.
Gałęzie `wip/sesja-007…014` są w main — można je usunąć po przeglądzie wstecznym.

Otwarty jest tylko **#3 (sesja 003, Codex)**. Sesje 004, 005 i 008 nie są rozpoczęte.

## Zlecenia dla Codexa (kolejność)

1. **#3 — czerwony krok CI `LinuxCNC RIP smoke`.** Przyczyna (log runu 39102795987): oba testy
   przechodzą, błąd jest w *teardown* `test_qtdragon_screen` — proces QtDragon kończy się
   `Segmentation fault (core dumped)` po `WM_DELETE_WINDOW`, a fixture zabrania segfaultu w logu.
   Lokalnie (WSL Ubuntu 24.04, Xvfb) Claude nie odtworzył błędu: 7/7 przebiegów zielonych, więc to
   niestabilne zamykanie ekranu na runnerze. Ponowny run joba na GitHubie przeszedł (success) — crash jest niestabilny; diagnoza w komentarzu w #3.
   Najpierw `git merge origin/main` do `codex/sesja-003` (konflikty: DZIENNIK/DECYZJE/DONE —
   zostaw wszystkie wpisy; `ci.yml` — zachowaj `make test-c`).
2. **#3 — Debian 12** według specyfikacji w komentarzu do #3 z 06:30Z (dystrybucja WSL Debian 12,
   guard w `build-linuxcnc.sh`, job CI w `container: debian:bookworm`, D27). To jest nadal
   wymaganie właściciela przed scaleniem #3.
3. **Przegląd wsteczny `d53aa04`** (sesje 007–014, kod Claude): uwagi z dawnych sekcji zleceń —
   `machine.c` (kinematyka `forward`, styki NC/NO, E-4207, E-STOP), presety `PRESET_CHAINS`
   w `build_machine.py` (znaki osi trunnion), wartości 7 szablonów napędów, model krokowca
   i mapowanie awarii w `drive.c`, `lrt_drive_set_live` i `live.c`. W WSL Debian 12:
   `make -C plant/core test shared` oraz ASan/UBSan na `axis.c`/`drive.c`/`machine.c`.
   Usterki zgłaszaj jako issue albo PR poprawkowy (model + SHA).
4. **Po scaleniu #3:** sesja 004 (konfiguracja sim 3 osie z QtDragon) i 005 (kopia ekranu
   QtDragon) — obszar Codexa (LinuxCNC, INI/HAL). 008 (bramka G0) dopiero po 003–005.
5. **Sesja 018** (z LinuxCNC): porównaj znaki A/B/C presetów trunnion z `xyzac-trt-kins` /
   `xyzbc-trt-kins` (`PlantMachine.tool_tip(workpiece=True)` vs układ detalu w LinuxCNC).

Następna sesja Claude: 016 (`prompts/START-016.md`, serwer LRT-NET).

## Zlecenia po sesji 015 (Model-Author: Claude → Codex)

1. **Przegląd PR sesji 015** (`wip/sesja-015`, SHA w opisie PR; zbudowany na `main` z #6–#12).
   Przejrzyj niezależnie: `drive.c` — `establish_offset`, `homing_update` (fazy, zbocza, ramka
   po `homing_set_home`), krokowiec (`pos_offset` przy włączeniu), E-4211; `machine.c` —
   `drive_inputs`, `switch.S.drive`, start losowy; `homing_master.py` (zgodność z homemod).
2. **W WSL Debian 12** (po #3): `make -C plant/core test`, ASan/UBSan na `drive.c`/`machine.c`,
   `pytest tests/test_homing.py` oraz `pytest -o addopts= -m linuxcnc tests/test_hal_comps.py`
   (kopiuje moduł do `rtlib` RIP na czas testu i usuwa). Wynik komentarzem w PR (model + SHA).
3. **CI `linuxcnc`:** dołącz `tests/test_hal_comps.py` do joba LinuxCNC (marker już jest).
4. **Sesja 018:** scenariusze `home_switch`, `home_switch_index`, `home_hardstop`, `home_absolute`,
   `home_drive_internal`, `home_gantry_square` z prawdziwym homemod; INI według
   `hal/README.md` i wpisu sesji 015 w `docs/DECYZJE.md` (HOME_ABSOLUTE_ENCODER 1/2).

## Dla Codex: (2026-10-18, Claude po sesji 016)
0. **Przegląd i scalenie PR Claude** w kolejności #13 → #17 (#17 jest na gałęzi #13), potem #14, #15,
   #16 (niezależne od siebie). Każdy: CI zielone, autor Claude; komentarz z modelem, SHA i wynikiem,
   potem merge commit albo lista usterek. Konflikty tylko w DZIENNIK/DECYZJE/DONE/PROMPT_NOWEJ_SESJI —
   zostaw wszystkie wpisy, DONE posortuj.
   - #17 lokalnie: `make test-c`, `pytest tests/test_lrtnet.py tests/test_plant_server.py`, potem ręcznie:
     `python -m linumert_plant serve config/machines/mill_servo_table.yaml --lockstep` i w drugim terminalu
     `python plant/server/test_master.py --axes 4 --distance 50000` (oczekiwane: utracone 0, spóźnione 0).
   - Proszę o próbę `--realtime` z masterem na drugim hoście/VM (jitter, watchdog) — wynik w „Dla Claude:”.

Następna sesja Claude: 017 (`prompts/START-017.md`, komponent HAL lrt_net) — od `wip/sesja-016`.
