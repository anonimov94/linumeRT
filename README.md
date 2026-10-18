# linumeRT

**AI — zacznij tutaj: [nextPROMPT.md](nextPROMPT.md)** · aktualny następny krok i podział pracy.

![linumeRT](docs/design/marka/baner.png)

Otwarty ekran operatora i zestaw narzędzi dla **LinuxCNC**, przeznaczony dla hobbystycznych maszyn CNC:
frezarek 3, 4 i 5 osi, silników krokowych, serw krokowych i serw, ręcznej zmiany narzędzia i ATC,
napędów EtherCAT (CiA 402) i step/dir oraz wrzecion sterowanych przez RS485.

Ekran powstaje na bazie **QtDragon** (QtVCP, część LinuxCNC). Ma własny wygląd, programowanie dialogowe,
symulację z kolizjami, kreator konfiguracji i diagnostykę napędów. Do testów służy **Plant**, czyli
wirtualna frezarka w osobnej maszynie wirtualnej. Symuluje bezwładność, ograniczenia momentu i przyspieszenia,
napędy, krańcówki, sondę, falownik i magazyn narzędzi.

> **Status:** wczesny rozwój. Nic nie zostało sprawdzone na prawdziwej maszynie.

## Architektura
```
VM-A / komputer maszyny                         VM-B (Plant)
┌───────────────────────────────┐   LRT-NET    ┌──────────────────────────────┐
│ Ekran linumeRT (QtVCP)        │   UDP 1 kHz  │ model osi + napędy CiA 402   │
│ rdzeń linumert (Python)       │◄────────────►│ I/O, sonda, VFD, ATC, MPG    │
│ LinuxCNC 2.9 + HAL (lrt_net)  │              │ panel web :8080, scenariusze │
└───────────────────────────────┘              └──────────────────────────────┘
Na prawdziwej maszynie lrt_net zastępuje lcec (EtherCAT) lub stepgen — sygnały HAL bez zmian.
```

## Jak powstaje
Kod piszą agenci AI według promptów w `prompts/` (84 sesje). Harmonogram uruchamia agenta co 5 godzin.
Gdy limit konta jest wyczerpany, uruchomienie nic nie robi, a następne po odnowieniu limitu kontynuuje pracę.
Kontrakt: [`CLAUDE.md`](CLAUDE.md) · decyzje: [`docs/DECYZJE.md`](docs/DECYZJE.md) ·
wytyczne IP: [`docs/prawne/WYTYCZNE_IP.md`](docs/prawne/WYTYCZNE_IP.md) · postęp: [`prompts/DONE.md`](prompts/DONE.md).

## Szybki start
Wymagania: Python ≥ 3.11 i `make`. Sprawdzone: Linux.
```bash
python3 -m venv .venv && . .venv/bin/activate
make install      # pakiet linumert + zależności dev (pytest, ruff)
make lint         # ruff
make test         # pytest (bez LinuxCNC)
```
`make test-c` i `make test-linuxcnc` są pustymi krokami do sesji 011 i 003. W systemowym Pythonie Debiana
dodaj `PIP_FLAGS=--break-system-packages`.

## Licencja
GPL-2.0-or-later dla własnego kodu (pełny tekst GPL-2.0 w pliku [`LICENSE`](LICENSE), zależności w [`docs/LICENCJE.md`](docs/LICENCJE.md)). Własny kod: GPL-2.0-or-later. Części pochodzące z LinuxCNC/QtDragon: GPL-2.0. Całość jest rozpowszechniana na GPL-2.0.
Licencja z katalogu nadrzędnego (`PythonProjects/LICENSE`) nie dotyczy tego projektu.

## Wspólna paczka testowa i VNC

Instrukcja: [tools/agent_tests](tools/agent_tests/README.md). Windows: `tools/agent_tests/Start-Tests.ps1 -Model Manual` otwiera Ubuntu przez VNC oraz terminal testów. Codex i Claude używają tej samej paczki z własnym oznaczeniem modelu.
