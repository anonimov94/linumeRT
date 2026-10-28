# Architektura linumeRT headless (beta)

SPDX-License-Identifier: GPL-2.0-or-later

Zasada nadrzędna: **logika sterowania nie wie, że istnieje GUI**. GUI jest klientem
kontraktu — tak samo jak CLI, skrypt serwisowy albo test. Dlatego GUI można dołożyć
na końcu projektu, bez refaktoryzacji.

## Warstwy

```
transport (REST · WebSocket · CLI · SDK)      ← cienkie, bez logiki domenowej
        │  wywołuje operacje po nazwie
kontrakt (rejestr operacji + walidacja + role)
        │  handler(request, ctx)
usługi domen (machine · program · tool · offset · sim · plant · config · alarm · diag · access)
        │  mówią do portów, nie do LinuxCNC/Plant/plików
porty (MachinePort · Clock · EventSink · PathResolver)
        │
backendy: atrapa (domyślnie) · LinuxCNC · Plant LRT-NET
```

Każda warstwa zna tylko tę pod sobą. Usługa `MachineService` nie wie, czy pod spodem
jest atrapa, LinuxCNC czy Plant — widzi `MachinePort`. Test podłącza atrapę i sprawdza
logikę bez sprzętu.

## Kontrakt — jedno źródło prawdy

`linumert_headless/contract.py` rejestruje operacje jako obiekty `Operation`:

| Pole | Znaczenie dla GUI |
| --- | --- |
| `name` | `domena.akcja`, np. `machine.jog` — nazwa polecenia w REST/WS/CLI |
| `domain` | grupa w menu/panelu (`machine`, `program`, `tool`, …) |
| `kind` | `command` (zmienia stan) albo `query` (tylko czyta) — query można odświeżać swobodnie |
| `status` | `implemented` albo `planned` — `planned` da się narysować, ale zwróci `not_implemented` |
| `safety` | `none` · `config` · `stop` · `motion` — ile potwierdzenia wymaga przycisk |
| `role` | `operator` < `technolog` < `serwis` — czy przycisk ma być aktywny |
| `request` / `result` | schematy pydantic → JSON Schema — formularz i walidacja bez ręcznego kodu |
| `idempotent` | czy ponowienie po zerwanym połączeniu jest bezpieczne |
| `plan` | dla `planned`: czego brakuje do wdrożenia |

Invariant sprawdzany testem: `operation.domain == name.split(".")[0]`.

**Stan zweryfikowany: 73 operacje, 12 domen** (`access, alarm, cam, config, diag,
machine, offset, plant, program, sim, system, tool`); **71 `implemented`, 2 `planned`**
(`machine.tool_change`, `offset.probe_run`). Rozkład `safety`: `none` 49, `motion` 12,
`stop` 7, `config` 5. Role: `operator`, `technolog`, `serwis`.

Dodanie funkcji = jedna rejestracja w kontrakcie + handler. REST, WebSocket, CLI i SDK
dostają ją automatycznie (CLI i SDK są generowane z kontraktu w locie).

## Stan: pull + push

- **Magazyn stanu** (`state.py`, `StateHub`): tematy `machine`, `alarms`, `plant`,
  `health`; globalny `version` rośnie przy każdej zmianie; `changes_since(version)`
  pozwala odświeżyć przyrostowo.
- **Pętla odpytywania** (`app.py`): `POLL_HZ = 50.0` — czyta backend i publikuje tematy.
- **Push do GUI**: WebSocket 20 Hz (`STATE_PUSH_HZ`), zmiany z jednego okna są sklejane,
  żeby nie zasypywać klienta pakietami.
- **Deduplikacja**: `StateHub.publish` pomija powiadomienie, gdy payload się nie zmienił.
  GUI nie dostaje sztucznego ruchu, ale musi liczyć się z tym, że „brak wiadomości”
  znaczy „bez zmian”.
- **Luka w `version`** = zgubiona wiadomość → klient pobiera pełną migawkę (`state.get`).

### Zegar i świeżość danych

Migawka niesie `fresh` i `age_s`. Atrapa stempluje migawki **czasem symulowanym**
(`FakeMachine.time`), LinuxCNC — systemowym. Dlatego wiek liczy `MachinePort.now()`
(zegar backendu), nie `time.monotonic()`: inaczej na atrapie każda migawka byłaby
trwale „nieświeża” (wiek = uptime hosta), a GUI pokazywałby fałszywy alarm.

## Bezpieczeństwo w warstwie usługi

| Mechanizm | Parametr | Zachowanie |
| --- | --- | --- |
| Deadman jogu | `JOG_HOLD_S = 0.4` | klient odświeża jog co ~100–150 ms; brak odświeżenia albo zerwanie połączenia zatrzymuje oś |
| Serce sesji | `HEARTBEAT_S = 1.0` | `{"type":"ping"}` podtrzymuje sesję |
| Limiter poleceń | `COMMAND_RATE = 60.0`/s | polecenia `stop` są z niego **wyłączone** — zatrzymanie musi przejść zawsze |
| Token | `X-LRT-Token` / `Authorization: Bearer` | wymagany do każdej operacji; `/health` i `/info` otwarte (health-check) |
| Nasłuch | `127.0.0.1` domyślnie | poza localhost bez tokenu → odmowa startu (brak domyślnych poświadczeń) |
| Strażnik Host/Origin | `--allow-origin`, `--allow-any-host` | blokuje DNS-rebinding; opt-in tylko do podglądu przez proxy |
| Role | `operator` < `technolog` < `serwis` | reset E-STOP wymaga `serwis` |

**E-STOP**: nie ma operacji zwalniającej. `machine.estop` zatrzymuje, `machine.estop_reset`
wymaga roli serwisowej i nie jest wywoływane automatycznie (D35/D37). Próba wywołania
`machine.estop_release` zwraca `not_found` — takiej operacji nie ma w kontrakcie.

## Porty i backendy

```python
class MachinePort(Protocol):
    name: str
    def tick(self) -> None: ...          # odśwież stan (backend, który sam nie płynie)
    def snapshot(self) -> MachineSnapshot: ...
    def now(self) -> float: ...          # zegar backendu — do liczenia wieku migawki
    def estop(self) -> None: ...         # i reszta: estop_reset, power_on/off, set_mode,
    ...                                  # home, mdi, load_program, run, pause, resume,
                                         # stop, set_override, spindle, jog, jog_increment,
                                         # jog_stop, set_work_offset, start, shutdown, close
```

- **Atrapa** (`backends/fake.py`) — domyślna; deterministyczna (`autostart=False`
  w testach: ruch postępuje tylko przez `advance(dt)`). Jog przyrostowy jest cięty
  na kroki z domknięciem ostatniego, żeby oś stanęła dokładnie na zadanym dystansie.
- **LinuxCNC** (`backends/linuxcnc.py`) — `LinuxCNCReader(module, stat, error_channel, clock)`;
  NIEZWERYFIKOWANE NA SPRZĘCIE.
- **Plant** — wirtualna obrabiarka przez LRT-NET; rdzeń dynamiki w C11 (`plant_core/`).

Różnica nazw, na którą trzeba uważać: port ma `stop()` (zatrzymanie ruchu) i `shutdown()`
(cykl życia). Wcześniejsza wersja miała dwie metody `stop` — druga przesłaniała pierwszą
i `close()` nie zatrzymywało wątku czasu.

## Wielowątkowość

Serwer to: wątek uvicorn (requesty), wątek pętli stanu (50 Hz), wątki klientów WebSocket.
Dlatego połączenia SQLite (dostęp, narzędzia, dziennik) są tworzone z
`check_same_thread=False` — `sqlite3.threadsafety == 3` (serialized) w CPython 3.11,
więc współdzielenie jest bezpieczne. Subskrypcje stanu trzyma **połączenie**, nie hub:
atrybut na współdzielonym hubie nadpisywałby się przy drugim kliencie GUI i wyciekał.

## Rozmiary (zweryfikowane)

| Pakiet | Linie |
| --- | --- |
| `linumert` (rdzeń) | 10 378 |
| `linumert_plant` (wirtualna obrabiarka) | 7 649 |
| `linumert_headless` (warstwa usługi) | 5 639 |
| `linumert_sim` (symulacja offline) | 2 771 |
| **razem `src/`** | **26 437** |

Testy: 63 pliki, **865 przechodzi, 3 pominięte, 77 podtestów** — bez LinuxCNC, bez Qt,
bez serwera X.
