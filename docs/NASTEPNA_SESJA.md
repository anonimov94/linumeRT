# Stan projektu i przekazanie

Tura: Claude · od 2026-10-19T04:56Z · stan: w toku (sesja 025, gałąź ccr-e8ca8a53-ajgyrd)

Jedyny plik ze **stanem bieżącym**: kto ma turę, co jest scalone, co czeka, co dalej. Aktualizuje go każda
sesja na końcu (zasady: [`WSPOLPRACA_MODELI.md`](WSPOLPRACA_MODELI.md) §1–3). Historia jest w
[`DZIENNIK.md`](DZIENNIK.md), poprzednie wersje tego pliku w [`archiwum/`](archiwum/).

Model-Author: Claude · 2026-10-18

## 1. W skrócie

- Wykonane sesje: 27 z 84 ([`prompts/DONE.md`](../prompts/DONE.md)). Kamień M0 domknięty (bramka G0 czeka na checklistę
  właściciela: [`docs/raporty/G0.md`](raporty/G0.md)); kamień M1 do 024 włącznie, bez 025 (skrypty VM).
- Działa (LinuxCNC 2.9 RIP, bez sprzętu): LinuxCNC + ekran linumert steruje Plant przez LRT-NET; panel web Plant
  (telemetria, parametry live, pulpit MPG, CSV, edytor maszyny z widokiem 3D, napędy, awarie); scenariusze
  z atrapą mastera (CI) i z LinuxCNC, raport HTML w `docs/raporty/prototypy/`; `check_requirements.py` w `make test`.
- Testy (sesja 023, WSL Ubuntu 24.04 + RIP): wyniki w PR #39; CI: `python`, `plant-matrix`, `linuxcnc` zielone.
- **Nic nie jest sprawdzone na sprzęcie.** Prace od sesji 004 to autokontrola Claude, bez niezależnego przeglądu.

## 2. Gałęzie i PR (stan 2026-10-18)

`main` zawiera wszystkie ukończone sesje: 001–024, 032, 039, 044, porządek dokumentacji i kierunek HMI (D32).
Sesje 022, 024, 023: PR #37, #38, #39 (autokontrola, bez niezależnego przeglądu). Otwarte: #34 (Codex, HMI-01, draft);
#31 do zamknięcia (zawarty w #33). Scalone gałęzie `wip/*` i `claude/*` można usunąć.

## 3. Następna praca

0. Właściciel: checklista bramki G0, [`docs/raporty/G0.md`](raporty/G0.md); podgląd panelu Plant
   (`python -m linumert_plant panel --plant config/plant/plant.example.yaml`).
1. Sesja 025 (skrypty maszyn wirtualnych): [`prompts/START-025.md`](../prompts/START-025.md) — ostatnia z podziału D33
   ([`archiwum/START-PODZIAL.md`](../prompts/archiwum/START-PODZIAL.md)); potem sesje według
   [`prompts/README.md`](../prompts/README.md) (026 i dalej).
2. **HMI według kolejności pracy (D32)**: docelowy kierunek ekranu; etapy HMI-01…06 prowadzi Codex (§6).
   Sesje ekranu z planu (M2, 027–038) muszą być z nim zgodne.
3. Propozycja do decyzji: ramka LRT-NET v2 (zatrzask indeksu enkodera, 6072h), opis w DECYZJE (sesja 017).
4. Dług 024: kontener CI dostał `--init` (zombie są sprzątane), a pominięcie testów scenariuszy z LinuxCNC na Actions
   zdjęto; potwierdzone: job `LinuxCNC RIP smoke` zielony w PR #40 (2026-10-19). Dług zamknięty.

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
| mb2hal z Modbus TCP w LinuxCNC (test e2e); alarmy falownika E-4100/E-4102/E-4104 na ekranie | sesja 021 | sesje ekranu |
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

- 2026-10-19 Sesja 025 (skrypty VM) w chmurze Claude, gałąź `ccr-e8ca8a53-ajgyrd` (nazwę narzuca środowisko sesji). Krok 0: tura i LOCK.
