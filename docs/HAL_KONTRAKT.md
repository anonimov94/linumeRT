# Kontrakt sygnałów HAL linumeRT (D05)

Model-Author: Claude · sesja 004 · 2026-10-18

Ekran, logika linumeRT i testy korzystają wyłącznie z sygnałów `linumert.*`. Każdy wariant
maszyny (symulator, Plant przez `lrt_net`, step/dir, EtherCAT) dostarcza te same sygnały; zmiana
napędów = zmiana tylko bloku „napędy” w pliku HAL. Wzorzec: `config/sim/linumert_xyz/`.

`N` = numer osi (joint) LinuxCNC, od 0. Kierunek: **→ LinuxCNC** = sygnał wchodzi do LinuxCNC,
**← LinuxCNC** = wychodzi z LinuxCNC do napędów i I/O.

## Osie

| Sygnał | Typ | Kierunek | Pin LinuxCNC | Znaczenie |
|---|---|---|---|---|
| `linumert.jN.pos-cmd` | float | ← | `joint.N.motor-pos-cmd` | pozycja zadana napędu [mm, °] |
| `linumert.jN.pos-fb` | float | → | `joint.N.motor-pos-fb` | pozycja rzeczywista z napędu |
| `linumert.jN.enable` | bit | ← | `joint.N.amp-enable-out` | zezwolenie na pracę napędu |
| `linumert.jN.fault` | bit | → | `joint.N.amp-fault-in` | awaria napędu (1 = awaria) |
| `linumert.jN.home-sw` | bit | → | `joint.N.home-sw-in` | czujnik bazy (stan logiczny, NC już odwrócone) |

## Wrzeciono (spindle 0)

| Sygnał | Typ | Kierunek | Pin LinuxCNC | Znaczenie |
|---|---|---|---|---|
| `linumert.spindle.on` | bit | ← | `spindle.0.on` | wrzeciono włączone |
| `linumert.spindle.cw` / `.ccw` | bit | ← | `spindle.0.forward` / `.reverse` | kierunek |
| `linumert.spindle.speed-cmd` | float | ← | `spindle.0.speed-out-rps` | prędkość zadana [obr/s] |
| `linumert.spindle.speed-fb` | float | → | `spindle.0.speed-in` | prędkość rzeczywista [obr/s] |
| `linumert.spindle.revs` | float | → | `spindle.0.revs` | pozycja wrzeciona [obr] (gwintowanie, posuw na obrót) |
| `linumert.spindle.index` | bit (io) | ↔ | `spindle.0.index-enable` | impuls indeksu wrzeciona |
| `linumert.spindle.at-speed` | bit | → | `spindle.0.at-speed` | prędkość osiągnięta |
| `linumert.spindle.inhibit` | bit | → | `spindle.0.inhibit` | blokada (ekran: pauza z podniesieniem Z) |

## Wejścia i wyjścia

| Sygnał | Typ | Kierunek | Pin LinuxCNC | Znaczenie |
|---|---|---|---|---|
| `linumert.io.estop-ok` | bit | → | `iocontrol.0.emc-enable-in` | obwód E-STOP zamknięty. Na maszynie wyłącznie z obwodu sprzętowego (CLAUDE.md §6); w symulatorze pętla z `user-enable-out` |
| `linumert.io.tool-prepare` | bit | ← | `iocontrol.0.tool-prepare` | przygotowanie narzędzia (sim: pętla do `tool-prepared`) |
| `linumert.io.tool-change` | bit | ← | `iocontrol.0.tool-change` | żądanie zmiany narzędzia |
| `linumert.io.tool-changed` | bit | → | `iocontrol.0.tool-changed` | zmiana potwierdzona (ręcznie: okno ekranu) |
| `linumert.io.tool-number` | s32 | ← | `iocontrol.0.tool-prep-number` | numer narzędzia |
| `linumert.io.coolant-flood` / `-mist` | bit | ← | `iocontrol.0.coolant-flood` / `-mist` | chłodzenie |

## Ekran (QtDragon, po starcie GUI)

| Sygnał | Pin | Znaczenie |
|---|---|---|
| `linumert.z.eoffset`, `.eoffset-counts`, `.eoffset-clear` | `axis.z.eoffset*` ↔ `qtdragon.eoffset-*` | podniesienie Z przy pauzie (offset zewnętrzny) |

## Zasady
- Nowy sygnał = wiersz w tej tabeli i w teście `tests/test_sim_config.py` (lista `CONTRACT`).
- Stan styku NC odwraca warstwa napędu/I/O; w kontrakcie `1` zawsze znaczy „aktywny”.
- NIEZWERYFIKOWANE NA SPRZĘCIE: warianty step/dir i EtherCAT powstaną w osobnych sesjach.
