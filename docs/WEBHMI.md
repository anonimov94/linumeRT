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
| `WS /ws` | pierwsza wiadomość `{"auth": "<token>"}`; potem serwer wysyła `{"type":"state","version","state"}` (≤ 30 Hz, keepalive 0,2 s); klient wysyła `{"id","cmd",...}` → `ack` / `error` |

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

## Strona — Cyberdeck PoC

Model-Author: ChatGPT. Klient operatora bez bibliotek i CDN znajduje się w
`webhmi/server/linumert_webhmi/static/` (`index.html`, `app.js`, `style.css`).
Brama serwuje stronę pod `/`, gdy katalog statyczny istnieje. Otwórz adres
bramy w przeglądarce i wpisz token wypisany przy starcie. Token jest utrzymywany
wyłącznie w pamięci bieżącej strony (nigdy w URL). WebSocket `/ws` najpierw
otrzymuje `{"auth":"…"}`; klient wymaga `state.schema == 1`, zgodnie z
`schema.py`, i przetwarza `ack` / `error` według identyfikatora polecenia.

Widok pokazuje DRO, stan, override, wrzeciono, narzędzie i błędy; umożliwia
polecenia operatorskie i przytrzymywany jog ± (odświeżany co 150 ms, stop
po zwolnieniu, utracie fokusu i ukryciu karty). Prosta scena WebGL 1 pokazuje
siatkę XY i marker XYZ, z limitem 30 FPS. To wizualizacja demonstracyjna,
nie symulacja kolizji, kinematyki ani weryfikator ścieżki. Testy:
`python -m pytest tests/test_webhmi_static.py`.

Model-Author: Codex · 2026-10-27. Pliki strony są dołączane również do paczki wheel.
CI buduje paczkę i sprawdza ją poza checkoutem: odpowiedzi HTTP dla trzech zasobów,
uwierzytelnienie WebSocket, jog atrapy i zatrzymanie po rozłączeniu. Uruchomienie:

```bash
python -m pip wheel --no-deps . --wheel-dir dist
python tools/ci/check_webhmi_wheel.py dist/linumert-*.whl
```

Kontrola używa zależności testowych z `.[dev]`; nie uruchamia LinuxCNC ani przeglądarki.

**Bezpieczeństwo:** E-STOP z przeglądarki jest wyłącznie poleceniem programowym,
a jog deadman klienta nie jest funkcją bezpieczeństwa. Przed podłączeniem
rzeczywistej maszyny wymagany jest sprzętowy E-STOP oraz niezależny watchdog HAL
powiązany z bramą. Funkcji resetu E-STOP w tym interfejsie nie ma.


## Sterowanie — hardening etap 1 (Model-Author: ChatGPT)

Zmiany bez przebudowy skórki. `static/app.js` to punkt wejścia ES Modules,
a logika jest w `static/js/{main,connection,interlocks,jog,dro,scene}.js`.
Żadnych CDN ani pakietów npm. `js/interlocks.js` eksportuje czystą
`allowed(state, link)`, używaną do blokad przycisków i JOG; odmowy pokazują
opis tekstowy oraz `title`. Nie jest to zabezpieczenie sprzętowe: brama
weryfikuje polecenia niezależnie. Wartości enumów pochodzą z
`core/linumert/cnc/model.py`:
`task_state=estop/estop_reset/off/on`, `mode=manual/mdi/auto`,
`interp_state=idle/reading/paused/waiting`.

**Reguły:** `power_on` przy `off`/`estop_reset`; `home` i `jog`
w `on+manual+idle`; `mdi` w `on+mdi+idle`; `run`
w `on+auto+idle` ze zbazowanymi osiami i wybranym programem;
`pause` przy `reading/waiting`; `resume` przy `paused`.
`stop` i `estop` pozostają dostępne przy uwierzytelnionym
WebSocket nawet gdy stan jest nieaktualny.

**Świeżość:** po 500 ms bez pakietu `state` DRO ma etykietę
„NIEAKTUALNE”, zwykłe komendy są blokowane, aktywny JOG jest zatrzymywany.
Po ponad 2 s bez stanu panel zrywa WS i wymaga ręcznego ponownego połączenia.
**Keepalive:** brama wypycha zmiany do 30 Hz, a przy niezmienionym stanie
wysyła pakiet co 0,2 s (`KEEPALIVE_S = 0.2`). Próg świeżości klienta to
500 ms (`FRESH_MS = 500`), a utraty łączności 2000 ms (`LOST_MS = 2000`).
Przy dużym opóźnieniu lub zawieszeniu bramy dane nadal mogą stać się
nieaktualne — wtedy sterowanie ruchem jest blokowane.

**JOG:** odświeżany co 150 ms; `jog_stop` po pointerup/cancel,
utracie capture/fokusu, ukryciu karty, utracie łączności lub przeterminowanym
stanie. Status „BEZ RUCHU” dopiero po `ack` zatrzymania (oraz bez
`jog_stop_pending` w bieżącym stanie). Błąd stopu oznacza wyraźny alarm;
przycisk STOP pozwala ponowić `jog_stop`, bez automatycznego startu ruchu.
Suwak ma `mm/s` dla X/Y/Z/U/V/W i `deg/s` dla A/B/C; prędkości
wynikają z kontraktu bramy, która nadal ogranicza je do 50.
**Brak autowznowienia poleceń** po ponownym połączeniu. Token pozostaje
w pamięci tej karty, nie w URL i nie w sessionStorage/localStorage.

Testy lokalne: `node --test tests/webhmi_js/test_interlocks.mjs` oraz
`python -m pytest tests/test_webhmi_static.py` (uruchamia node:test,
jeśli Node.js jest dostępny). Przed obsługą maszyny realnej nadal wymagane
sprzętowy E-STOP, watchdog HAL i niezależne testy ruchu/failure-injection.
Etap 2 (dziennik i eksport diagnostyki) jest odłożony do osobnego PR.

## Diagnostyka — etap 2 (Model-Author: ChatGPT)

Panel diagnostyki w istniejącym wyglądzie WebHMI zawiera:
- `static/js/events.js` — czystą funkcję `diffState(prev, next)` zwracającą zdarzenia
  `{level, source, text}`: zmiany zasilania/E-STOP, trybu, interpretera,
  bazowania, krańcówek osi, numeru narzędzia, programu, błędów bramy
  i `jog_stop_pending`.
- `static/js/log.js` — wyłącznie **ulotny bufor pierścieniowy 500 zdarzeń**
  z lokalnym czasem `HH:MM:SS.mmm`, filtrem Wszystkie/Ostrzeżenia i alarmy/Tylko alarmy,
  czyszczeniem i eksportem TXT. Przy przewinięciu dziennika w górę nowe zdarzenia
  nie wymuszają przewijania do dołu. Eksport obejmuje bufor niezależnie od filtra.
  Dziennik nie przechowuje tokenu ani treści wysyłanych poleceń MDI.
- Lampki ŁĄCZE, E-STOP, ZASILANIE, BAZOWANIE, KRAŃCÓWKI, JOG, BŁĘDY
  z **kolorem i jednoznacznym tekstem**. Przy utracie świeżości maszyna
  otrzymuje oznaczenie NIEAKTUALNE zamiast domniemanego stanu bezpiecznego.
- DRO: kolumna `FERR` (`following_error`) z czterema miejscami po przecinku,
  progiem ostrzeżenia `|FERR| > 0.05 mm` na osiach liniowych X/Y/Z/U/V/W
  (znacznik `!` i podświetlenie). Osie A/B/C pokazują stopnie — próg w mm
  nie jest stosowany do wartości kątowych. Aktualny schemat przekazuje FERR
  w jednostkach natywnych maszyny: próg 0,05 mm jest prawidłowy dla maszyn
  liniowych skonfigurowanych w milimetrach; dla konfiguracji calowej konieczne
  będzie udostępnienie skali w schemacie i przeliczenie po stronie klienta.
- Liczniki pakietów `state` odebranych w ostatniej sekundzie, wieku
  ostatniej migawki oraz czasu RTT ostatniego `ack` (w milisekundach).
  Pomiar RTT obejmuje WebSocket i obsługę polecenia przez bramę, a nie
  rzeczywiste zakończenie ruchu CNC.

**Semantyka `errors`:** `LinuxCNCReader._drain_errors()` odczytuje i opróżnia
`linuxcnc.error_channel` przy każdej migawce; `FakeMachine` może udostępniać
listę narastającą. `diffState` porównuje liczności identycznych wpisów pomiędzy
kolejnymi migawkami: bez duplikowania keepalive/narastających komunikatów,
ale ponowne wystąpienie po zniknięciu traktuje jako nowe zdarzenie. Bieżąca
lampka BŁĘDY odzwierciedla wyłącznie ostatnią migawkę, natomiast wcześniejsze
błędy pozostają w dzienniku do wyparcia lub ręcznego wyczyszczenia.

Testy: `node --test tests/webhmi_js/test_events.mjs`, istniejące testy
`node:test` interlocks oraz `python -m pytest tests/test_webhmi_static.py`
(HTTP 200 wszystkich modułów, brak CDN, nagłówki SPDX, sprawdzenie selektorów,
statyczny kontrakt FERR, `node --check` gdy dostępny Node.js).

Pakiet wheel dołącza `static/js/*.js` i `static/js/*.json` w `pyproject.toml`,
aby strona z importami ES działała również poza repozytorium.

Nie modyfikowano bramy Python, HAL ani interfejsu poleceń. Etap 2 nie
dodaje funkcji bezpieczeństwa; do maszyny realnej nadal niezbędny jest
niezależny watchdog HAL oraz sprzętowy E-STOP.
