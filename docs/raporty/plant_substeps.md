# Plant: zależność wyniku od `substeps` — diagnoza i poprawka

Model-Author: Claude · 2026-10-24 · ustalenie z sesji 049 (suite_cycles), poprawka w rdzeniu C (M1).

## Objaw
Atrapa mastera (`run_mock`) dawała inne wyniki dla tego samego programu przy różnym
`timing.substeps`: `mill_servo_table` przy `substeps ≥ 2` — E-4201 (błąd nadążania Z ok. 0,65 mm)
już na pierwszym G0 Z; `router_gantry_steppers` przy `substeps ≥ 4` — ok. 1560 zgubionych kroków
X/Y przy `G0 X100`, a `G1 X100 F600` bez strat.

## Przyczyna
Master wysyła cel 607Ah raz na cykl (1 ms). `PlantServer` dzielił cykl na `n` podkroków rdzenia,
ale cel przykładał w całości w pierwszym podkroku i trzymał go przez pozostałe. Napęd CSP liczy
prędkość FF z różnicy celów w swoim kroku (`ctrl_csp`: Δcel / dt), więc widział impuls `n` razy
większy od prędkości rzeczywistej, potem zero; to samo pole krokowca (`ctrl_stepper_open`) —
skok o cały przyrost cyklu w 1/n okresu. Skutek: szarpnięcie momentu, nasycenie, E-4201 albo
poślizg pola i zgubione kroki. To artefakt modelu, nie zachowanie maszyny: napęd CSP interpoluje
cel w okresie synchronizacji (60C2h), a stepgen LinuxCNC rozkłada impulsy w okresie wątku.

Test C bez interpolacji (rampa X do 6 m/min, n = 8): napęd przechodzi w FAULT (E-4201) po ok.
0,1 s i staje; cel jedzie dalej, stąd „błąd” 49 mm = zadana − stojąca oś. Nie jest to ruch ani
przejechanie osi, tylko zatrzymanie napędu po alarmie. Prawdziwy odpowiednik ryzyka na maszynie:
niezgodny okres interpolacji napędu (60C2h) z okresem wątku serwo — wtedy napęd też widzi
szarpnięcia; generator konfiguracji EtherCAT (063) musi ustawiać 60C2h = okres wątku.

## Poprawka
`lrt_machine_step_cycle(m, dt, n)` (rdzeń C): cykl mastera w `n` podkrokach; napędy w CSP
w stanie „praca” dostają cel liniowo rozłożony na podkroki (od celu przyłożonego na końcu
poprzedniego cyklu, z uwzględnieniem przesunięcia ramki przy bazowaniu w napędzie). Poza CSP
(bazowanie, stany wyłączone) bez zmian. `PlantServer` i `HomingMaster` używają nowej funkcji.
Domyślne `substeps` = 4 (`DEFAULT_SUBSTEPS`, wzory `plant.yaml`, `tools/vm/lib.sh`).

## Pomiar (`tools/plant_substeps.py`, atrapa, bazowanie + program)

| Maszyna | Program | n = 1 | n = 2 | n = 4 przed | n = 4 po | n = 8 po | n = 16 po |
|---|---|---|---|---|---|---|---|
| mill_servo_table | G0 Z-15 | PASS Z 0,047 | PASS 0,047 | **E-4201**, Z 0,651 | PASS 0,047 | PASS 0,047 | PASS 0,047 |
| mill_servo_table | G0 X100 Y80 | PASS | PASS | **E-4201** | PASS X 0,042 Y 0,054 | PASS | PASS |
| router_gantry_steppers | G0 X10 | 16 kroków Z | PASS | 16 kroków X | PASS | PASS | PASS |
| router_gantry_steppers | G0 X100 | 16 kroków Z | PASS | **1560 kroków X** | PASS | PASS | PASS |
| router_gantry_steppers | G1 X100 F600 | 16 kroków Z | PASS | PASS | PASS | PASS | PASS |
| router_gantry_steppers | G0 Y100 | 680 Y, 16 Z | PASS | **1564 kroków Y** | PASS | PASS | PASS |

Kolumny „n = 1” i „n = 2”: po poprawce (n = 1 bez zmian względem stanu wcześniejszego).
Wynik zbieżny dla n ≥ 2; przy n = 1 krokowiec przy G0 gubi kroki, bo krok całkowania 1 ms jest
za gruby dla dynamiki pola (wirnik krokowca ~kHz) — stąd domyślne 4. Scenariusz
`too_much_accel_stepper` (przyspieszenie ponad moment) nadal gubi kroki zgodnie z oczekiwaniem,
macierz Plant 14/14 PASS.

Model rdzenia, nie maszyna. NIEZWERYFIKOWANE NA SPRZĘCIE.
