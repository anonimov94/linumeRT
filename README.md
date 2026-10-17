# linumeRT

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

## Licencja
Własny kod: GPL-2.0-or-later. Części pochodzące z LinuxCNC/QtDragon: GPL-2.0. Całość jest rozpowszechniana na GPL-2.0.
Licencja z katalogu nadrzędnego (`PythonProjects/LICENSE`) nie dotyczy tego projektu.
