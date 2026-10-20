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

Wariant z falownikiem (`spindle_vfd.hal`, hy_vfd): `linumert.spindle.rpm-cmd` (`spindle.0.speed-out-abs`
→ `vfd.speed-command`, obr/min), `linumert.spindle.rpm-fb` (`vfd.spindle-speed-fb`, obr/min, przeliczane na
obr/s do `speed-in`), `linumert.spindle.enable` (`motion.motion-enabled` → `vfd.enable`), `linumert.spindle.vfd-ok`
(`vfd.hycomm-ok`). Bez `revs` i `index` (hy_vfd nie ma enkodera wrzeciona).

## Wejścia i wyjścia

| Sygnał | Typ | Kierunek | Pin LinuxCNC | Znaczenie |
|---|---|---|---|---|
| `linumert.io.estop-ok` | bit | → | `iocontrol.0.emc-enable-in` | zezwolenie z zatrzasku `estop_latch` (reset: `linumert.io.estop-reset` = `iocontrol.0.user-request-enable`). Wejście zatrzasku = łańcuch AND: obwód sprzętowy maszyny (Plant: `din-00` i łącze LRT-NET) ∧ `linumert.hmi.estop-ok` (D35, CLAUDE.md §6); w symulatorze tylko grzyb HMI |
| `linumert.io.estop-button` | bit | ← | `lrt-net.0.din-00` → `lrt-estop2.0.ch-a` | kanał A E-STOP (NC, 1 = zamknięty) |
| `linumert.io.estop-b` | bit | ← | `lrt-net.0.din-15` → `lrt-estop2.0.ch-b` | kanał B E-STOP (NC, druga linia przewodów tego samego grzyba) |
| `linumert.io.estop-2ch` | bit | → | `estop_chain.in0` | oba kanały zamknięte i brak błędu rozbieżności (`hal/lrt_estop2.comp`) |
| `linumert.io.estop-fault` | bit | → | (ekran, diagnostyka) | rozbieżność kanałów > `discrepancy-time` (0,1 s), zatrzask; kasuje test obwodu (oba otwarte → oba zamknięte) + Reset |
| `linumert.hmi.estop-ok` | bit | → łańcuch | `lrt_hmi_bypass.out` | grzyb HMI zwolniony ∧ HMI żyje ∧ E-STOP potwierdzony w HMI po ostatnim zdarzeniu (`config/hal/linumert_hmi_estop.hal`); 0 przed startem ekranu |
| `linumert.hmi.ack` | bit | ← ekran | `linumert.hmi-ack` → `lrt_ack_edge.in` | impuls potwierdzenia (zwolnienie grzyba; w `--classic` żądanie resetu z ekranu); zbocze narastające ustawia zatrzask `lrt_hmi_ack` |
| `linumert.io.user-enable`, `linumert.hmi.estop-event`, `linumert.hmi.acked` | bit | wewn. | `iocontrol.0.user-enable-out` → `lrt_estop_edge` → `lrt_hmi_ack.reset`, `lrt_hmi_ack.out` | każde wejście LinuxCNC w E-STOP (zbocze opadające) kasuje potwierdzenie HMI — reset inną drogą nie zamknie łańcucha (przegląd Codexa P1) |
| `linumert.hmi.button` | bit | ← ekran | `linumert.hmi-estop-ok` | grzyb E-STOP w HMI: 1 = zwolniony (postgui) |
| `linumert.hmi.heartbeat` | bit | ← ekran | `linumert.hmi-heartbeat` → `watchdog.input-0` | sygnał życia ekranu (przełączany co 100 ms; limit `[LINUMERT]HMI_HEARTBEAT_TIMEOUT`) |
| `linumert.hmi.wd-enable` | bit | ← ekran | `linumert.hmi-wd-enable` → `watchdog.enable-in` | uzbrojenie watchdoga (zbocze przy starcie i przy potwierdzeniu grzybem) |
| `linumert.hmi.alive`, `linumert.hmi.chain` | bit | wewn. | `watchdog.ok-out`, `lrt_hmi_ok.and` | stan watchdoga i iloczynu grzyb ∧ HMI żyje |
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

## Plant przez LRT-NET: `lrt_net` i `lrt_cia402` (sesja 017)

Blok „napędy” dla wirtualnej obrabiarki. `lrt_net` = jedno połączenie UDP (osie w kolejności
napędów z `machine.yaml` bez wrzeciona, gantry = dwie osie), `lrt_cia402` = jedna instancja na oś.

```
loadrt lrt_net personality=3 ip=127.0.0.1 port=47700
loadrt lrt_cia402 count=3
addf motion-command-handler servo-thread
addf motion-controller servo-thread
addf lrt-cia402.0 servo-thread        # ... .1, .2
addf lrt-net.0 servo-thread           # wysyła świeże polecenie; sprzężenie z poprzedniego cyklu
setp lrt-net.0.axis.0.scale [JOINT_0]SCALE
net linumert.j0.pos-cmd   joint.0.motor-pos-cmd  => lrt-net.0.axis.0.pos-cmd
net linumert.j0.pos-fb    lrt-net.0.axis.0.pos-fb => joint.0.motor-pos-fb
net linumert.j0.enable    joint.0.amp-enable-out => lrt-cia402.0.enable
net linumert.j0.fault     lrt-cia402.0.fault     => joint.0.amp-fault-in
net lrt.j0.cw   lrt-cia402.0.controlword  => lrt-net.0.axis.0.controlword
net lrt.j0.sw   lrt-net.0.axis.0.statusword => lrt-cia402.0.statusword
net lrt.j0.mode lrt-cia402.0.mode         => lrt-net.0.axis.0.mode
net lrt.j0.md   lrt-net.0.axis.0.mode-display => lrt-cia402.0.mode-display
```

### `lrt_net` (instancja `lrt-net.0`, parametry modułu `ip`, `port`, `personality` = liczba osi)

| Pin | Typ | Kier. | Znaczenie |
|---|---|---|---|
| `axis.N.controlword` | u32 | in | 6040h (z `lrt_cia402`) |
| `axis.N.mode` | s32 | in | 6060h; 0 = bez zmiany (ostatni poprawny, na starcie 8) |
| `axis.N.pos-cmd` | float | in | pozycja zadana [jedn. osi] → 607Ah = `pos-cmd·scale` |
| `axis.N.scale` | float | in | impulsy na jednostkę (`SCALE` z INI, `MachineModel.counts_per_unit`) |
| `axis.N.statusword` / `.mode-display` | u32 / s32 | out | 6041h / 6061h |
| `axis.N.pos-fb` / `.counts` | float / s32 | out | 6064h w jednostkach osi / w impulsach |
| `axis.N.ferror` | float | out | błąd nadążania napędu [jedn. osi] |
| `axis.N.torque` / `.error-code` | float / u32 | out | 6077h [‰] / 603Fh |
| `din-00…31` / `dout-00…31` | bit | out / in | wejścia (stan elektryczny: 1 = obwód zamknięty, NC w spoczynku = 1; odwrócenie w HAL) / wyjścia cyfrowe Plant (`machine.yaml io`) |
| `spindle-speed-cmd` / `-fb` | float | in / out | wrzeciono [obr/min]; Plant modeluje wał (bez falownika steruje nim `-cmd`), docs/PLANT.md §5a |
| `drive-fault`, `estop-open` | bit | out | flagi odpowiedzi Plant |
| `connected` | bit | out | odpowiedź w ostatnich `timeout-cycles` (20) cyklach |
| `sent`, `received`, `missed`, `bad-frames`, `send-errors` | u32 | out | liczniki mastera (`reset-stats`: zbocze zeruje też Plant) |
| `plant-lost`, `plant-late`, `plant-jitter-us`, `reply-age` | u32 | out | statystyki Plant; `reply-age` = 1 → odpowiedź z poprzedniego cyklu |

### `lrt_cia402` (instancje `lrt-cia402.N`)

| Pin | Typ | Kier. | Znaczenie |
|---|---|---|---|
| `enable` | bit | in | `joint.N.amp-enable-out` |
| `statusword`, `mode-display` | u32, s32 | in | z `lrt_net` |
| `mode-request` | s32 | in | tryb poza bazowaniem (8 = CSP) |
| `controlword`, `mode` | u32, s32 | out | do `lrt_net` |
| `enabled`, `state` | bit, s32 | out | OPERATION ENABLED; stan 0–7 (opis w komponencie) |
| `fault` | bit | out | do `joint.N.amp-fault-in`, po `fault-grace` (0,5 s) kasowania przy włączeniu |
| `drive-fault` | bit | out | fault bez zwłoki (diagnostyka) |
| `home-start` → `homing-active`, `homed`, `homing-error` | bit | in → out | bazowanie w napędzie (tryb 6, 6041h bity 10/12/13) |
| `homing`, `torque-limit-normal/-homing` → `torque-limit` | bit, float | in → out | zredukowany moment przy bazowaniu na zderzak (6072h; LRT-NET v1 bez pola — ramka v2) |

NIEZWERYFIKOWANE NA SPRZĘCIE. Test: `tests/test_hal_lrt_net.py` (halrun + serwer Plant, marker linuxcnc).

Obsługa D37: grzyb i podwójny Reset korzystają z impulsu `linumert.hmi-ack`;
żaden nie zamyka fizycznego wejścia safety. W konfiguracji wirtualnej handshake
`io.tool-change` → `sim_toolchange` → `io.tool-changed` zastępuje fizyczną wymianę narzędzia.
