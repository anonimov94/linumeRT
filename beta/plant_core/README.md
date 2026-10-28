# plant/core

Rdzeń dynamiki Plant w C11, bez zależności poza libc/libm. Zero alokacji po `lrt_axis_init()`,
zero I/O, ograniczony czas kroku (≤ 2000 podkroków). Zawiera: osie, napęd CiA 402, I/O,
kinematykę, magazyn (kolejne sesje M1). Testy: `make -C plant/core test` albo `make test-c`.

## Oś (`axis.h`, `axis.c`) — sesja 011

Jedna oś liniowa albo obrotowa sterowana **momentem silnika** na wale. Jednostki SI.
`ratio` = przemieszczenie obciążenia na 1 rad wału (śruba: skok/(2π) w m/rad; stół ze
ślimakiem 1:90: 1/90 rad/rad).

| Zjawisko | Model |
|---|---|
| Bezwładność | `J = j_motor + j_screw + load·ratio²` (masa w kg dla osi liniowej, kg·m² dla obrotowej) |
| Moment dostępny | krzywa moment–prędkość (2–16 punktów, interpolacja liniowa, symetryczna); powyżej ostatniego punktu 0; obcięcie sygnalizuje `LRT_AXIS_EV_TORQUE_LIMITED` |
| Tarcie | lepkie, Coulomba i statyczne (moment odrywania); sprowadzone do wału, działa na obciążenie |
| Grawitacja | stała siła `gravity_force` na obciążenie (np. `-m·9,81` dla Z) |
| Luz i podatność | `backlash > 0` albo `stiffness > 0` włącza model dwuczłonowy: silnik i obciążenie połączone sprężyną z tłumieniem poza szczeliną; `stiffness = 0` przy luzie → `LRT_AXIS_DEFAULT_CONTACT_STIFFNESS` |
| Zderzaki | `use_stops`; `stop_stiffness = 0` → zderzak sztywny (zderzenie niesprężyste), `> 0` → sprężyna z tłumieniem; zdarzenia `LRT_AXIS_EV_HARDSTOP_MIN/MAX`, `impact_speed` |

Całkowanie: półjawny Euler dla prędkości, trapez dla pozycji (dokładny przy stałym przyspieszeniu),
tarcie lepkie niejawnie, tarcie suche z przejściem przez zero → przylgnięcie. Krok `dt` dzielony na
podkroki wg największej sztywności (`dt_sub_max`); po przekroczeniu `LRT_AXIS_MAX_SUBSTEPS` ustawiana
jest flaga `LRT_AXIS_EV_SUBSTEPS_CAPPED`. Wartości NaN/inf w stanie lub momencie → błąd
`LRT_AXIS_ERR_NUMERIC` i przywrócenie stanu sprzed kroku.

```c
lrt_axis_params p;
lrt_axis a;
lrt_axis_params_default(&p);          /* oś 5 mm/obr, 20 kg, krzywa płaska 1 N·m */
p.friction_coulomb = 0.1; p.friction_static = 0.15;
if (lrt_axis_init(&a, &p) != LRT_AXIS_OK) { /* lrt_axis_strerror(rc) */ }
lrt_axis_step(&a, torque_cmd, 1e-3);  /* a.pos, a.vel, a.events */
```

Nie ma hamulca. Napęd CiA 402 (sesja 012), kinematyka wielu osi (014) i bazowanie (015) opisano niżej.
Model sprawdzony wyłącznie wzorami analitycznymi: **NIEZWERYFIKOWANE NA SPRZĘCIE**.

## Napęd (`drive.h`, `drive.c`) — sesja 012

Wirtualny napęd między masterem a osią: maszyna stanów CiA 402 (6040h/6041h), tryb CSP, krokowiec
bez sprzężenia i z pętlą zamkniętą. Kolejność kroku: pomiar → wykrycie awarii → maszyna stanów →
moment → I2t → raporty. Do osi trafia `torque_cmd`; z osi napęd bierze `lrt_drive_feedback`
(`theta_m`, `omega_m`, `torque_avail`, `j_total`).

```c
lrt_drive d; lrt_drive_params p;
lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
lrt_drive_tune_servo(&p, j_total, bandwidth_rad_s, dt);
lrt_drive_init(&d, &p);
lrt_drive_set_controlword(&d, 0x06); /* ...0x07, 0x0F */
lrt_drive_set_target_position(&d, target_counts);
lrt_drive_step(&d, &fb, dt, &torque_cmd);
```

- Serwo CSP: P położenia + PI prędkości (warunkowa całka), FF prędkości i przyspieszenia, limit
  momentu `min(6072h, torque_avail)`, okno błędu nadążania 6065h/6066h (E-4201), I2t (ostrzeżenie 80 %,
  kasowanie awarii dopiero poniżej 50 %), kwantyzacja enkodera i deterministyczny szum.
- Krokowiec bez sprzężenia: moment `A·sin(δ_e)` + ograniczone tłumienie; poślizg liczony w okresach
  elektrycznych (4 pełne kroki), `lost_steps` > 0 = wirnik za polem; master widzi pozycję zadaną, bez awarii.
- Krokowiec z pętlą zamkniętą: pętla CSP z limitem z krzywej i awarią przy błędzie nadążania.
- Awarie: tablica `LRT_DRIVE_FAULT_LIST` (603Fh + alarm E-4200…E-4208 z katalogu alarmów), wstrzykiwanie
  `lrt_drive_inject_fault` (trwałe do `clear_fault_cause`).
- Tryb bazowania (6): od sesji 015 obsługiwany (metody 1, 2, 3, 5, 17, 18, 19, 21, 33–35, 37, -1, -2), enkoder przyrostowy lub absolutny z baterią (awaria E-4211); hamulec niemodelowany.

59 testów w `tests/test_drive.c` (wzory analityczne: błąd ustalony, kąt obciążenia, czas I2t, bariera
potencjału). **NIEZWERYFIKOWANE NA SPRZĘCIE.**

## Testy

`tests/lrt_test.h` to minimalny framework (wynik w stylu TAP). 29 testów w `tests/test_axis.c`
porównują wyniki z rozwiązaniami analitycznymi (tolerancja ≤ 1 %): przyspieszenie stałym momentem,
F = m·a, wpływ masy, bezwładność odbita (liniowa i obrotowa), krzywa momentu, tarcie lepkie
(wykładnicze), Coulomba i statyczne (odrywanie, czas wybiegu), grawitacja, luz (droga przy zmianie
kierunku), zderzaki sztywne i sprężyste (maks. penetracja z bilansu energii), niezależność od
kroku, walidacja parametrów. `tests/test_plant_core.py` uruchamia je z pytest i pilnuje braku
`malloc`/I/O w rdzeniu.

## Maszyna (`machine.h`, sesja 014)

`lrt_machine` składa napędy (`lrt_drive` + `lrt_axis` na każdy silnik) w obrabiarkę (REQ-VM-02…05):

- **Osie maszyny** z jednym albo dwoma napędami; gantry: pozycja = średnia stron, rozjazd
  `drive0 − drive1`, zdarzenie `GANTRY_SKEW` po przekroczeniu `max_skew`.
- **Łańcuch kinematyczny**: człony liniowe/obrotowe (wektor osi, przesunięcie, rodzic), gałąź narzędzia
  i gałąź detalu; kinematyka prosta daje koniec narzędzia w układzie maszyny i detalu
  (`lrt_machine_tool_tip`, `lrt_machine_forward`).
- **Twarde zderzaki** (sprężyna + tłumik z `stop_k`, `stop_c` w jednostkach fizycznych; współczynnik
  tłumienia liczony z masy odbitej osi): zdarzenie `CRASH_HARDSTOP` przy nowym kontakcie, prędkość
  uderzenia, opcjonalnie awaria napędu HW_LIMIT (E-4207).
- **Krańcówki i czujniki bazowe**: pozycja, histereza, NC/NO, drgania styku (losowe z ziarnem,
  przez `bounce` sekund), wspólne wejście (NC szeregowo = AND, NO równolegle = OR; mieszanie NC/NO
  na jednym wejściu jest błędem konfiguracji). Zdarzenia `LIMIT_TRIP`, `HOME_SENSOR`.
- **Impuls indeksu** raz na obrót silnika (licznik i położenie zatrzaśnięte), **pętla E-STOP**
  (STO = trwała awaria STO wszystkich napędów, albo quick stop przez bit 6040h), **sonda**
  (prostopadłościan przygotówki albo płytka), **wejścia/wyjścia** 32-bitowe jak w LRT-NET v1.

Konfiguracja przez klucze `nazwa wartość` (`lrt_machine_cfg_set`, lista w nagłówku `machine.h`), więc
wiązanie Pythona nie odwzorowuje struktur C. `make shared` buduje `build/libplant_core.so` dla
`linumert_plant.core_binding` (ctypes). 20 testów w `tests/test_machine.c` (w tym bazowanie, sesja 015).
**NIEZWERYFIKOWANE NA SPRZĘCIE.**

## Parametry w locie (`live.h`, `live.c`) — sesja 013

Wspólne dla osi i napędu (REQ-VD-04): `lrt_axis_set_live()` i odpowiednik napędu zmieniają masę, J, tarcie,
luz, napięcie i limit momentu w trakcie pracy. Zmiany trafiają do dziennika, czyli bufora kołowego o stałym
rozmiarze, bez alokacji i bez I/O, więc można go wołać z pętli czasu rzeczywistego.
