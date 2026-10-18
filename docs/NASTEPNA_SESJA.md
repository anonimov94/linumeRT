# Stan projektu i przekazanie

Tura: Claude · od 2026-10-18T16:02Z · stan: oddana (2026-10-18T16:37Z; sesja 021 i porządek dokumentacji gotowe, PR #32 i #33 czekają na scalenie)

Jedyny plik ze **stanem bieżącym**: kto ma turę, co jest scalone, co czeka, co dalej. Aktualizuje go każda
sesja na końcu (zasady: [`WSPOLPRACA_MODELI.md`](WSPOLPRACA_MODELI.md) §1–3). Historia jest w
[`DZIENNIK.md`](DZIENNIK.md), poprzednie wersje tego pliku w [`archiwum/`](archiwum/).

Model-Author: Claude · 2026-10-18

## 1. W skrócie

- Wykonane sesje: 23 z 84 ([`prompts/DONE.md`](../prompts/DONE.md)). Kamień M0 bez 008, kamień M1 do 021 włącznie.
- Działa (sprawdzone w LinuxCNC 2.9 RIP na Debianie 12, bez sprzętu): LinuxCNC z ekranem linumert steruje
  wirtualną obrabiarką Plant przez LRT-NET: bazowanie, ruch G1, wyrocznia soft limits i stref, magazyn
  narzędzi i kolizje w Plant, wrzeciono przez prawdziwy `hy_vfd` i emulator falownika.
- Testy na `wip/sesja-021`: ruff czysty, pytest 489 OK, testy LinuxCNC 8/8 OK, testy C 29/59/20 (sesja 020).
- **Nic nie jest sprawdzone na sprzęcie.** Prace od sesji 004 to autokontrola Claude, bez niezależnego przeglądu.

## 2. Gałęzie i PR (stan 2026-10-18T16:33Z)

`main` zawiera sesje 001, 002, 003, 006, 007, 009–016, 032, 039, 044. Reszta czeka w stosie PR, gdzie każda
gałąź bazuje na poprzedniej:

| PR | Gałąź → baza | Zawartość | Stan |
|---|---|---|---|
| #18 | `claude/lrtnet-walidacja` → `main` | walidacja pól ramki LRT-NET (reserved, pad, NaN) | otwarty, konflikt w PROVENANCE |
| #19 | `claude/kosmetyka-nazwa` → `main` | `[LINUMERIK]` → `[LINUMERT]`; zawiera już #20–#22 (blokady D30, laptop, Debian 12) | otwarty, konflikty w dokumentach |
| #23 | `claude/bazowanie-strategie` → `claude/laptop-weryfikacja` | `homing.latch` approach/release | otwarty |
| #24 | `wip/sesja-004` → `claude/bazowanie-strategie` | sesja 004 | otwarty |
| #25, #27, #28, #29 | 005, 017, 018, 019 → gałąź poprzednia | sesje 005, 017–019 | scalone do gałęzi stosu (nie do `main`) |
| #30 | `wip/sesja-020` → `wip/sesja-019` | sesja 020 | otwarty |
| #32 | `wip/sesja-021` → `wip/sesja-020` | sesja 021 | otwarty |
| #33 | `claude/dokumentacja` → `wip/sesja-021` | ten porządek dokumentacji | otwarty |
| #31 | `feature/hmi-workflow-tabs` → `wip/sesja-020` | projekt HMI według kolejności pracy (`docs/design/HMI_WORKFLOW.md`) | otwarty; dokument jest też w #33 z poprawioną pisownią nazwy, więc #31 można zamknąć jako zawarty w #33 |

**Plan integracji do `main`** (merge commit na PR, bez przepisywania historii; każdy PR po kolei z bazą
przestawioną na `main`): #19 → #18 → #23 → #24 → #25 → #27 → #28 → #29 → #30 → #32 → #33 (#31 zawarty w #33).
Próba lokalna (2026-10-18) pokazała, że konflikty są tylko tu:
- dokumenty statusowe (DZIENNIK, DONE, PROVENANCE, DECYZJE, NASTEPNA_SESJA, WSPOLPRACA_MODELI): po #33 obowiązuje
  wersja z #33, bo ma już wpisy z `main` (sesja 003, D20, D27, D28);
- `Makefile` (#23): zostaje `test-san` z gałęzi i `test-linuxcnc` z `main`, a komentarz „No-op do sesji 003” znika;
- `tests/test_ip_guard.py` (#24): zostaje reguła z gałęzi (`docs/raporty/` dozwolone), wyjątek dla
  `spike_qtdragon.png` z `main` staje się zbędny;
- `nextPROMPT.md` (tylko w `main`): do usunięcia, bo punktem wejścia jest [`PROMPT_NOWEJ_SESJI.md`](PROMPT_NOWEJ_SESJI.md).

Scalanie własnych PR przez Claude blokuje mechanizm uprawnień narzędzia (klasyfikator „merge without
review”), więc scala właściciel albo Claude po jawnym zezwoleniu w ustawieniach.

## 3. Następna praca

1. **Integracja stosu do `main`** (sekcja 2), potem usunięcie scalonych gałęzi `wip/*` i `claude/*`.
2. Sesje według [`prompts/README.md`](../prompts/README.md): **008** (bufor i bramka G0), potem 022 (panel Plant
   i pulpit MPG), 023 (edytor wirtualnej obrabiarki), 024 (scenariusze, raport, `tools/check_requirements.py`).
3. **HMI według kolejności pracy (D32)**: docelowy kierunek ekranu; etapy HMI-01…06 prowadzi Codex (§6).
   Sesje ekranu z planu (M2, 027–038) muszą być z nim zgodne.
4. Propozycja do decyzji: ramka LRT-NET v2 (zatrzask indeksu enkodera, 6072h), opis w DECYZJE (sesja 017).

## 4. Środowisko

**Laptop właściciela (EndeavourOS, podman), Claude:**
- testy na Debianie 12: `tools/dev/debian-container.sh make lint test test-c test-san`;
- LinuxCNC 2.9 RIP (obraz `linumert-rip:bookworm`, RIP w `~/.cache/linumert/rip-home`), testy z LinuxCNC i
  polecenia: [`PLANT_START.md`](PLANT_START.md);
- GUI na pulpicie: `tools/dev/plant-gui.sh` (LinuxCNC + Plant + ekran linumert), `VFD=1 tools/dev/plant-gui.sh`
  (wrzeciono przez hy_vfd), `tools/dev/linuxcnc-gui.sh` (symulator z pakietów linuxcnc.org,
  [`SIM_WSL.md`](SIM_WSL.md)).

**Windows z WSL (Codex):** paczka testowa i podgląd VNC: [`tools/agent_tests/README.md`](../tools/agent_tests/README.md),
[`PODGLAD_UBUNTU.md`](PODGLAD_UBUNTU.md).

## 5. Otwarte sprawy

| Sprawa | Od | Kto |
|---|---|---|
| Niezależny przegląd wsteczny prac Claude: `d53aa04` (sesje 007–014), #13–#17, sesje 004–005, 017–021 | 2026-10-18 | drugi model albo właściciel |
| Weryfikacja na sprzęcie (napędy, falownik RS485, E-STOP); obecnie wszystko NIEZWERYFIKOWANE NA SPRZĘCIE | — | właściciel, po zakupie sprzętu |
| Tryb `--realtime` Plant między dwiema VM (jitter, watchdog) i `socat` dla hy_vfd między VM | sesja 016, 021 | 025 (skrypty VM) |
| Znaki presetów trunnion wobec `xyzac-trt-kins` / `xyzbc-trt-kins` w LinuxCNC | sesja 014 | sesja z 4/5 osiami (065) |
| Warianty bazowania hardstop / w napędzie / switch_index bez testu e2e (ramka v2) | sesja 018 | decyzja o LRT-NET v2 |
| mb2hal z Modbus TCP w LinuxCNC (test e2e); alarmy falownika E-4100/E-4102/E-4104 na ekranie | sesja 021 | 024, sesje ekranu |
| Tłumaczenia Qt (`.ts`, `tools/i18n.sh`), przycisk „Sprawdź” G-code, zakładka narzędzi na ekranie | 007, 032, 044 | sesje ekranu (M2) |
| Zgodność PyQt5 (GPL-3.0) z dystrybucją na GPL-2.0 | 001 | 080 |

## 6. Dla Codex:

**HMI według kolejności pracy (D32), w wolnej chwili.** Specyfikacja: `docs/design/HMI_WORKFLOW.md`.
- Kolejność: HMI-01 (inwentaryzacja widgetów `screens/linumert/linumert.ui`, kontrakt sygnałów, zrzut bazowy) →
  HMI-02 (pasek stanu, nawigacja, Start, Bazowanie, Ręczne) → HMI-03 … HMI-06; każdy etap = osobny PR do `main`.
- Zasady: `linumert_upstream_handler.py` bez zmian; logika w `linumert_handler.py` i osobnych modułach;
  zmiana zakładki nie wykonuje ruchu ani zmiany trybu; wygląd z `docs/design/tokens.yaml` (CLAUDE.md §6a).
- Odbiór: testy QtVCP pod Xvfb i z LinuxCNC RIP z Plant (`tools/dev/plant-gui.sh`, `HEADLESS=1`), zrzuty
  wszystkich widoków w `docs/raporty/`, 1280×768, obsługa klawiaturą; wpis w DZIENNIK.
- Środowisko: §4 (laptop z podmanem albo WSL); blokada `python tools/lock.py acquire linuxcnc --model Codex`.

## 7. Dla Claude:

(brak)

## 8. Stan zatrzymania (bieżąca tura)

- 2026-10-18T16:02Z Przejęcie tury, kontynuacja sesji 021 według `prompts/archiwum/START-021.md`.
- Sesja 021 ukończona: testy `vfd.py` (fb4aed2), integracja z serwerem (c658f6c), wariant LinuxCNC `_vfd` z
  prawdziwym hy_vfd (07c70ad), dokumentacja (dbf0d9e); PR #32.
- 2026-10-18T16:33Z Integracja stosu do `main` wstrzymana: mechanizm uprawnień zablokował scalanie bez
  przeglądu. Porządek dokumentacji na `claude/dokumentacja`.
- 2026-10-18T16:37Z Porządek dokumentacji gotowy (PR #33); `make lint test` 489 OK. Tura oddana, LOCK i blokady zwolnione.
