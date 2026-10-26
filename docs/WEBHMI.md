# Brama web-hmi (LinuxCNC ↔ przeglądarka)

Model-Author: Claude · 2026-10-26. Wynik decyzji „Ekran operatora w HTML/WebGL obok QtDragon”
(`docs/DECYZJE.md`). Backend; strona z WebGL (DRO, skórki) to następny krok (PoC `web-hmi-poc`).

## Uruchomienie
```bash
pip install -e '.[dev]'
python -m linumert_webhmi --fake          # atrapa maszyny, bez LinuxCNC
python -m linumert_webhmi --linuxcnc      # działający LinuxCNC (RIP), moduł `linuxcnc`
```
Adres domyślny `127.0.0.1:8765`. Token wypisywany przy starcie (albo `--token` /
`LINUMERT_WEBHMI_TOKEN`, min. 16 znaków). Adres inny niż loopback tylko z `--allow-remote`.

## Układ i kontrakt
- Pakiet `linumert_webhmi` w `webhmi/server/linumert_webhmi/`, proces osobny, poza RT.
- `backend.py`: `FakeBackend` (atrapa `linumert.cnc.FakeMachine`) i `LinuxCNCBackend`
  (`linuxcnc.command` + `LinuxCNCReader`; moduł wstrzykiwany do testów).
- `gateway.py`: wątek odpytujący 50 Hz, deadman jogu, limit poleceń, licznik klientów.
- `schema.py`: stan JSON (`SCHEMA_VERSION` = 1) i polecenia (walidacja pydantic).
- `app.py`: REST + WebSocket.

## API
| Wejście | Opis |
|---|---|
| `GET /api/health` | bez tokenu: `ok`, `schema`, `task_state` |
| `GET /api/state` | nagłówek `X-Linumert-Token`; `{version, state}` |
| `POST /api/command` | nagłówek tokenu; ciało `Command` (poniżej); 409 przy odmowie maszyny, 422 przy złym ciele |
| `WS /ws` | pierwsza wiadomość `{"auth": "<token>"}`; potem serwer wysyła `{"type":"state","version","state"}` (≤ 30 Hz, keepalive 1 s); klient wysyła `{"id","cmd",...}` → `ack` / `error` |

Polecenia (`cmd`): `estop`, `power_on`, `power_off`, `mode` (`mode`: manual/mdi/auto), `home`
(`axis` opcjonalnie), `mdi` (`text` ≤ 200 znaków, jedna linia), `run` (`from_line`), `pause`,
`resume`, `stop`, `override` (`feed` 0–2, `rapid` 0–1, `spindle` 0–2), `jog` (`axis`, `speed` mm/s
ze znakiem, ≤ 50), `jog_stop`.

## Bezpieczeństwo (CLAUDE.md §6)
Ekran nie jest funkcją bezpieczeństwa; E-STOP to obwód sprzętowy.
- **Brak resetu E-STOP w bramie.** `estop` tylko odbiera zezwolenie; `power_on` działa dopiero po
  resecie wykonanym poza bramą (zatrzask HAL, D35/D37).
- **Deadman jogu (programowy, NIE funkcja bezpieczeństwa):** jog trwa 0,4 s od ostatniego odświeżenia
  i należy do jednej sesji WebSocket (inna sesja go nie odświeży ani nie przejmie). Stop po
  wygaśnięciu, po rozłączeniu sesji właściciela, po `estop`/`stop`/`power_off`/zmianie trybu i po
  błędzie odczytu stanu; nieudany stop jest ponawiany w każdym obiegu (50 Hz). Wygaszanie idzie
  przed odczytem stanu. **Gdy proces bramy padnie albo zawiesi się backend, ciągły jog w LinuxCNC trwa
  dalej** — przed sprzętem wymagane jest wiązanie z `watchdog` HAL (E-STOP po utracie bramy).
- **Token** w nagłówku (REST) lub pierwszej wiadomości (WS), nigdy w URL; porównanie w stałym czasie,
  typ sprawdzany. Token wypisywany jest na stdout przy starcie (uwaga na logi usługi; `--token`/zmienna
  środowiskowa pozwalają go podać z zewnątrz).
- **Host i Origin** tylko loopback (parser URL; odrzucane: obcy host, `null`, userinfo, ścieżka, zły
  port, inny schemat); brak Origin dozwolony (klient nieprzeglądarkowy, token i tak wymagany); brak CORS.
- **Limity:** ramka WS ≤ 8 KiB (uvicorn i aplikacja), 60 poleceń/s (zatrzymania `estop`, `stop`, `pause`,
  `jog_stop`, `power_off`, jog z prędkością 0 poza limitem), 4 klienci WS, 8 połączeń czekających na
  uwierzytelnienie (3 s), walidacja pól (jog ≤ 50 mm/s).
- `LinuxCNCBackend`: nie czyta stanu podczas poleceń (odczyt opróżnia kanał błędów LinuxCNC); jog
  **przegubu** (`jjogmode=True`, `teleop_enable(0)`) przy założeniu kinematyki tożsamościowej jak w
  czytniku; prędkość liniowa API w mm/s jest przeliczana przez `stat.linear_units` na
  jednostki maszyny/s (`command.jog` nie przyjmuje jednostek/min). Osie ABC używają stopni/s.
  Brak poprawnej skali blokuje jog liniowy. `wait_complete` -1 (timeout) i `RCS_ERROR`
  zgłaszane operatorowi. Maszyny z innym
  układem przegubów (np. gantry z dwoma przegubami na oś) wymagają jawnego mapowania — jeszcze nie ma.
Sygnał życia do `watchdog` HAL (D35, `linumert.hmi-wd-enable`) **nie jest jeszcze podpięty**:
brama wystawia `heartbeat` w stanie, wiązanie z HAL to następny krok.

## Testy
```bash
python -m pytest tests/test_webhmi_gateway.py tests/test_webhmi_app.py tests/test_webhmi_linuxcnc_backend.py
```
Bez LinuxCNC (atrapa i sztuczny moduł `linuxcnc`). Mapowanie `LinuxCNCBackend` na prawdziwy LinuxCNC 2.9 i
sprzęt: NIEZWERYFIKOWANE (marker `linuxcnc` do dodania w PoC). NIEZWERYFIKOWANE NA SPRZĘCIE.

## Poza zakresem (następne kroki)
Strona kliencka (DRO, scena WebGL, skórki cyberdeck/sci-fi), podpięcie `watchdog` HAL, `jog_incr`,
wczytywanie programów, alarmy z katalogu, kiosk Chromium.
