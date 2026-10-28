# linumeRT headless (beta)

Aplikacja sterująca CNC **bez GUI**: bez Qt, bez OpenGL, bez panelu web. Cała funkcjonalność
jest dostępna przez **kontrakt operacji** — ten sam dla REST, WebSocket, CLI i SDK Python.
Dzięki temu dowolne GUI (Qt, web, mobilne, terminal) można dołożyć na końcu projektu,
nie przepisując ani jednej linijki logiki sterowania.

```
┌─────────────────────────────────────────────────────────────┐
│  GUI (dowolne, na końcu projektu)                           │
│  Qt · web · mobile · TUI          ← budujesz TY, z kontraktu │
└───────────────┬─────────────────────────────────────────────┘
                │  REST / WebSocket / SDK / CLI
┌───────────────▼─────────────────────────────────────────────┐
│  linumert_headless  — warstwa usługi                        │
│  kontrakt (85 operacji, 12 domen) · sesje · deadman jogu    │
│  limiter · token · strażnik Host/Origin · magazyn stanu     │
├─────────────────────────────────────────────────────────────┤
│  rdzeń: linumert · linumert_sim · linumert_plant            │
│  maszyna · programy/CAM · narzędzia · korektory · alarmy    │
│  diagnostyka · konfiguracja · wirtualna obrabiarka (C11)    │
├─────────────────────────────────────────────────────────────┤
│  port MachinePort: atrapa (domyślnie) ↔ LinuxCNC ↔ Plant    │
└─────────────────────────────────────────────────────────────┘
```

## Szybki start

```bash
make install                     # pip install -e ".[dev]"
make test                        # 902 testów (bez LinuxCNC, bez Qt, bez serwera X)
make lint                        # ruff + strażnik "brak GUI"

make serve                       # serwer API na 127.0.0.1:8080 (backend: atrapa)
make contract                    # api/contract.json — podstawa codegen dla GUI
```

Serwer:

```bash
linumertd serve --backend fake --host 127.0.0.1 --port 8080 --print-contract
linumertd serve --backend linuxcnc --ini /path/to/machine.ini   # na maszynie
```

Klient (CLI zbudowane z kontraktu — nowa operacja jest w CLI bez zmian w kodzie):

```bash
linumertctl machine.state
linumertctl program.list
linumertctl machine.jog axis=X speed=10
linumertctl operations --json
```

Zainstalowane polecenia (`pip install -e .`):

| Polecenie | Przeznaczenie |
| --- | --- |
| `linumertd` | serwer API (REST + WebSocket) — do niego podłącza się GUI |
| `linumertctl` | CLI generowane z kontraktu operacji |
| `linumert-config` | generator konfiguracji LinuxCNC z `machine.yaml` (INI + HAL) |
| `linumert-plant` | wirtualna obrabiarka i serwer LRT-NET (bez panelu web) |

Kompilacja `.lnx` → G-code nie ma osobnego skryptu: to operacja `program.compile`
w kontrakcie, więc działa przez REST, WebSocket, SDK i `linumertctl program.compile`
— jedna ścieżka walidacji zamiast dwóch.

Python:

```python
from linumert_headless.sdk import Client

client = Client("http://127.0.0.1:8080", token="...")
print(client.machine.state()["task_state"])
client.machine.estop_reset()
for change in client.subscribe(topics=("machine", "alarms")):   # push stanu
    print(change["version"], change["topics"])
```

## Bezpieczeństwo

Zasady, których interfejs nie pozwala obejść — GUI dostaje je „za darmo”:

- **E-STOP nigdy nie jest zwalniany automatycznie.** Nie ma operacji `estop_release`;
  reset wymaga jawnej roli serwisowej (`machine.estop_reset`). Zgodne z D35/D37.
- **Deadman jogu**: jog należy do sesji; zerwanie WebSocket albo brak `ping` zatrzymuje oś.
- **Token** wymagany do każdej operacji; `GET /health` i `/info` są otwarte (health-check).
  Nasłuch poza `127.0.0.1` bez tokenu jest odmawiany — brak domyślnych poświadczeń.
- **Strażnik Host/Origin** blokuje DNS-rebinding; `--allow-any-host` to jawne opt-in
  wyłącznie do podglądu przez proxy.
- **Limiter poleceń** (stop jest z niego wyłączony — zatrzymanie musi przejść zawsze).
- **Role**: `operator` < `technolog` < `serwis`.

## Układ katalogów

| Ścieżka | Zawartość |
| --- | --- |
| `src/linumert_headless/` | warstwa usługi: kontrakt, usługi domen, transporty, SDK |
| `src/linumert/` | rdzeń: maszyna, programy/CAM, narzędzia, alarmy, diagnostyka |
| `src/linumert_sim/` | symulacja offline ścieżki narzędzia (bez renderowania GL) |
| `src/linumert_plant/` | wirtualna obrabiarka, serwer LRT-NET (bez panelu web) |
| `plant_core/` | rdzeń dynamiki w C11 (`make -C plant_core test`) |
| `library/drives/` | biblioteka napędów (YAML + schemat) |
| `config/` | konfiguracje maszyn, programy NC, HAL, scenariusze |
| `hal/` | komponenty HAL (`.comp`) i protokół LRT-NET |
| `api/contract.json` | wygenerowany kontrakt operacji (wejście codegen) |
| `tests/` | testy usługi i przejętego rdzenia |
| `tools/check_no_gui.py` | strażnik: w `beta/` nie ma Qt, OpenGL ani panelu web |

## Dokumentacja

- [`ARCHITEKTURA.md`](ARCHITEKTURA.md) — warstwy, porty, przepływ stanu, decyzje
- [`API.md`](API.md) — **przewodnik budowy GUI**: kontrakt, REST, WebSocket, SDK, przepływy
- [`PROVENANCE.md`](PROVENANCE.md) — co usunięto z wersji GUI i dlaczego (ścieżka audytu)

## Licencja

GPL-2.0-or-later — tak jak repozytorium nadrzędne.
