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

Nie ma jeszcze: hamulca, napędu CiA 402 (sesja 012), kinematyki wielu osi (014), bazowania (015).
Model sprawdzony wyłącznie wzorami analitycznymi: **NIEZWERYFIKOWANE NA SPRZĘCIE**.

## Testy

`tests/lrt_test.h` to minimalny framework (wynik w stylu TAP). 23 testy w `tests/test_axis.c`
porównują wyniki z rozwiązaniami analitycznymi (tolerancja ≤ 1 %): przyspieszenie stałym momentem,
F = m·a, wpływ masy, bezwładność odbita (liniowa i obrotowa), krzywa momentu, tarcie lepkie
(wykładnicze), Coulomba i statyczne (odrywanie, czas wybiegu), grawitacja, luz (droga przy zmianie
kierunku), zderzaki sztywne i sprężyste (maks. penetracja z bilansu energii), niezależność od
kroku, walidacja parametrów. `tests/test_plant_core.py` uruchamia je z pytest i pilnuje braku
`malloc`/I/O w rdzeniu.
