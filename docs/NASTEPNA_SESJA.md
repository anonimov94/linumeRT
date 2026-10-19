# Stan projektu i przekazanie

Tura: Claude · od 2026-10-19T04:56Z · stan: oddana (sesja 025, PR #41)

Jedyny plik ze **stanem bieżącym**: kto ma turę, co jest scalone, co czeka, co dalej. Aktualizuje go każda
sesja na końcu (zasady: [`WSPOLPRACA_MODELI.md`](WSPOLPRACA_MODELI.md) §1–3). Historia jest w
[`DZIENNIK.md`](DZIENNIK.md), poprzednie wersje tego pliku w [`archiwum/`](archiwum/).

Model-Author: Claude · 2026-10-19

## 1. W skrócie

- Wykonane sesje: 28 z 84 ([`prompts/DONE.md`](../prompts/DONE.md)). Kamień M0 domknięty (bramka G0 czeka na checklistę
  właściciela: [`docs/raporty/G0.md`](raporty/G0.md)); kamień M1 do 025 włącznie, zostaje 026 (bramka G1).
- Działa (LinuxCNC 2.9 RIP, bez sprzętu): LinuxCNC + ekran linumert steruje Plant przez LRT-NET; panel web Plant
  (telemetria, parametry live, pulpit MPG, CSV, edytor maszyny z widokiem 3D, napędy, awarie); scenariusze
  z atrapą mastera (CI) i z LinuxCNC, raport HTML w `docs/raporty/prototypy/`; `check_requirements.py` w `make test`;
  skrypty VirtualBox dla VM-A i VM-B ([`VM.md`](VM.md), NIEZWERYFIKOWANE W VIRTUALBOX); **ekran HMI linumeRT**
  (nakładka na QtDragon, HMI-PoC, D34): pasek trybu/stanu, szyna obszarów, pasek akcji, widoki Start, Maszyna,
  Produkcja, Diagnostyka (PR #42, #43).
- Testy (sesja 025, kontener Ubuntu 24.04 bez LinuxCNC + CI): wyniki w PR #41.
- **Nic nie jest sprawdzone na sprzęcie.** Prace od sesji 004 to autokontrola Claude, bez niezależnego przeglądu.

## 2. Gałęzie i PR (stan 2026-10-19)

`main` zawiera wszystkie ukończone sesje: 001–025, 032, 039, 044, porządek dokumentacji i kierunek HMI (D32).
Sesje 022, 024, 023, 025: PR #37, #38, #39, #41; dług 024: PR #40 (autokontrola, bez niezależnego przeglądu).
Otwarte: #34 (Codex, HMI-01, draft). Scalone gałęzie `wip/*`, `claude/*` i `ccr-*` można usunąć.

## 3. Następna praca

0. Właściciel: checklista bramki G0, [`docs/raporty/G0.md`](raporty/G0.md); podgląd panelu Plant
   (`python -m linumert_plant panel --plant config/plant/plant.example.yaml`).
1. Sesja 026 (bufor i bramka G1, domknięcie M1): [`prompts/sesja-026.md`](../prompts/sesja-026.md); potem sesje według
   [`prompts/README.md`](../prompts/README.md) (027 i dalej). Właściciel: [`VM.md`](VM.md) §10 (pierwsza instalacja VM).
2. **HMI według kolejności pracy (D32, D34)**: działa HMI-PoC (nakładka `screens/linumert/linumert_shell*.py`, PR #42);
   kolejne etapy (widoki Start, Bazowanie, Produkcja, Diagnostyka, tłumaczenia, poziomy dostępu) rozwijają tę nakładkę.
   Sesje ekranu z planu (M2, 027–038) muszą być z nią zgodne.
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
| Tryb `--realtime` i `socat` dla hy_vfd między dwiema VM w VirtualBox (na localhost sprawdzone w sesji 025) | sesja 016, 021, 025 | właściciel, [`VM.md`](VM.md) §10 |
| Znaki presetów trunnion wobec `xyzac-trt-kins` / `xyzbc-trt-kins` w LinuxCNC | sesja 014 | sesja z 4/5 osiami (065) |
| Warianty bazowania hardstop / w napędzie / switch_index bez testu e2e (ramka v2) | sesja 018 | decyzja o LRT-NET v2 |
| mb2hal z Modbus TCP w LinuxCNC (test e2e); alarmy falownika E-4100/E-4102/E-4104 na ekranie | sesja 021 | sesje ekranu |
| Tłumaczenia Qt (`.ts`, `tools/i18n.sh`), przycisk „Sprawdź” G-code, zakładka narzędzi na ekranie | 007, 032, 044 | sesje ekranu (M2) |
| Zgodność PyQt5 (GPL-3.0) z dystrybucją na GPL-2.0 | 001 | 080 |
| Łącze LRT-NET z Plant w kontenerze chmurowym gubi ≥ 20 odpowiedzi → E-STOP (LinuxCNC bez RT, Plant w Pythonie); w VM-A/VM-B do sprawdzenia | HMI etap 2 | właściciel ([`VM.md`](VM.md) §6) / decyzja o `timeout-cycles` w konfiguracji deweloperskiej |

## 6. Dla Codex:

**Najpierw: trudne problemy, których Claude nie domknął (2026-10-19, kolejność = priorytet).** Gotowy prompt:
[`prompts/START-CODEX-HMI.md`](../prompts/START-CODEX-HMI.md). Każdy = osobny PR,
`Model-Author: Codex`, wynik w DZIENNIK. Masz Windows/WSL z pełną siecią i prawdziwym pulpitem — tego brakuje Claude.

1. **Łącze LRT-NET gubi ≥ 20 odpowiedzi → E-STOP (niestabilne testy z Plant).** LinuxCNC RIP bez RT + Plant
   (Python, lockstep 1 kHz) na wspólnych rdzeniach: losowo `first_motion`/`rapid_vs_feed`/`hy_vfd_m4/m5` czerwone,
   także na `main` sprzed zmian (A/B). Nakładka pokazuje przyczynę („przerwa łącza LRT-NET, N cykli”). Do zrobienia:
   zmierzyć, czy to opóźnienie wątku servo (`latency-histogram`, `lrt-net.0.reply-age`, `missed`), czy Plant
   (czas `PlantServer.handle`); naprawić u źródła (np. pętla UDP Plant w C, priorytet tylko dla Plant, odbiór
   w `lrt_net` bez gubienia kolejnych odpowiedzi) — NIE przez podniesienie `timeout-cycles` w konfiguracji
   produkcyjnej. Kryterium: `-m linuxcnc` z Plant 10× z rzędu zielone w WSL.
2. **`tests/test_hal_comps.py::test_hardstop_home_comp_in_halrun` czerwony na Ubuntu 24.04 + Python 3.12 (RIP
   ze źródeł)**, także na `main`; w CI (Debian 12) zielony. Ustalić: środowisko (Python/halrun) czy błąd komponentu
   `lrt_hardstop_home`.
3. **Starter `tools/linumert-start.sh` nigdy nie zbudował obrazu** (u Claude proxy blokuje linuxcnc.org i
   deb.debian.org). Sprawdzić na prawdziwym Linuksie (WSL Debian/Ubuntu z podmanem): pierwszy start, `--plant`
   (panel :8080), `--classic`, skróty `.desktop`; poprawić to, co nie działa.
4. **Grzyb E-STOP w HMI (D35) przy zamrożeniu GUI:** limit sygnału życia 2 s. Zmierzyć najdłuższe zamrożenie
   ekranu przy wczytaniu dużego programu (podgląd 3D QtDragon, np. 50 000 linii) i zaproponować limit albo
   przeniesienie sygnału życia poza wątek GUI — bez osłabienia zasady „zawieszone HMI = E-STOP”.
5. **Skrypty VirtualBox (sesja 025, `docs/VM.md` §10) niesprawdzone w VirtualBox:** `create-vms.ps1` na Windows,
   instalacja VM-B z `preseed-plant.cfg` (pola `@@VBOX_INSERT_…@@`), `lrtnet_probe.py` z VM-A — wyniki do VM.md.


**HMI według kolejności pracy (D32), w wolnej chwili.** Specyfikacja: `docs/design/HMI_WORKFLOW.md`.
Od D34 (2026-10-19) jest działająca nakładka (HMI-PoC, Claude, PR #42): kolejne etapy budują na niej, nie od zera.
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

- 2026-10-19 Sesja 025 (skrypty VM) w chmurze Claude, gałąź `ccr-e8ca8a53-ajgyrd` (nazwę narzuca środowisko sesji), PR #41.
- Kroki 1–4: skrypty VM, sonda łącza, testy, `docs/VM.md`, poprawka nowej sesji mastera w Plant; zamknięcie sesji.
- Tura oddana; LOCK pusty.
- 2026-10-19 HMI-PoC (D34): nakładka linumeRT na QtDragon, PR #42, samotest GUI 18/18 z LinuxCNC RIP i z Plant.
- 2026-10-19 HMI etap 2: widoki Start, Produkcja, Diagnostyka, przyczyna E-STOP; PR #43.
