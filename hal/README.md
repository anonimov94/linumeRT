# hal

Komponenty HAL (.comp), m.in. lrt_net. Dzialaja w czasie rzeczywistym: bez alokacji i blokujacego I/O.

| Komponent | Sesja | Opis |
|---|---|---|
| `lrt_net.comp` (+ `lrt_net_proto.h`) | 017 | Master LRT-NET v1 (UDP, nieblokująco) do Plant: piny osi CiA 402, I/O, wrzeciono, diagnostyka. Protokół w nagłówku C testowanym bez LinuxCNC (`tests/test_lrt_net_proto.py`). |
| `lrt_cia402.comp` | 017 | Maszyna stanów CiA 402 mastera: włączanie, kasowanie faultu, bazowanie w napędzie (tryb 6), zredukowany moment. |
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
Z Plant: `<moment napędu 6077h>` = `lrt-net.0.axis.N.torque`; `<6072h napędu>` = `lrt-cia402.N.torque-limit` (w LRT-NET v1 bez pola w ramce). Okablowanie `lrt_net`/`lrt_cia402`: `docs/HAL_KONTRAKT.md`. NIEZWERYFIKOWANE NA SPRZĘCIE.

Budowa i test (RIP): `halcompile --compile hal/lrt_net.comp` (nagłówek `lrt_net_proto.h` obok), `pytest -o addopts= -m linuxcnc tests/test_hal_lrt_net.py`.
