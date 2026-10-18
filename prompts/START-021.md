# Prompt startowy: sesja 021 (wrzeciono VFD w Plant) — kontynuacja

Model-Author: Claude · 2026-10-18. Wklej na początku nowej sesji Claude (laptop właściciela,
EndeavourOS, podman). D31: Claude prowadzi cały zakres (także dawny obszar Codexa).

## Start
1. `cd ~/Projekty/linumeRT-claude && git fetch origin && git checkout wip/sesja-021`
2. Czytaj oszczędnie: CLAUDE.md, docs/WSPOLPRACA_MODELI.md, docs/NASTEPNA_SESJA.md
   („Stan zatrzymania”, ostatnie linie), prompts/sesja-021.md, ostatnie 3 wpisy docs/DZIENNIK.md.
3. `prompts/LOCK` = `Claude · sesja 021 · <UTC> · <opis>`; `python tools/lock.py acquire linuxcnc
   --model Claude --note "..."` przed LinuxCNC; linia `Tura:` = w toku.
4. Opcjonalnie autozapis co 10 min: `tools/dev/autozapis.sh` w tle (tylko gałęzie wip/* i claude/*).

## Środowisko (gotowe na laptopie)
- Testy Debian 12: `tools/dev/debian-container.sh make lint test test-c test-san` (podman).
- LinuxCNC RIP 2.9 (budowa ze źródeł): obraz `linumert-rip:bookworm`, RIP w
  `~/.cache/linumert/rip-home`; polecenia w RIP: zob. docs/PLANT_START.md. Testy z LinuxCNC:
  `podman run --rm -i --userns=keep-id --security-opt label=disable -e HOME=/home/rip
   -v ~/.cache/linumert/rip-home:/home/rip -v "$PWD:/work" -w /work linumert-rip:bookworm bash -c
   'source /home/rip/.cache/linuxcnc-2.9/scripts/rip-environment; make -s -C plant/core shared;
    /home/rip/venv/bin/python -m pytest -o addopts= -m linuxcnc tests/test_plant_linuxcnc.py tests/test_hal_lrt_net.py'`
- GUI na pulpicie: `tools/dev/plant-gui.sh` (LinuxCNC + Plant + ekran linumert),
  `tools/dev/linuxcnc-gui.sh` (pakiety linuxcnc.org). W RIP są `hy_vfd` i `mb2hal`.

## Stan sesji 021 (przerwana na prośbę właściciela)
- Zrobione: `plant/server/linumert_plant/vfd.py` — `SpindleModel` (bezwładność/krzywa/tarcie
  z szablonu napędu, rampa z machine.yaml `spindle.ramp_*`, obciążenie, I²t → FAULT_OVERLOAD,
  at-speed 2 %), `HyVfdProtocol` (ramki hy_vfd 0x01–0x05, CRC Modbus, PD004/005/011/141–144,
  statusy SetF/OutF/OutA/RoTT), `ModbusMap` + `ModbusTcpServer` (funkcje 3/4/6/16, mapa
  `DEFAULT_MODBUS_MAP`), `HyVfdPty` (os.openpty + dowiązanie dla `hy_vfd -d`), `VfdFaults`.
  Lint czysty; **brak testów i brak integracji**.
- Do zrobienia (kolejno, commit po każdym kroku):
  1. Testy jednostkowe `tests/test_vfd.py` (bez LinuxCNC): CRC (znane wektory Modbus), odpowiedzi
     ramek hy_vfd (długości 8/6/8/7 jak w hy_comm.c compute_response_length), rampa 0→max w
     `ramp_up_s`, at-speed, kierunek wstecz, przeciążenie (load_torque 2 N·m → FAULT po I²t),
     błąd falownika = wybieg, Modbus PDU 3/6/16 i wyjątki.
  2. Integracja w `server.py`: `PlantConfig.vfd` (plant.yaml `vfd: {device, modbus_listen,
     modbus_port, slave, modbus_map}`), `self.spindle` (szablon z `resolve_machine_drives` +
     `load_library`), krok w `_step_discrete`, `spindle_actual` w odpowiedzi LRT-NET; serwery
     pty/TCP uruchamiane w `serve.py` (zamykane w finally); wstrzykiwanie: `comm_lost`,
     `spindle.fault = FAULT_DRIVE`, `load_torque`.
  3. Konfiguracja LinuxCNC `config/plant/linumert_plant_xyz` wariant `_vfd` (INI + HAL z
     `loadusr -Wn vfd hy_vfd -n vfd -d <pty> -S 1 ...`, sygnały `linumert.spindle.*` zamiast
     sim_spindle); test z markerem linuxcnc: M3 S6000 → at-speed, M5 → 0, z prawdziwym hy_vfd.
  4. LICENCJE.md (biblioteka Modbus: własna, bez zależności), PROVENANCE, DECYZJE (sesja 021),
     MACIERZ (REQ-VD-01 wrzeciono), DZIENNIK, DONE, PR do `wip/sesja-020`.

## Kolejka po 021
008 (bramka G0), 022 (panel Plant i pulpit MPG), 023 (edytor maszyny), 024 (scenariusze i raport,
`tools/check_requirements.py`), dalej prompts/sesja-0NN.md w kolejności. Ramka LRT-NET v2
(indeks enkodera, 6072h) — PROPOZYCJA w DECYZJE sesja 017.

## Otwarte PR (scalanie: właściciel; klasyfikator blokuje scalanie własnych PR przez Claude)
Stos: #18, #19→#20→#21→#22→#23→#24→#25 (004/005), #26 (003, zastępuje #3 Codexa, CI zielone),
#27 (017) → #28 (018) → #29 (019) → #30 (020). Gałąź wip/sesja-021 bez PR (draft po kroku 1).

## Zasady
CLAUDE.md wygrywa. Model-Author: Claude. Autokontrola ≠ niezależny przegląd. Małe kroki, commit
i push po każdym. RT: bez alokacji i blokującego I/O. Oszczędzaj tokeny (bez całych plików i logów).
Na końcu: DZIENNIK, DONE, „Stan zatrzymania” i `Tura:` w NASTEPNA_SESJA.md, zwolnij LOCK i blokadę.
