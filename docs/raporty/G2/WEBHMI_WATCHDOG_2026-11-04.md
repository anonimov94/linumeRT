# G2 — watchdog HAL i podwójny Reset w WebHMI

Model-Author: Claude · 2026-11-04. Gałąź `claude/webhmi-hal-watchdog` (od `claude/g2-webhmi`).
NIEZWERYFIKOWANE NA SPRZĘCIE.

Prawdziwy LinuxCNC 2.9 (RIP) i Plant w WSL `linumeRT-Debian12`, maszyna
`config/machines/mill_servo_table.yaml`, konfiguracja wygenerowana przez `configgen`,
**łańcuch HMI bez obejścia** (`HMI_ESTOP_BYPASS = 0`, `HMI_HEARTBEAT_TIMEOUT = 2.0`).
Brama z pinami HAL (`open_hal`) i `halcmd -f config/hal/linumert_webhmi_postgui.hal`,
przeglądarka w aplikacji Claude (Windows) pod `http://127.0.0.1:8765/`.

## Kroki w przeglądarce

| Krok | Działanie w GUI | Wynik | Zrzut |
|---|---|---|---|
| 1 | Połączenie tokenem | `ESTOP`, alarm E-1100, podpowiedź „Dwa razy szybko: potwierdzenie E-STOP”, Zasilanie ON zablokowane: „Najpierw podwójny Reset” | [1](WEBHMI_WATCHDOG_2026-11-04/1_start_estop.jpg) |
| 2 | Reset, Reset (podwójny) | `ESTOP_RESET`, Zasilanie ON odblokowane | — |
| 3 | Zasilanie ON | `ON`, po 5 s nadal `ON` (karta wysyła `{"alive":1}` co 250 ms) | [2](WEBHMI_WATCHDOG_2026-11-04/2_podwojny_reset_on.jpg) |
| 4 | Zawieszona karta (wstrzymane `alive`, gniazdo otwarte) | `ESTOP` po **3,10 s**, alarm E-1100 | [3](WEBHMI_WATCHDOG_2026-11-04/3_cicha_karta_estop.jpg) |

## Co wykrył odbiór w GUI (testy logiki tego nie widziały)

1. **Klient nie wysyłał sygnału życia.** `heartbeat` gasł 1 s po ostatnim poleceniu, więc z `--hal`
   maszyna wracała do E-STOP chwilę po podwójnym Resecie. Pierwszy test na LinuxCNC wołał `touch`
   wprost i przechodził. Poprawka: `{"alive":1}` co 250 ms; test idzie teraz przez WebSocket
   aplikacji.
2. **Stary JS z pamięci podręcznej.** Po aktualizacji bramy przeglądarka wczytała poprzedni
   `connection.js` (bez `alive`) mimo przeładowania. Poprawka: `Cache-Control: no-cache`.
3. **E-1100 zostawał po `ESTOP_RESET`** do kolejnego Resetu. Poprawka: Reset alarmów 0,7 s po
   potwierdzeniu, jak ekran Qt.

## Test automatyczny

`tests/test_webhmi_watchdog_linuxcnc.py` (`@pytest.mark.linuxcnc`, ~20 s), te same kroki przez
WebSocket aplikacji: start w E-STOP; pojedynczy Reset nie zwalnia; podwójny Reset → `ESTOP_RESET`
→ `ON`; cicha karta → E-STOP po 3,11 s; `STATE_ESTOP_RESET` z innego procesu bez potwierdzenia
→ nadal E-STOP; ponowne potwierdzenie → `ON`; zatrzymana brama → E-STOP po 2,01 s.
Bez LinuxCNC: `tests/test_webhmi_hal_link.py`, `tests/test_webhmi_app.py`.

## Otwarte

- Ukryta karta: przeglądarka dławi zegary, więc watchdog może otworzyć E-STOP (fail-safe).
  Do decyzji, czy to pożądane (PROPOZYCJA w `docs/DECYZJE.md`).
- Uruchomienie bramy z `--hal` z `[DISPLAY]` konfiguracji (dziś ręcznie albo w teście).
