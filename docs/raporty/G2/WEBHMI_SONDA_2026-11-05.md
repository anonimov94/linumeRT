# G2 — sonda w WebHMI

Model-Author: Claude · 2026-11-05. Gałąź `claude/webhmi-probe` (od `claude/webhmi-hal-watchdog`, #210).
NIEZWERYFIKOWANE NA SPRZĘCIE.

LinuxCNC 2.9 (RIP) i Plant w WSL `linumeRT-Debian12`, `config/machines/mill_servo_table.yaml`
(cel sondy: górna ściana na Z maszyny −30 przy końcówce 60 mm), maszyna włączona i zbazowana,
narzędzie nad celem (G53 X300 Y400 Z−5), G54 wyzerowany. Przeglądarka w aplikacji Claude
pod `http://127.0.0.1:8765/`. Przycisk „Sonduj” wysyła `{"cmd":"probe", ...}`; brama woła makro
`o<lrt_probe>` z #204 jednym MDI w aktywnym układzie (F100 mm/min, odjazd 2 mm).

| Krok | Działanie w GUI | Wynik | Zrzut |
|---|---|---|---|
| 1 | Panel SONDA: Z, w stronę −, droga 50, styk = 5 | aktywny przy ON, bazowaniu, bezczynności | [1](WEBHMI_SONDA_2026-11-05/1_panel_sondy.jpg) |
| 2 | Sonduj | ~8 s; Z robocze 6,9936 (oczekiwane 7,000 = styk 5 + odjazd 2), Z maszyny −28,018; bez alarmów | [2](WEBHMI_SONDA_2026-11-05/2_po_sondowaniu_z.jpg) |
| 3 | Droga 1 mm z wysokości ~7 mm (sonda nie sięga) | alarm E-1000 „G38.2 move finished without making contact”, Z −1 mm, offset bez zmian | [3](WEBHMI_SONDA_2026-11-05/3_chybienie_alarm.jpg) |

Uchyb 0,006 mm mieści się w tolerancji modelu napędu Plant (0,02 mm, jak test makra #204).

## Test automatyczny

`tests/test_webhmi_probe_linuxcnc.py` (`@pytest.mark.linuxcnc`, ~30 s): polecenie `probe` bramy
na Plant → offset G54 Z = −35,012 (oczekiwane −35 ± 0,02), zgodny z `probed_position`, odjazd 2 mm,
stan ON, bez alarmów. Bez LinuxCNC: `tests/test_webhmi_g2.py` (wywołanie makra, odmowy),
`tests/webhmi_js/test_interlocks.mjs` (blokady przycisku).

## Otwarte

- Sonda X/Y w GUI działa tym samym poleceniem, ale odbiór kliknięty tylko dla Z.
- Posuw i odjazd stałe (F100, 2 mm); kalibracja sondy (033) jeszcze nie w GUI.
