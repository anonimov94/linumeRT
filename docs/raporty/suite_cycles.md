# suite_cycles — generatory na wirtualnych maszynach Plant

Model-Author: Claude · 2026-10-24 · `tools/suite_cycles.py` (atrapa mastera, lockstep z napędami z `machine.yaml`; frezarka: wariant `mill_servo_table_y2` z czujnikiem bazy drugiej strony bramy).

Kryteria: ukończony, brak alarmu, 0 zgubionych kroków, błąd nadążania XYZ ≤ 0.2 mm. Detal w układzie maszyny X/Y 100–200, Z −20.

## A. G0 według `machine.yaml`

Wynik: **10/20 PASS**.

| Generator | Maszyna | Wynik | Bloki | Maks. błąd nadążania [mm] | Uwagi |
|---|---|---|---|---|---|
| `face_mill` | router_gantry_steppers | FAIL | 13 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: -32 kroków; zgubione kroki Y ≤ 0: 40 kroków; zgubione kroki Z ≤ 0: -276 kroków |
| `face_mill` | mill_servo_table | PASS | 13 | X 0.053, Y 0.0582, Z 0.0468 | OK |
| `drill_holes` | router_gantry_steppers | FAIL | 28 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: 180 kroków; zgubione kroki Y ≤ 0: 100 kroków; zgubione kroki Z ≤ 0: 12 kroków |
| `drill_holes` | mill_servo_table | PASS | 28 | X 0.0668, Y 0.042, Z 0.0488 | OK |
| `drill_holes` | router_gantry_steppers | FAIL | 56 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: -140 kroków; zgubione kroki Y ≤ 0: -124 kroków; zgubione kroki Z ≤ 0: 84 kroków |
| `drill_holes` | mill_servo_table | PASS | 56 | X 0.0683, Y 0.0685, Z 0.0585 | OK |
| `pocket_rect` | router_gantry_steppers | FAIL | 1509 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: 112 kroków; zgubione kroki Y ≤ 0: 172 kroków; zgubione kroki Z ≤ 0: -164 kroków |
| `pocket_rect` | mill_servo_table | PASS | 1509 | X 0.0514, Y 0.0589, Z 0.047 | OK |
| `pocket_circle` | router_gantry_steppers | FAIL | 1219 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: 76 kroków; zgubione kroki Y ≤ 0: 116 kroków; zgubione kroki Z ≤ 0: -628 kroków |
| `pocket_circle` | mill_servo_table | PASS | 1219 | X 0.0586, Y 0.0578, Z 0.0491 | OK |
| `slot_linear` | router_gantry_steppers | FAIL | 262 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki Y ≤ 0: 44 kroków; zgubione kroki Z ≤ 0: -492 kroków |
| `slot_linear` | mill_servo_table | PASS | 262 | X 0.0518, Y 0.052, Z 0.0497 | OK |
| `slot_arc` | router_gantry_steppers | FAIL | 578 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: -40 kroków; zgubione kroki Y ≤ 0: 120 kroków; zgubione kroki Z ≤ 0: -208 kroków |
| `slot_arc` | mill_servo_table | PASS | 578 | X 0.0521, Y 0.0536, Z 0.05 | OK |
| `stud_rect` | router_gantry_steppers | FAIL | 758 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: 76 kroków; zgubione kroki Y ≤ 0: 32 kroków; zgubione kroki Z ≤ 0: -208 kroków |
| `stud_rect` | mill_servo_table | PASS | 758 | X 0.0536, Y 0.0434, Z 0.0499 | OK |
| `stud_circle` | router_gantry_steppers | FAIL | 734 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: 92 kroków; zgubione kroki Y ≤ 0: 712 kroków; zgubione kroki Z ≤ 0: -208 kroków |
| `stud_circle` | mill_servo_table | PASS | 734 | X 0.0515, Y 0.0472, Z 0.05 | OK |
| `contour` | router_gantry_steppers | FAIL | 139 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: -92 kroków; zgubione kroki Y ≤ 0: -36 kroków; zgubione kroki Z ≤ 0: -40 kroków |
| `contour` | mill_servo_table | PASS | 139 | X 0.055, Y 0.0438, Z 0.0472 | OK |

## B. G0 ograniczone do 3000 mm/min (jak obniżone MAX_VELOCITY w INI)

Wynik: **10/20 PASS**.

| Generator | Maszyna | Wynik | Bloki | Maks. błąd nadążania [mm] | Uwagi |
|---|---|---|---|---|---|
| `face_mill` | router_gantry_steppers | FAIL | 13 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: 4 kroków; zgubione kroki Y ≤ 0: 784 kroków; zgubione kroki Z ≤ 0: -236 kroków |
| `face_mill` | mill_servo_table | PASS | 13 | X 0.0397, Y 0.043, Z 0.0466 | OK |
| `drill_holes` | router_gantry_steppers | FAIL | 28 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: 248 kroków; zgubione kroki Y ≤ 0: 812 kroków; zgubione kroki Z ≤ 0: 68 kroków |
| `drill_holes` | mill_servo_table | PASS | 28 | X 0.0405, Y 0.0403, Z 0.0466 | OK |
| `drill_holes` | router_gantry_steppers | FAIL | 56 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: -132 kroków; zgubione kroki Y ≤ 0: -128 kroków; zgubione kroki Z ≤ 0: -172 kroków |
| `drill_holes` | mill_servo_table | PASS | 56 | X 0.0405, Y 0.0392, Z 0.0585 | OK |
| `pocket_rect` | router_gantry_steppers | FAIL | 1509 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: 12 kroków; zgubione kroki Y ≤ 0: 1084 kroków; zgubione kroki Z ≤ 0: 100 kroków |
| `pocket_rect` | mill_servo_table | PASS | 1509 | X 0.0515, Y 0.0589, Z 0.0466 | OK |
| `pocket_circle` | router_gantry_steppers | FAIL | 1219 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: -52 kroków; zgubione kroki Y ≤ 0: 1324 kroków; zgubione kroki Z ≤ 0: -212 kroków |
| `pocket_circle` | mill_servo_table | PASS | 1219 | X 0.0587, Y 0.0578, Z 0.0466 | OK |
| `slot_linear` | router_gantry_steppers | FAIL | 262 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: -8 kroków; zgubione kroki Y ≤ 0: 660 kroków; zgubione kroki Z ≤ 0: -540 kroków |
| `slot_linear` | mill_servo_table | PASS | 262 | X 0.0516, Y 0.052, Z 0.0466 | OK |
| `slot_arc` | router_gantry_steppers | FAIL | 578 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: -224 kroków; zgubione kroki Y ≤ 0: 100 kroków; zgubione kroki Z ≤ 0: -180 kroków |
| `slot_arc` | mill_servo_table | PASS | 578 | X 0.0521, Y 0.0519, Z 0.0466 | OK |
| `stud_rect` | router_gantry_steppers | FAIL | 758 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: 68 kroków; zgubione kroki Y ≤ 0: -56 kroków; zgubione kroki Z ≤ 0: -180 kroków |
| `stud_rect` | mill_servo_table | PASS | 758 | X 0.0534, Y 0.0426, Z 0.0466 | OK |
| `stud_circle` | router_gantry_steppers | FAIL | 734 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: 72 kroków; zgubione kroki Y ≤ 0: 916 kroków; zgubione kroki Z ≤ 0: -180 kroków |
| `stud_circle` | mill_servo_table | PASS | 734 | X 0.0515, Y 0.0472, Z 0.0466 | OK |
| `contour` | router_gantry_steppers | FAIL | 139 | X 0.0, Y 0.0, Z 0.0 | zgubione kroki X ≤ 0: -32 kroków; zgubione kroki Y ≤ 0: 820 kroków; zgubione kroki Z ≤ 0: 100 kroków |
| `contour` | mill_servo_table | PASS | 139 | X 0.0404, Y 0.043, Z 0.0466 | OK |

## Ustalenia

- Próby kontrolne bez generatorów: na `router_gantry_steppers` sam `G0 X10` gubi kroki (24), `G0 X100` ok. 1800, a `G1 X10 F600` i dłuższe posuwy — 0; na `mill_servo_table` sam `G0 Z-15` daje błąd nadążania ok. 0,72 mm i E-4201, a `G1 Z-15 F600` przechodzi (0,07 mm). Przyczyna leży w profilu G0 atrapy i modelu napędów/konfiguracji maszyn, nie w generatorach — do sprawdzenia w M1 (Plant).
- Wynik atrapy zależy od kroku całkowania `substeps` (prosty program G0/G1, z bazowaniem): frezarka przy 1 — 0,05 mm, przy 2–10 — E-4201 i Z ok. 0,7 mm; router przy 1 — 44 kroki Z, przy 4–10 — ok. 1600–1800 kroków X/Y. Suite używa `substeps = 1` jak scenariusze i macierz Plant; zależność do wyjaśnienia w M1.
- Generatory ocenia wariant B: posuwy i dojazdy w granicach napędów.
- Atrapa wykonuje tylko G0/G1: łuki rozbite na cięciwy ≤ 3°, cykle wiercenia rozwinięte; kontur z korekcją G41.1/G42.1 tylko w teście rs274 (CI).

Wynik nie zastępuje testu z LinuxCNC ani maszyny. NIEZWERYFIKOWANE NA SPRZĘCIE.
