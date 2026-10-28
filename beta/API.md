# API — jak zbudować GUI na tym interfejsie

SPDX-License-Identifier: GPL-2.0-or-later

Ten dokument jest przepisem: co pobrać, co wygenerować, jak narysować przycisk i jak
odebrać stan. Wszystkie liczby i nazwy są zweryfikowane na działającym kodzie.

**Zasada: GUI nie zna Pythona, LinuxCNC ani backendu.** Zna kontrakt JSON i cztery
transporty. Zmiana backendu (atrapa → LinuxCNC → Plant) nie wymaga zmian w GUI.

---

## 1. Pobierz kontrakt

```bash
curl -H "X-LRT-Token: $TOKEN" http://127.0.0.1:8080/api/v1/contract > contract.json
# albo lokalnie, bez serwera:
linumertd contract --out api/contract.json
```

Kontrakt to lista operacji. Każda ma:

```jsonc
{
  "name": "machine.jog",            // nazwa polecenia (REST/WS/CLI)
  "domain": "machine",              // grupa w menu
  "kind": "command",                // command | query
  "status": "implemented",          // implemented | planned
  "safety": "motion",               // none | config | stop | motion
  "role": "operator",               // operator | technolog | serwis
  "idempotent": false,              // czy ponowienie po zerwaniu jest bezpieczne
  "summary": "Jog ciągły osi",
  "request": { /* JSON Schema */ }, // → formularz i walidacja
  "result":  { /* JSON Schema */ }  // → typ odpowiedzi
}
```

**Stan: 85 operacji, 12 domen** — `access, alarm, cam, config, diag, machine, offset,
plant, program, sim, system, tool`. **85 `implemented`, 0 `planned`**
(ostatnie dwie: `machine.tool_change`, `offset.probe_run`). Rozkład `safety`: `none` 60, `motion` 12,
`stop` 7, `config` 6.

### Co z tym zrobić w GUI

| Pole | Decyzja w interfejsie |
| --- | --- |
| `domain` | zakładka / sekcja panelu |
| `kind == "query"` | można odświeżać dowolnie często, bez potwierdzenia |
| `kind == "command"` | przycisk; `safety != none` → potwierdzenie albo przytrzymanie |
| `status == "planned"` | przycisk widoczny, ale wyszarzony z tooltipem z `plan` |
| `role` | aktywność przycisku wg zalogowanej roli |
| `request` | formularz (generowany z JSON Schema) |
| `idempotent` | czy wolno ponowić po zerwanym połączeniu |

---

## 2. Autoryzacja

```
X-LRT-Token: <token>          # albo: Authorization: Bearer <token>
```

- Token jest wymagany do **każdej** operacji.
- `GET /api/v1/health` i `GET /api/v1/info` są **otwarte** (health-check dla orkiestracji).
- Nasłuch poza `127.0.0.1` bez tokenu jest odmawiany — brak domyślnych poświadczeń.
- WebSocket: token w query (`/ws?token=…`); brak tokena → zamknięcie kodem **4401**.

Role: `operator` < `technolog` < `serwis`. Reset E-STOP wymaga `serwis`.

---

## 3. REST

| Metoda i ścieżka | Przeznaczenie |
| --- | --- |
| `GET /api/v1/health` | zdrowie backendu (otwarte, bez tokenu) |
| `GET /api/v1/info` | wersja, backend, `gui: false`, `opengl: false` (otwarte) |
| `GET /api/v1/contract` | pełny kontrakt ze schematami — podstawa codegen |
| `GET /api/v1/operations` | skrócona lista (bez schematów) — szybki przegląd |
| `GET /api/v1/state` | pełna migawka stanu (tematy + wersje) |
| `POST /api/v1/call` | **wywołanie dowolnej operacji** |

Wywołanie:

```bash
curl -H "X-LRT-Token: $TOKEN" -H "Content-Type: application/json" \
     -d '{"command":"machine.jog","params":{"axis":"X","speed":10}}' \
     http://127.0.0.1:8080/api/v1/call
```

Sukces:

```json
{"ok": true, "id": 0, "result": {"ok": true, "message": "…", "details": {}}}
```

Błąd — zawsze ten sam kształt, niezależnie od transportu:

```json
{"ok": false, "error": {"code": "safety_refused", "message": "…", "details": {}}}
```

### Kody błędów → reakcja GUI

| `code` | HTTP | Co powinno zrobić GUI |
| --- | --- | --- |
| `invalid_request` | 400 | podświetlić pola z `details.errors` |
| `permission_denied` | 403 | komunikat o roli / prośba o logowanie |
| `not_found` | 404 | odświeżyć kontrakt (operacja zniknęła albo literówka) |
| `conflict` | 409 | stan maszyny nie pozwala — odświeżyć migawkę |
| `safety_refused` | 422 | **nie ponawiać**; pokazać przyczynę (E-STOP, brak bazy, zakres) |
| `rate_limited` | 429 | zwolnić; polecenia `stop` nigdy nie są limitowane |
| `not_implemented` | 501 | operacja `planned` — pokazać `details.plan` |
| `backend_unavailable` | 503 | backend nie odpowiada — pasek stanu + ponowienie |
| `internal` | 500 | zgłosić błąd, zebrać `details` do logu |

---

## 4. WebSocket — stan na żywo

```
ws://127.0.0.1:8080/ws?token=…
```

### Serwer → klient

Na dzień dobry pełna migawka:

```json
{"type":"hello","session":"s1","schema":1,"version":3191,
 "topics":{"machine":{…},"alarms":{…}}}
```

Potem zmiany (20 Hz, sklejane w oknach):

```json
{"type":"state","version":3192,"topics":{"machine":{…}}}
```

Odpowiedzi na polecenia: `{"id":…,"ok":…,"result":…}` albo `{"id":…,"ok":false,"error":…}`.

### Klient → serwer

| Wiadomość | Działanie |
| --- | --- |
| `{"id":1,"command":"machine.jog","params":{…}}` | wywołanie operacji |
| `{"id":2,"method":"state.get"}` | pełna migawka (odświeżenie po luce) |
| `{"type":"hello","topics":["machine","alarms"]}` | wybór tematów — mniej ruchu w sieci |
| `{"type":"ping"}` | podtrzymanie sesji → `{"type":"pong"}` |

Tematy: `machine`, `alarms`, `plant`, `health`. Nieznany temat → `invalid_request`
z listą znanych w `details.known`.

### Trzy rzeczy, które musi robić każde GUI

1. **Deadman jogu** — jog jest trzymany, nie przełączany. Wysyłaj `machine.jog`
   co ~100–150 ms, dopóki przycisk jest wciśnięty (`JOG_HOLD_S = 0.4`). Po puszczeniu
   wyślij `machine.jog_stop`. Zerwanie połączenia też zatrzymuje oś.
2. **`ping` co ~1 s** (`HEARTBEAT_S = 1.0`) — inaczej sesja wygaśnie i jog stanie.
3. **Luka w `version`** → zgubiona wiadomość → pobierz `state.get`. Nie zgaduj stanu.

Wiadomość bez `command` (i nie będąca `ping`/`hello`/`state.get`) dostaje
`invalid_request` z opisem oczekiwanych pól — nie `not_found`.

---

## 5. SDK Python

```python
from linumert_headless.sdk import Client, RemoteError

client = Client("http://127.0.0.1:8080", token="…")

client.health()                      # {"ok": true, "backend": "fake", …}
client.info()                        # {"gui": false, "opengl": false, …}
client.machine.state()               # migawka maszyny
client.machine.estop_reset()         # polecenie
client.program.list()                # lista programów

for change in client.subscribe(topics=("machine", "alarms")):
    render(change["topics"])         # push stanu
```

Metody domen i akcji są **generowane z kontraktu** — nowa operacja pojawia się w SDK
bez zmian w kodzie klienta. `client.operations()` zwraca kontrakt,
`client.call("dowolna.operacja", **params)` wywołuje po nazwie.

Błędy: `RemoteError(code, message, details)` — ten sam `code` co w REST/WS.
Każda odpowiedź z błędem jest wyjątkiem, więc GUI nie musi sprawdzać `ok` po każdym
zapytaniu. Brak połączenia: `ApiClientError`.

---

## 6. CLI

```bash
linumertctl machine.state
linumertctl program.list
linumertctl machine.jog axis=X speed=10
linumertctl operations --json
linumertctl contract --out api/contract.json
linumertctl --url http://maszyna:8080 --token "$TOKEN" machine.state
```

Podpolecenia są generowane z kontraktu — każda operacja jest dostępna bez zmian w CLI.
Parametry: `nazwa=wartość` (JSON dla złożonych). Kody wyjścia: `0` OK, `1` błąd operacji,
`2` błąd użycia.

Serwer: `linumertd serve --backend fake|linuxcnc --host … --port … [--token …]`.

---

## 7. Przepływy, które GUI musi obsłużyć

### Start maszyny (kolejność jest wymuszona)

```
machine.estop_reset      → task_state: estop → estop_reset   (rola: serwis)
machine.power_on         → estop_reset → off
machine.home             → bazowanie jest RUCHEM: all_homed pojawi się po czasie
machine.set_mode mode=auto
machine.run              → program
```

`machine.home` zwraca `ok` od razu, ale `all_homed` staje się `true` dopiero, gdy ruch
się zakończy — GUI musi czytać stan z pusha, nie zakładać wyniku po odpowiedzi.

### Zatrzymanie

`machine.stop` (ruch), `machine.pause` / `machine.resume` (program), `machine.estop`
(natychmiast). Polecenia `stop`/`estop` są **wyłączone z limitera** — przejdą zawsze.

### E-STOP — najważniejsza zasada

Nie ma operacji zwalniającej E-STOP. `machine.estop_release` → `not_found`.
Zwolnienie to jawne `machine.estop_reset` z rolą serwisową, nigdy automatyczne (D35/D37).
GUI nie może rysować „auto-reset” ani zwalniać E-STOP przy starcie.

### Jog przyrostowy

`machine.jog_increment axis=X speed=10 distance=2` — oś stanie dokładnie na zadanym
dystansie. Jog należy do sesji: inne połączenie go nie zatrzyma, ale zerwanie własnego — tak.

### Zmiana narzędzia i sondowanie (makra ruchu)

Obie operacje wymagają `confirm=true` (potwierdzenie operatora w GUI), zasilania,
zbazowanych osi i maszyny bez ruchu; tryb MDI usługa ustawia sama.

- `machine.tool_change tool=3 confirm=true` → MDI `T3 M6`. Sekwencję wykonuje remap M6
  konfiguracji (`lrt_m6` / `lrt_m6_atc`, z G43 H<n>). Narzędzie musi być w bazie
  (`not_found`), wrzeciono stać (`safety_refused`); ten sam numer = nic się nie dzieje.
- `offset.probe_run axis=Z direction=-1 distance=10 offset=G54 value=0 confirm=true`
  (rola technolog) → jedno MDI `o<lrt_probe> call [...]`: G38.2, zapis offsetu G10 L20
  w punkcie styku, odjazd `retract`. Wartość uwzględnia poprawkę z `offset.probe_calibrate`;
  inny posuw niż posuw kalibracji → `invalid_request`. Makro: `macros/lrt_probe.ngc`
  (generator konfiguracji je dokłada). Atrapa nie wykonuje G38.x → `conflict`.
  Wynik pomiaru GUI widzi w `machine.state` (`work_offset`) po zakończeniu ruchu.

---

## 8. Wiarygodność wyniku — GUI musi ją pokazywać

Cztery operacje liczą na interpreterze G-code. Z modułem `gcode` LinuxCNC jest to pełny
`rs274`; bez niego działa interpreter podzbioru (`subset`), który **pomija pętle `o-word`
i ruchy `G53`**. Wynik jest wtedy prawdziwy, ale niepełny — i nie da się tego zgadnąć
z samych liczb.

Przykład z `config/nc_files/linumert_demo.ngc`: całe skrawanie siedzi w pętlach
`o100`/`o110`, więc bez LinuxCNC `sim.run` daje `volume_removed_mm3: 0.0` przy
116 odcinkach i 3077 mm drogi. Zero wygląda na „program nic nie obrabia”, a znaczy
„interpreter nie wszedł w pętle”.

| Operacja | Pole wiarygodności | Co zrobić w GUI |
| --- | --- | --- |
| `sim.run` | `source`, `notes` | przy `source: "subset"` oznacz wynik jako przybliżony i pokaż `notes` |
| `program.toolpath` | `source`, `notes` | jw. — podgląd ścieżki może nie mieć pętli |
| `program.estimate` | `source` | przy `subset` czas i droga bez pętli |
| `program.check` | `interpreter` | jw. — granice osi policzone z dostępnych ruchów |

`notes` to lista czytelnych komunikatów po polsku (`"Linia 30: o-word while pominięte
(tylko interpreter LinuxCNC)."`). Nie chowaj ich — to jedyne miejsce, gdzie użytkownik
dowie się, dlaczego liczby są mniejsze niż oczekuje.

---

## 9. Czego jeszcze nie ma

Wszystkie operacje kontraktu są `implemented`. Mechanizm `planned` zostaje dla przyszłych
funkcji: rysuj je normalnie, a `not_implemented` obsługuj jako „funkcja w planie”,
nie jako błąd aplikacji.

Wszystko, co dotyczy fizycznej maszyny, jest **NIEZWERYFIKOWANE NA SPRZĘCIE** —
testy idą na atrapie (`backend=fake`).
