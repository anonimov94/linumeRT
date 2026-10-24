# suite_cycles — generatory na wirtualnych maszynach Plant

Model-Author: Claude · 2026-10-24 · `tools/suite_cycles.py` (atrapa mastera, lockstep z napędami z `machine.yaml`; frezarka: wariant `mill_servo_table_y2` z czujnikiem bazy drugiej strony bramy).

Kryteria: ukończony, brak alarmu, 0 zgubionych kroków, błąd nadążania XYZ ≤ 0.2 mm. Detal w układzie maszyny X/Y 100–200, Z −20.

## A. G0 według `machine.yaml`

Wynik: **20/20 PASS**.

| Generator | Maszyna | Wynik | Bloki | Maks. błąd nadążania [mm] | Uwagi |
|---|---|---|---|---|---|
| `face_mill` | router_gantry_steppers | PASS | 13 | X 0.0, Y 0.0, Z 0.0 | OK |
| `face_mill` | mill_servo_table | PASS | 13 | X 0.0555, Y 0.0472, Z 0.047 | OK |
| `drill_holes` | router_gantry_steppers | PASS | 28 | X 0.0, Y 0.0, Z 0.0 | OK |
| `drill_holes` | mill_servo_table | PASS | 28 | X 0.066, Y 0.0459, Z 0.049 | OK |
| `drill_holes` | router_gantry_steppers | PASS | 56 | X 0.0, Y 0.0, Z 0.0 | OK |
| `drill_holes` | mill_servo_table | PASS | 56 | X 0.0677, Y 0.0677, Z 0.0593 | OK |
| `pocket_rect` | router_gantry_steppers | PASS | 1509 | X 0.0, Y 0.0, Z 0.0 | OK |
| `pocket_rect` | mill_servo_table | PASS | 1509 | X 0.0531, Y 0.0586, Z 0.0472 | OK |
| `pocket_circle` | router_gantry_steppers | PASS | 1219 | X 0.0, Y 0.0, Z 0.0 | OK |
| `pocket_circle` | mill_servo_table | PASS | 1219 | X 0.0604, Y 0.0517, Z 0.0492 | OK |
| `slot_linear` | router_gantry_steppers | PASS | 262 | X 0.0, Y 0.0, Z 0.0 | OK |
| `slot_linear` | mill_servo_table | PASS | 262 | X 0.0529, Y 0.0523, Z 0.0503 | OK |
| `slot_arc` | router_gantry_steppers | PASS | 578 | X 0.0, Y 0.0, Z 0.0 | OK |
| `slot_arc` | mill_servo_table | PASS | 578 | X 0.0529, Y 0.0542, Z 0.0507 | OK |
| `stud_rect` | router_gantry_steppers | PASS | 758 | X 0.0, Y 0.0, Z 0.0 | OK |
| `stud_rect` | mill_servo_table | PASS | 758 | X 0.0418, Y 0.0467, Z 0.0504 | OK |
| `stud_circle` | router_gantry_steppers | PASS | 734 | X 0.0, Y 0.0, Z 0.0 | OK |
| `stud_circle` | mill_servo_table | PASS | 734 | X 0.0522, Y 0.0459, Z 0.0506 | OK |
| `contour` | router_gantry_steppers | PASS | 139 | X 0.0, Y 0.0, Z 0.0 | OK |
| `contour` | mill_servo_table | PASS | 139 | X 0.0593, Y 0.0472, Z 0.0474 | OK |

## B. G0 ograniczone do 3000 mm/min (jak obniżone MAX_VELOCITY w INI)

Wynik: **20/20 PASS**.

| Generator | Maszyna | Wynik | Bloki | Maks. błąd nadążania [mm] | Uwagi |
|---|---|---|---|---|---|
| `face_mill` | router_gantry_steppers | PASS | 13 | X 0.0, Y 0.0, Z 0.0 | OK |
| `face_mill` | mill_servo_table | PASS | 13 | X 0.0404, Y 0.0465, Z 0.0468 | OK |
| `drill_holes` | router_gantry_steppers | PASS | 28 | X 0.0, Y 0.0, Z 0.0 | OK |
| `drill_holes` | mill_servo_table | PASS | 28 | X 0.0415, Y 0.0445, Z 0.0468 | OK |
| `drill_holes` | router_gantry_steppers | PASS | 56 | X 0.0, Y 0.0, Z 0.0 | OK |
| `drill_holes` | mill_servo_table | PASS | 56 | X 0.0414, Y 0.0434, Z 0.0593 | OK |
| `pocket_rect` | router_gantry_steppers | PASS | 1509 | X 0.0, Y 0.0, Z 0.0 | OK |
| `pocket_rect` | mill_servo_table | PASS | 1509 | X 0.0531, Y 0.0586, Z 0.0468 | OK |
| `pocket_circle` | router_gantry_steppers | PASS | 1219 | X 0.0, Y 0.0, Z 0.0 | OK |
| `pocket_circle` | mill_servo_table | PASS | 1219 | X 0.0603, Y 0.0462, Z 0.0468 | OK |
| `slot_linear` | router_gantry_steppers | PASS | 262 | X 0.0, Y 0.0, Z 0.0 | OK |
| `slot_linear` | mill_servo_table | PASS | 262 | X 0.0529, Y 0.0523, Z 0.0468 | OK |
| `slot_arc` | router_gantry_steppers | PASS | 578 | X 0.0, Y 0.0, Z 0.0 | OK |
| `slot_arc` | mill_servo_table | PASS | 578 | X 0.0529, Y 0.0522, Z 0.0468 | OK |
| `stud_rect` | router_gantry_steppers | PASS | 758 | X 0.0, Y 0.0, Z 0.0 | OK |
| `stud_rect` | mill_servo_table | PASS | 758 | X 0.0416, Y 0.0461, Z 0.0468 | OK |
| `stud_circle` | router_gantry_steppers | PASS | 734 | X 0.0, Y 0.0, Z 0.0 | OK |
| `stud_circle` | mill_servo_table | PASS | 734 | X 0.0522, Y 0.0452, Z 0.0468 | OK |
| `contour` | router_gantry_steppers | PASS | 139 | X 0.0, Y 0.0, Z 0.0 | OK |
| `contour` | mill_servo_table | PASS | 139 | X 0.0412, Y 0.0465, Z 0.0468 | OK |

## Ustalenia

- Próby kontrolne bez generatorów (G0 X10/X100 na routerze, G0 Z-15 na frezarce) przed poprawką Plant gubiły kroki lub dawały E-4201; po poprawce przechodzą — był to artefakt modelu (cel w pierwszym podkroku), nie cecha G0 ani konfiguracji maszyn.
- Podkroki całkowania: Plant interpoluje cel CSP w cyklu mastera i domyślnie liczy 4 podkroki; wynik nie zależy od podkroków ≥ 2. Przed poprawką (cel w pierwszym podkroku) frezarka przy ≥ 2 dawała E-4201 na G0 Z, a router przy ≥ 4 gubił ok. 1560 kroków na G0; przy 1 podkroku router gubił kroki na każdym generatorze (krok 1 ms za gruby dla krokowca). Opis i pomiar: `docs/raporty/plant_substeps.md`.
- Generatory ocenia wariant B (posuwy i dojazdy w granicach napędów); po poprawce Plant przechodzą też w wariancie A. Generator nie wymagał zmian.
- Atrapa wykonuje tylko G0/G1: łuki rozbite na cięciwy ≤ 3°, cykle wiercenia rozwinięte; kontur z korekcją G41.1/G42.1 tylko w teście rs274 (CI).

Wynik nie zastępuje testu z LinuxCNC ani maszyny. NIEZWERYFIKOWANE NA SPRZĘCIE.
