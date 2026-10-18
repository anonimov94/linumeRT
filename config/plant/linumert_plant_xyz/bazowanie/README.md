# Warianty bazowania (metody z sesji 015, `homing.method` w machine.yaml)

Model-Author: Claude · sesja 018. NIEZWERYFIKOWANE NA SPRZĘCIE.

Domyślna konfiguracja `linumert_plant_xyz` używa metody **switch** (krańcówka jako czujnik bazy).
Pozostałe metody = zmiana sekcji `[JOINT_N]` w INI i dołączenie pliku HAL z tego katalogu
(`HALFILE = bazowanie/<plik>.hal` po `linumert_plant.hal`), z usunięciem połączenia
`joint.N.home-sw-in` z pliku głównego dla tej osi.

| Metoda (machine.yaml) | INI `[JOINT_N]` | HAL | Stan |
|---|---|---|---|
| `switch`, `latch: approach` | `HOME_SEARCH_VEL` i `HOME_LATCH_VEL` ten sam znak | `linumert_plant.hal` | test e2e (`tests/test_plant_linuxcnc.py`) |
| `switch`, `latch: release` | `HOME_LATCH_VEL` znak przeciwny (wolny zjazd, baza na zwolnieniu styku) | jw. | jak wyżej, zmiana znaku |
| `switch_index` | `HOME_USE_INDEX = YES` | wymaga `index-enable` | **czeka na ramkę LRT-NET v2** (DECYZJE, sesja 017) |
| `hardstop` | `HOME_SEARCH_VEL`/`HOME_LATCH_VEL` w stronę zderzaka, `HOME_IGNORE_LIMITS = YES`, `FERROR` > próg | `home_hardstop_x.hal` | zredukowany moment 6072h czeka na ramkę v2; detekcja z momentu działa |
| `absolute` | `HOME_ABSOLUTE_ENCODER = 2`, `HOME_SEARCH_VEL = 0`, `HOME_LATCH_VEL = 0` | — | Plant: enkoder absolutny z baterią (plik stanu) |
| `drive` | `HOME_SEARCH_VEL = 0`, `HOME_LATCH_VEL = 0`, `HOME_ABSOLUTE_ENCODER = 2` po bazowaniu w napędzie | `home_drive_x.hal` | `lrt_cia402` tryb 6; start z `halui`/MDI przed „Home” |

Uwaga do `drive`: LinuxCNC 2.9 nie ma wbudowanej sekwencji „bazowanie w napędzie”. Napęd bazuje
w trybie 6 (`lrt-cia402.N.home-start`), ustala 607Ch, a LinuxCNC potem przyjmuje pozycję jak
z enkodera absolutnego (`HOME_ABSOLUTE_ENCODER = 2`). Joint musi być w tym czasie włączony, ale
bez ruchu z LinuxCNC; pozycję śledzi pętla `motor-pos-fb`.
