# Dziennik pracy

Chronologiczny zapis pracy agentów: **najnowsze wpisy na dole**. Spis poniżej porządkuje wpisy według
numeru sesji; stan bieżący i otwarte sprawy są w [`NASTEPNA_SESJA.md`](NASTEPNA_SESJA.md), decyzje w
[`DECYZJE.md`](DECYZJE.md).

**Format wpisu.** Nagłówek: `## NNN — Tytuł (PR #N) · RRRR-MM-DD · Model` (sesja z planu,
[`prompts/`](../prompts/README.md)) albo `## Organizacja — Temat · RRRR-MM-DD · Model` (praca poza planem
sesji: proces, scalenia, przeglądy). Treść: zrobione · testy · decyzje · do sprawdzenia ręcznie · długi
(≤ 10 linii, szczegóły w PR i dokumentach). Wpisy są niezmienne; poprawki dopisuje się nowym wpisem.

## Spis sesji (według numeru)

| Sesja | Temat | PR | Model |
|---|---|---|---|
| [000](#000--planowanie--2026-10-17--) | Planowanie | — | — |
| [001](#001--szkielet-repozytorium-ci-i-licencja--2026-10-17--claude-sonnet-55) | Szkielet repozytorium, CI i licencja | — | Claude (Sonnet 5.5) |
| [002](#002--wytyczne-ip-i-rejestr-pochodzenia--2026-10-17--claude-sonnet-55) | Wytyczne IP i rejestr pochodzenia | — | Claude (Sonnet 5.5) |
| [003](#003--spike-linuxcnc-29-w-środowisku-agenta-część-1-pr-3--2026-10-18--codex) | Spike: LinuxCNC 2.9 w środowisku agenta, część 1 | #3 | Codex |
| [003](#003--spike-linuxcnc-29-dokończenie-pr-26-zamiast-3--2026-10-18--claude-d31-praca-bazowa-codex) | Spike: LinuxCNC 2.9, dokończenie | #26 zamiast #3 | Claude (D31), praca bazowa Codex |
| [004](#004--konfiguracja-sim-3-osie-z-qtdragon-pr-24--2026-10-18--claude-d31-zakres-przejęty-od-codexa) | Konfiguracja sim 3 osie z QtDragon | #24 | Claude (D31, zakres przejęty od Codexa) |
| [005](#005--kopia-bazowa-ekranu-qtdragon-pr-25--2026-10-18--claude-d31) | Kopia bazowa ekranu QtDragon | #25 | Claude (D31) |
| [006](#006--rdzeń-model-stanu-maszyny-i-atrapa-pr-5--2026-10-18--claude-sonnet-55) | Rdzeń: model stanu maszyny i atrapa | #5 | Claude (Sonnet 5.5) |
| [007](#007--katalog-alarmów-i-manager-pr-6--2026-10-18--claude-sonnet-55) | Katalog alarmów i manager | #6 | Claude (Sonnet 5.5) |
| [008](#008--bufor-i-bramka-g0-pr-35--2026-10-18--claude-opus-55) | Bufor i bramka G0 | #35 | Claude (Opus 5.5) |
| [009](#009--specyfikacja-wirtualnej-maszyny-plant-pr-7--2026-10-18--claude-sonnet-55) | Specyfikacja wirtualnej maszyny Plant | #7 | Claude (Sonnet 5.5) |
| [010](#010--schemat-i-walidacja-machineyaml-pr-8--2026-10-18--claude) | Schemat i walidacja machine.yaml | #8 | Claude |
| [011](#011--plant-rdzeń-dynamiki-osi-c-pr-9--2026-10-18--claude-sonnet-55) | Plant: rdzeń dynamiki osi (C) | #9 | Claude (Sonnet 5.5) |
| [012](#012--plant-emulacja-napędów-cia-402-i-krokowców-pr-10--2026-10-18--claude-sonnet-55) | Plant: emulacja napędów CiA 402 i krokowców | #10 | Claude (Sonnet 5.5) |
| [013](#013--biblioteka-napędów-wirtualnych-pr-11--2026-10-18--claude-sonnet-55-dokończenie-opus-55) | Biblioteka napędów wirtualnych | #11 | Claude (Sonnet 5.5, dokończenie Opus 5.5) |
| [014](#014--plant-łańcuch-kinematyczny-przejazdy-zderzaki-krańcówki-io-pr-12--2026-10-18--claude-opus-55) | Plant: łańcuch kinematyczny, przejazdy, zderzaki, krańcówki, I/O | #12 | Claude (Opus 5.5) |
| [015](#015--bazowanie-po-rozruchu-krańcówka-indeks-twardy-zderzak-absolut-napęd-pr-13--2026-10-18--claude-opus-55) | Bazowanie po rozruchu: krańcówka, indeks, twardy zderzak, absolut, napęd | #13 | Claude (Opus 5.5) |
| [016](#016--plant-serwer-lrt-net-pr-17--2026-10-18--claude-opus-55) | Plant: serwer LRT-NET | #17 | Claude (Opus 5.5) |
| [017](#017--komponent-hal-lrt_net-pr-27--2026-10-18--claude-d31) | Komponent HAL lrt_net | #27 | Claude (D31) |
| [018](#018--konfiguracja-linuxcnc-dla-plant-pr-28--2026-10-18--claude-d31) | Konfiguracja LinuxCNC dla Plant | #28 | Claude (D31) |
| [019](#019--ograniczenia-programowe-strefy-zakazane-i-wyrocznia-testowa-pr-29--2026-10-18--claude-d31) | Ograniczenia programowe, strefy zakazane i wyrocznia testowa | #29 | Claude (D31) |
| [020](#020--magazyn-narzędzi-pozycje-wymiany-i-kolizje-w-plant-pr-30--2026-10-18--claude-d31) | Magazyn narzędzi, pozycje wymiany i kolizje w Plant | #30 | Claude (D31) |
| [021](#021--plant-wrzeciono-vfd-przez-modbus-pr-32--2026-10-18--claude-d31) | Plant: wrzeciono VFD przez Modbus | #32 | Claude (D31) |
| [022](#022--plant-panel-sterowania-i-pulpit-mpg-pr-37--2026-10-18--claude-opus-55) | Plant: panel sterowania i pulpit MPG | #37 | Claude (Opus 5.5) |
| [023](#023--edytor-wirtualnej-obrabiarki-w-panelu-plant-pr-39--2026-10-18--claude-opus-55) | Edytor wirtualnej obrabiarki w panelu Plant | #39 | Claude (Opus 5.5) |
| [024](#024--plant-scenariusze-i-raport-prototypu-pr-38--2026-10-18--claude-opus-55) | Plant: scenariusze i raport prototypu | #38 | Claude (Opus 5.5) |
| [025](#025--skrypty-maszyn-wirtualnych-virtualbox-pr-41--2026-10-19--claude-opus-55) | Skrypty maszyn wirtualnych (VirtualBox) | #41 | Claude (Opus 5.5) |
| [032](#032--baza-narzędzi-z-typami-część-rdzenia-pr-16--2026-10-18--claude-opus-55) | Baza narzędzi z typami, część rdzenia | #16 | Claude (Opus 5.5) |
| [039](#039--format-lnx-i-basemacrogenerator-pr-14--2026-10-18--claude-opus-55) | Format .lnx i BaseMacroGenerator | #14 | Claude (Opus 5.5) |
| [044](#044--lekser-g-code-i-walidacja-w-edytorze-pr-15--2026-10-18--claude-opus-55) | Lekser G-code i walidacja w edytorze | #15 | Claude (Opus 5.5) |

---

## 000 — Planowanie · 2026-10-17 · —
- Zrobione: analiza QtDragon, wytyczne IP użytkownika, plan v3 (84 sesje, 7 kamieni), specyfikacja wirtualnej obrabiarki (docs/wymagania), nazwa linumeRT, nowa identyfikacja wizualna i makiety, kontrakt CLAUDE.md v2, specyfikacja kierunku dla wirtualnej maszyny Plant.
- Decyzje: D01–D23 w docs/DECYZJE.md.
- Do sprawdzenia ręcznie: nic — repo `anonimov94/linumert` utworzone i wypchnięte 17.10.2026.
- Długi: brak.

## 001 — Szkielet repozytorium, CI i licencja · 2026-10-17 · Claude (Sonnet 5.5)
- Zrobione: `pyproject.toml` (pakiety `linumert`, `linumert_sim`, `linumert_plant`; numpy, pyyaml; dev: pytest, ruff; Python ≥ 3.11); wszystkie katalogi z CLAUDE.md §3 z `README.md`; podpakiety rdzenia (alarms, tools, programs, generators, machine, plugins, cnc, diag); `Makefile` (install, lint, test, test-c i test-linuxcnc jako no-op); `.github/workflows/ci.yml` (Python 3.11, `make install lint test`); `LICENSE` (GPL-2.0, tekst z `/usr/share/common-licenses/GPL-2`); `docs/LICENCJE.md`; `docs/PROVENANCE.md` (zalążek, rozbuduje go sesja 002); `.gitignore`; sekcja „Szybki start” w README; testy `test_license.py`, `test_ip_guard.py`, `test_layout.py` (39 testów).
- Decyzje: dwie PROPOZYCJE w `docs/DECYZJE.md` (nazwy pakietów, zakres strażnika IP).
- Do sprawdzenia ręcznie: czy workflow CI uruchomił się na GitHubie i jest zielony (w środowisku agenta sprawdzono tylko lokalnie: `make lint test` przechodzi); zgodność PyQt5 (GPL-3.0) z dystrybucją na GPL-2.0 — wpis „do potwierdzenia” w `docs/LICENCJE.md` (sesje 005 i 080). Plik `prompts/LOCK` ma wpis „praca interaktywna” — usuń go, gdy harmonogram ma ruszyć z sesją 002.
- Długi: fonty IBM Plex Sans i JetBrains Mono nie są dołączone (wpis licencji OFL przy ich dodaniu); `make test-c` i `make test-linuxcnc` to no-op do sesji 011 i 003.

## 002 — Wytyczne IP i rejestr pochodzenia · 2026-10-17 · Claude (Sonnet 5.5)
- Zrobione: `docs/prawne/PROCES.md` (wdrożenie §4 i §7 wytycznych w codziennej pracy); `docs/PROVENANCE.md` przebudowany na tabelę (zasób, typ, autor, data, źródło, licencja, zakres użycia, ścieżka) z 52 wpisami: wszystkie pliki `docs/design/`, roadmapa, dokument prawny właściciela, `LICENSE` i dwa fonty (OFL-1.1) jako „gdy dodane”; `docs/prawne/LISTA_PRZED_WYDANIEM.md` (8 pozycji §9 z polami kto, kiedy, dowód); `docs/SLOWNIK.md` (terminy projektu, słowa zakazane i zamienniki); `tests/test_ip_guard.py` rozszerzony (nazwy producentów, słowa ze słownika, brak odwołań do wcześniejszych materiałów, każdy obraz i font w rejestrze, kompletność wpisów dla `docs/design`, kolumny tabeli). 45 testów przechodzi, lint czysty.
- Decyzje: dwie PROPOZYCJE w `docs/DECYZJE.md` (lista słów zakazanych w słowniku, wymóg wpisu dla zasobów).
- Do sprawdzenia ręcznie: lista słów zakazanych w `docs/SLOWNIK.md` jest moim wstępnym doborem (MDA, R-/Q-parametry, nazwy trybów dialogowych) — przejrzyj i uzupełnij; test nie sprawdza, czy zasoby faktycznie narysowano od zera (wpisy autora i źródła pochodzą z sesji 000); zdalna gałąź `wip/sesja-001` nadal istnieje.
- Długi: fonty IBM Plex Sans i JetBrains Mono jeszcze niedodane (wiersze czekają na ścieżki i pliki OFL, sesja 027); pozycje listy przed wydaniem do wypełnienia w sesji 080.

## Organizacja — Współpraca modeli (D24, PR #1) · 2026-10-17 · Codex
- Zrobione: zweryfikowano dostęp GitHub i historię obu gałęzi; przygotowano kontrakt wspólnej pracy, AGENTS.md i szablon PR.
- Decyzje: D24, naprzemienny przegląd Claude/Codex.
- Do sprawdzenia: Claude powinien przejrzeć PR po odzyskaniu dostępności; rozpocząć sesję 003 w środowisku Linux.
- Długi: sesja 003 nieukończona; historyczny prompts/LOCK pozostawiony do wyjaśnienia.

## Organizacja — Przejęcie pracy (D25) · 2026-10-17 · Codex
- Uwagi: Decyzja właściciela D25: praca samodzielna do odwołania, push po każdym kroku.
- Weryfikacja PR #1: 45 testów przeszło w WSL, CI zielone (lint i testy).
- Podgląd: uruchomiono TigerVNC na localhost:5908 i Viewer; konfiguracja pulpitu X11 w WSLg wymaga jeszcze końcowej weryfikacji.
- Następna praca: sesja 003, LinuxCNC.

## Organizacja — Paczka testowa i VNC (PR #2) · 2026-10-17 · Codex
- Zrobione: tools/agent_tests (runner Python, launcher PowerShell, instrukcja), tools/vm/start-vnc.sh, wspólne raporty JSON/logi, dwa testy obsługi błędów runnera, końcówki LF dla pracy Windows/WSL.
- Weryfikacja: uruchomiono paczkę przez Start-Tests.ps1 -Model Codex -DisplayNumber 11; Viewer połączył się z localhost:5911; potwierdzono pulpit i terminal ze zrzutu; diff i ruff bez błędów, 47 testów przeszło. Raport state/test-runs/20261017T212444.650344Z-Codex/report.json zawiera PASS (stan roboczy podczas poprawek, pełna identyfikacja w JSON).
- Decyzje: nie przesyłamy haseł, Xauthority, logów lokalnych ani venv do Git. PR #2, push po każdym kroku.
- Do sprawdzenia: LinuxCNC jeszcze niebudowany; kolejny etap to sesja 003.
- Długi: VNC/WSL nie potwierdzają czasu rzeczywistego i sprzętu; wymagane osobne testy VM-A/VM-B.

## 003 — Spike: LinuxCNC 2.9 w środowisku agenta, część 1 (PR #3) · 2026-10-18 · Codex
- Start: Przejęto historyczną blokadę sesji 001 Claude zgodnie z poleceniem właściciela; PR #2 scalony, checkout czysty.
- Budowa i testy LinuxCNC w WSL; pulpit VNC uruchomiony ponownie na porcie 5911.
- Zrobione: budowa RIP/uspace upstream a33293f46575c809e082e0806e79ab996f982513; skrypt apt/build/cache; pełna kompilacja po make clean 50 s; import, headless sim, bazowanie XYZ, ruch MDI i pozycja końcowa, QtDragon/Xvfb i zrzut; integracja wspólnego runnera; workflow PR/ręczny/tygodniowy; raport, licencje i provenance.
- Testy lokalne: PASS, 47 bazowych + 2 integracyjne, lint i diff OK. Raport state/test-runs/20261018T060319.515034Z-Codex/report.json. Testy pokazywane w VNC localhost:5911.
- Decyzje: D20 przyjęta dla testów funkcjonalnych non-realtime. Bez zmian kodu upstream i bez make setuid. Tymczasowa preferencja QtDragon wyłącza dialog zamknięcia, test weryfikuje brak awarii przy wyjściu.
- Do sprawdzenia: najnowsze CI LinuxCNC PR #3 (trwa przy zatrzymaniu), autokontrola końcowego diffu i merge po zielonych kontrolach. CI Python przeszło. NIEZWERYFIKOWANE NA SPRZĘCIE.
- Długi: użytkownik polecił kończyć i wypchnąć postęp; PR pozostaje draft, bez merge i bez wpisu 003 do DONE. Najpierw zamknąć 003, potem sesja 004. Szczegóły w docs/NASTEPNA_SESJA.md.

## 007 — Katalog alarmów i manager (PR #6) · 2026-10-18 · Claude (Sonnet 5.5)
- Zrobione: `alarms/catalog.yaml` (56 kodów W/E/K/P, teksty własne PL/EN), `catalog.py` (loader z walidacją), `manager.py` (raise/ack/clear/reset/historia, zegar wstrzykiwany, wątkowo bezpieczny), package-data dla yaml, 23 testy; `make lint test`: 100 OK.
- Decyzje (PROPOZYCJA): pole `clear` = auto|ack|reset; kody K wg tabeli z NARZEDZIA_I_KOLIZJE.md §3 (bez K-306..309, K-312..319, których nie zdefiniowano); znaczenia W/E/P spoza dokumentów to propozycja, edytowana w jednym pliku.
- Do sprawdzenia ręcznie: sens i brzmienie tekstów PL/EN oraz podział kodów w zakresach E-4xxx.
- Długi: punkt 3 zakresu (plik `.ts` PL i `tools/i18n.sh` z pylupdate5/lrelease) czeka na kopię ekranu (sesja 005) i środowisko Qt: zadanie dla Codex.

## 006 — Rdzeń: model stanu maszyny i atrapa (PR #5) · 2026-10-18 · Claude (Sonnet 5.5)
- Zrobione: `cnc/model.py` (niezmienna migawka, świeżość), `cnc/linuxcnc_reader.py` (leniwy import, mapowanie po nazwach stałych, wstrzykiwany moduł), `cnc/fake.py` (atrapa z wirtualnym zegarem), `docs/RDZEN.md`; 30 nowych testów (21 atrapa, 9 czytnik), `make lint test`: 77 OK.
- Decyzje: pozycje w układzie maszynowym; błąd nadążania w atrapie = 0 (dynamika w Plant); po E-stop i wyłączeniu bazowanie jest kasowane (uproszczenie).
- Do sprawdzenia ręcznie: czytnik na prawdziwym RIP (znaczenie `gcodes[0]`/`mcodes[0]`, `stat.axis`, `stat.limit`, `spindle[0]`). NIEZWERYFIKOWANE NA PRAWDZIWYM LINUXCNC; zadanie dla Codexa.
- Długi: brak tabeli narzędzi i G92 w atrapie i `work_position`; brak jednostek G20.

## 009 — Specyfikacja wirtualnej maszyny Plant (PR #7) · 2026-10-18 · Claude (Sonnet 5.5)
- Uwagi: Niezależny od PR #5 i #6 (konflikt tylko na końcu DZIENNIK/DONE).
- Zrobione: `docs/PLANT.md` (architektura z mermaid, protokół LRT-NET v1 z tabelą ramki i regułami, model osi, typy napędów i CiA 402, `machine.yaml`, `plant.yaml`, scenariusze, odporność, kryteria jakości, plan sesji 010–024, 061, 082), `docs/wymagania/MACIERZ.md` (22 REQ, generowana z tabel wymagań), `tests/test_plant_spec.py` (11 testów: pokrycie REQ, parsowanie przykładów YAML, rozmiary ramek przez `struct`, CRC32); `make lint test`: 58 OK.
- Decyzje (PROPOZYCJA): układ ramki z nagłówkiem 20 B i magic `LR`; `torque_pct` w jednostce 0,1 %; watchdog 50 ms domyślnie; kody błędów napędów mapowane na E-4200…E-4203.
- Do sprawdzenia ręcznie: sensowność parametrów przykładowych i kolejności pól ramki przed sesją 016/017 (komponent HAL w C).
- Długi: model nieweryfikowany na sprzęcie; liczby w przykładach są typowe, nie pomiarowe.

## 010 — Schemat i walidacja machine.yaml (PR #8) · 2026-10-18 · Claude
- Zrobione: `core/linumert/machine/schema.py` (Pydantic v2, błędy po polsku ze ścieżką pola, `load_machine`), `validate.py` (24 reguły spójności, zbiera wszystkie błędy), 5 przykładów w `config/machines/`, `tests/test_machine_config.py` (42 testy, w tym 36 negatywnych REQ-VM-11 i REQ-VM-01).
- Zależność: pydantic (MIT) w pyproject i LICENCJE.md.
- Założenia (PROPOZYCJA): kolejność bazowania — X/Y nie przed Z; krańcówka nie dalej niż soft limit, ogranicznik za krańcówką; portal (wiele napędów) wymaga `gantry_square` i `gantry_max_skew`.
- Nie zweryfikowano: szablony napędów (`stepper_open_loop`, `servo_cia402`, `vfd_modbus`) powstaną w sesji napędów Plant; do tego czasu `validate_machine` nie sprawdza ich istnienia (parametr `drive_templates`).

## 011 — Plant: rdzeń dynamiki osi (C) (PR #9) · 2026-10-18 · Claude (Sonnet 5.5)
- Zrobione: `plant/core/axis.h/.c` (oś liniowa/obrotowa sterowana momentem: bezwładność odbita, krzywa moment–prędkość, tarcie lepkie/Coulomba/statyczne, grawitacja, luz i sztywność w modelu dwuczłonowym, zderzaki sztywne i sprężyste ze zdarzeniami, podkroki wg sztywności, jawne kody błędów po polsku, przywracanie stanu przy NaN); `plant/core/Makefile` (C11, `-Wall -Wextra -Wpedantic -Werror`); `tests/lrt_test.h` (framework) i `tests/test_axis.c` (23 testy, błąd względem wzorów analitycznych ≤ 1 %); `tests/test_plant_core.py` (uruchamia testy C z pytest, pilnuje braku alokacji i I/O); krok `make test-c` w `ci.yml`.
- Weryfikacja: `make -C plant/core test` 23/23; `ruff` czysty; `pytest` 51 przeszło (z `PYTHONPATH=core`); dodatkowo ręcznie: build z `-fsanitize=address,undefined` bez błędów, `clang -Wconversion -Wshadow` bez ostrzeżeń.
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (zakres i uproszczenia modelu osi).
- Do sprawdzenia: krok `make test-c` w `ci.yml` (nie uruchomiony na GitHubie w chwili pisania; przy scalaniu z #3 możliwy konflikt w `ci.yml`); zgodność modelu z realną maszyną — NIEZWERYFIKOWANE NA SPRZĘCIE; progi tolerancji testów dobrane do kroków 20–100 µs.
- Długi: brak hamulca silnika (Z opada przy zerowym momencie, jeśli tarcie < grawitacja) — do sesji napędów; model nie zna kierunku odwróconego ani osi gantry (sesja 014); brak REQ-znaczników w testach C do czasu `tools/check_requirements.py` (sesja 024). Nowe zasoby i zależności: brak (tylko libc/libm), więc bez zmian w LICENCJE.md i PROVENANCE.md.

## 012 — Plant: emulacja napędów CiA 402 i krokowców (PR #10) · 2026-10-18 · Claude (Sonnet 5.5)
- Zrobione: `plant/core/drive.h/.c` (maszyna stanów CiA 402, quick stop, reakcja na awarię, reset zboczem; CSP z FF, anty-windup, limit 6072h, okno nadążania, I2t; krokowiec bez sprzężenia z utratą okresów i licznikiem `lost_steps`; krokowiec z pętlą zamkniętą; enkoder z kwantyzacją i szumem; obiekty 603Fh…60B2h; wstrzykiwanie awarii; tablica awarii X-macro); `tests/test_drive.c` (49 testów); Makefile; dwa testy Python spójności tablicy awarii z katalogiem alarmów (pomijane bez katalogu z PR #6).
- Weryfikacja: `make -C plant/core test` 23 + 49 OK; ruff czysty; pytest OK; ASan/UBSan czyste; `clang -Wconversion -Wshadow` czyste; ręczny test mutacyjny 22 mutacji — wszystkie wykryte (4 testy dopisane po ocalałych mutantach).
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (model krokowca, kody 603Fh, bazowanie odroczone, opóźnienie pomiaru).
- Do sprawdzenia: niezależny przegląd modelu krokowca i mapowania awarii (Codex); po scaleniu PR #6 uruchomić test katalogu bez pomijania; PR #10 zawiera commity PR #9 do czasu jego scalenia.
- Długi: brak hamulca; bazowanie (tryb 6) w sesji 015; brak znaczników REQ w testach C do sesji 024; wszystko NIEZWERYFIKOWANE NA SPRZĘCIE.

## 013 — Biblioteka napędów wirtualnych (PR #11) · 2026-10-18 · Claude (Sonnet 5.5, dokończenie Opus 5.5)
- Zrobione: (1) `plant/library/drives/` — 7 szablonów YAML (krokowce NEMA 23 i 34, serwo krokowe, serwa 400 W i 750 W, stół obrotowy 1:90, wrzeciono 2,2 kW; wartości przykładowe z komentarzem źródła) + `drive_template.schema.json` generowany z tabeli parametrów; (2) `linumert_plant/drive_template.py` — tabela `PARAMS` z zakresami, walidacja z polskimi komunikatami i ścieżkami pól (wszystkie błędy naraz), reguły między polami, mapowanie na `lrt_drive_params`/`lrt_axis_params`, wzory fizyczne (`max_acceleration`), `LiveParams` z dziennikiem zmian; (3) `drive_library.py` — ładowanie biblioteki, instancje `template` + `overrides` z walidacją tymi samymi zakresami, klonowanie szablonu i instancji (`based_on`, `version`), zapis; (4) CLI `python -m linumert_plant drive list|show|validate|clone|schema`; (5) rdzeń C: `lrt_axis_set_live/get_live` (masa, J wirnika, J śruby, tarcie, luz, napięcie jako mnożnik krzywej), czas modelu `lrt_axis.time`, dziennik zmian `lrt_live_log` (bufor kołowy 64 wpisy, bez alokacji); (6) `plant/core/tools/check_params.c` — narzędzie sprawdzające szablony walidatorami C i krótkim ruchem napęd+oś (`--simulate`); (7) 6 nowych testów C i `tests/test_drive_library.py` (48 przypadków) ze znacznikami `# REQ-VD-nn`.
- Weryfikacja: `make lint test test-c` zielone (ruff czysty; pytest 100 + 1 pominięty; testy C 29 osi + 49 napędu); wszystkie 7 szablonów przechodzi walidatory C i ruch 0,5 obr w pętli napęd+oś (stan OPERATION_ENABLED, bez awarii i bez utraconych kroków, błąd końcowy < 0,03 % obrotu); ASan/UBSan czyste, `clang -Wconversion -Wshadow` czyste dla `axis.c` i narzędzia.
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (format szablonu, `live:` jako lista ścieżek, typy → modele C, luz live wymaga modelu dwuczłonowego, CLI pod `linumert_plant`, brak nowych zależności).
- Do sprawdzenia ręcznie / przez drugi model: (a) po scaleniu #8 podłączyć `resolve_instances()` do ładowarki `machine.yaml` (sekcja `drives:`) — w tej sesji `machine.yaml` nie było na gałęzi; (b) po scaleniu #6 test spójności tablicy awarii z katalogiem alarmów ma przejść bez pominięcia; (c) przegląd wartości szablonów (przykładowe, NIEZWERYFIKOWANE NA SPRZĘCIE) i przybliżenia wrzeciona VFD jako serwa CSP.
- Długi: hamulec i `brake_on_fault` są tylko przechowywane (model hamulca: sesja 014+); `real:` (REQ-VD-06) — sesja 061; wiązanie Pythona z rdzeniem C (ctypes) i przekazywanie `LiveParams.c_command()` do `lrt_axis_set_live` — orkiestrator w sesji 014/016; scenariusze `drive_clone_tuning` i `heavy_table_live` oraz panel (REQ-VD-03/04, sesje 022–023) jeszcze nie istnieją; zmiana `load` w locie nie przestraja regulatorów; brak `tools/check_requirements.py` (sesja 024), więc znaczniki REQ nie są jeszcze egzekwowane w CI. Nowe zależności: brak (PyYAML już w LICENCJE.md); zasoby w PROVENANCE.md.
- Dokończenie (Claude Opus 5.5, ta sama gałąź `wip/sesja-013`): (a) scalono `origin/wip/sesja-010` (#8) do gałęzi — `drives:` w `machine.yaml` to teraz instancje szablonów: `DriveInstance` przyjmuje klucz `id` (alias `name` z sesji 010), 5 przykładowych maszyn używa szablonów z biblioteki (z przykładami `overrides`), `linumert_plant/machine_drives.py` łączy walidację maszyny, rozwiązanie instancji (błędy z indeksami pliku) i zgodność mechaniki linear/rotary z osią i wrzecionem; (b) `python -m plant drive ...` z katalogu głównego (`plant/__main__.py`) i polecenie `drive instances <machine.yaml>`; (c) API live w `drive.c`: `lrt_drive_set_live/get_live` (limit momentu 6072h, estymata J regulatora), czas modelu napędu, wspólny dziennik `plant/core/live.h/.c` dla osi i napędu; (d) testy: `tests/test_machine_drives.py` (11), 2 nowe testy C napędu (w tym fizyczny: J ×4 w locie → a = T_lim/J, błąd < 1 %).
- Weryfikacja dokończenia (WSL Ubuntu 24.04, gcc, Python 3.12 venv): `ruff` czysty; `pytest` 153 przeszło + 1 pominięty; `make test-c` 29 osi + 51 napędu; ASan/UBSan czyste. LinuxCNC nie dotyczy.
- Do sprawdzenia przez Codexa: zmiana w `core/linumert/machine/schema.py` (alias `id`) i w jednym teście sesji 010 (nazwa szablonu w przykładzie) — dotyka kodu z #8; zgodność mapowania przykładowych maszyn na szablony.

## 014 — Plant: łańcuch kinematyczny, przejazdy, zderzaki, krańcówki, I/O (PR #12) · 2026-10-18 · Claude (Opus 5.5)
- Zrobione: (1) `plant/core/machine.h/.c` — maszyna z napędów i osi: konfiguracja kluczami `nazwa wartość`, osie z 1–2 napędami (gantry, alarm rozjazdu), łańcuch kinematyczny z gałęzią narzędzia i detalu (kinematyka prosta), twarde zderzaki (sprężyna + tłumik, `CRASH_HARDSTOP`, opcjonalna awaria E-4207), krańcówki i czujniki bazowe (histereza, NC/NO, wspólne wejście, drgania styku z ziarnem), impuls indeksu, pętla E-STOP (STO albo quick stop), sonda (przygotówka/płytka), 32 wejścia jak w LRT-NET; `make shared` (biblioteka dla ctypes); 17 testów C (`tests/test_machine.c`). (2) `linumert_plant/build_machine.py` — machine.yaml + biblioteka napędów → model rdzenia C (mm/stopnie → SI), presety łańcucha i mapowanie na kinematyki LinuxCNC; `core_binding.py` — `PlantMachine` (ctypes); CLI `python -m plant machine build <machine.yaml> [--keys] [--run]`. (3) Schemat machine.yaml: `kinematics.chain[].branch`, `hardstops.drive_fault`, `io.estop.action`, sekcja `probe`; walidacja: człon łańcucha dla każdej osi, zgodność rodzaju i gałęzi, wejście sondy. (4) Przykłady: sonda-płytka w `router_gantry_steppers`, przygotówka i `drive_fault` w `mill_servo_table`. (5) `tests/test_build_machine.py` (30 testów): wszystkie 5 przykładów buduje się i działa w rdzeniu C, `kin_gantry`, `kin_xyza`, `kin_trunnion` (porównanie z rachunkiem obrotów), `gantry_skew_alarm` (statyczny i z awarią jednej strony w ruchu), `hardstop_crash` (z awarią napędu i bez), `limit_switch_trip` (statyczny i w ruchu), `shared_limit_input`, E-STOP, sonda, błędy budowy, CLI.
- Weryfikacja (WSL Ubuntu 24.04, gcc, Python 3.12 venv): `make lint` czysty; `pytest` 183 przeszło + 1 pominięty (czeka na #6); `make test-c` 29 osi + 51 napędu + 17 maszyny; `test_machine.c` czysty pod ASan/UBSan. LinuxCNC nie dotyczy.
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (klucze konfiguracji, model gantry, gałęzie łańcucha, zderzaki, styki i drgania, E-STOP, sonda, indeks).
- Do sprawdzenia ręcznie / przez drugi model: znaki obrotu presetów trunnion wobec `xyzac-trt-kins`/`xyzbc-trt-kins` (test z LinuxCNC, sesja 018); czy alarm rozjazdu gantry ma też wyłączać napędy; wartości domyślne zderzaków (500 N/mm, 5 N·s/mm) — NIEZWERYFIKOWANE NA SPRZĘCIE.
- Długi: hamulec silnika nadal niemodelowany (oś Z bez momentu opada, jeśli szablon ma grawitację); belka gantry bez sprzężenia mechanicznego stron; indeks bez wejścia w machine.yaml; czujnik długości narzędzia (`positions.tool_setter`) jeszcze nie działa w Plant (sesja 020); scenariusze YAML `kin_*`, `gantry_skew_alarm` itd. istnieją jako testy pytest — format scenariuszy i `tools/check_requirements.py` w sesjach 016/024. Nowe zależności i zasoby: brak (ctypes ze stdlib), bez zmian w LICENCJE.md i PROVENANCE.md.

## Organizacja — Scalenie #6–#12 (d53aa04) · 2026-10-18 · Claude (Opus 5.5)
- Uwagi: Na polecenie właściciela, Codex niedostępny (D26 wariant b).
- Zrobione: scalono do `main` kolejno sesje 007, 009, 010, 011, 012, 013, 014 (PR #6–#12, merge commity, bez przepisywania historii) w `d53aa04`; konflikty tylko w DZIENNIK/DONE/DECYZJE/PROMPT_NOWEJ_SESJI (zachowano wszystkie wpisy, DONE posortowane). W każdym PR komentarz „autokontrola, bez niezależnego przeglądu”.
- Weryfikacja (WSL Ubuntu 24.04, venv Python 3.12): ruff czysty; pytest 248 OK, 0 pominiętych; `make test-c` OK.
- #3 (Codex): diagnoza czerwonego CI — segfault QtDragon przy zamykaniu w teardown `test_qtdragon_screen`; lokalnie nieodtwarzalny (7/7 zielone pod Xvfb). Ponowny run CI: success (crash niestabilny); kodu #3 nie zmieniano, diagnoza w komentarzu w #3.
- Uporządkowano `docs/NASTEPNA_SESJA.md` (aktualny stan, zlecenia dla Codexa w kolejności, usunięte nieaktualne sekcje) i sekcję „Stan” w `docs/PROMPT_NOWEJ_SESJI.md`.
- Do sprawdzenia: przegląd wsteczny `d53aa04` przez Codexa.

## 015 — Bazowanie po rozruchu: krańcówka, indeks, twardy zderzak, absolut, napęd (PR #13) · 2026-10-18 · Claude (Opus 5.5)
- Uwagi: Gałąź `wip/sesja-015` od `main` po scaleniu #6–#12.
- Zrobione: (1) `drive.c/.h`: przetwornik przyrostowy/absolutny (`encoder`, `pos_offset`, `lrt_drive_set_absolute/get_absolute/set_battery`), awaria ENCODER_BATTERY → E-4211 (nowy alarm w katalogu), tryb 6 (metody 1, 2, 3, 5, 17, 18, 19, 21, 33, 34, 35, 37, -1, -2; bity 10/12/13; 607Ch; wejścia `lrt_drive_set_inputs`); krokowiec: całe okresy pole–wirnik w `pos_offset`; (2) `machine.c/.h`: start losowy z ziarna (`joint.J.initial_random/min/max`), styki na wejściach napędu (`drive.N.din_*`), czujnik jednej strony gantry (`switch.S.drive`), styk tylko na napędzie (`input = -1`), `counts_for` z przesunięciem enkodera; (3) Python: `build_machine` (start, enkodery, metoda drive → 6098h/6099h/607Ch w impulsach, gantry_square → kopie czujnika i wejście `<nazwa>_2`, `counts_per_unit`), `core_binding` (tryb, słowo stanu, 6064h/6077h, OD, absolut, bateria, `drive_position`, `index_count`, `lost_steps`), `plant_state.py` (plik stanu), `homing_master.py` (atrapa mastera w stylu LinuxCNC: switch, switch_index, hardstop, absolute, drive, gantry, kolejność osi, ruch trapezowy); (4) `hal/lrt_hardstop_home.comp` — skompilowany halcompile i sprawdzony w halrun LinuxCNC 2.9 (uspace) w WSL; (5) testy: C +8 napęd, +3 maszyna; pytest `tests/test_homing.py` (13: wszystkie scenariusze REQ-VM-07 + start, plik stanu) i `tests/test_hal_comps.py` (marker linuxcnc).
- Weryfikacja (WSL Ubuntu 24.04, gcc, venv Python 3.12): `ruff` czysty; `pytest` 261 przeszło (`-m 'not linuxcnc'`); `make test-c` 29 osi + 59 napędu + 20 maszyny; `pytest -m linuxcnc tests/test_hal_comps.py` 1 OK z RIP 2.9.
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (przetworniki, bateria, komponent zderzakowy, HOME_ABSOLUTE_ENCODER, numery metod trybu 6, start losowy, gantry).
- Do sprawdzenia ręcznie / przez drugi model: numeracja metod 6098h wobec normy i prawdziwych napędów; parametry INI dla zderzaka z homemod (sesja 018, scenariusze `home_*` z LinuxCNC); dokładności w testach uwzględniają luz śrub z szablonów (10–20 µm) i drgania styków 1 ms — NIEZWERYFIKOWANE NA SPRZĘCIE.
- Długi: `test_hal_comps.py` kopiuje moduł do `rtlib` RIP na czas testu (rtapi_app nie ładuje ścieżek); master ma indeks z licznika Plant (LRT-NET bez pola zatrzasku indeksu — do decyzji w sesji 016/017); schemat `homing.cia402_method` przyjmuje 1–35 (bez -1/-2 i 37); brak wejścia indeksu w machine.yaml.

## 016 — Plant: serwer LRT-NET (PR #17) · 2026-10-18 · Claude (Opus 5.5)
- Uwagi: Gałąź `wip/sesja-016` od `wip/sesja-015` (#13 nie scalony), PR #17. Scalenie własnych #13–#16 przez Claude zablokowane w tej sesji — czekają na przegląd Codexa.
- Zrobione: `lrtnet.py` (kodek v1), `server.py` (`PlantServer.handle`/`serve`, lockstep/realtime, watchdog E-4003 jako awaria napędu `COMM_WATCHDOG` 8130h w rdzeniu C, statystyki lost/late/jitter, stan bezpieczny po wyjątku modelu, SHA-256 śladu), `trace.py` (CSV/JSONL w wątku), `serve.py` + `python -m linumert_plant serve`, `plant/server/test_master.py` (CiA 402, trapez), `config/plant/plant.example.yaml`.
- Testy: `tests/test_lrtnet.py` (14), `tests/test_plant_server.py` (26): 10 000 ramek UDP lockstep bez strat (~2,3 s), watchdog lockstep i realtime, REQ-QA-03, REQ-QA-04, proces CLI.
- Weryfikacja (WSL Ubuntu 24.04, venv 3.12): ruff czysty; pytest 300 OK; `make test-c` OK (29/59/20).
- Decyzje: PROPOZYCJA sesji 016 w `docs/DECYZJE.md`.
- Do sprawdzenia ręcznie: tryb `--realtime` między dwiema VM (sieć lrtnet) — jitter i watchdog przy prawdziwym zegarze.
- Długi: wrzeciono przez LRT-NET (0 do sesji 021); zatrzask indeksu enkodera (sesja 017); `plant_restart_midrun` i `link_loss` jako scenariusze (024); panel web.

## 032 — Baza narzędzi z typami, część rdzenia (PR #16) · 2026-10-18 · Claude (Opus 5.5)
- Uwagi: Gałąź `wip/sesja-032` od `main` (niezależna od PR #13–#15 i od Codexa). Zakres: punkty 1 i 3 promptu; punkt 2 (ekran) czeka na sesję 005.
- Zrobione: `tools/types.py` (10 typów, walidacja i reguły między polami), `tools/tbl.py` (tool.tbl bez strat, błędy linii, mm ↔ cale), `tools/db.py` (`ToolDB`: migracje, historia z zegarem, unikalne T/P, eksport/import tool.tbl atomowo, import zachowujący typ, CSV), alarmy P-5201…P-5206, `tests/test_tools_db.py` (41 + 1 z LinuxCNC).
- Weryfikacja (WSL Ubuntu 24.04, venv Python 3.12): `ruff` czysty; `pytest` 289 przeszło; test `linuxcnc`: tool.tbl z bazy wczytany przez rs274 LinuxCNC 2.9, `G43 H1/H2` daje długości z bazy na maszynie metrycznej i calowej.
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (sesja 032).
- Do sprawdzenia ręcznie: nazwy typów i pól po polsku w ekranie (sesja 037: tłumaczenia).
- Długi: zakładka narzędzi w ekranie, dialog edycji typu, synchronizacja z widokiem tool offset QtVCP i przeładowanie tabeli w LinuxCNC (po 005); oprawka tylko jako tekst (bez geometrii, sesja 058); trwałość: pola `life_min`/`used_min` bez liczenia czasu pracy (W-2110 w sesji ekranu/AUTO).

## 039 — Format .lnx i BaseMacroGenerator (PR #14) · 2026-10-18 · Claude (Opus 5.5)
- Uwagi: Gałąź `wip/sesja-039` od `main` (niezależna od PR #13 i od Codexa).
- Zrobione: `programs/lnx.py` (model `.lnx`, błędy ze ścieżką pola, zapis atomowy, `lnx_schema.json` z modelu), `programs/stock.py` (przygotówka BOX/CYL, `;@STOCK` bezstratnie), `generators/base.py` (`BaseMacroGenerator`, `Field`, `Issue`, `fmt`, nakładki `is_valid`/`generate_ngc`), `generators/registry.py` (wersje), `programs/compiler.py` (deterministyczny `.ngc`, błąd blokuje zapis, kontrola wyjścia P-5013); alarmy P-5011…P-5015; testy `tests/test_lnx.py` (40) z plikiem golden i `tests/test_ngc_linuxcnc.py` (rs274 z LinuxCNC 2.9).
- Weryfikacja (WSL Ubuntu 24.04, venv Python 3.12): `ruff` czysty; `pytest` 288 przeszło; `pytest -m linuxcnc tests/test_ngc_linuxcnc.py` 2 OK (plik golden przechodzi przez interpreter LinuxCNC do PROGRAM_END, test negatywny wykrywa błąd).
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (sesja 039).
- Do sprawdzenia ręcznie: nazwy pól i treść komentarzy w `.ngc` (bez polskich znaków w komentarzach kompilatora; komentarze kroków z polskimi znakami LinuxCNC przyjmuje).
- Długi: generatory wbudowane (040–043) i rejestracja w `DEFAULT_REGISTRY`; `preview_2d` tylko w interfejsie bazowym (podglądy: 046); jednostki „inch” przyjmowane, ale bez przeliczania pól generatorów; edytor programów w ekranie (045, 047).

## 044 — Lekser G-code i walidacja w edytorze (PR #15) · 2026-10-18 · Claude (Opus 5.5)
- Uwagi: Gałąź `wip/sesja-044` od `main` (niezależna od PR #13/#14 i od Codexa). Zakres: część rdzenia (punkty 1–2); punkt 3 (ekran) czeka na sesję 005.
- Zrobione: `programs/lexer.py` (słowa, komentarze, N, `/`, `%`, parametry i przypisania, wyrażenia z operatorami i funkcjami, słowa O z parowaniem bloków, błędy P-5101…P-5111 z linią i kolumną), `programs/linuxcnc_check.py` (kontrola w `rs274` LinuxCNC, limit czasu), alarmy P-5101…P-5111, `docs/GCODE_LEKSER.md`, 44 próbki `tests/data/gcode_samples.yaml`, `tests/test_lexer.py`.
- Weryfikacja (WSL Ubuntu 24.04, venv Python 3.12): `ruff` czysty; `pytest` 299 przeszło; `pytest -o addopts= -m linuxcnc tests/test_lexer.py` 44 OK — werdykty leksera zgodne z rs274 LinuxCNC 2.9 dla wszystkich próbek (z podziałem same/strict/semantic).
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (sesja 044).
- Do sprawdzenia ręcznie: czy surowość `strict` (np. puste `#<>`) nie przeszkadza w prawdziwych programach z CAM.
- Długi: przycisk „Sprawdź”, lista błędów i ostrzeżenie przy edycji `.ngc` z `.lnx` w ekranie (po sesji 005); komunikaty rs274 tylko po angielsku i bez numeru linii; lekser nie zna jeszcze `(MSG,` / `(DEBUG,` jako osobnych typów komentarzy (traktuje jak komentarze).

## Organizacja — Porządek dokumentacji statusowej · 2026-10-18 · Claude
Audyt NASTEPNA_SESJA.md, PROMPT_NOWEJ_SESJI.md, README.md i DONE.md względem GitHuba. Rozbieżności: dokumenty
mówiły, że #13–#17 czekają na przegląd Codexa, a właściciel scalił je 11:08–11:15Z; „następna sesja Claude: 016”
mimo zakończonej 016; README twierdził, że `make test-c` jest pusty. #18 (walidacja ramki LRT-NET) nie miał wpisu.
Poprawiono teksty; przegląd wsteczny #13–#17 pozostaje do wykonania.

Uzupełnienie audytu: MACIERZ.md — 11 wymagań (REQ-VD-01…05, REQ-VM-01…05, REQ-VM-11) ma testy z tagami REQ w main, status zmieniony z „planowane” na „zaimplementowane” (jak REQ-VM-07; „zielone” po przeglądzie niezależnym). PROVENANCE: dopisano sesje 016, 032, 039, 044.

Uzupełnienie: README plant/core (liczby testów 29/59/20, bazowanie, parametry w locie) oraz README pakietów cnc, machine, programs zgodne z modułami.

## Organizacja — Blokady zasobów (D30, PR #20) · 2026-10-18 · Claude
- Zrobione: `tools/lock.py` (acquire/release/status, O_EXCL, TTL 2 h, przejęcie przerwanej), 4 testy, zasady w WSPOLPRACA_MODELI §2a, D30, PROVENANCE.
- Zasoby: `linuxcnc`, `wsl-build`. Nie zastępuje tur ani prompts/LOCK. Do przeglądu przez Codexa (używa LinuxCNC).

## Organizacja — Przygotowanie sesji laptopowej (PR #21) · 2026-10-18 · Claude
- `make test-san` (ASan/UBSan, plant/core/build-san): 29+59+20 testów bez usterek w chmurze; `tools/dev/debian-container.sh` (Debian 12, D27); prompt: `prompts/START-LAPTOP.md`.

## Organizacja — Debian 12 na laptopie i autokontrola #13–#17 (PR #22, #23) · 2026-10-18 · Claude
- Laptop (EndeavourOS) bez podman/docker i sudo: `debian-container.sh` dostał tryb rootfs Debiana 12 (unshare -r + chroot), sprawdzony od zera.
- A (Debian 12.15, `6105649`): ruff czysty, pytest 436 OK, testy C 29/59/20 OK, ASan/UBSan bez usterek.
- B: autokontrola (nie niezależny przegląd) #13–#17, komentarze w PR. Usterek w drive.c/machine.c nie znalazłem. #17 lockstep: utracone 0, spóźnione 0.
  Uwagi do sesji 018: kierunek szukania indeksu w `switch_index` i prędkość zjazdu w homing_master.py vs homemod.
- C: pominięte, brak LinuxCNC RIP (budowa w #3, zakres Codexa). PR #22.
- Uzupełnienie (właściciel): po krańcówce maszyna wolno zjeżdża, baza na zwolnieniu styku NC; jazda dalej = uszkodzenie. Dodano `homing.latch: approach|release` (PR #23), korekta uwagi 1 w #13. Docker niepotrzebny (tryb rootfs).

## 004 — Konfiguracja sim 3 osie z QtDragon (PR #24) · 2026-10-18 · Claude (D31, zakres przejęty od Codexa)
- Zrobione: `config/sim/linumert_xyz/` (INI, `linumert_sim.hal`, `linumert_postgui.hal`, tool.tbl 5 narzędzi), 3 programy w `config/sim/nc_files/`, `docs/HAL_KONTRAKT.md`, `docs/SIM_WSL.md`, `tests/test_sim_config.py` (4 testy + 1 z markerem linuxcnc: 20 s bez ekranu).
- Sprawdzone w LinuxCNC 2.9.10 (podman, QtDragon na pulpicie): start bez błędów, bazowanie XYZ OK, programy przez rs274 OK, test linuxcnc zielony.
- Decyzje: bazowanie X/Y/Z na krańcówkach ze strategią release (HOME_LATCH_VEL przeciwny znak, 1 mm/s), napęd w HAL jako osobny blok `sim_jN` (podmieniany przez lrt_net/step-dir/EtherCAT).
- Do sprawdzenia ręcznie: okno zmiany narzędzia po M6, wygląd ekranu (nadal QtDragon — sesja 005).

## 005 — Kopia bazowa ekranu QtDragon (PR #25) · 2026-10-18 · Claude (D31)
- Zrobione: `screens/linumert/` z QtDragon 2.9.10 (commit 86cdca7): `linumert.ui/.qrc/.qss`, niezmieniony `linumert_upstream_handler.py` + własny `linumert_handler.py` (klasa pochodna), `UPSTREAM.md` z procedurą aktualizacji; sim `DISPLAY = qtvcp linumert` przez dowiązanie `qtvcp/screens/linumert`; zrzut `docs/raporty/G0/ekran_bazowy.png` (`tools/dev/zrzut_ekranu.py`, Xvfb).
- Decyzje: style alternatywne QtDragon nieskopiowane; grafiki QtDragon zostają do czasu własnego zestawu z docs/design; test IP dopuszcza zrzuty w `docs/raporty/`.
- Do sprawdzenia ręcznie: ekran na pulpicie (tytuł linumeRT), wygląd nadal QtDragon.
- Długi: własny wygląd (tokens.yaml) i nazewnictwo w UI — kolejne sesje ekranu.

## 003 — Spike: LinuxCNC 2.9, dokończenie (PR #26 zamiast #3) · 2026-10-18 · Claude (D31), praca bazowa Codex
- Scalony `main` do pracy Codexa (konflikty w DECYZJE/NASTEPNA_SESJA — wszystkie wpisy zostawione).
- Debian 12 (podman): budowa RIP OK (a33293f), testy linuxcnc 49 passed + QtDragon pod Xvfb 3/3, pytest 432 passed.
- Przyczyna czerwonego CI: brak gita przed checkoutem w `debian:bookworm` (nie segfault); poprawka w `linuxcnc.yml`.
- Gałąź `claude/sesja-003` (nowy PR zamiast #3; `codex/sesja-003` nietknięta). Push wymagał zakresu `workflow` tokenu gh.

## 017 — Komponent HAL lrt_net (PR #27) · 2026-10-18 · Claude (D31)
- Zrobione: `hal/lrt_net.comp` (master LRT-NET v1, UDP nieblokująco), `hal/lrt_cia402.comp` (włączanie, fault z zwłoką, bazowanie w napędzie, zredukowany moment), `hal/lrt_net_proto.h` (protokół w C, test zgodności z lrtnet.py bez LinuxCNC), test halrun + Plant (4 napędy, ruch X ±0,01 mm, 3/3).
- Decyzje: własny lrt_cia402 (porównanie z cia402 lcec i hal-cia402), indeks i 6072h w ramce v2, tryb 0 ignorowany w lrt_net i Plant.
- Do sprawdzenia ręcznie: nic (testy automatyczne w RIP).

## 018 — Konfiguracja LinuxCNC dla Plant (PR #28) · 2026-10-18 · Claude (D31)
- Zrobione: `config/plant/linumert_plant_xyz/` (mill_servo_table XYYZ, krańcówki NC z Plant, portal Y synchronicznie, E-STOP przez estop_latch, sonda, ekran linumert), `plant.yaml`, warianty bazowania (`bazowanie/`), `tools/dev/plant-gui.sh`, `docs/PLANT_START.md`, zrzut `docs/raporty/G0/ekran_plant.png`.
- Testy: zgodność INI z machine.yaml (5), end-to-end w LinuxCNC RIP: bazowanie z losowego startu, G1 ±5 µm, bez strat ramek (~75 s).
- Długi: switch_index i 6072h przez LRT-NET (ramka v2); warianty hardstop/drive bez testu e2e.

## 019 — Ograniczenia programowe, strefy zakazane i wyrocznia testowa (PR #29) · 2026-10-18 · Claude (D31)
- Zrobione: `linumert_plant/oracle.py` (soft limits z 607Ah, strefy z kinematyki prostej, zdarzenia na zboczu, raport JSON), integracja w serwerze (`oracle.arm_bit`, `serve --report`), HAL `motion.is-all-homed` → `dout-31`, strefa `magazyn_narzedzi` w mill_servo_table.
- Scenariusze (LinuxCNC RIP + Plant): `softlimit_oracle` — G0 X700 odrzucone przez LinuxCNC, wyrocznia bez naruszeń; `forbidden_zone_oracle` — wjazd w magazyn wykryty raz z pozycją. Testy jednostkowe geometrii i logiki (6).
- Decyzje: strefy względem stołu (= G53), uzbrojenie po bazowaniu (DECYZJE sesja 019).

## 020 — Magazyn narzędzi, pozycje wymiany i kolizje w Plant (PR #30) · 2026-10-18 · Claude (D31)
- Zrobione: `linumert_plant/atc.py` (regał, karuzela, parasolowy, ręczny; zacisk z czasem i czujnikiem, osłona, indeks karuzeli; TOOL_PLACED/PICKED/DROP, CLAMP_FAULT, POCKET_OCCUPIED, COVER_CRASH, MANUAL_CHANGE_POSITION; czujnik długości), `collisions.py` (CRASH z parą brył), integracja w serwerze (wejścia w ramce, długość narzędzia w modelu C, raport), schemat `toolchanger.outputs`/`index_ms`/`tolerance_mm` z walidacją, router_atc_rack z wyjściami, czujnikami i bryłą magazynu.
- Testy (9): atc_rack_geometry, atc_carousel_index, atc_cover_timing, manual_change_position, toolsetter_measure, crash_head_magazine, fizyka wymiany, błąd zacisku/osłony, I/O magazynu przez LRT-NET (atrapa mastera).
- Długi: makra M6 w LinuxCNC (066), konfiguracja LinuxCNC dla routera z ATC.

## 021 — Plant: wrzeciono VFD przez Modbus (PR #32) · 2026-10-18 · Claude (D31)
- Zrobione: `linumert_plant/vfd.py` — model wrzeciona z instancji szablonu napędu (bezwładność, krzywa momentu, tarcie, rampa falownika, obciążenie, I²t, at-speed 2 %), protokół hy_vfd (ramki 0x01–0x05, CRC, PD004/005/011/141–144, Hz ↔ obr/min z PD144), Modbus TCP dla mb2hal (funkcje 3/4/6/16, wyjątki, mapa z plant.yaml), transport hy_vfd przez pty, usterki (utrata komunikacji, błąd falownika = wybieg, przeciążenie). Integracja w serwerze: `plant.yaml vfd`, `spindle_actual` w LRT-NET, serwery w `serve.py`. LinuxCNC: wariant `linumert_plant_xyz_vfd.ini` z `spindle_vfd.hal` (hy_vfd), HAL wrzeciona wydzielony do `spindle_sim.hal`/`spindle_vfd.hal`, `VFD=1 tools/dev/plant-gui.sh`.
- Testy: `tests/test_vfd.py` (21, bez LinuxCNC: CRC, długości ramek jak `hy_comm.c`, rampa, at-speed, wstecz, przeciążenie, wybieg, Modbus PDU i TCP na localhost, pty, utrata komunikacji, plant.yaml, serwer z LRT-NET i z Modbus TCP); `tests/test_plant_vfd_linuxcnc.py` (3, marker linuxcnc: prawdziwy hy_vfd z RIP, po bazowaniu M3 S6000 → at-speed, M4 S3000 → −3000 obr/min w Plant, M5 → 0). Wynik na Debianie 12 (podman): ruff czysty, pytest 489 OK, testy LinuxCNC 8/8 OK.
- Poprawki wykryte testami: przeliczanie Hz ↔ obr/min z PD144 (jak hy_vfd po `-S`), opór bierny nie odwraca kierunku wału (wcześniej drgania wokół −12 obr/min przy wybiegu z obciążeniem), dokładny odczyt PDU w serwerze TCP, MDI w teście wymaga bazowania.
- Decyzje: DECYZJE sesja 021 (Python poza rdzeniem C, własny Modbus, pty + socat, `spindle_cmd` tylko bez falownika, osobne pliki HAL wrzeciona, at-speed hy_vfd bez znaku).
- Do sprawdzenia ręcznie: `VFD=1 tools/dev/plant-gui.sh`, na ekranie M3 S6000, M5; nawrót M3 → M4 bez M5 (chwilowe at-speed hy_vfd przy przejściu przez |S|).
- Długi: mb2hal z Modbus TCP w LinuxCNC (test e2e; serwer TCP sprawdzony bez LinuxCNC), alarmy E-4100/E-4102/E-4104 po stronie ekranu (z `vfd.hycomm-ok` i rejestrów), scenariusze YAML usterek falownika (024), `socat` między VM opisany, ale nie testowany. Autokontrola Claude, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Organizacja — Porządek dokumentacji (PR #33) · 2026-10-18 · Claude (D31)
- Zrobione: DZIENNIK z jednolitymi nagłówkami (numer, PR, data, model) i spisem sesji według numeru; wpisy sesji 003 z `main` wstawione chronologicznie; treść wpisów bez zmian. DONE posortowane według numeru, z PR i modelem. DECYZJE: D20 w tabeli ze statusem z `main`, osobno decyzje właściciela (D24–D31) i decyzje sesji (według numeru), uzupełnione D27, D28 i wyjątek sesji 003. NASTEPNA_SESJA tylko ze stanem bieżącym (stara wersja w `docs/archiwum/`), PROMPT_NOWEJ_SESJI jako stały prompt bez stanu, prompty `START-*` w `prompts/archiwum/`, status sesji w `prompts/README.md`. Nowe README: główne (co działa, szybki start), `docs/` (spis wszystkich dokumentów), `tools/`, `config/plant/`.
- Integracja stosu PR do `main` niewykonana: mechanizm uprawnień zablokował scalanie bez przeglądu; plan i znane konflikty w NASTEPNA_SESJA §2.

## Organizacja — HMI jako kierunek rozwoju (D32, PR #31 → #33) · 2026-10-18 · Claude (D31)
- Na polecenie właściciela: `docs/design/HMI_WORKFLOW.md` z PR #31 dołączony do dokumentacji (pisownia nazwy wg CLAUDE.md §6a), decyzja D32, zlecenie HMI-01…06 dla Codexa w NASTEPNA_SESJA §6, odnośniki w README, `docs/README.md`, `design/README.md`, `prompts/README.md`, WSPOLPRACA §7, PROVENANCE.
- Ponowna próba integracji stosu do `main` zablokowana przez mechanizm uprawnień narzędzia; `main` bez zmian.

## Organizacja — Integracja stosu PR do `main` · 2026-10-18 · Claude (D31)
- Za wyraźną zgodą właściciela scalono do `main` po kolei: #19 (z #20–#22), #18, #23, #24, #25, #27, #28, #29, #30, #32, #33 (merge commity; #31 zawarty w #33).
- Konflikty: dokumenty statusowe (wersja z #33; PROVENANCE z obu stron), `Makefile` (`test-san` i `test-linuxcnc`), `tests/test_ip_guard.py` (`docs/raporty/` dozwolone, wyjątek sesji 003 zbędny); usunięty `nextPROMPT.md`.
- Testy na zintegrowanym drzewie (Debian 12): ruff czysty, pytest 499 OK, testy C i ASan/UBSan bez błędów; testy z LinuxCNC RIP: wynik w commicie scalenia #33.

## 008 — Bufor i bramka G0 (PR #35) · 2026-10-18 · Claude (Opus 5.5)
- Krok 0 (`prompts/archiwum/START-008.md`): 4 testy LinuxCNC padały w pełnym przebiegu, bo `terminate()` trafiał tylko w skrypt `linuxcnc` (bash czeka na zastępczy ekran `sleep 3600`), po `kill()` bez `Cleanup` zostawały `linuxcncsvr`, `sleep` i `/tmp/linuxcnc.lock`; potwierdzone na `ps`. Poprawka w `tests/rip_support.py`: `start_linuxcnc`/`stop_linuxcnc` (grupa procesów), `cleanup_linuxcnc` (`halrun -U`, resztki po nazwie, blokada); autouse w `conftest.py` po każdym teście `linuxcnc`.
- Sesja 008: zaległość 006, czyli czytnik `LinuxCNCReader` sprawdzony na RIP (`tests/test_reader_linuxcnc.py`: stan, bazowanie, G55, pozycje, limity INI, kody G/M, wrzeciono); `docs/raporty/G0.md` (checklista użytkownika: WSL lub VM-A, ekran linumert, Plant); README: architektura w 10 linijkach.
- Testy (Windows 11 + WSL Ubuntu 24.04, RIP 2.9, świeży klon w systemie plików WSL): ruff czysty, pytest 499 OK, testy C 29/59/20, `-m linuxcnc` 61/61 trzy razy pod rząd, bez resztek procesów. Raz `test_sim_import_home_and_mdi` (Codex) padł na przekroczeniu czasu IO (pętla task 5 s), potem zielony 3×.
- Pozostałe zaległości 001–007 bez zmian i z właścicielem: tłumaczenia Qt (007, sesje ekranu), słowa zakazane w SLOWNIK (002, przegląd właściciela), PyQt5 GPL-3 (080). CI na `main` zielone.
- Do sprawdzenia ręcznie: `docs/raporty/G0.md` (bramka G0), wynik w tabeli §5.
- Długi: brak testu na Debianie 12 w podmanie w tej sesji; checkout na dysku Windows (`core.symlinks=false`) psuje dowiązanie ekranu, opisane w G0.md. Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 022 — Plant: panel sterowania i pulpit MPG (PR #37) · 2026-10-18 · Claude (Opus 5.5)
- Zrobione (START-022, bez przycisków awarii → 023): podpakiet `linumert_plant/panel/` (FastAPI + WebSocket ≤ 20 Hz, uPlot 1.6.31), `python -m linumert_plant panel` i `serve --panel PORT`; telemetria w buforze pierścieniowym (5 ms, okno 10 s); suwaki parametrów live → `lrt_machine_set_live` z dziennikiem; presety wbudowane i zapisane; nagrywanie CSV; wirtualny pulpit (MPG w kwadraturze A/B, oś, krok, Start/Stop posuwu, kluczyk) jako bity `digital_in` z sekcji `desk:` plant.yaml (docs/PLANT.md §7a).
- Testy (WSL Ubuntu 24.04, świeży klon): ruff czysty, pytest 518 OK (19 nowych: `tests/test_panel.py`, `tests/test_panel_parts.py`), testy C 29/59/20, `-m linuxcnc` 61/61. Masa ×10 z panelu: przyspieszenie maks. spada z ok. 1540 do ok. 860 mm/s².
- Decyzje: DECYZJE, sesja 022. Pliki spoza zakresu: `core_binding.py` (opakowania), `__main__.py` (polecenie panel), `tools/dev/wsl-test.sh` (worktree z Git for Windows).
- Do sprawdzenia ręcznie: `python -m linumert_plant panel --plant config/plant/plant.example.yaml` → http://127.0.0.1:8080/ (wygląd wobec makiety 06, suwaki, MPG, CSV).
- Długi: piny pulpitu niepodłączone w HAL LinuxCNC (sesja 029); fonty IBM Plex/JetBrains Mono niedołączone (zapas systemowy); bardzo małe J z suwaka może rozkołysać serwo (to fizyka modelu, nie błąd). Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 024 — Plant: scenariusze i raport prototypu (PR #38) · 2026-10-18 · Claude (Opus 5.5)
- Zrobione (START-024): `faults.py` (8 awarii z włączeniem i zdjęciem, REST w panelu), format scenariusza i atrapa mastera (`scenario.py`, G0/G1, kroki czasowe i `at_line`), backend LinuxCNC (`scenario_linuxcnc.py`), raport HTML/SVG (`report.py`, `docs/raporty/prototypy/`), `tools/run_scenario.py` (`--matrix`, `--ssh`), 9 scenariuszy (6 startowych + `link_loss`, `heavy_table_live`, `matrix_smoke`), `tools/check_requirements.py` w `make test`, job CI `plant-matrix`, fuzz machine.yaml.
- Testy (WSL Ubuntu 24.04, świeży klon): ruff czysty, pytest, testy C, pytest 564 OK, testy C 29/59/20, `-m linuxcnc` 66/66 (w tym 4 scenariusze `master: both` z LinuxCNC RIP); check_requirements: 22 wymagania, błędów 0.
- Znalezisko: w `config/plant/linumert_plant_xyz/linumert_plant.hal` fault napędu w łańcuchu E-STOP blokował reset po STO (zakleszczenie) — usunięty z łańcucha (plik spoza zakresu, opis w PR i DECYZJE).
- Do sprawdzenia ręcznie: `python tools/run_scenario.py` i `docs/raporty/prototypy/index.html`; z LinuxCNC: `--master linuxcnc first_motion`.
- Długi: bazowanie Z w LinuxCNC pod WSL czasem kończy się błędem nadążania (brak RT) — skrypt ponawia raz; backend LinuxCNC tylko dla mill_servo_table; testy scenariuszy z LinuxCNC pomijane na GitHub Actions (w kontenerze zostają procesy rtapi_app, kaskada błędów) — do zbadania; awaria `delay` działa w pętli UDP (nie w atrapie). Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 023 — Edytor wirtualnej obrabiarki w panelu Plant (PR #39) · 2026-10-18 · Claude (Opus 5.5)
- Zrobione (START-023): zakładki panelu Napędy, Maszyna, Awarie; `panel/editor.py` (drzewo, walidacja REQ-VM-11, zapis wersji z historią, przeładowanie modelu bez restartu przy wyłączonych napędach — `PlantServer.reload_machine`, scena 3D, klonowanie szablonów i instancji, różnice z `based_on`); widok **3D z modelu** zamiast samego rzutu 2D (polecenie właściciela); akcje scenariusza `edit_machine`/`reload`, scenariusz `edit_reload`; zakładka Awarie z API `faults.py`.
- Testy (WSL Ubuntu 24.04, świeży klon): ruff czysty, pytest 571 OK, testy C 29/59/20, `-m linuxcnc` 65/66 — `test_forbidden_zone_oracle` (019) raz niestabilny w WSL, powtórzony 2× zielony; check_requirements 0 błędów (REQ-VM-12 pokryte).
- Zamknięcie podziału D33: 022, 023, 024 scalone; 025 (skrypty VM) nadal otwarta.
- Do sprawdzenia ręcznie: `python -m linumert_plant panel --plant config/plant/plant.example.yaml` → zakładki Maszyna (obrót 3D, przesuwanie magazynu, „Zapisz wersję”, „Przeładuj model” przy wyłączonych napędach) i Napędy („Kopiuj”).
- Długi: formularz edytuje istniejące pola (dodawanie stref/brył przez plik); przeciąganie elementów myszą w 3D zastąpione przyciskami X/Y/Z; zakładka Scenariusze z makiety jeszcze nie istnieje (CLI `tools/run_scenario.py`). Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 025 — Skrypty maszyn wirtualnych (VirtualBox) (PR #41) · 2026-10-19 · Claude (Opus 5.5)
- Zrobione (START-025, sesja w chmurze Claude, gałąź `ccr-e8ca8a53-ajgyrd`): `tools/vm/vm.conf`, `create-vms.ps1` (VBoxManage, sumy SHA-256, karty NAT/lrtnet/host-only, unattended VM-B z `preseed-plant.cfg`), `post-install-plant.sh` (usługa `linumert-plant`, `--vfd`: most socat), `post-install-ctl.sh` (`halcompile --install`, `*_vm.ini`, `--vfd`), `lib.sh`, `lrtnet_probe.py` (pomiar łącza), `docs/VM.md` krok po kroku (Hyper-V, RT w VM, pomiary).
- Znalezisko i poprawka (plik spoza zakresu `server.py`): przy Plant działającym jako usługa restart LinuxCNC (seq od 1) dawał same ramki „spóźnione” — Plant przyjmuje teraz nową sesję mastera po przerwie > `watchdog_ms`.
- Testy (kontener Ubuntu 24.04, Python 3.13, bez LinuxCNC): ruff czysty, pytest 598 OK (35 nowych: `tests/test_vm_scripts.py`, `tests/test_vm_link.py`), testy C 29/59/20, check_requirements 0 błędów; shellcheck i PSScriptAnalyzer czyste, `create-vms.ps1` uruchomiony w PowerShell 7 z atrapą VBoxManage; `-m linuxcnc`: job CI `linuxcnc` uruchomiony ręcznie na gałęzi.
- Pomiary łącza (localhost, Plant realtime): RTT p50 0,4 ms; 20 ms opóźnienia bez strat i watchdoga; zawieszenie mastera 120 ms → E-4003. `tc netem` niedostępne — opóźnienie z przekaźnika UDP.
- Do sprawdzenia ręcznie: `docs/VM.md` §10 (create-vms.ps1 na Windows, instalacja VM-B z preseed, post-install-ctl.sh na obrazie LinuxCNC, `lrtnet_probe.py` z VM-A).
- Długi: NIEZWERYFIKOWANE W VIRTUALBOX (brak VirtualBoxa w środowisku agenta); pola preseed `@@VBOX_INSERT_…@@` z dokumentacji, nie z działającej instalacji; zmiana kolejności ramek (rozrzut > cykl) daje ramki spóźnione bez kroku. Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Organizacja — HMI-PoC: nakładka linumeRT na QtDragon (PR #42) · 2026-10-19 · Claude (Opus 5.5)
- Na polecenie właściciela (D34): działający w GUI ekran operatora jako nakładka na QtDragon — pasek trybu i stanu, alarmy, szyna obszarów (strony QtDragon przeniesione, nie skopiowane), dolny pasek akcji i widok „Maszyna” wg makiety 01 (DRO, bieżący blok, narzędzie, posuw/wrzeciono, JOG, MDI); `linumert_upstream_handler.py` bez zmian.
- Testy: model bez Qt (30), samotest w GUI z LinuxCNC 2.9 RIP pod Xvfb — 18/18 kroków (E-STOP, maszyna, bazowanie, MDI, program, pauza, stop, JOG, obszary), także z Plant przez LRT-NET (wyrocznia PASS); `make lint test` 628 OK. LinuxCNC RIP zbudowany w chmurze na Ubuntu 24.04 z Pythonem 3.12 (`PYTHON_BIN=python3.12`, Debian/linuxcnc.org niedostępne przez proxy).
- Do sprawdzenia ręcznie: `tools/dev/plant-gui.sh` albo `tools/dev/linuxcnc-gui.sh linuxcnc /work/config/sim/linumert_xyz/linumert_xyz.ini` — nakładka jest domyślna (`LINUMERT_SHELL=0` = czysty QtDragon).
- Długi: tłumaczenia Qt, poziomy dostępu, fonty marki, widoki Start/Bazowanie/Produkcja z HMI_WORKFLOW; „Hard limits tripped” przy starcie sim (konfiguracja). Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Organizacja — HMI etap 2: Start, Produkcja, Diagnostyka (PR #43) · 2026-10-19 · Claude (Opus 5.5)
- Na polecenie właściciela („dodawaj”): widoki Start (lista gotowości z akcjami, domyślny), Produkcja (postęp, czas pracy, korekcje F/G0/S, blok „/”, M1, start od linii z potwierdzeniem) i Diagnostyka (LRT-NET, napędy CiA 402 z alarmami 603Fh z `drive.h` i katalogu, osie, wejścia, historia); przyczyna E-STOP w pasku alarmów (pętla din-00, przerwa łącza z liczbą cykli).
- Poprawka w handlerze (kopia upstream bez zmian): QtDragon zgłaszał „Hard limits tripped” na starcie (sygnał z `tripped=False`) i przy bazowaniu na krańcówce wspólnej z czujnikiem bazowania.
- Testy: model 52, samotest GUI 27 kroków z symulatorem (pytest `-m linuxcnc`) i z Plant; `make test` zielony.
- Znalezisko środowiska: w kontenerze chmurowym (4 współdzielone vCPU, LinuxCNC RIP bez RT, Plant w Pythonie, lockstep 1 kHz) łącze LRT-NET okresowo gubi ≥ 20 odpowiedzi i HAL słusznie zgłasza E-STOP (zatrzask). Porównanie A/B z commitem sprzed zmian: ten sam objaw, więc to nie nakładka; nakładka teraz podaje przyczynę. Test w CI działa na symulatorze (bez Plant).
- Długi: Bazowanie/Zero/Narzędzia/Program/Edytor/Symulacja jako własne widoki, tłumaczenia Qt, poziomy dostępu, fonty marki; stabilność łącza z Plant w kontenerze (np. większy `timeout-cycles` tylko w konfiguracji deweloperskiej — do decyzji). Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Organizacja — Starter aplikacji `tools/linumert-start.sh` (PR #43) · 2026-10-19 · Claude (Opus 5.5)
- Na polecenie właściciela: jedno polecenie (`bash <(curl … linumert-start.sh)`) pobiera/aktualizuje main do `~/linumeRT`, instaluje git i podman (pacman/dnf/apt), buduje obraz Debian 12 + LinuxCNC 2.9 z linuxcnc.org (z `linuxcnc-uspace-dev`, venv Plant z pydantic 2 i panelem) i otwiera okno LinuxCNC z ekranem linumeRT; `--plant` dodaje Plant i panel w przeglądarce (port 8080), `--vfd`, `--classic`, skróty w menu aplikacji.
- Pliki robocze LinuxCNC śledzone w `config/plant/` (`linumert.var/.pref/.log`) starter oznacza lokalnie `skip-worktree`, żeby `git pull` nie był blokowany.
- Testy: `tests/test_launcher.py` (atrapa podmana: klon z GitHuba, skróty, obraz, polecenia trybów), shellcheck; skrypt kontenera wykonany z LinuxCNC RIP: komponenty, Plant z panelem (HTTP 200), samotest 27/27. Obrazu z linuxcnc.org nie dało się zbudować w środowisku agenta (proxy blokuje linuxcnc.org i deb.debian.org): **do sprawdzenia ręcznie na EndeavourOS**.

## Organizacja — Grzyb E-STOP w HMI w łańcuchu HAL (D35, PR #44) · 2026-10-19 · Claude (Opus 5.5)
- Na polecenie właściciela: grzyb E-STOP w HMI jako dodatkowy, szeregowy element łańcucha E-STOP w HAL; reset E-STOP (także zdarzeń emulowanych: pętla Plant, łącze) tylko zwolnieniem grzyba; sygnał życia ekranu do `watchdog` (zawieszone HMI = E-STOP, ponowne uzbrojenie tylko potwierdzeniem). Wspólny `config/hal/linumert_hmi_estop.hal`; symulator dostał zatrzask `estop_latch` (wcześniej pętla `user-enable-out`); Plant: (din-00 ∧ łącze) ∧ HMI z dwóch `and2` (`logic` ładuje tylko plik HMI; test: każdy moduł raz). Przycisk E-STOP QtDragon ukryty, F1 = wciśnięcie grzyba; tryb `--classic` bez grzyba (piny i sygnał życia z handlera).
- CLAUDE.md §6 zmieniony osobnym commitem (D35). Uruchomienia bez ekranu (testy headless, scenariusze z LinuxCNC) jawnie `HMI_ESTOP_BYPASS = 1`.
- Testy: `tests/test_hmi_estop_hal.py` (statycznie + `halrun`: grzyb, reset przy wciśniętym, watchdog, ponowne uzbrojenie), samotest GUI 33 kroki (grzyb wciśnięty, nieskuteczny reset inną drogą, zwolnienie, brak sygnału życia → E-STOP z przyczyną, potwierdzenie), pełny `-m linuxcnc` lokalnie. NIEZWERYFIKOWANE NA SPRZĘCIE.
- Przegląd Codexa (SHA 7b2cb32, `docs/ROZMOWA_MODELI.md`): P1 — po przywróceniu pętli/łącza reset inną drogą omijał grzyb → zatrzask potwierdzenia `lrt_hmi_ack` (kasowany zboczem opadającym `iocontrol.0.user-enable-out`, ustawiany impulsem `linumert.hmi-ack`); P2 — `--classic` bez ponownego uzbrojenia watchdoga → żądanie resetu z procesu ekranu potwierdza i uzbraja. Testy: `halrun` (pętla przerwana/przywrócona, reset inną drogą nieskuteczny), samotest nakładki 36 kroków, samotest `--classic`.

## HMI — Bazowanie · 2026-10-19 · Codex (PR #46)
- Własny widok stawów, czujników i krańcówek; jawne bazowanie przez ACTION, bez ruchu przy nawigacji.
- Portal i stawy ze zsynchronizowaną sekwencją pozostają w Home All; blokada podczas programu i bazowania.
- Przewijana szyna zapewnia dostęp do wszystkich widoków na niskich ekranach. Qt offscreen: 56 testów OK, ruff czysty; pełny GUI w CI.

## HMI — Program: wybór i podgląd · 2026-10-19 · Codex (PR #46)
- Własny widok Program: katalog z ustawień INI, podgląd do 2000 linii, informacja o źródle .lnx, osobne wczytanie przez ACTION.
- Wybór pliku nie zmienia programu ani trybu; wczytanie zablokowane podczas programu i pauzy.
- Testy Qt offscreen i modelu: 58 OK; lint czysty.
## Organizacja — HMI: symulacja materiału i kolizji, tabela narzędzi (PR #45) · 2026-10-19 · Claude (Opus 5.5)
- Na polecenie właściciela (PoC HMI w symulacji dziś): `simulation/linumert_sim` — materiał 2.5D (mapa wysokości), profile wszystkich typów narzędzi, reguły K-301…K-309 (nowe K-306 wrzeciono, K-307 oś, K-308 kierunek obrotów, K-309 obroty > max, K-322 podcięcie), granice obciążenia z szablonów napędów w `machine.yaml`; proces `linumert_sim.live` przy LinuxCNC (nice 10) wywołuje E-STOP przy każdej kolizji i przeciążeniu, reset grzybem (D35).
- HMI: obszary Symulacja (pyqtgraph 3D, przygotówka `;@STOCK` z programu albo z formularza, model maszyny, obciążenia, zdarzenia) i Narzędzia (baza narzędzi → tool.tbl → LinuxCNC i symulacja). Typy narzędzi: wspólne pola `flutes`, `max_rpm`, `hand`, `d_wear` (±1 mm), `holder_d`, `holder_l`; nowy typ `tap`.
- Konfiguracja symulatora: `machine.yaml` (stół, dociski, napędy), `tools_seed.yaml` (11 narzędzi), `linumert.var.default` (G54 X100 Y100 Z-150, kopiuje starter). Programy `linumert_demo.ngc`, `linumert_kolizja.ngc`; `;@STOCK` w przykładach w aktualnej składni.
- Testy: `tests/test_sim_engine.py` (każda reguła, profile, objętości), pełny pytest; e2e `tools/dev/sim-e2e.sh` (Xvfb, obraz startera). Ograniczenia: brak podcięć w 2.5D, siły z kc materiału. NIEZWERYFIKOWANE NA SPRZĘCIE.

## HMI — Integracja widoków Claude i Codex · 2026-10-19 · Codex (PR #46)
- Połączono #45 (Symulacja/Narzędzia) z #46 (Bazowanie/Program), zachowano autorstwo i oba zestawy zmian.
- Rozwiązano konflikty rejestracji stron i dokumentacji; 154 testy zakresu oraz lint OK, pełny GUI w CI.

- Poprawka integracji: kopia konfiguracji samotestu nie dziedziczy linumert.var po lokalnym demo (G54=100,100,−150 powodowało soft limit Z zamiast ruchu). Ustawienia operatora pozostają nienaruszone; symulacja nadal może zatrzymać ruch.

## HMI — Priorytet Zero detalu · 2026-10-19 · Codex
- Polecenie właściciela: własny widok maszyny i przygotówki BOX/walec/rura/odlew obrotowy.
- Monitor terminalowy `python3 tools/dev/hmi-progress.py`: 6 kroków, odświeżanie i znaczniki; sprawdzony `--once`, lint OK.

- Zero detalu, geometria: cztery zamknięte siatki, profil odlewu Z/R obracany 360°, punkty odniesienia i komendy G54–G59 z przeliczeniem mm/inch. 9 testów objętości, domknięcia i walidacji OK; lint OK.

- Zero detalu, widok 3D: maszyna i cztery przygotówki, obrót myszą, powiększanie i znacznik zera; renderuje także bez OpenGL. 13 testów geometrii i rzeczywistego renderowania Qt OK, lint OK.

- Własny widok Zero detalu zastępuje stronę QtDragon: maszyna, cztery kształty, edycja wymiarów, profil Z/R, punkt odniesienia i pozycja w G53. 19 testów geometrii/widgetów OK; edycja i nawigacja nie wysyłają komend maszyny.

- Zero detalu, zapis i układy: atomowy zapis/wczytanie przygotówki przy konfiguracji maszyny, pełny profil odlewu; jawne G10 L2 po potwierdzeniu, blokada przed bazowaniem i w trakcie programu, przeliczenie mm/inch. 21 testów geometrii, renderowania i operacji GUI OK.

- Podgląd offline Zero detalu: osobna aplikacja Qt, brak importów LinuxCNC/QtVCP, zapisy tylko w katalogu tymczasowym, ustawianie zer zablokowane także w slocie. Akcje zapisu i zera zawsze widoczne pod formularzem. Test osobnego procesu i izolacji konfiguracji OK.

- Końcowy zakres: 178 testów geometrii, UI, offline, symulacji, narzędzi, alarmów i wymagań OK; ruff czysty. Zrzut faktycznej aplikacji 1280×768 w docs/raporty/zero_detalu/offline.png; instrukcja w ZERO_DETALU.md. Otwarcie okna pulpitu z sesji agenta zablokowane (socket X11: EPERM); launcher gotowy do terminala właściciela.

## 2026-10-19 · Obsługa operatora D37 · Codex

Trzy alarmy, Reset, cztery miejsca po przecinku i wpis ręczny. Wspólny panel JOG/MDI,
M3/M4/M5 i WYMIANA M6 w Maszyna/Symulacja. Jawny bliźniak: reset HOME i wycofanie po kolizji.
Specjalista nie omija fizycznego safety ani limitów. Testy wykryły i poprawiono resztki alarmu
przeciążenia po zatrzymaniu wrzeciona oraz brak sygnałów kontraktu HAL wymiany wirtualnej.
Samotest GUI rozszerzony do 42 kroków; pełne CI w toku. Dokumentacja i README ujednolicone.
Model-Author: Codex.

## 2026-10-20 · Granica procesu interpretera · Codex

Model-Author: Codex. Część sesji 081, bez deklarowania całej sesji jako ukończonej.
Ścieżki RIP i G-code są cytowane jako dane; exec wiąże limit czasu z procesem rs274.
Niezerowy kod procesu blokuje sukces także po PROGRAM_END. Cztery testy bez LinuxCNC
uruchamiają atrapę procesu (RIP/system, znaki powłoki, błąd procesu, timeout): OK.
Pełne testy i lint przez CI; NIEZWERYFIKOWANE NA SPRZĘCIE.

## 2026-10-20 · CI: pokrycie zmian runtime · Codex

Model-Author: Codex. Workflow LinuxCNC obejmuje core, hal, config, simulation, plant i tests.
Concurrency anuluje starsze przebiegi tego samego PR/ref; różne PR mają osobne grupy.
Lokalnie parsowanie YAML i reprezentatywne ścieżki OK. CI w toku; bez deklaracji sprzętowych.
