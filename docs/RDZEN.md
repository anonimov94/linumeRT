# Rdzeń linumeRT: model stanu maszyny

Model-Author: Claude · sesja 006.

## Po co jest rdzeń
`core/linumert/` nie zależy od interfejsu. Dzięki temu te same moduły służą ekranowi QtVCP,
raportom, generatorom cykli, symulacji i scenariuszom testowym, a testują się bez LinuxCNC.
Ekran importuje rdzeń zwykłym `import linumert...` w tym samym procesie; nie ma serwera ani
własnego protokołu między ekranem a rdzeniem.

## Migawka stanu (`linumert.cnc.model`)
- `MachineSnapshot` jest niezmienna (`frozen`): osie (`AxisSnapshot`), tryb, stan interpretera,
  linia, override, wrzeciono, narzędzie, offsety, aktywne G/M, błędy i `timestamp`.
- Pozycje są w układzie maszynowym (jak `stat.actual_position`). `work_position()` odejmuje
  tylko offset układu roboczego (G54..G59.3); G92 i długość narzędzia nie są uwzględnione.
- Świeżość: `snapshot.is_fresh(now, max_age=0.5)`. Konsument sam pilnuje, czy dane nie są stare.

## Dwa źródła migawek, jeden model
| Źródło | Plik | Użycie |
|---|---|---|
| Prawdziwy LinuxCNC | `cnc/linuxcnc_reader.py` | odczyt `linuxcnc.stat` (tylko odczyt), narzędzia poza ekranem |
| Atrapa | `cnc/fake.py` | testy generatorów, symulacji i scenariuszy; zegar wirtualny |

`LinuxCNCReader` importuje moduł `linuxcnc` dopiero przy pierwszym `read()`. Import pakietu
`linumert` nigdy go nie wymaga (pilnuje tego test). Moduł, `stat` i kanał błędów można
wstrzyknąć, więc mapowanie testuje się na sztucznym module.

## Jak ekran QtVCP z tego korzysta
Widżety QtVCP nadal opierają się na `STATUS`/`ACTION` z QtVCP. Rdzeń dostarcza logikę, która
ma działać identycznie na ekranie i w testach: wywołanie `reader.read()` w timerze GUI
(np. 10 Hz) daje migawkę, którą dostają raporty, diagnostyka i symulacja. Polecenia do
LinuxCNC nadal idą przez `linuxcnc.command` / `ACTION`, nie przez czytnik.

## Atrapa: zakres i ograniczenia
Obsługuje E-stop/zasilanie, bazowanie, MANUAL/MDI/AUTO, G0/G1 z override, G4, G53, G54..G59.3,
G90/G91, M3/M4/M5, M6 (bez tabeli narzędzi), M0/M2/M30 i limity programowe osi. Pozycja
rzeczywista równa się zadanej; dynamikę, napędy i bazowanie z krańcówkami daje dopiero Plant.
Atrapa jest modelem do testów logiki rdzenia, nie wzorcem zachowania LinuxCNC.

## Weryfikacja
Wszystko poza czytnikiem sprawdzają testy `tests/test_cnc_fake.py`. Czytnik jest testowany na
sztucznym module (`tests/test_cnc_reader.py`) oraz na LinuxCNC 2.9 RIP z konfiguracją
`config/sim/linumert_xyz` (`tests/test_reader_linuxcnc.py`, marker `linuxcnc`, sesja 008): stan E-STOP,
bazowanie, MDI w G55, pozycje w układzie maszyny, limity `[AXIS_*]`, kody G/M i wrzeciono `spindle[0]`.
Nie sprawdzono: `limit_hit` na krańcówce, `tool_offset` po M6, kinematyki inne niż trivkins.
