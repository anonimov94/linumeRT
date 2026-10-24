# plant/library/drives

Szablony napędów wirtualnych (kopiowalne). **Każdy wirtualny napęd w maszynie jest instancją szablonu
stąd** (CLAUDE.md §5a). Model-Author: Claude · sesja 013 (REQ-VD-01…05).

## Biblioteka startowa (REQ-VD-05)

Wartości są **przykładowe** (typowe dla klasy, zaokrąglone), bez nazw producentów i bez danych z kart
katalogowych. NIEZWERYFIKOWANE NA SPRZĘCIE.

| id | typ | klasa |
|---|---|---|
| `stepper_nema23_3nm` | `stepper_open` | krokowiec NEMA 23, ok. 3 N·m, bez sprzężenia |
| `stepper_nema34_85nm` | `stepper_open` | krokowiec NEMA 34, ok. 8,5 N·m, bez sprzężenia |
| `servo_stepper_22nm` | `servo_stepper` | serwo krokowe ok. 2,2 N·m, pętla zamknięta |
| `servo_400w` | `servo_csp` | serwo 400 W, enkoder 17 bit |
| `servo_750w` | `servo_csp` | serwo 750 W z hamulcem |
| `rotary_table_worm_1_90` | `rotary_geared` | stół obrotowy ze ślimakiem 1:90 (serwo 200 W) |
| `spindle_vfd_22kw` | `spindle_vfd` | wrzeciono 2,2 kW z falownikiem (przybliżenie momentowe) |

## Format szablonu (`<id>.yaml`, nazwa pliku = `id`)

Wszystkie pola są jawne — brak ukrytych wartości domyślnych. Zakresy i jednostki: tabela `PARAMS` w
`plant/server/linumert_plant/drive_template.py`; wygenerowany z niej JSON Schema:
`drive_template.schema.json` (`python -m linumert_plant drive schema`).

| Sekcja | Zawartość |
|---|---|
| (góra) | `id`, `version` (≥ 1), `based_on` (id źródła kopii albo `null`), `name`, `description`, `value_source` (musi mówić, że wartości są przykładowe), `type`, `live` |
| `motor` | momenty (znamionowy, szczytowy, czas szczytu), `rotor_inertia`, `torque_constant`, prądy, `encoder_counts_per_rev`, szum enkodera, `torque_curve` `[[omega, moment], ...]`, hamulec (obecność, czasy) |
| `electrical` | `nominal_voltage`, `supply_voltage` |
| `controller` | `kp_pos`, `kv`, `ti`, `kff_vel`, `kff_acc`, `inertia_est`, filtry, `max_speed` |
| `limits` | `torque_limit_permille` (6072h), okno nadążania 6065h/6066h, `quick_stop_decel` 6085h, próg zatrzymania, czas rozruchu |
| `reactions` | `quick_stop_option` 605Ah, `fault_reaction_option` 605Eh, `brake_on_fault` |
| `cia402` | lista obsługiwanych obiektów (podzbiór wymagany z REQ-VD-01), parametry bazowania 6098h/6099h/609Ah |
| `mechanics` | domyślna mechanika osi: `kind` (`linear` / `rotary`), `load`, `ratio`, `j_screw`, tarcie, `backlash`, `contact_stiffness`, `gravity_force` |
| `stepper` | tylko dla typów krokowych: `full_steps_per_rev` (wielokrotność 4), `damping_ratio` |

Typy → model w rdzeniu C: `servo_csp`, `rotary_geared`, `spindle_vfd` → serwo CSP (oś obrotowa albo
przybliżenie momentowe wrzeciona); `stepper_open` → krokowiec bez sprzężenia; `servo_stepper` → krokowiec
z pętlą zamkniętą.

Sekcja `real:` (opcjonalna, REQ-VD-06, sesja 061) opisuje napęd rzeczywisty: `driver` (`stepgen` z `timing_ns`
{steplen, stepspace, dirsetup, dirhold}; `ethercat_cia402` z `pdo` (co najmniej 6040h, 6041h, 607Ah, 6064h);
`vfd_modbus` z `vfd` {protocol hy_vfd|mb2hal, baud, address}; `pwm` z `pwm.frequency_hz`). Typ napędu ogranicza
sterowniki (krokowiec: stepgen albo EtherCAT; serwo: EtherCAT albo step/dir; wrzeciono: Modbus, PWM, EtherCAT).
Skala impulsów na mm/° wynika z `motor.encoder_counts_per_rev` i `mechanics.ratio` — nie wpisuje się jej
osobno. Kanały napędów podaje `machine.yaml` (`hardware:`); plan sprzętu: `linumert_plant.drive_real.hardware_plan`.
NIEZWERYFIKOWANE NA SPRZĘCIE.

### Reguły między polami (sprawdza `validate_template`)
- moment szczytowy ≥ znamionowy, prąd szczytowy ≥ znamionowy; stała momentu × prąd znamionowy = moment
  znamionowy ±10 %;
- krzywa momentu: od `omega = 0`, `omega` rosnąco, moment przy 0 ≥ znamionowego, żaden punkt > szczytowego;
- `torque_limit_permille` ≤ moment szczytowy / znamionowy × 1000 (jak w rdzeniu C);
- `supply_voltage` w zakresie 0,1…1,5 × `nominal_voltage`; tarcie statyczne ≥ Coulomba;
- `rotary_geared` i `spindle_vfd` wymagają `mechanics.kind: rotary`; krokowce wymagają sekcji `stepper`,
  pozostałe typy jej zabraniają; krokowiec bez sprzężenia: mikrokroki na obrót podzielne przez pełne kroki.

### Parametry `live:` (REQ-VD-04)
Lista ścieżek parametrów zmienianych w trakcie pracy (dozwolone: `motor.rotor_inertia`, `mechanics.load`,
`mechanics.j_screw`, `mechanics.friction_*`, `mechanics.backlash`, `limits.torque_limit_permille`,
`electrical.supply_voltage`). Pozostałe parametry wymagają przeładowania modelu. Zmiany: `LiveParams.set()`
(walidacja zakresów, dziennik `[czas, ścieżka, było, jest]`) → rdzeń C (`plant/core/live.h`):
`lrt_axis_set_live()` dla masy, J, tarcia, luzu i napięcia, `lrt_drive_set_live()` dla limitu momentu
(6072h) i estymaty J regulatora (`LRT_LIVE_INERTIA_EST`, nie jest polem szablonu). Oba wpisują zmianę do
wspólnego dziennika `lrt_live_log` (bufor kołowy, bez alokacji) z czasem modelu.
Luz zmieniany w locie wymaga modelu dwuczłonowego od startu (rdzeń odrzuca przełączenie sztywny ↔ luz):
`to_c_params()` ustawia wtedy `stiffness` = 1000 N·m/rad, jeśli `contact_stiffness` = 0.
Regulatory (`kv`, `ti`, `kp_pos`) są jawne i dobrane dla bezwładności z szablonu; po dużej zmianie `load`
w locie trzeba je dostroić (`lrt_drive_tune_servo`) albo zaakceptować mniejsze pasmo/tłumienie;
estymatę J dla FF przyspieszenia można przestawić w locie przez `lrt_drive_set_live(LRT_LIVE_INERTIA_EST)`.

## Instancje i kopiowanie
- Instancja w `machine.yaml`: `drives: [{id: X1, template: servo_400w, overrides: {mechanics: {load: 150}}}]`;
  nadpisania (zagnieżdżone albo `mechanics.load: 150`) są walidowane tymi samymi zakresami co szablon;
  błąd ma ścieżkę `drives[0].overrides.mechanics.load`. (`machine.yaml` wprowadza PR sesji 010; moduł
  `drive_library.resolve_instances()` rozwiązuje listę `drives:`.)
- Kopiowanie (REQ-VD-03): `python -m linumert_plant drive clone <źródło> <nowe_id> [--machine machine.yaml]
  [--name "..."] [--force]` — źródło to id szablonu albo (z `--machine`) id instancji; kopia ma `version: 1`,
  `based_on: <szablon źródłowy>` i jest niezależna od oryginału. Pozostałe polecenia: `drive list|show|validate|schema`.
- Zalecany krok czasu symulacji: serwa 1 ms; krokowiec bez sprzężenia ≤ 100 µs (wymaga tego model pull-out).
