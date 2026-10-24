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
| [085](#085--skin-01-renderer-3d-pr-87--2026-10-23--codex) | SKIN-01: renderer 3D | #87 | Codex |
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

## Organizacja — punkty roadmapy na szybko: 040, 042, 059 (części) · 2026-10-19 · Claude (Opus 5.5)
- 040: generatory `header`, `program_end`, `tool_change`, `face_mill` (zygzak / jednokierunkowo, warstwy, wybieg, podgląd 2D) — `core/linumert/generators/basic.py`; poprawka `fmt(x, 0)` (obcinało zera: S8000 → S8).
- 042: generator `drill_holes` — wzory pojedynczy/lista/rząd/siatka/okrąg/łuk, G81/G82/G83/G73, G33.1 tylko przy `spindle_sync` (G84 nie istnieje w LinuxCNC 2.9), walidacja, podgląd 2D.
- 059: eksport STL materiału z mapy wysokości (bryła szczelna, objętość zgodna) + przycisk „Eksport STL” w widoku Symulacja.
- Brak: walidacja z ToolDB (040 p.2), raport HTML symulacji (059 p.1), panel dialogowy (045). Testy: `test_gen_basic.py`, `test_gen_drilling.py`, `test_sim_engine.py::test_stl_*`; pytest 684 OK.

## Organizacja — domknięcie pracy z 2026-10-19: #46 scalony, Program, E-STOP dwukanałowy · Claude (Opus 5.5)
- #46 Codexa (Bazowanie, Program, Zero detalu, D36/D37) scalony po zielonym CI; wcześniej poprawka `INFO.JOINT_SEQUENCE` (lista w LinuxCNC 2.9 — ekran nie wstawał).
- Program: przyciski Sprawdź (lekser, kursor na pierwszym błędzie) i Edytuj/Zapisz (zapis atomowy, blokada w trakcie programu, „wczytaj ponownie” dla aktywnego pliku).
- E-STOP dwukanałowy NC (zalecenie właściciela): `hal/lrt_estop2.comp` + model `core/linumert/diag/estop2.py` — oba kanały zamknięte = ok; rozbieżność > 0,1 s = błąd zatrzaśnięty; kasowanie: test obwodu (oba otwarte → oba zamknięte) + Reset. Plant: `io.inputs.estop_b` (bit 15) = kopia kanału A, awaria `estop_channel` (kanał B zablokowany). Konfiguracja Plant: łańcuch przez `lrt_estop2`; ekran podaje przyczynę „rozbieżność kanałów”. Testy: model, `halrun`, Plant. NIEZWERYFIKOWANE NA SPRZĘCIE.
- D38 (PROPOZYCJA, wznowienie z helisą i łukiem) w sesji 031; stan częściowy sesji 040, 042, 055–059 w `prompts/README.md`.

## Bezpieczeństwo — audyt i rozdział symulacji od toru PC · 2026-10-20 · Codex
- Model-Author: Codex. PR #48, gałąź codex/safety-separation; założenia właściciela w CLAUDE/DECYZJE.
- Audyt main 7ad6313: poprawki względem Groka, niezależny nadzór PC, bez przypisywania kategorii/PL.
- Proces symulacji bez kanału komend LinuxCNC; kolizje/przeciążenia nadal raportowane; komunikat diagnostyczny.
- Zastąpiony test obejścia geometrii testem braku możliwości przywrócenia sterowania; e2e oczekuje diagnostyki.
- Testy lokalne Debian 13: 3 unittest (w tym 6 wariantów zdarzeń/profilu) i compileall OK; bez Qt/LinuxCNC.
- Debian 12 i pełny LinuxCNC: CI PR, nie deklaruję lokalnego odbioru GUI ani sprzętu.
- Zakres Plant oczekuje doprecyzowania; jego łańcuch, watchdogi i testy usterek zachowane.
- Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Bezpieczeństwo — profile i kontrola deklaracji · 2026-10-20 · Codex
- Model-Author: Codex. PR #48; jawne sim/plant/hardware, CLI bez uruchamiania CNC.
- Hardware wymaga monitorów E-STOP/nadzoru PC, heartbeat, resetu fizycznego i zakazu autorestartu.
- Odrzucane: bypass, virtual, sygnały software w rolach I/O, powtarzane deklaracje; hardware_verified=false.
- Przykład celowo niekompletny, bez połączeń HAL; kontrola nie jest jeszcze bramką startu/eksportu.
- Testy lokalne Debian 13: 5 unittest profili + 1 synchronizacji HMI; poprzednie 3 diagnostyki OK.
- CI b626235: ogólne zielone; LinuxCNC 68/69, błąd synchronizacji MDI→M3; poprawka 6047a13.
- Pełny wynik ostatniego SHA pozostaje do weryfikacji; bez lokalnego odbioru Qt/LinuxCNC.
- Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Bezpieczeństwo — audyt HAL offline · 2026-10-20 · Codex
- Model-Author: Codex. PR #48, po zgodzie właściciela na zadania bez LinuxCNC poza kolejnością.
- Audyt tekstowych net/source bez wykonywania HAL, wykrycie pętli software i brakujących połączeń.
- CLI --hal-from-ini zachowuje wszystkie HALFILE/POSTGUI_HALFILE; --hal dla wskazanych plików.
- Wynik rozdziela deklarację i ograniczony audyt; hardware_verified=false, bez automatycznej zgody.
- Lokalne Debian 13: 10 kolejnych unittest OK, łącznie 19 nowych testów gałęzi; bez LinuxCNC/Qt.
- Dodano pusty protokół odbioru toru PC: próby i pomiary niewykonane, brak deklaracji PL/SIL.
- Pełne CI finalnego SHA do weryfikacji; autokontrola, bez niezależnego przeglądu.
- NIEZWERYFIKOWANE NA SPRZĘCIE. Plant bez zmian zakresu.

## 2026-10-20 · Granica procesu interpretera · Codex

Model-Author: Codex. Część sesji 081, bez deklarowania całej sesji jako ukończonej.
Ścieżki RIP i G-code są cytowane jako dane; exec wiąże limit czasu z procesem rs274.
Niezerowy kod procesu blokuje sukces także po PROGRAM_END. Cztery testy bez LinuxCNC
uruchamiają atrapę procesu (RIP/system, znaki powłoki, błąd procesu, timeout): OK.
Pełne testy i lint przez CI; NIEZWERYFIKOWANE NA SPRZĘCIE.


## 040 — Generatory: walidacja z bazą narzędzi (p.2) · 2026-10-20 · Claude
- Zrobione: `core/linumert/generators/tooling.py` — `tool_change` wybiera narzędzie z bazy, następne kroki
  `face_mill` i `drill_holes` sprawdzane z jego danymi: typ do operacji (P-5207; narzędzie bez typu przepuszczane,
  symulacja i tak zgłasza K-320), średnica i skok gwintu (P-5208), głębokość przejścia vs długość ostrza / wysokość
  głowicy (P-5209), `max_rpm` (P-5210), kierunek M3/M4 vs `hand` (P-5211), brak w bazie (P-5206). Program w calach
  przeliczany na mm. `compile_program(..., tools=ToolDB.get)`; bez `tools` zachowanie bez zmian.
- Testy: `tests/test_gen_tooling.py` (11). Decyzje: tolerancja średnicy 0,01 mm.
- Do sprawdzenia ręcznie: podpięcie `tools=` w panelu dialogowym (sesja 045). Długi: brak.

## 059 — Raport symulacji HTML (p.1) · 2026-10-20 · Claude
- Zrobione: `simulation/linumert_sim/report.py` — statyczny HTML (kolory z tokenów, bez JS i zasobów zewnętrznych):
  program, czas symulacji, długość ruchów roboczych i G0, objętość materiału i usuniętego, zdarzenia K-3xx z czasem,
  linią, narzędziem i pozycją G53, widok z góry (mapa wysokości PNG zapisywana biblioteką standardową + ślad
  narzędzia SVG), opcjonalny zrzut widoku. Proces `linumert_sim.live`: polecenie `export_report`, zdarzenie `report`;
  przebieg liczony od wczytania programu albo odnowienia materiału. Strona Symulacja: przycisk „Raport”.
- Testy: `tests/test_sim_report.py` (7). Do sprawdzenia ręcznie: przycisk „Raport” w działającym HMI (CI: samotest GUI).
- Długi: przycisk „Symuluj” w panelu dialogowym (045) i plikach; zrzut widoku 3D z ekranu do raportu.

## 054 — Przygotówka: cel sondy Plant (p.2) · 2026-10-20 · Claude
- Zrobione: `tools/stock_probe.py` — linia `;@STOCK` (z programu albo podana) + zero układu detalu (plik .var
  LinuxCNC albo `--origin`) → `probe.target` w machine.yaml (układ maszyny, liczone jak w symulacji HMI,
  `stock_bounds`); walec jako prostopadłościan opisany (Plant zna tylko box/plate). `--write` zmienia jedną linię
  `target:` atomowo, komentarze zostają. p.1 (parser, dialog) i p.3 (K-321) były już zrobione.
- Testy: `tests/test_stock_probe.py` (6; wynik wczytywany schematem machine.yaml). NIEZWERYFIKOWANE NA SPRZĘCIE.

## 048 — Biblioteka podprogramów o-word (część) · 2026-10-20 · Claude
- Zrobione: `core/linumert/generators/subroutines.py` — `o<lrt_face_mill>`, `o<lrt_drill_grid>`, `o<lrt_drill_circle>`
  (cykle 81/82/83/73, G98/G99) z nagłówkiem NgcGui; eksport `python -m linumert.generators.subroutines <user_macros>`;
  dokumentacja `docs/user/PODPROGRAMY.md`.
- Testy: `tests/test_subroutines.py` — nagłówek NgcGui, lekser, eksport, dokumentacja; z markerem `linuxcnc`
  zgodność ruchu (STRAIGHT_TRAVERSE/FEED z rs274) podprogramu i generatora Pythona dla 8 zestawów parametrów
  (sprawdzone lokalnie na LinuxCNC 2.9 RIP).
- Długi: kieszenie i rowki (po sesjach 041/043); zakładka NgcGui w ekranie nie sprawdzona ręcznie.

## 053 — Estymator czasu obróbki (część) · 2026-10-20 · Claude
- Zrobione: `core/linumert/programs/estimate.py` — ruch z wywołań kanonicznych `rs274` (podprogramy, pętle i cykle
  rozwinięte przez LinuxCNC), profil trapezowy od zera do zera na odcinek i łuk (górne oszacowanie względem G64),
  limity `[AXIS_*]` i `[TRAJ]` z INI wzdłuż kierunku ruchu, posuw F, przyspieszenie dośrodkowe na łukach, DWELL,
  stały czas wymiany `[LINUMERT]TOOL_CHANGE_TIME` (domyślnie 10 s); wynik całkowity, G0/G1/postoje/wymiany, na
  narzędzie i na krok `.lnx`. Jednostki calowe przeliczane.
- Testy: `tests/test_estimate.py` (7, w tym rs274 z pętlą `repeat`).
- Długi: „czas pozostały” na ekranie, tabela odchyłek względem Plant w `docs/SYMULACJA.md` i strojenie modelu.

## 2026-10-20 · Izolacja awarii smoke LinuxCNC · Codex

Model-Author: Codex. Run 113 ujawnił BadWindow i pozostawiony proces przed testami Plant.
Obsługa znikającego okna i zakończenie procesu w finally, także przy błędzie X11.
Trzy testy regresji offline OK; pełna weryfikacja w CI. Wynik nieudanego shutdown nadal jest błędem.

## 2026-10-20 · Program: kontrola składni w GUI · Codex

Model-Author: Codex. Przycisk Sprawdź składnię, lista z kodami alarmów i przejście do linii.
Kontrola ponownie czyta plik, obejmuje tekst poza pierwszymi 2000 liniami; limit 64 KiB,
lista do 100 błędów. Komunikat odróżnia składnię od semantyki i ruchu LinuxCNC.
Cztery funkcje testowe Program uruchomione na rzeczywistym Qt offscreen w chmurze: OK.
Brak komend ruchu przy kontroli; screenshot wykonany lokalnie. CI oraz odbiór w pełnym HMI pozostają.

## HMI — Cykle: baza narzędzi, czas, podprogramy (D36) · 2026-10-20 · Claude
- Strona Cykle pokazuje wynik `check_steps` po każdej zmianie kroków (narzędzie z bazy strony Narzędzia; brak bazy =
  jawny komunikat „niesprawdzone”), przycisk „Szacuj czas” (rs274 + limity INI w wątku tła, odczyt co 200 ms — GUI
  nie staje, watchdog HMI D35) i „Podprogramy NgcGui…” (eksport `o<lrt_...>`, domyślny katalog z
  `[RS274NGC]SUBROUTINE_PATH`, wpis z `user_macros`). Komunikaty o polach używają etykiet formularza.
- Testy: 3 nowe w `tests/test_hmi_workflow_widgets.py` (Qt offscreen). Zrzut z prawdziwym rs274:
  `docs/raporty/cykle/cykle_narzedzia_czas.png` (2:27 dla planowania 100×50, 2 warstwy; niezgodna średnica wykryta).

## Odbiór rozpoczętych gałęzi — 2026-10-20 · Codex
- Model-Author: Codex. PR #56 łączy #48/#50/#54/#55; historia każdego PR zachowana.
- Odzyskano niescalony 7a71581 Claude: Cykle/narzędzia/czas/NgcGui; autokontrola, bez niezależnego przeglądu.
- Poprawiono nieaktualny wynik czasu po edycji kroków i sprzątanie pliku interpretera przy zamknięciu.
- Kieszenie: test usuwania materiału, router krokowy Plant, rs274 i rzeczywisty widget Qt.
- Szablon routera: brakujący drugi czujnik bazy Y; pierwotna usterka odtworzona testem i usunięta.
- Starszy D33 z codex/hmi-01 miał kolidującą numerację; zachowana historia i treść zasad bez nadpisania obecnego D33.
- Pełny lokalny pytest: 816 PASS; 13 błędów testów sieci to EPERM sandboxa; wiążące testy Debian/LinuxCNC w CI.

## 026 — Odbiór automatyczny P0/G1 · 2026-10-20 · Codex
- Model-Author: Codex. Kod 4ca3f57: pełny runner Debian 12/LinuxCNC PASS, 81 testów CNC i 42 kroki HMI.
- Ogólne CI: 823 PASS; C: 108 PASS, sanitizery Debian PASS; scenariusze 9 + matrix 5 PASS, REQ bez błędów.
- Raport: docs/raporty/prototypy/P0-2026-10-20.md; MACIERZ zielona dla 21 bieżących REQ, REQ-VD-06 nadal planowane.
- Odbiór ręczny i sprzęt oddzielnie w G1.md; sesja 041 pozostaje częściowa. Autokontrola, bez niezależnego przeglądu.

## Launcher HMI i lista tygodnia · 2026-10-20 · Codex
- Model-Author: Codex. Po scaleniu #56: skróty HMI/Plant/QtDragon dla głównego repozytorium.
- Poprawiono Exec dla spacji i znaków specjalnych oraz rozpoznawanie worktree; instalacja skrótów bez kontenera i aktualizacji.
- Lokalnie 10 testów launchera PASS (w tym faktyczne uruchomienie przez Gio), shellcheck pominięty — brak narzędzia.
- Skróty menu i Pulpit zainstalowane; uruchomienie pełnego okna na pulpicie z sandboxa niewykonane.
- Lista braków i kryteria: docs/PLAN_TYGODNIA_2026-10-21.md; runtime sprawdzony w CI z raportu P0.

## Plan 21.10 — wejście do kieszeni · Codex
- Model-Author: Codex. Właściciel polecił kontynuować cały plan 21–27 bez czekania na odpowiedź, aż do „stop”.
- Wybór plunge/ramp/helix, kąt i podgląd w Cyklach; wejście posuwem od poprzedniej warstwy, bez pionowego cięcia w trybie rampy/helisy.
- Geometria wejścia mieści się w kieszeni, helisa nie zostawia centralnego rdzenia; ograniczenie liczby bloków także dla wejść.
- Golden, kontrola kąta i Z, testy objętości i Plant; rs274 i pełna regresja wymagane w CI przed scaleniem. Autokontrola, bez niezależnego przeglądu.

## Plan 22.10 — geometria i wykańczanie kieszeni · Codex
- Model-Author: Codex. Własne kontury z łukami G2/G3, obrót punktów i środków łuków, promień naroża, CW/CCW.
- Naddatki pozostają bez zaznaczenia wykańczania; osobny posuw, ściany warstwami i dno pełną ścieżką.
- Walidacja pasowania narzędzia z naddatkiem, naroży, dna i budżetu bloków. Krok XY uwzględnia odległość po przekątnej.
- Lokalnie 65 testów kieszeni/widgetów PASS; dodatkowe rs274 i wykonanie kieszeni na prawdziwym LinuxCNC + Plant do odbioru CI. Niezweryfikowane na sprzęcie.

## Plan 23.10 — pliki .lnx i edycja kroków w Cyklach · Codex
- Model-Author: Codex. Lista kroków i edycja wskazanego kroku; ponowna walidacja geometrii i narzędzi, unieważnienie oszacowanego czasu.
- Otwieranie i atomowy zapis .lnx przez istniejący model; zachowane jednostki, przygotówka, komentarze, włączenie kroków i wersje generatorów, także kieszenie v1.
- Niepoprawny plik nie zmienia bieżącego programu. Niezapisane zmiany wymagają świadomego odrzucenia w HMI. G-code pochodzi ze wspólnego kompilatora.
- Testy rzeczywistych kliknięć Qt offscreen, roundtrip i odrzucenia błędnego pliku; pełny odbiór CI przed scaleniem. Autokontrola, bez niezależnego przeglądu.

## Plan 24.10 — podgląd geometrii D38 · Codex
- Model-Author: Codex. Pierwsza działająca porcja: zakładka po zmierzonym śladzie XY, wycofanie Z, helisa i łuk styczny; okno podglądu z przycisku Symulacji.
- Sprawdzenie kopii materiału i modelu maszyny; obie strony/dwa promienie, odmowa przy naruszeniu materiału, kolizji, braku danych, ruchu, korekcji lub cyklu.
- Lokalnie 21 testów PASS i 6 subtestów; kliknięcie w złożonym HMI i zrzut okna, bez kanału komend CNC.
- Otwarte: external offsets w pauzie, dokładny stan/ścieżka interpretera, wznowienie wykonania. Podgląd nie eksportuje programu i nie wykonuje ruchu. Autokontrola, bez niezależnego przeglądu.

## Plan 25.10 — czas pozostały i porównanie z Plant · Codex
- Model-Author: Codex. Produkcja: szacowanie w tle, ETA podczas pracy i pauzy, unieważnienie po zmianie programu/INI, ograniczenia korekcji i startu od linii.
- Estymator uwzględnia limit Z helisy; jawnie odmawia nieobsługiwanej płaszczyzny/trybu posuwu i brakujących limitów XYZ.
- Lokalnie 41 testów czasu/widgetów/złożenia HMI PASS. Pomiar czasu dwóch kieszeni i planowania LinuxCNC + Plant oraz błąd modelu w pocket_calibration.json — odbiór CI wymagany.
- Wynik jest przybliżeniem, nie gwarancją czasu cyklu; start od XYZ=0 i oczekiwania operatora opisane w planie. Bez niezależnego przeglądu.

## Plan 26.10 — bieżący widok i oś czasu raportu · Codex
- Model-Author: Codex. Zrzut bufora OpenGL / zastępczego widoku 2D osadzony w HTML przez istniejący parametr view_png.
- Wspólny czas względny zdarzeń HMI/tabeli/osi SVG, odnośniki do wierszy i jawne pominięcia ponad limit 500. Usunięto sugestię, że diagnostyka zatrzymuje CNC.
- Test faktycznego kliknięcia Raport zapisuje HTML z obrazem Qt; test 3D/kamery przez Xvfb/Mesa wymagany w CI. Pyqtgraph już w runtime, dodany do CI.
- Brak dodatkowych zależności/licencji; autokontrola, bez niezależnego przeglądu. Odbiór ręczny na pulpicie nadal otwarty.

## Odbiór planu 21–27 — 2026-10-21 · Codex
- Model-Author: Codex. Zweryfikowano scalone #58/#59/#60 i końcowe CI 5f290103.
- Debian: 915 PASS + 96 LinuxCNC PASS, 12 subtestów PASS, 9 pominięć; ogólne CI PASS.
- Raport zawiera pomiar czasu trzech programów, granice D38 i niezaliczony protokół pulpitu.
- PR #61 domyka rejestr sesji 041 i dokumentację; bez nowych sesji i bez zmian kodu.
- Punkt 27 ręcznie niewykonany. Autokontrola, bez niezależnego przeglądu; NIEZWERYFIKOWANE NA SPRZĘCIE.

## D38 — wykonanie wycofania w pauzie · 2026-10-21 · Codex
- Model-Author: Codex. PR #62: Z przez external offsets, powrót i opcjonalne wznowienie.
- Kolejka i G41/G42 pozostają w LinuxCNC; brak Abort, MDI i kasowania korekcji.
- Blokada komend ruchu i HAL inhibit; zmiana kontekstu zamraża powrót, aż do wyłączenia.
- Lokalnie sześć testów modelu/widgetów Qt PASS; wyniki runtime i SHA w [PR #62](https://github.com/anonimov94/linumeRT/pull/62).
- Obejmuje pauzę bez wymiany narzędzia, nie powrót po Abort ani helisę z zakładką.
- Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Kontrola GitHuba i synchronizacja EndeavourOS · 2026-10-21 · Codex
- Model-Author: Codex. #62 scalony jako 979c672; brak otwartych PR/zgłoszeń i niescalonych gałęzi GitHuba.
- Poprawiono nieaktualne przekazanie i status D38: wycofanie/powrót w pauzie działa; Abort/E-STOP i helisa pozostają otwarte.
- Potwierdzono CI #62: 921 testów + 98 LinuxCNC PASS; ogólne CI main PASS.
- Lokalny main zaktualizowany z weryfikacją SHA obiektów; T12 i stare kopie robocze zachowane; skróty odświeżone.
- Pełne okno niewykonane: sandbox blokuje Podmana; ręczny odbiór pulpitu nadal wymagany.
- Zmiany wyłącznie dokumentacyjne. Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Dopracowanie planu 21–27 — ETA · 2026-10-21 · Codex
- Model-Author: Codex. Korekcja F/G0 unieważnia ETA całego przebiegu, także przed szacowaniem.
- Powrót do 100% nie przywraca wyniku opartego na niepoprawnym czasie; nowy pełny start resetuje historię.
- Lokalnie 41 testów czasu/widgetów PASS; lint PASS. Autokontrola, bez niezależnego przeglądu.
- Osobny checkout; tabela narzędzi i pliki właściciela zachowane. Odbiór pulpitu nadal otwarty.

## Dopracowanie planu 21–27 — D38-A · 2026-10-21 · Codex
- Model-Author: Codex. Ustawienia wysokości/posuwu z INI, jawna odmowa błędnej konfiguracji.
- Kontrola limitu po zaokrągleniu do rozdzielczości HAL, odmowa zerowego wycofania i pokazanie wysokości zadanej.
- Lokalnie 7 testów PASS i 10 subtestów; rzeczywiste kliknięcia Qt i błędne INI.
- Abort/E-STOP, wymiana narzędzia i wykonanie helisy nadal otwarte. Autokontrola, bez niezależnego przeglądu.
- Łącznie 50 testów funkcji PASS + 10 subtestów; złożenie HMI PASS; lint, C 108 i wymagania PASS.
- Próba pełna: 895 PASS; 8 porażek i 5 błędów przez zakaz gniazd; błąd środowiska pytest w procesie potomnym usunięto i złożenie HMI ponowiono z PASS.
- Odbiór runtime w kontrolach PR #64; ponowny `podman info` potwierdza blokadę `/run/user/1000`, więc pkt 27 niezaliczony.
- Regresja ułamkowej wysokości 1,001 mm: uwzględniono obcięcie float→s32 w HAL; testy GUI i LinuxCNC/Plant sprawdzają osiągnięcie pełnej liczby impulsów bez utknięcia.

## Odbiór pulpitu — start Plant z QtVCP · 2026-10-21 · Codex
- Model-Author: Codex. Właściciel odtworzył przerwanie startu: brak `sim_toolchange.in` w postgui.
- Plant ładuje teraz ten sam wirtualny komponent potwierdzenia M6 co symulator; obie odmiany wrzeciona korzystają ze wspólnego HAL.
- Nowa regresja uruchamia prawdziwy ekran HMI/klasyczny z Plant i nie usuwa POSTGUI ani nie włącza obejścia E-STOP.
- Sprawdza kompletne połączenia po starcie, działający sygnał życia GUI i zapisuje zrzut oraz log.
- Lokalnie 20 testów PASS, 1 pominięcie (shellcheck), lint PASS; odbiór runtime w CI wymagany przed scaleniem.
- Ręczny audyt pulpitu trwa. Autokontrola, bez niezależnego przeglądu; NIEZWERYFIKOWANE NA SPRZĘCIE.
- Pierwsze CI: 926 PASS; w CNC 97 PASS i 3 porażki. Dodano pełny log odmowy startu i wczesny test ekranu przed długą regresją.
- Test D38 czeka na ustalenie rzeczywistych napędów z zapasem przed kliknięciem powrotu; próg blokady produkcyjnej pozostaje 0,005 mm.

## Audyt — szacowanie pętli i izolacja rs274 · 2026-10-21 · Codex
- Model-Author: Codex. Właściciel odtworzył zamknięcie HMI po szacowaniu programu `while [1]`.
- Journal: SIGBUS w libtooldata, 21:20:50; rs274 w 2.9.10 współdzieli `$HOME/.tool.mmap` z sesją CNC.
- Gałąź `codex/bounded-offline-interpreter`: ograniczenie czasu/danych i zamykanie wyłącznie grupy procesu analizy; izolacja tabeli narzędzi w kolejnym kroku.
- Ręczny odbiór pozostaje otwarty. Autokontrola, bez niezależnego przeglądu.

Izolacja obejmuje teraz szacowanie i kontrolę semantyczną: prywatne HOME/TMPDIR/cwd, bez zapisu do wspólnego sim.var; 20 s/8 MiB, bez częściowego wyniku czasu. 108 testów lokalnych PASS (3 subtesty), w tym regresja starego rs274 uszkadzającego mmap oraz kliknięcie GUI i nadal dostępna kontrola składni. Autokontrola; PR #66 czeka na pełne CI. Model-Author: Codex.

## Audyt — wpisywanie liczb z klawiatury (2026-10-21)

Właściciel zgłosił pola działające tylko przez +/−. QtVCP kierował zdarzenia QAbstractSpinBox do skrótów maszyny; nakładka rozpoznaje edytory liczbowe i nie pozwala ich klawiszom propagować do skrótów. Krok JOG jest edytowalny, walidowany przed ruchem; zwolnienie zawsze zatrzymuje. 42 testy PASS: wpis, zaznaczenie, wklejenie, F1/F2/Esc i zwolnienie JOG po zmianie fokusu. Gałąź codex/numeric-keyboard-entry, kolejny krok: prawdziwy QtVCP. Autokontrola, Model-Author: Codex.

PR #67 rozszerza wpis na korekcje F/G0/S, synchronizuje suwaki i chroni rozpoczęty wpis przed odświeżaniem. 97 lokalnych testów PASS; samotest pełnego QtVCP wpisuje sześć rodzajów wartości i linię programu, zapisuje stany/zrzuty. Pełny wynik w kontrolach PR #66/#67; manualny punkt 27 otwarty. Autokontrola, Model-Author: Codex.
Pełne CI ujawniło ostrzeżenie rs274 przy pierwszym zapisie nieistniejących prywatnych parametrów, interpretowane jako błąd poprawnego programu. Inicjalizujemy plik i nadpisujemy także PARAMETER_FILE w prywatnej kopii INI (INI ma pierwszeństwo przed -v). Nowa regresja chroni absolutną ścieżkę parametrów sterowania; wczesny test Plant sprawdza również poprawny skończony program. 109 testów lokalnych PASS, autokontrola, Model-Author: Codex.

## Diagnostyka — trwała historia komunikatów · 2026-10-22 · Codex
- Model-Author: Codex. PR #68: ostatnie 1000 wpisów SQLite, oddzielnie dla konfiguracji INI.
- Filtr poziomu i wyszukiwanie; widok do 200, eksport CSV wszystkich pasujących wpisów.
- Błąd bazy nie usuwa komunikatu z widoku: jawny tryb pamięciowy, bez nadpisania uszkodzonego pliku.
- Diagnostyka przewijana na mniejszym ekranie; bez komend CNC i bez zmiany Resetu alarmów.
- Lokalnie 7 testów PASS: restart, retencja, filtry, awarie zapisu i faktyczne kliknięcia Qt/CSV.
- Próba złożonej Diagnostyki i zrzut Qt; pełne CI do odbioru w PR #68.
- Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Narzędzia — wyszukiwanie i filtr typu · 2026-10-22 · Codex
- Model-Author: Codex. Wyszukiwanie po T/P, opisie i wyświetlonych danych; filtr typu / bez typu.
- Filtry łączone, licznik widocznych/wszystkich; pozostają po odświeżeniu listy.
- Bez zapisu bazy/tool.tbl, bez komend CNC i bez automatycznego przełączenia edytora.
- Test klika rzeczywiste Qt i używa prawdziwej SQLite: lokalnie PASS; pełne CI do odbioru w PR.
- Własny podgląd z danymi testowymi; autokontrola, bez niezależnego przeglądu.

## Narzędzia — zachowanie zaznaczenia przy odświeżaniu · 2026-10-22 · Codex
- Model-Author: Codex. Odtworzono przeskok zaznaczenia T50→T30 po dodaniu rekordu.
- Odświeżanie zachowuje T i kolumnę, również dla ukrytego wiersza; nie ładuje innego narzędzia.
- Niezapisane pola edytora pozostają; po usunięciu T z bazy zaznaczenie jest czyszczone.
- Istniejące komórki aktualizowane bez ponownego setItem; brak ostrzeżeń Qt o własności.
- Regresja Qt/SQLite: przed poprawką FAIL, po poprawce PASS; brak komend CNC/zapisów z odświeżania.
- Dokumentacja i podgląd GUI; pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu.

## Narzędzia — eksport całej bazy CSV · 2026-10-22 · Codex
- Model-Author: Codex. Przycisk eksportuje wszystkie zapisane narzędzia, niezależnie od filtrów.
- Istniejący format ToolDB zachowuje geometrię, korekcje, kierunek, oprawkę i dane trwałości.
- QSaveFile zapisuje atomowo; anulowanie i błędy odczytu/zapisu nie zmieniają danych.
- Bez komend CNC, przeładowania tool.tbl i zapisywania pól edytora; opis zakresu w podpowiedzi.
- Dwa testy Qt/SQLite PASS, w tym ponowny import CSV, Unicode, anulowanie i błędy.
- Własny podgląd Qt; pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu.

## Narzędzia — pełne wartości obrotów i liczby ostrzy · 2026-10-22 · Codex
- Model-Author: Codex. Usuwanie końcowych zer dotyczy tylko części ułamkowej liczby.
- Przy formacie całkowitym 12000 obr/min i 10 ostrzy nie są już pokazywane jako 12 i 1.
- Zero pozostaje zerem; format wymiarów i oznaczenie braku danych zachowane.
- Regresja rzeczywistego Qt: stary kod FAIL, poprawka PASS; łącznie trzy testy GUI PASS.
- Własny podgląd tabeli/edytora; bez zmiany bazy i komend CNC. Pełne CI do odbioru w PR.
- Autokontrola, bez niezależnego przeglądu.

## Narzędzia — zachowanie danych poza formularzem · 2026-10-22 · Codex
- Model-Author: Codex. Odtworzono utratę oprawki, trwałości i korekcji innych osi przy edycji.
- Formularz aktualizuje edytowane pola istniejącego T; zachowuje pozostałe dane, w tym STL.
- Nowy numer T nie dziedziczy ukrytych pól poprzednio oglądanego narzędzia.
- Regresja starego kodu FAIL; cztery testy Qt/SQLite PASS, walidacja specjalnego STL i nowego T.
- Samo budowanie rekordu nie zapisuje bazy ani nie wysyła CNC; istniejąca ścieżka zapisu zachowana.
- Dokumentacja i przekazanie; pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu.
- NIEZWERYFIKOWANE NA SPRZĘCIE.

## Narzędzia — wskazanie modelu specjalnego STL · 2026-10-22 · Codex
- Model-Author: Codex. Pole ścieżki i Wybierz… tylko dla typu Specjalne STL; anulowanie zachowuje pole.
- Odczyt/zapis ścieżki przez istniejący rekord Tool i walidację; Nowe nie przejmuje ścieżki.
- Jawna informacja o walcu zastępczym w symulacji; brak ładowania ani analizy siatki.
- Edytor przewijany, długie wiersze zawijane; podgląd i próba rzeczywistego Qt w 1200×600.
- Pięć testów Qt/SQLite PASS: wybór/anulowanie, wymagane pole, reload, brak zmian pliku/CNC.
- Pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu.

## Narzędzia — błędy zapisu i brak statusu CNC · 2026-10-22 · Codex
- Model-Author: Codex. Brak statusu (utworzenie stat/poll) blokuje zapis i usunięcie; program nadal blokuje.
- Błędy pliku i SQLite pokazane w edytorze/alarmie, bez nieobsłużonego wyjątku z przycisku Qt.
- Po błędzie nie wysyła się przeładowania tabeli CNC; baza mogła już się zmienić, co mówi komunikat.
- Bez pozornego rollbacku ani zapewnienia atomowości bazy i pliku; operator sprawdza oba przed pracą.
- Dwie regresje na starym kodzie FAIL; sześć testów Qt/SQLite PASS, w tym blokada SQLite i częściowy zapis.
- Własny podgląd błędu; pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu.
- NIEZWERYFIKOWANE NA SPRZĘCIE.

## Narzędzia — podgląd historii zmian przed/po · 2026-10-22 · Codex
- Model-Author: Codex. Historia T… pokazuje do 100 najnowszych zmian dla T z edytora, także usuniętego.
- Pola przed/po z nazwami parametrów i jednostkami, czas UTC, rodzaj zmiany i źródło.
- Odczyt ograniczony w SQL; API historii bez limitu zachowuje dotychczasowe działanie.
- Bez przywracania danych i komend CNC; historia bazy nie potwierdza wczytania tabeli przez CNC.
- Dziewięć testów core/Qt/SQLite PASS: kolejność/limit, kliknięcie, pusta historia i błędne dane.
- Własny podgląd Qt i dokumentacja; pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu.

## Narzędzia — oprawka i ręczne dane trwałości · 2026-10-22 · Codex
- Model-Author: Codex. Formularz odczytuje/zapisuje nazwę oprawki, planowaną trwałość i ręczne zużycie.
- Brak planu = pusta trwałość; zużycie 0 poprawne. Nowe zeruje wartości, sama edycja nie zapisuje.
- Brak automatycznego naliczania i blokady po przekroczeniu planu; dopuszczone zużycie większe od planu.
- Core odrzuca ujemne/nieskończone/błędnie typowane czasy; próby zapisu/importu nie zmieniają rekordu.
- Trzynaście testów core/Qt/SQLite PASS, w tym roundtrip pól i błędny CSV; własny podgląd Qt.
- Dokumentacja poprawiona do bieżących pól; pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu.

## Narzędzia — walidacja liczb i odmowa niepoprawnego eksportu · 2026-10-22 · Codex
- Model-Author: Codex. Odtworzono eksport Dinf/Zinf i ciche obcięcie Q2.5→Q2.
- Skończone liczby w średnicy, korekcjach i I/J; Q całkowite 0…9, bez bool i nieznanych pól tokarki.
- params/offsets/lathe muszą być obiektami; wspólne sprawdzenie liczb obsługuje też zbyt duże int.
- Eksport waliduje stare rekordy przed zapisem pliku; błąd pozostawia poprzedni tool.tbl.
- Odmowa walidacji w Zapisz/Usuń jest obsłużona w HMI, bez przeładowania CNC.
- Dwie regresje starego kodu FAIL; 17 testów core/Qt/SQLite PASS, także atomowość wsadu CSV.
- Pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Narzędzia — korekcja średnicy w tabeli LinuxCNC · 2026-10-22 · Codex
- Model-Author: Codex. Odtworzono pominięcie d_wear: nominalne 6 i −0,02 dawało D6 zamiast D5.98.
- D tabeli = nominalne d + d_wear; zwykły wpis bez geometrii zachowuje surowe D tabeli.
- Import efektywnego D zachowuje korekcję i wylicza nominalne d, bez ponownego dodawania zużycia.
- Odrzucenie D po korekcji <= 0 oraz niezerowej korekcji bez nominalnego d.
- Regresje starego kodu FAIL; 21 testów lokalnie PASS, także rzeczywisty Cutter i import mm/cale.
- Cztery próby G41/G42 z ± korekcją w rzeczywistym rs274 dodane do CI; lokalnie niewykonane.
- Pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Narzędzia — jednostki tabeli zgodne z INI · 2026-10-22 · Codex
- Model-Author: Codex. Odtworzono import D0.25/Z2 z profilu calowego jako mm zamiast 6,35/50,8 mm.
- Odczyt TRAJ/LINEAR_UNITS; import tabeli i eksport danych startowych z jednostkami maszyny.
- Zapisz/Usuń w HMI przekazują jednostki tabeli, baza i pola długości pozostają w mm; kąty bez skali.
- Nieznane jednostki odrzucone przed zapisem; przy braku ustawienia zachowany domyślny mm.
- 26 testów lokalnie PASS, także rzeczywiste przyciski Qt, dane startowe i brak mutacji przy błędzie.
- Próby G41/G42 w rs274 rozszerzone o tabelę calową; lokalnie niewykonane, odbiór przez CI.
- Oddzielny dług przeliczenia pozycji/WCS/narzędzi Live zapisany; brak deklaracji pełnej symulacji calowej.
- Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Symulacja — wspólne jednostki mm procesu Live · 2026-10-22 · Codex
- Model-Author: Codex. XYZ, WCS z parametrów/statusu i Z/D tabeli przeliczane z jednostek INI na mm.
- Silnik, komunikaty położenia i ślad końcówki otrzymują te same fizyczne długości dla mm/inch.
- Nieznane jednostki raportowane zdarzeniem error przed startem odczytu i wątku poleceń.
- Odtworzono regresję starego kodu FAIL; 30 testów lokalnie PASS (21 core/sim oraz 9 rzeczywistego Qt).
- Testy obejmują WCS, narzędzie zastępcze i typowane, identyczną mapę materiału oraz ślad końcówki.
- Atrapa statusu nie udostępnia komend CNC; bez zmian toru ruchu/safety. Fixture podglądu jawnie mm.
- Wymagane pełne CI, ręcznego odbioru calowego HMI/obrabiarki nie zaliczono.
- Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Symulacja — aktualny WCS początku przygotówki · 2026-10-22 · Codex
- Model-Author: Codex. Odtworzono użycie starego X1 z pliku zamiast bieżącego X20 z G54.
- Aktywny WCS bierze początek ze świeżo odczytanego statusu; inny z zapisanych parametrów.
- Nie podstawia się przesunięcia aktywnego układu pod brakujący nieaktywny WCS.
- Brak danych lub błąd poll daje error i zachowuje poprzednią mapę/definicję, bez komend CNC.
- Regresja starego kodu FAIL; 32 testy lokalnie PASS, także przeliczenie zapisanego nieaktywnego WCS.
- Dokumentacja opisuje świeżość statusu i ograniczenie pliku parametrów; pełne CI do odbioru w PR.
- Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Narzędzia — wskaźnik niezapisanych zmian · 2026-10-22 · Codex
- Model-Author: Codex. Bursztynowy napis przy T po edycji, także liczby przed Enterem.
- Programowe wczytanie i udany Zapis czyszczą wskaźnik; Nowe oznacza niezapisany formularz.
- Filtry/refresh zachowują stan; kolejna edycja czyści stare potwierdzenie sukcesu, nie błąd zapisu.
- Usunięcie ma własny komunikat i nagłówek; bez automatycznego zapisu i zmiany komend CNC.
- 33 testy lokalnie PASS, w tym rzeczywista klawiatura/przyciski Qt, SQLite i obsługa błędu.
- Podgląd Qt i dokumentacja; potwierdzenie porzucenia edycji pozostaje osobnym zakresem.
- Pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu.

## Narzędzia — ochrona porzucenia edycji · 2026-10-22 · Codex
- Model-Author: Codex. Inny T/Nowe pyta o odrzucenie niezapisanych pól; Zostań jest domyślne i pod Escape.
- Anulowanie odtwarza poprzednie zaznaczenie, również ukryte lub brak zaznaczenia dla nowego T.
- Docelowy rekord czytany po dialogu; jego zniknięcie/błąd odczytu zachowuje formularz z komunikatem.
- Zapis klonu/nowego T zaznacza zapisany numer; odrzucenie nie zapisuje danych ani nie cofa bazy.
- Regresja starego kodu FAIL; 35 testów lokalnie PASS, w tym prawdziwe okna/klawisze Qt i SQLite.
- Podgląd i dokumentacja; pełne CI do odbioru w PR. Autokontrola, bez niezależnego przeglądu.

## GUI SKIN-00 — 2026-10-23 · Codex

- Audyt QtVCP/QSS/renderera i kolejność zmian według nowych wytycznych.
- Kontrakt prototypu: osobne skórka/motyw/język, wersjonowany JSON, cztery palety.
- 4 testy unittest PASS: 32 kombinacje, walidacja, niezmienność, kontrast 4.5:1.
- Grafit wymaga jaśniejszego tekstu błędu; obecna prezentacja pozostaje bez zmian.
- Pełny Qt/LinuxCNC i GPU/Mesa niewykonane lokalnie. Bez scalania na życzenie właściciela.
- Model-Author: Codex. Następne kroki: docs/design/SKIN_AUDIT.md.

## GUI — wspólne napisy prototypu EN/PL · 2026-10-23 · Codex

- Dodano katalog nawigacji, trybów i stanów, niezależny od skórki oraz palety.
- Brakujące klucze dają jawny błąd; identyfikatory alarmów nie są tłumaczone.
- 6 testów unittest PASS, 32 kombinacje; pełne tłumaczenie obecnych stron poza zakresem.
- Model-Author: Codex. Bez scalania.

## GUI — manifesty i warunki przełączenia · 2026-10-23 · Codex

- Poprawiono rejestr dokładnych ścieżek dokumentów: przyczyna błędu poprzedniego CI.
- Manifest API 1 sprawdza komplet widoków, globalnych kontrolek i rozdzielczości.
- Niezmienny model warunków przełączenia odmawia przy ruchu, programie, bazowaniu,
  oczekujących komendach, braku/nieaktualności statusu. Bez dostępu do ACTION/HAL.
- Lokalnie 20 testów + 87 subtestów PASS (kontrakty i strażnik IP), ruff PASS.
- Integracja powłoki i renderer pozostają do wykonania; bez scalania.
- Model-Author: Codex. Szczegóły kontraktu w docs/design/SKIN_AUDIT.md.

## GUI — osobny podgląd czterech kompozycji Qt · 2026-10-23 · Codex

- Dodano tools/dev/skin-preview.py i niezależne okno PyQt5, bez LinuxCNC/HAL.
- Cztery układy, cztery palety, EN/PL; status niedostępny, STOP/Hold nieaktywne.
- Panele 3D oznaczone jako niepodłączone; to studium układu, nie kompletny HMI.
- Lokalnie 22 testy + 87 subtestów PASS; Qt obejmuje 64 warianty i cele >=44 px.
- Ruff i diff-check PASS; wizualna kontrola zrzutów Windows/offscreen po dodaniu
  fontu systemowego (tryb offscreen nie wylicza fontów). Bez redystrybucji fontu.
- Model-Author: Codex. Bez scalania; docelowy renderer/GPU oraz podłączenie CNC do wykonania.

## PR #67 — lokalizacja kroku JOG przed scaleniem · 2026-10-23 · Codex

- Właściciel zezwolił na scalanie ukończonych aktywnych gałęzi; #67 odświeżono main.
- Qt/Windows odtworzył 2.5 → 25 przy rozbieżności lokalizacji walidatora i edytora.
- Usunięto filtr klawiszy; wpis walidowany dopiero przed JOG, bez separatorów tysięcy.
- 13 testów Qt PASS: C/PL/DE, kropka/przecinek, błędny wpis i zatrzymanie mimo błędu.
- Model-Author: Codex. Pełne CI po poprawce wymagane przed scaleniem.

## SKIN-01 — reprodukcja geometrii · 2026-10-23 · Codex
- Model-Author: Codex. Main po #67/#86, 11 lokalnych plików zachowanych bajt w bajt.
- Osobny checkout/gałąź, bez przejmowania globalnej blokady i instancji CNC.
- QPainter: rzeczywisty obraz przecinających się trójkątów potwierdza złe zasłanianie.
- Stare _revolve: 48 zerowych trójkątów kapsli przy 24 segmentach.
- Przygotówki box/cylinder/tube/casting i próbka STL mają poprawny winding/objętość.
- Nowy kontrakt siatki odrzuca błędne indeksy/NaN i jawnie liczy degeneracje.
- 13 lokalnych testów PASS, ruff PASS; prototyp GL i odbiór GPU/Debian jeszcze w toku.
- Autokontrola, bez niezależnego przeglądu; bez zmian renderera produkcyjnego.


## 085 — SKIN-01: renderer 3D (PR #87) · 2026-10-23 · Codex
- Model-Author: Codex. Osobny offline podgląd GL z trzema scenami, kamerami, cullingiem, wireframe i odświeżeniem ≤30/s.
- Odtworzono przecinające się trójkąty QPainter oraz 48 zerowych ścian w starym `_revolve`.
- Radeon 660M/Mesa 26.2 oraz Debian 12/LinuxCNC 2.9.10/llvmpipe Mesa 22.3: depth 24, order 0%, culling zamkniętych brył, 3 kamery, obrót i limit klatek PASS.
- Debian 12 lokalnie: 1018 pytest PASS, 10 skip, 109 deselected; requirements (21/22, 0 błędów), lint, test-c i test-san PASS.
- Końcowe CI Python + Plant matrix + LinuxCNC RIP PASS; 109 testów LinuxCNC PASS. Artefakty zrzutów w `build/skin01/`.
- PR #87 scalony 2026-10-23 jako `b22689f`. Autokontrola, bez niezależnego przeglądu.
- NIEZWERYFIKOWANE na konkretnym GPU właściciela ani na fizycznej obrabiarce.

## 086 — podgląd skórek według materiałów właściciela · 2026-10-23 · Codex
- Model-Author: Codex. PR #89, osobny checkout; lokalne pliki operatora nietknięte.
- Pobrano/obejrzano cztery wzorce WEBP; zachowano pochodzenie i ograniczenia licencji.
- Odrębne kompozycje i obudowy, wskaźniki, trzy sceny OpenGL i powiększanie paneli.
- Test Qt obejmuje przywracanie układu oraz usuwanie ukrytych kart po przełączeniu.
- Naprawiono puste złożone panele po przełączeniach przez współdzielenie kontekstów Qt.
- Radeon/Mesa i Debian llvmpipe: po końcowej poprawce 64 warianty PASS; 23 testy + 87 subtestów PASS.
- Debian: lint PASS, 1018 pytest PASS, 11 skip, 109 deselected, wymagania bez błędów.
- Autokontrola, bez niezależnego przeglądu. Offline; pełne skórki i CNC nadal otwarte.

## 087 — nowe zrzuty i README · 2026-10-23 · Codex
- Model-Author: Codex. PR #89 scalony (8483b81); lokalne main zaktualizowane.
- Polecenie właściciela: odświeżyć docs/raporty/hmi_sym i README projektu, PR #90.
- Cztery nowe zrzuty skórek Qt 1920×1080; osobny raport i rozróżnienie offline/CNC.
- Przebieg obróbki ujawnił zagnieżdżony komentarz M4: stary odbiór zaliczał przerwane demo.
- Poprawiono komentarz i kontrolę finału (T11 + idle), regresje leksera obu programów.
- Świeże obrazy z rzeczywistego LinuxCNC i wynik JSON; K-302 wyłącznie diagnostycznie.
- Autokontrola, bez niezależnego przeglądu; końcowy stan kontroli/scalenia w PR #90.

## 088 — osobne ekrany skórek według wizji · 2026-10-23 · Codex
- Model-Author: Codex. PR #91, osobny checkout; lokalne pliki operatora zachowane.
- Cztery osobne klasy/moduły, układy paneli, konsole i typografia według obrazów właściciela.
- Fizyczne klawisze, selektor obrotowy, przełączniki, ramki ścięte i płynne metalowe obudowy.
- Samodzielny launcher --skin, lokalna nawigacja, atomowe ustawienia; podpisy EN/PL bez obcięcia.
- Komendy CNC nieaktywne; grzyb to nieinteraktywny wskaźnik stanu nieznanego.
- Radeon i Debian/Mesa: 128 wariantów PASS; Debian 26 testów + 87 subtestów PASS.
- Nowa galeria w README/raporcie; pełna integracja QtVCP i szczegółowe modele nadal otwarte.
- Autokontrola, bez niezależnego przeglądu; wynik końcowego CI i scalenia w PR #91.

## Konkurs 04 — read-only integracja skórek · 2026-10-23 · Codex
- Model-Author: Codex. PR #96, osobny checkout; bez scalania przed oceną konkursu.
- Wspólny typowany adapter stat/NML, osobny monitor czterech skórek, G53 mm/°.
- Brak komend/HAL/odbierania error_channel; produkcyjny handler bez zmian.
- Jednorazowy proces izoluje tool mmap; limit 500 ms, wygaszenie i reconnect.
- LinuxCNC 2.9.10 + Xvfb: brak CNC → odczyt → utrata → restart PASS, bez resetu E-STOP.
- Debian 1039 PASS/10 skip, lint/wymagania i 108 testów C + ASan/UBSan PASS.
- Końcowy Qt/IP: 41 PASS + 87 subtestów; logi/zrzuty w build/skin-monitor, raport raporty/04.md.
- Autokontrola; świeżość producenta NML niepotwierdzona. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Konkurs 01 — bramka konfiguracji przed startem CNC · 2026-10-23 · Codex
- Model-Author: Codex. PR #93; osobny worktree i gałąź, bez scalenia przed oceną.
- Deklaracje hardware i ograniczony audyt HAL wymagane przed exec LinuxCNC.
- Główny starter korzysta z bramki; trzy INI sim/Plant mają jawne profile; HAL bez zmian.
- 41 testów bramki/deklaracji/HAL PASS; pełny make lint test: 1033 PASS, 11 skip; wymagania bez błędów.
- CI wykryło RuntimeError Path.resolve na Pythonie 3.11; poprawiono jawną odmowę; raport opisuje granice.
- Autokontrola, bez niezależnego przeglądu; NIEZWERYFIKOWANE NA SPRZĘCIE.

## Konkurs 3 — pokrycie wymagań poza GUI · 2026-10-23 · Codex
- Model-Author: Codex. Osobna gałąź/worktree, PR #95; raport audytu `raporty/03.md`.
- Ustalono luki: real mapping napędów, walidacja geometrii ATC i NaN/inf w schemacie.
- Zamknięto lukę liczbową REQ-VM-11/REQ-QA-03; polskie błędy z pełną ścieżką pola.
- Regresja starego kodu: 75 FAIL/4 PASS; po poprawce 167 testów wybranego zakresu PASS.
- Debian: 1104 pytest PASS, 10 skip, 109 deselected; po 108 testów C i ASan/UBSan PASS.
- Lint i wymagania PASS (21/22, 0 błędów); zapis/reload panelu zachowuje model po odmowie.
- Autokontrola, bez niezależnego przeglądu. Bez zmian safety-profile, odbioru i skórek.
- NIEZWERYFIKOWANE NA SPRZĘCIE. Bez scalenia do wspólnej oceny konkursu; dalszy etap w raporcie.

## Konkurs 2 — odbiór stanowiska · 2026-10-23 · Codex
- Model-Author: Codex. PR #94, osobny checkout; bez scalania przed oceną konkursu.
- Procedura A–E/T1–T7, szablon PASS/FAIL/BLOCKED, powiązania G1/RT i surowe dowody.
- Debian: 1024 pytest + 166 subtestów PASS; C/ASan/UBSan PASS; demo HMI T11/IDLE i K-302 PASS.
- OD-01 odtworzone: macierz router_atc_rack ma kod 0 mimo CRASH/COVER_CRASH; odbiór A3 FAIL.
- Raport i końcowy wynik CI: `prompts/konkurs-2026-10/raporty/02.md`.
- Pulpit właściciela i T1–T7 niewykonane; NIEZWERYFIKOWANE NA SPRZĘCIE.

## ISO — integracja funkcji · 2026-10-23 · Codex
- Zmiany ISO na `codex/iso-integrated`: launcher obrazu używa bramki profilu `sim`/`plant` i kontroluje proces Plant.
- Dodano menu osobnego monitora skórek read-only do statusu działającego LinuxCNC.
- Workflow PR buduje i publikuje artifact testowy bez tworzenia Release; trwała publikacja wyłącznie z ręcznego `workflow_dispatch` (D39).
- README i provenance opisują aktualny zakres obrazu. Budowa ISO i testy CI pozostają do zakończenia PR.
- Uruchomienie i obraz: symulacja, NIEZWERYFIKOWANE NA SPRZĘCIE.
- Model-Author: Codex.

## Wspólna roadmapa — 2026-10-24 · Codex
- Model-Author: Codex. Na polecenie właściciela: jeden rejestr 84 sesji i późniejszych rozszerzeń.
- `plan.json` → generator → spis promptów, DONE, pełny plan i HTML; brak statusów w localStorage.
- Zachowano numerację, aliasy i historyczne dowody; 007/048 skorygowano na częściowe.
- Instrukcje sesji korzystają z rejestru; dawne plany są specyfikacjami/historią, przekazanie odchudzono.
- Lokalnie: lint, 1071 pytest PASS (88 skip bez GUI), REQ 21/22 bez błędów; odbiór DOM PASS.
- Końcowy generator/IP: 20 testów PASS; pełne CI i SHA w PR #99 (LinuxCNC/Plant osobno).
- Autokontrola, bez niezależnego przeglądu. Bez zmiany funkcji CNC i odbioru sprzętowego.

## Lekcja AI — dyscyplina pierwotnego planu · 2026-10-24 · Codex
- Model-Author: Codex. Polecenie właściciela: zachować wnioski audytu dla następnych sesji.
- Reguła w WSPOLPRACA_MODELI: cel i ID przed pracą, domykanie kryteriów/bramek M0–M6.
- Nowe pomysły są rozszerzeniami; jawna zmiana priorytetu właściciela ma zapis wpływu na plan.
- Prompt startowy i Savoir-vivre AI przypominają lekcję; bez nowej listy statusów i zmian funkcji CNC.
- Walidacja: roadmapa i lint PASS; 1072 pytest PASS, 88 skip, REQ 21/22 bez błędów; PR #100.
- Tylko dokumentacja; autokontrola, bez niezależnego przeglądu, scalanie według §5 WSPOLPRACA_MODELI.

## Edytor G-code — walidacja i wyszukiwanie · 2026-10-24 · Codex
- Model-Author: Codex. Roadmapa 044/HMI-04: kontrola niezapisanej treści w Program → Edytuj kopię.
- Lista błędów z przejściem do linii/kolumny (także Unicode); edycja unieważnia wynik.
- Wyszukiwanie dosłowne, zamiana pojedyncza/wszystkich, jedna operacja Cofnij; limit wyniku 256 KiB.
- 10 testów Qt PASS, ruff i kontrola wymagań PASS; zrzut build/editor-preview.png.
- Szerszy zestaw Windows ujawnił ograniczenia lokalizacji, kodowania i dowiązań; odbiór LinuxCNC przez CI.
- Kontrola składni do 64 KiB nie jest kontrolą semantyki/ruchu. Bez nowych zależności produkcyjnych.

## Domknięcie edytora PR #98 — 2026-10-24 · Codex
- Model-Author: Codex. Polecenie właściciela: dokończyć wszystkie rozpoczęte gałęzie i scalić.
- 044/047, EDITOR-VALIDATION: zachowano walidację, wyszukiwanie i Undo; integracja z nowym rejestrem.
- Zachowano obie historie dziennika/provenance; przekazanie korzysta z bieżącego dokumentu main.
- Debian 12/Qt: 60 testów zakresu PASS; rzeczywisty dialog zapisany w build/editor-closeout/.
- Pełne kontrole i SHA w PR #98; autokontrola, bez niezależnego przeglądu.

## Domknięcie ISO i historii gałęzi — 2026-10-24 · Codex
- Model-Author: Codex. Polecenie właściciela: ukończyć i scalić istniejące gałęzie; zakres 044/047/077.
- ISO: zachowano poprawki user-setup/sudo, konto linumert, autologin i test realnego tworzenia konta.
- Debian 12: konto, UID 1000, hasło, home, sudo i drugie uruchomienie testu PASS; 8 testów ISO PASS.
- Pięć lokalnych gałęzi ma wyłącznie poprawki równoważne main; historia scalona, drzewo bez zmian.
- Raport: docs/raporty/ZAMKNIECIE_GALEZI_2026-10-24.md; końcowe kontrole i SHA w PR #101.
- Bez publikacji wydania i odbioru sprzętu; autokontrola, bez niezależnego przeglądu.

## Awaria HMI przy podglądzie powrotu w pauzie — 2026-10-24 · Codex
- Model-Author: Codex. Zakres 031/045/057: naprawa zgłoszonego błędu bieżącego HMI.
- Log operatora: QtVCP /usr/bin/python3 nie widzi pydantic z venv startera; wyjątek w podglądzie D38.
- Bramka exec przekazuje ścieżki zależności venv; wspólny Preview2D nie importuje kompilatora cykli.
- Przed poprawką 2 regresje FAIL; po poprawce 94 testy zakresu i 10 subtestów PASS w Debianie 12.
- Pełny HMI z bramki startera: 15 kroków PASS (42,72 s), pauza/podgląd/raport/Z+2 mm/powrót/wznowienie.
- Nowy test integracyjny wewnątrz QtVCP, zrzuty i raport; brak zmian progów oraz zabezpieczeń ruchu.
- Autokontrola, bez niezależnego przeglądu; końcowe SHA i pełny odbiór w PR #102.

## OD-01 — Macierz Plant bez nieoczekiwanych kolizji — 2026-10-24 · Claude
- Model-Author: Claude. Zakres 024/066/072/082; pierwszy punkt kolejności z WSPOLPRACA_MODELI.md.
- Przyczyna: losowy start po włączeniu (ziarno 1) w router_atc_rack lądował wewnątrz magazynu (CRASH, COVER_CRASH).
- Start omija bryły kolizyjne: Python odtwarza xorshift32 rdzenia C i zmienia pozycję tylko przy kolizji (inne starty bez zmian).
- matrix_smoke wymaga teraz `event: CRASH` i `COVER_CRASH` z `present: false`; przed poprawką FAIL 2/4, po niej 5 maszyn × 4/4.
- Testy: nowy tests/test_start_collision.py, 1116 PASS; test_sim_engine::test_sample_programs_stock_lines pada przez plik bez ;@STOCK w config/sim/nc_files (poza zakresem).
- Autokontrola, bez niezależnego przeglądu; ponowny odbiór A3 na stanowisku właściciela osobno.

## LEGACY-RUNTIME — zrywanie LRT-NET przy zakładkach panelu Plant — 2026-10-24 · Claude
- Model-Author: Claude. Zgłoszenie właściciela: przełączanie zakładek Praca/Napędy/Maszyna daje „N cykli bez odpowiedzi” (do 335).
- Pomiar na żywo: serie 70–350 zgubionych cykli; wątek RT LinuxCNC i ekran nie głodowały (opóźnienie kolejki 0–2 ms), więc zatrzymywał się proces Plant.
- Przyczyna: endpointy zakładek wołały `load_library` (102 ms czystego Pythona, 7 szablonów YAML) w wątku panelu; GIL opóźniał odpowiedzi pętli UDP.
- Poprawka: CSafeLoader, cache biblioteki wg mtime/rozmiaru plików (kopia głęboka), `sys.setswitchinterval(0.0005)` w `serve`.
- Odtworzenie lokalne (Plant + lrtnet_probe 1 kHz + odpytywanie endpointów): przed RTT maks. 242 ms, 130 utraconych, watchdog; po 11,9 ms, 0 utraconych.
- Testy: tests/test_library_cache.py. Nie zmieniono timeout-cycles ani łańcucha E-STOP. Do potwierdzenia na pulpicie właściciela.

## PLAN-27 — częściowy ręczny odbiór pulpitu — 2026-10-24 · Claude
- Model-Author: Claude. Właściciel przeszedł checklistę na własnym pulpicie (HMI z Plant, SHA 4bc7a14 i 27b9245).
- Potwierdzone: punkty 1–6 i 8; przełączanie kart panelu Plant nie zrywa łącza po poprawce LEGACY-RUNTIME.
- Otwarte: punkt 7 (raport HTML), skróty QtDragon/Plant z menu, zrzuty i log. NIEZWERYFIKOWANE NA SPRZĘCIE.

## LIMITS-PREFLIGHT — kontrola limitów osi przed startem — 2026-10-24 · Claude
- Model-Author: Claude. Zakres 031/051; sugestia właściciela po zatrzymaniu maszyny w materiale z błędem limitu Z.
- LinuxCNC odrzuca ruch dopiero w planerze; teraz edytor G-code ma przycisk „Sprawdź limity osi” (praca w tle, bez blokowania GUI/heartbeat).
- Rdzeń `programs/limits.py`: rs274 z kopią pliku parametrów i jednostkami z INI; pozycja maszynowa = program + G5x + G92 + korekta długości; numery linii pliku.
- Odtworzono zgłoszony błąd: G54 Z=-150, `G0 Z20` → linia 3, Z=-130 < -120; po offsecie -50 brak naruszeń (rs274 w Debianie 12).
- Nie zmieniono zachowania LinuxCNC ani limitów; sprawdzane tylko punkty końcowe (łuki, obrót XY, osie ABC pominięte).
- Testy: tests/test_limits.py (7 + 1 z rs274), test GUI w tests/test_hmi_workflow_widgets.py (42 PASS w Debianie).

## Starter — jedna instancja linumeRT — 2026-10-24 · Claude
- Model-Author: Claude. Zgłoszenie właściciela: aplikacja padła po uruchomieniu drugiej kopii.
- Dowód w logu: druga instancja LinuxCNC dostała „tpmod/homemod/trivkins: already exists” (wspólne zasoby), po czym obie zostały zatrzymane.
- Kontener ma teraz stałą nazwę `linumert-hmi`; starter odmawia drugiego startu komunikatem i podaje `podman stop linumert-hmi`. Tryb `--shell` bez blokady.
- Test z atrapą podmana (nazwa kontenera, odmowa, brak `podman run`); 11 PASS. Nieprzetestowane na pulpicie właściciela.

## ORIGIN-WIZARD — kreator zera detalu na przygotówce — 2026-10-24 · Claude
- Model-Author: Claude. Polecenie właściciela: kreator wyboru punktu zera na przygotówce jak w programach CAM.
- Rdzeń: `Workpiece` ma 10 punktów zera (narożniki i środek, góra/dół), `bounds()` i `fit_issues(limits)`; `anchor_name()` z kliknięcia.
- GUI: „Kreator zera detalu…” w Zero detalu: widok z góry, klik punktu, narożnik i wierzch przygotówki na stole w G53, pobranie pozycji narzędzia jako zera, kontrola zakresów osi z INI.
- Zmiana punktu zera nie rusza przygotówki (przelicza zero); przesunięcie narożnika przesuwa przygotówkę. Wynik trafia do formularza, G5x zapisuje osobny przycisk.
- Testy: 65 PASS (rdzeń + GUI w Debianie 12), zrzut build/kreator/kreator.png. Do sprawdzenia na pulpicie.

## LIMITS-PREFLIGHT — automatyczna kontrola po wczytaniu programu — 2026-10-24 · Claude
- Model-Author: Claude. Polecenie właściciela: zachowanie jak w sprzęcie przemysłowym.
- Przyczyna komunikatów K-301/302/303/305 w CSV: program z G49 (bez G43) przy narzędziu T2 o długości 80 mm; symulator liczy czubek jako oś − 80 mm, więc czubek wchodzi w materiał i stół.
- Po wczytaniu programu ekran sprawdza go w tle (rs274 + parametry układów, jednostki INI); wynik na stronie Produkcja; „Cykl start” pyta, gdy program wyjdzie poza limity osi (domyślnie Nie).
- Ostrzeżenie informacyjne, gdy program tnie przy nieaktywnej korekcie długości (G49). Nic nie blokuje sterownika; ekran nie jest funkcją bezpieczeństwa.
- Raport grupuje powtórzenia (jeden wiersz + licznik); kreator zera wyraźnie oznacza wynik poza zakresem osi.
- Testy: 54 PASS w Debianie (GUI + rdzeń); do sprawdzenia na pulpicie. Poza zakresem: automatyczne G43 po M6 (remap).

## LIMITS-PREFLIGHT — poprawki po uwadze właściciela — 2026-10-24 · Claude
- Model-Author: Claude. Uwaga właściciela: g54 wczytuje się automatycznie przy starcie.
- Kontrola uruchamia się też dla programu wczytanego przed podłączeniem statusu (start ekranu).
- Błąd własny: oś jeszcze nieruszona przez program (interpreter startuje w zerze maszyny) dawała fałszywe „X=0 poniżej limitu 1” w konfiguracji Plant; teraz oś jest oceniana od pierwszego ruchu.
- Na g54: sim — linia 13, Z=-130 < -120 (i 81 ruchów); Plant — linia 9, Z=-134 < -119 (i 85 ruchów); G49 bez G43.
- Testy: 55 PASS (GUI + rdzeń), 3 PASS z prawdziwym LinuxCNC (start ekranu).

## M6-G43 — automatyczna korekta długości po wymianie narzędzia — 2026-10-24 · Claude
- Model-Author: Claude. Polecenie właściciela: automatyczne G43 po M6.
- Remap `REMAP = M6 modalgroup=6 ngc=lrt_m6` w INI sim, Plant i Plant+VFD; `macros/lrt_m6.ngc` w każdej konfiguracji (kopie pilnowane testem) czyta numer z T, wykonuje wbudowane M6 i `G43 H<n>` (T0 → G49).
- Powód kopii w katalogu konfiguracji: testy i instalacje kopiują katalog `config/...`, względne `../../` się rozjeżdża.
- Kontrola limitów (`run_interpreter(machine_ini=…)`) wczytuje remapy i SUBROUTINE_PATH z INI maszyny, żeby nie zgłaszać fałszywego „bez korekty długości”.
- Testy: 5 w tests/test_m6_remap.py (w tym rs274 z INI maszyny: T2 M6 → 80 mm, T0 M6 → 0), e2e `sim-e2e.sh` PASS (demo 306 s, 6 wymian, bez kolizji).
- Nie obejmuje Facing z QtDragon (G49, bez M6) ani ATC. NIEZWERYFIKOWANE NA SPRZĘCIE; do sprawdzenia ręcznie wymiana M6 w oknie QtDragon.

## Classic × Neon — renderer detal + maszyna · 2026-10-24 · Claude
- Model-Author: Claude. Gałąź `claude/neon-render` (worktree), polecenie właściciela: render jak w koncepcji HTML.
- Rdzeń `programs/toolpath.py`: ruchy z liniami programu, łuki ARC_FEED, strefy START/KONIEC, DTG,
  `locate(motion_line, pozycja)`; odbiornik `PreviewCanon` dla `gcode.parse` (bez LinuxCNC nietestowany z interpreterem).
- `linumert_neon_view.py`: scena wspólna, widok detalu (śledzi narzędzie), widok maszyny, oś programu;
  Classic używa go dla ról toolpath/machine, gdy host ma fabrykę widoków. Motyw `neon-punk`.
- `tools/dev/neon-preview.py` (okno i `--png`), program `linumert_neon_demo.ngc`, koncepcja HTML w `docs/design/koncepcje/`.
- Testy: 10 nowych (model + Qt offscreen), pełne pytest lokalnie (WSL, Python 3.11, bez LinuxCNC): 1143 PASS, 12 skip; ruff PASS.
- Otwarte: podłączenie do `stat.motion_line`/`stat.file` w monitorze NML, test `PreviewCanon` z prawdziwym `gcode`.
- Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Classic × Neon — sposoby renderowania · 2026-10-24 · Claude
- Model-Author: Claude. Polecenie właściciela: ustawiany render z cieniowaniem dla detalu i maszyny, oszczędnie jak w grach.
- `linumert_neon_render.py`: RenderSettings + 3 presety, profil QSettings (uszkodzony wpis → preset), regulator jakości,
  cieniowanie Lamberta z cullingiem, cienie rzutowane, tekstura materiału warstwami Z z `StockMap`.
- `linumert_neon_view.py`: menu ⚙ per widok, warstwy wypiekane/przesuwane, akumulacja wykonanych ruchów, strumieniowanie
  następnych warstw, poświata/ślad w ½ rozdzielczości, polilinie zamiast QPainterPath (~10× szybciej dla półprzezroczystych).
- Pomiar detalu: z 37 ms do 2,9–6,8 ms mediany; najgorsza klatka z 54 ms do ≤ 20 ms (3 mm/klatkę). Szczegóły w DECYZJE.
- Testy: 10 nowych w `test_neon_render.py`; pełne pytest lokalnie: 1153 PASS, 12 skip; ruff i wymagania PASS.
- Zrzuty presetów: `tools/dev/neon-preview.py --png … --preset …` (build/neon). Autokontrola. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Classic × Neon — N2 + N3: monitor na żywo i zmiana skórek · 2026-10-24 · Claude
- Model-Author: Claude. Podział z Codex: Claude N2+N3, Codex N1+N4 (prawdziwy LinuxCNC).
- N2: próbka NML z `file`, `motion_line`, G5x/G92/narzędzie, `distance_to_go`, `dtg` (walidacja, mm);
  `linumert_neon_loader.py` — `gcode.parse` w jednorazowym procesie (timeout 20 s, limit 64 MB);
  monitor: nowy plik → wczytanie, linia + pozycja detalu → następny punkt, DTG z LinuxCNC; bez programu
  uczciwy opis zamiast sceny demo. Przygotówka z `;@STOCK` (dowolne ORIGIN) albo z obrysu ruchów.
- N3: scena w stanie hosta (`shared`) — zmiana skórki/motywu/języka nie gubi sceny ani materiału;
  launcher ISO `linumert --neon` + skrót pulpitu. Uruchomienie z prawdziwym `gcode`: zadanie N4 Codex.
- Testy: pełne pytest 1181 PASS, 12 skip; ruff, wymagania PASS. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 036 — Poziomy dostępu · 2026-10-24 · Claude
- **Zrobione:** `core/linumert/access` (role, PIN scrypt w SQLite, blokada po błędach, audyt, CLI
  `python -m linumert.access`); ekran: `linumert_access_ui` (przycisk roli w górnym pasku, okno PIN z keypadem
  44 px, `require()`/`audit()`); strażnicy: zapis/usuwanie narzędzi, zero detalu i zapis przygotówki
  (technolog), Konfiguracja i pełny QtDragon (serwis). Zrzut: build/access/pin-dialog.png.
- **Decyzje:** bez domyślnych PIN-ów, brak PIN-ów = kontrola wyłączona (PROPOZYCJA w DECYZJE).
- **Do sprawdzenia ręcznie:** ustawić PIN serwisu CLI, w HMI zalogować się, sprawdzić odmowę dla Operatora.
- **Długi:** pin HAL klucza pulpitu (API gotowe). Testy: 12 nowych; pełne pytest w PR. NIEZWERYFIKOWANE NA SPRZĘCIE.

## N1 — rzeczywisty interpreter podglądu · 2026-10-24 · Codex
- Model-Author: Codex. Naprawiono TypeError: jawny parameter_file i prywatny plik parametrów.
- Debian12/RIP: 6 testów PASS, G20/G21 i fizyczne linie przy N900 potwierdzone; ruff i REQ PASS.
- Demo z T1 M6: SIGSEGV w tool_mmap_mutex_get (gdb); pełny N1/N4 pozostają otwarte.
- M1: ręczny odbiór oraz LEGACY-RUNTIME nadal otwarte; cudzych procesów LinuxCNC nie przerwano.

## 027 — Własny system projektowy ekranu (domknięcie) · 2026-10-24 · Claude
- **Zrobione:** rozliczenie promptu: QSS powłoki z tokenów już generowany w czasie działania (`shell_qss`, test
  kolorów i celu 44 px) — dodano `tools/gen_qss.py` (zrzut tego samego stylu); fonty IBM Plex Sans (Regular,
  SemiBold, Bold) i JetBrains Mono (Regular, Bold) z licencjami OFL w `screens/linumert/fonts/`, rejestrowane
  przez `linumert_fonts.register()` w powłoce HMI i podglądzie skórek; PROVENANCE z sumami SHA-256.
- **Decyzje:** `linumert.qss` (arkusz bazy QtDragon) nie jest nadpisywany — źródłem stylu jest `shell_qss(tokens)`.
- **Do sprawdzenia ręcznie:** HMI w LinuxCNC rysuje teksty fontem IBM Plex Sans, a DRO JetBrains Mono.
- **Długi:** brak. Testy: pełne pytest, ruff, REQ — wynik w PR. Model-Author: Claude. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 007 — Katalog alarmów i tłumaczenia (domknięcie) · 2026-10-24 · Claude
- **Zrobione:** `linumert_i18n.py` (`translate()`, `TsTranslator` czyta `.ts` bez lrelease, `.qm` gdy jest,
  język z env/INI, domyślnie PL), `i18n/linumert_pl.ts`, `tools/i18n.sh` (pylupdate5 + opcjonalnie lrelease),
  `tools/i18n_check.py` (kompletność PL); powłoka HMI instaluje język przed budową widoków; panel alarmów
  przez `translate()`. Katalog W/E/K/P i AlarmManager z 2026-10-18 bez zmian.
- **Decyzje:** źródło EN + `.ts` PL, forma `translate()` (PROPOZYCJA w DECYZJE).
- **Do sprawdzenia ręcznie:** HMI w LinuxCNC pokazuje polską podpowiedź Resetu; `LINUMERT_LANG=en` — angielską.
- **Długi:** pozostałe napisy ekranu i skórek → sesja 037. Testy: pełne pytest 1230 PASS; ruff, REQ PASS.
  Model-Author: Claude. Autokontrola. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 043 — Generatory: rowki, czopy, kontur · 2026-10-24 · Claude
- **Zrobione:** `core/linumert/generators/contours.py`: slot_linear, slot_arc, stud_rect, stud_circle, contour
  (segmenty L/A z tekstu, G41.1/G42.1 D=średnica, styczny dojazd/odjazd, P-5010 z numerem segmentu, promień łuku),
  preview_2d; na stronie Cykle (menu + rejestr). Zrzut: build/contours/cycles-contours.png.
- **Testy:** golden 5 programów; materiał `StockMap`: rowek tnie dokładnie szerokość, czop nietknięty, rowek łukowy
  bez cięciwy, G0 bez materiału, rampa bez zagłębienia pionowego; walidacje; GUI Cykli; test rs274 (`linuxcnc`, CI).
- **Decyzje:** tor środka narzędzia; kontur z korekcją dynamiczną LinuxCNC (bez tabeli narzędzi).
- **Do sprawdzenia ręcznie:** kontur z korekcją na Plant; czopy przy realnym marginesie przygotówki.
  Model-Author: Claude. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 051 — Ścieżka z programu · 2026-10-24 · Claude
- **Zrobione:** `simulation/linumert_sim/path.py`: `MoveList` w tablicach (float32/int32/int8), `PathCanon` dla
  `gcode.parse`, `SubsetInterpreter` dla CI (G0–G3 w G17/G18/G19, IJK/R, linia śrubowa, G20/21, G90/91, G90.1/91.1,
  T/M6, G81/G82/G83/G73 z G98/G99 i Q); łuki na cięciwach z błędem ≤ 0,01 mm; `load_path(prefer=auto|rs274|subset)`.
  Nieobsługiwane (o-word call, G41/G42, G28/G30/G53, G5.1…) → notatka, ruch pominięty.
- **Błąd znaleziony przy okazji:** canon bez atrybutu `parameter_file` → `gcode.parse` kończył się TypeError
  (gcodemodule czyta go jako tekst). Dotyczyło też `core/linumert/programs/toolpath.py` (`load_ngc`, Classic × Neon).
- **Testy:** 10 programów golden (M3): ciągłość, końce linii, posuwy, błąd cięciwy; R krótki/długi, płaszczyzny,
  pełny okrąg, G91/G20, cykle; z LinuxCNC 2.9 RIP: 9 programów bez korekcji = rs274 (linie, końce, długości).
- **Decyzje:** współrzędne programu bez G5x/G92 (jak podgląd LinuxCNC); start podzbioru 0,0,0.
- **Długi:** podłączenie do procesu symulacji/widoku (052/057). Model-Author: Claude. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 052 — Proces symulacji (offline, worker) · 2026-10-24 · Claude
- **Zrobione:** `offline.py`: `OfflineJob` (program, ;@STOCK, narzędzia T/długość/średnica, układ detalu, G0, krok)
  z kluczem SHA-256; `simulate()` prowadzi `SimEngine` po ścieżce z 051 (materiał, K-301/302/…, czas G0/G1, objętość
  usunięta), anulowanie co odcinek, postęp. `worker.py`: `SimWorker` — proces `spawn`, nice ≥ 10, kolejka, anulowanie
  bieżącego i oczekującego zadania, cache (pamięć + `<sha256>.json`), `start_listener` (wątek pomocniczy).
  `linumert_sim_worker.py`: sygnały Qt progress/finished/cancelled/failed. MoveList dostał `spindle` (S, M3/M4/M5).
- **Testy:** reguły i czas na programie z M3/M5 i G0 w materiał; brak ;@STOCK; klucz cache; anulowanie w procesie
  i w workerze (bieżące + w kolejce, worker działa dalej, wynik anulowany nie trafia do cache); cache z pliku w nowym
  procesie; błąd programu; most Qt — sygnał w wątku GUI.
- **Decyzje:** pierwszy ruch programu tylko do czasu (pozycja startowa nieznana); czas bez przyspieszeń (053).
- **Długi:** strona Symulacja na workerze offline, widok 3D (057). Model-Author: Claude. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 048 — Biblioteka podprogramów o-word (domknięcie) · 2026-10-24 · Claude
- **Zrobione:** `o<lrt_pocket_rect>`, `o<lrt_pocket_circle>`, `o<lrt_slot_linear>` (NgcGui) — ruch jak generatory
  pocket_rect v2 / pocket_circle v2 (wejście pionowe, bez naddatków) i slot_linear v1; fragmenty o-word kieszeni
  generowane z szablonu (punkty, odwrócenie CW, pomijanie zerowych odcinków, obrót); eksport z Cykli z poprawną odmianą.
- **Testy:** rs274 (CI `linuxcnc`, 133 PASS) porównuje STRAIGHT i ARC_FEED podprogramu z generatorem: obrót 90°, CW,
  narożniki R=D/2 i R>D/2, rowek pionowy/ukośny/wąski; lekser bez MIN/MAX i minusa jednoargumentowego.
- **Do sprawdzenia ręcznie:** zakładka NgcGui QtDragon z katalogiem user_macros. Model-Author: Claude. NIEZWERYFIKOWANE NA SPRZĘCIE.

## PLANT-SUBSTEPS — zależność Plant od substeps (M1) · 2026-10-24 · Claude
- **Zrobione:** diagnoza ustalenia z 049: cel CSP przykładany w pierwszym podkroku → n-krotny impuls FF
  (frezarka E-4201 przy G0 Z, router ~1560 zgubionych kroków przy G0). `lrt_machine_step_cycle` interpoluje cel
  liniowo w cyklu (z poprawką ramki przy bazowaniu); `PlantServer`, `HomingMaster` na nowej funkcji; domyślne
  `substeps` = 4 (wzory plant.yaml, lib.sh VM). `tools/plant_substeps.py`, raport `docs/raporty/plant_substeps.md`.
- **Testy:** C 29/59/21 (+ sanitizery), test `step_cycle` (bez interpolacji n=8: napęd w FAULT, 49 mm zadana −
  stojąca oś; z interpolacją 0,013 mm); pełne pytest PASS; macierz Plant 14/14; ruff, REQ PASS.
- **Decyzje:** PROPOZYCJA w DECYZJE (interpolacja, 4 podkroki, 60C2h w generatorze 063).
- **Do sprawdzenia ręcznie:** Plant realtime z LinuxCNC na VM — obciążenie CPU przy 4 podkrokach.
  Model-Author: Claude. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 049 — Test technologiczny na Plant (suite_cycles) · 2026-10-24 · Claude
- **Zrobione:** `tools/suite_cycles.py` — każdy generator cykli (10 przypadków) na `router_gantry_steppers`
  i `mill_servo_table` (atrapa mastera, lockstep), wariant A (G0 z machine.yaml) i B (G0 ≤ 3000 mm/min);
  łuki → cięciwy, cykle wiercenia rozwinięte. Raport `docs/raporty/suite_cycles.md`: **40/40 PASS**.
- **Ustalenie:** pierwszy przebieg (przed poprawką Plant) — router 0/20 (zgubione kroki, także przy G0 10 mm),
  frezarka E-4201 przy substeps ≥ 2. Przyczyna w rdzeniu Plant (cel CSP w pierwszym podkroku) — poprawka
  PLANT-SUBSTEPS (PR #116); generator nie wymagał zmian.
- **Decyzje:** PROPOZYCJA w DECYZJE (interpolacja celu, 4 podkroki). Atrapa bez korekcji G41.1/G42.1.
- **Do sprawdzenia ręcznie:** kontur z korekcją na Plant z LinuxCNC. Model-Author: Claude. NIEZWERYFIKOWANE NA SPRZĘCIE.

## 061 — machine.yaml: napędy rzeczywiste (REQ-VD-06) · 2026-10-24 · Claude
- **Zrobione:** sekcja `real:` szablonów napędów (`drive_real.py`): `stepgen` (czasy impulsów), `ethercat_cia402`
  (PDO CSP), `vfd_modbus` (hy_vfd/mb2hal), `pwm`; zgodność typ ↔ sterownik; JSON Schema; wpisy w 7 szablonach.
  `machine.yaml`: `target: plant | sim | hardware` i `hardware:` (parport/mesa 7i96s/7i76e/ethercat, kanały,
  port falownika). `hardware_plan()` — sterownik, kanał, skala impulsów z `encoder_counts_per_rev` i `ratio`.
- **Testy:** `test_template_real_mapping` (REQ-VD-06): ten sam plik → Plant i plan sprzętu, NEMA 23 = 640 kroków/mm;
  frezarka serwo → EtherCAT; reguły sekcji hardware; walidacja `real:`. Wymagania 22/22.
- **Decyzje:** skala nie jest wpisywana osobno (jedno źródło: mechanika szablonu); nazwy pinów HAL dopiero w 062/063.
- **Długi:** pulpit/MPG i E-STOP rzeczywisty w `hardware:`. Model-Author: Claude. NIEZWERYFIKOWANE NA SPRZĘCIE.

## D38 — histereza dotrzymania pozycji (poprawka) · 2026-10-24 · Claude
- **Zrobione:** próg |błąd nadążania| przed wycofaniem Z: wejście ≤ 5 µm, wyjście > 10 µm; przyczyna niestabilnego
  `test_retract_returns_to_compensated_path[plant]` i odmowy przy aktywnym przycisku. Test `tests/test_pause_settled.py`;
  test LinuxCNC + Plant PASS lokalnie. Model-Author: Claude. NIEZWERYFIKOWANE NA SPRZĘCIE.


## 062 — Generator INI/HAL: krok 1 · 2026-10-24 · Codex
- Model-Author: Codex. Start po scaleniu #125/b2ee924 na polecenie właściciela.
- Zrobione: kopia pełnej konfiguracji, unikalne backupy, diff bez zapisu, walidacja ścieżek.
- Testy: 8 PASS Windows/Python3.12; pełny odbiór i uruchomienie generatora otwarte.
- Długi: szablony sim/Plant/parport/Mesa, CLI build, golden oraz LinuxCNC.

## LIMITS-PREFLIGHT — zgodność jednostek INI — 2026-10-24 · Codex
- Model-Author: Codex. Niezależna pomoc do PR #103, zakres 031/051; baza 98191c4.
- Odtworzono błąd: limit 10 cali porównywany z pozycją 127 mm jak limit 10 mm.
- Granice XYZ z INI są przeliczane do mm przed porównaniem z pozycjami kanonicznymi.
- Regresja: mm oraz inch/in/imperial, programy mm/cale, oba końce zakresu.
- Przed zmianą 3 warianty FAIL, po zmianie 4 warianty PASS (unittest, Windows).
- Odbiór GUI/LinuxCNC i sprzętu nie został wykonany; NIEZWERYFIKOWANE NA SPRZĘCIE.

## 062 — Generator INI/HAL: szablony, CLI, sprzęt step/dir · 2026-10-24 · Claude
- **Zrobione:** `configgen.py` (cele `plant`, `sim`), `configgen_hw.py` (`hardware`: Mesa 7i96S/7i76E przez hm2_eth
  i port równoległy z programowym stepgen i ostrzeżeniem o latencji; falownik hy_vfd; [SAFETY]), CLI
  `linumert-config build` (`config_build.py`: podgląd diff, zapis z kopią zapasową z kroku 1 Codex, kody 0/1/2),
  `hardware.inputs/outputs/step_dir/heartbeat_output/watchdog_monitor` w schemacie, przykład
  `config/hardware/router_gantry_mesa.example.yaml`.
- **Testy:** golden — `plant` dla mill_servo_table = ręczna konfiguracja Plant (INI klucz po kluczu, HAL instrukcja
  po instrukcji); wszystkie 5 maszyn × plant/sim — kontrakt D05; CLI (podgląd, zapis, kopia, plik operatora,
  odmowa złej maszyny); sprzęt: `deployment --hal-from-ini` PASS dla Mesa i LPT, odmowy bez E-STOP/heartbeat/
  watchdog/krańcówki, EtherCAT → 063. **LinuxCNC 2.9 RIP:** wygenerowany `sim` bramy routera startuje, włącza się
  i bazuje 4 jointy do HOME z generatora.
- **Incydent:** pierwsze uruchomienie mojego testu LinuxCNC (23:17) zbiegło się z serią prób M1 Codex na tej samej
  maszynie; `start_linuxcnc` sprząta procesy LinuxCNC użytkownika, więc najpewniej przerwałem jedną jego próbę
  (zakończona 23:19 bez wyniku). Test pomija się teraz, gdy działa inny LinuxCNC; kolejne przebiegi pod
  `tools/lock.py acquire linuxcnc`.
- **Decyzje:** PROPOZYCJA w DECYZJE (reguły generatora). **Do sprawdzenia ręcznie:** nazwy pinów Mesa na karcie.
- **Długi:** EtherCAT (063), PWM/mb2hal wrzeciona (064), kreator (067). Model-Author: Claude. NIEZWERYFIKOWANE NA SPRZĘCIE.

## M1 — odbiór powtarzalności · 2026-10-24 · Codex
- Model-Author: Codex. Wynik FAIL: d643a97 7 PASS/8. próba FAIL; 8b255cd 5 PASS/6. próba FAIL.
- Stary: nadążanie X 0,3 mm > 0,2; nowy: KeyboardInterrupt przy bazowaniu i rapid_vs_feed nieukończony.
- Raport i dane: docs/raporty/prototypy/M1_REPEAT_2026-10-24.md/.json. Nie zamknięto LEGACY-RUNTIME.
- Blokada linuxcnc zwolniona. Następny krok: zachować pełne logi first_motion i ustalić przyczynę.


## README — aktualny postęp sesji · 2026-10-24 · Codex
- Zastąpiono statyczne 31/84 grafiką SVG generowaną z plan.json: obecnie 39/84 (46,4%).
- Model-Author: Codex. Rozkład M0–M6 liczy sesje, bez deklarowania odbioru bramek.
- Generator i --check obejmują grafikę; odnośniki Markdown są identyczne na Windows/Linux.
