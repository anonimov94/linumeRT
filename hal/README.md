# hal

Komponenty HAL (.comp), m.in. lrt_net. Dzialaja w czasie rzeczywistym: bez alokacji i blokujacego I/O.

| Komponent | Sesja | Opis |
|---|---|---|
| `lrt_hardstop_home.comp` | 015 | Bazowanie na twardym zderzaku: z momentu (6077h) albo błędu nadążania (`joint.N.f-error`) ≥ `threshold` przez `detect-time` robi czujnik `home-sw` (do `joint.N.home-sw-in`); przy `enable` (= `joint.N.homing`) wystawia `torque-limit-homing` dla 6072h. Test w halrun: `tests/test_hal_comps.py` (marker `linuxcnc`). |

Przykład (INI: `HOME_SEARCH_VEL` i `HOME_LATCH_VEL` w stronę zderzaka, `HOME_IGNORE_LIMITS = YES`,
`FERROR`/`MIN_FERROR` większe niż próg detekcji błędu nadążania):

```
loadrt lrt_hardstop_home count=1
addf lrt-hardstop-home.0 servo-thread
net x-homing   joint.0.homing          => lrt-hardstop-home.0.enable
net x-torque   <moment napędu 6077h>   => lrt-hardstop-home.0.value
net x-home-sw  lrt-hardstop-home.0.home-sw => joint.0.home-sw-in
net x-tlimit   lrt-hardstop-home.0.torque-limit => <6072h napędu>
setp lrt-hardstop-home.0.threshold 180
setp lrt-hardstop-home.0.detect-time 0.02
```
Nazwy pinów napędu (`<...>`) poda komponent `lrt_net` (sesja 017). NIEZWERYFIKOWANE NA SPRZĘCIE.
