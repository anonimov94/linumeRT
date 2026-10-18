# Prompt startowy: następna sesja (naprawa 4 testów LinuxCNC, potem sesja 008)

Model-Author: Claude · 2026-10-18. Wklej na początku nowej sesji:

> Przeczytaj `prompts/START-008.md` w ~/Projekty/linumeRT-claude (gałąź `main`) i wykonaj go.

## Start
1. `cd ~/Projekty/linumeRT-claude && git pull` (jedyna gałąź: `main`; brak otwartych PR).
2. Lektura według `docs/PROMPT_NOWEJ_SESJI.md` §1 (CLAUDE.md, WSPOLPRACA_MODELI, NASTEPNA_SESJA, DECYZJE, DZIENNIK).
3. Zajmij turę: `prompts/LOCK`, linia `Tura:` w `docs/NASTEPNA_SESJA.md`; `python tools/lock.py acquire linuxcnc --model Claude`.
4. Pracuj na gałęzi `wip/sesja-NNN`, PR do `main`; scalanie dozwolone (reguła w `~/.claude/settings.json`).

## Krok 0: 4 testy LinuxCNC (zrobić najpierw)
Pełny przebieg w jednym kontenerze RIP daje 55 OK i 4 błędy:
`tests/test_plant_vfd_linuxcnc.py` (3) i `tests/test_sim_config.py::test_headless_run_20s`.
Uruchamiane osobno przechodziły. Podejrzenie: po `tests/test_plant_linuxcnc.py` zostaje `linuxcncsvr`
(i okno `show_errors.tcl` przy kolejnym starcie), więc następny LinuxCNC nie wstaje. Polecenie testu:
```
podman run --rm -i --userns=keep-id --security-opt label=disable -e HOME=/home/rip \
 -v ~/.cache/linumert/rip-home:/home/rip -v "$PWD:/work" -w /work linumert-rip:bookworm bash -c \
 'source /home/rip/.cache/linuxcnc-2.9/scripts/rip-environment >/dev/null; export LINUXCNC_DIR=/home/rip/.cache/linuxcnc-2.9;
  make -s -C plant/core shared; xvfb-run -a /home/rip/venv/bin/python -m pytest -q -o addopts= -m linuxcnc'
```
Naprawa: wspólne sprzątanie po teście LinuxCNC (np. w `tests/rip_support.py`: `linuxcnc` zakończone,
`halrun -U`, zabicie pozostałych `linuxcncsvr`/`milltask`/`rtapi_app`), użyte we wszystkich testach z
markerem `linuxcnc`. Kryterium: cały przebieg zielony (59/59), dwa razy pod rząd.

## Potem: sesja 008 (`prompts/sesja-008.md`, bufor i bramka G0)
Dalej kolejka z `docs/NASTEPNA_SESJA.md` §3: 022, 023, 024. HMI (D32, `docs/design/HMI_WORKFLOW.md`) prowadzi Codex.

## Zamknięcie
Według `docs/PROMPT_NOWEJ_SESJI.md` §3; ten plik przenieś do `prompts/archiwum/`.
