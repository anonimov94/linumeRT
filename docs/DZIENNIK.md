# Dziennik pracy agentów

Najnowsze wpisy na dole. Każda sesja dopisuje: zrobione · decyzje · do sprawdzenia ręcznie · długi.

## 000 — Planowanie (2026-10-17)
- Zrobione: analiza QtDragon, wytyczne IP użytkownika, plan v3 (84 sesje, 7 kamieni), specyfikacja wirtualnej obrabiarki (docs/wymagania), nazwa linumeRT, nowa identyfikacja wizualna i makiety, kontrakt CLAUDE.md v2, specyfikacja kierunku dla wirtualnej maszyny Plant.
- Decyzje: D01–D23 w docs/DECYZJE.md.
- Do sprawdzenia ręcznie: nic — repo `anonimov94/linumert` utworzone i wypchnięte 17.10.2026.
- Długi: brak.

## 001 — Szkielet repozytorium, CI i licencja (2026-10-17)
- Zrobione: `pyproject.toml` (pakiety `linumert`, `linumert_sim`, `linumert_plant`; numpy, pyyaml; dev: pytest, ruff; Python ≥ 3.11); wszystkie katalogi z CLAUDE.md §3 z `README.md`; podpakiety rdzenia (alarms, tools, programs, generators, machine, plugins, cnc, diag); `Makefile` (install, lint, test, test-c i test-linuxcnc jako no-op); `.github/workflows/ci.yml` (Python 3.11, `make install lint test`); `LICENSE` (GPL-2.0, tekst z `/usr/share/common-licenses/GPL-2`); `docs/LICENCJE.md`; `docs/PROVENANCE.md` (zalążek, rozbuduje go sesja 002); `.gitignore`; sekcja „Szybki start” w README; testy `test_license.py`, `test_ip_guard.py`, `test_layout.py` (39 testów).
- Decyzje: dwie PROPOZYCJE w `docs/DECYZJE.md` (nazwy pakietów, zakres strażnika IP).
- Do sprawdzenia ręcznie: czy workflow CI uruchomił się na GitHubie i jest zielony (w środowisku agenta sprawdzono tylko lokalnie: `make lint test` przechodzi); zgodność PyQt5 (GPL-3.0) z dystrybucją na GPL-2.0 — wpis „do potwierdzenia” w `docs/LICENCJE.md` (sesje 005 i 080). Plik `prompts/LOCK` ma wpis „praca interaktywna” — usuń go, gdy harmonogram ma ruszyć z sesją 002.
- Długi: fonty IBM Plex Sans i JetBrains Mono nie są dołączone (wpis licencji OFL przy ich dodaniu); `make test-c` i `make test-linuxcnc` to no-op do sesji 011 i 003.

## 002 — Wytyczne IP i rejestr pochodzenia (2026-10-17)
- Zrobione: `docs/prawne/PROCES.md` (wdrożenie §4 i §7 wytycznych w codziennej pracy); `docs/PROVENANCE.md` przebudowany na tabelę (zasób, typ, autor, data, źródło, licencja, zakres użycia, ścieżka) z 52 wpisami: wszystkie pliki `docs/design/`, roadmapa, dokument prawny właściciela, `LICENSE` i dwa fonty (OFL-1.1) jako „gdy dodane”; `docs/prawne/LISTA_PRZED_WYDANIEM.md` (8 pozycji §9 z polami kto, kiedy, dowód); `docs/SLOWNIK.md` (terminy projektu, słowa zakazane i zamienniki); `tests/test_ip_guard.py` rozszerzony (nazwy producentów, słowa ze słownika, brak odwołań do wcześniejszych materiałów, każdy obraz i font w rejestrze, kompletność wpisów dla `docs/design`, kolumny tabeli). 45 testów przechodzi, lint czysty.
- Decyzje: dwie PROPOZYCJE w `docs/DECYZJE.md` (lista słów zakazanych w słowniku, wymóg wpisu dla zasobów).
- Do sprawdzenia ręcznie: lista słów zakazanych w `docs/SLOWNIK.md` jest moim wstępnym doborem (MDA, R-/Q-parametry, nazwy trybów dialogowych) — przejrzyj i uzupełnij; test nie sprawdza, czy zasoby faktycznie narysowano od zera (wpisy autora i źródła pochodzą z sesji 000); zdalna gałąź `wip/sesja-001` nadal istnieje.
- Długi: fonty IBM Plex Sans i JetBrains Mono jeszcze niedodane (wiersze czekają na ścieżki i pliki OFL, sesja 027); pozycje listy przed wydaniem do wypełnienia w sesji 080.

## Współpraca modeli — 2026-10-17
- Autor: model językowy Codex.
- Zrobione: zweryfikowano dostęp GitHub i historię obu gałęzi; przygotowano kontrakt wspólnej pracy, AGENTS.md i szablon PR.
- Decyzje: D24, naprzemienny przegląd Claude/Codex.
- Do sprawdzenia: Claude powinien przejrzeć PR po odzyskaniu dostępności; rozpocząć sesję 003 w środowisku Linux.
- Długi: sesja 003 nieukończona; historyczny prompts/LOCK pozostawiony do wyjaśnienia.

## Przejęcie pracy — 2026-10-17
- Model-Author: Codex. Decyzja właściciela D25: praca samodzielna do odwołania, push po każdym kroku.
- Weryfikacja PR #1: 45 testów przeszło w WSL, CI zielone (lint i testy).
- Podgląd: uruchomiono TigerVNC na localhost:5908 i Viewer; konfiguracja pulpitu X11 w WSLg wymaga jeszcze końcowej weryfikacji.
- Następna praca: sesja 003, LinuxCNC.

## Paczka testowa i VNC — 2026-10-17
- Model-Author: Codex.
- Zrobione: tools/agent_tests (runner Python, launcher PowerShell, instrukcja), tools/vm/start-vnc.sh, wspólne raporty JSON/logi, dwa testy obsługi błędów runnera, końcówki LF dla pracy Windows/WSL.
- Weryfikacja: uruchomiono paczkę przez Start-Tests.ps1 -Model Codex -DisplayNumber 11; Viewer połączył się z localhost:5911; potwierdzono pulpit i terminal ze zrzutu; diff i ruff bez błędów, 47 testów przeszło. Raport state/test-runs/20261017T212444.650344Z-Codex/report.json zawiera PASS (stan roboczy podczas poprawek, pełna identyfikacja w JSON).
- Decyzje: nie przesyłamy haseł, Xauthority, logów lokalnych ani venv do Git. PR #2, push po każdym kroku.
- Do sprawdzenia: LinuxCNC jeszcze niebudowany; kolejny etap to sesja 003.
- Długi: VNC/WSL nie potwierdzają czasu rzeczywistego i sprzętu; wymagane osobne testy VM-A/VM-B.

## 007 — Katalog alarmów i manager (2026-10-18)
- Model-Author: Claude (Sonnet 5.5).
- Zrobione: `alarms/catalog.yaml` (56 kodów W/E/K/P, teksty własne PL/EN), `catalog.py` (loader z walidacją), `manager.py` (raise/ack/clear/reset/historia, zegar wstrzykiwany, wątkowo bezpieczny), package-data dla yaml, 23 testy; `make lint test`: 100 OK.
- Decyzje (PROPOZYCJA): pole `clear` = auto|ack|reset; kody K wg tabeli z NARZEDZIA_I_KOLIZJE.md §3 (bez K-306..309, K-312..319, których nie zdefiniowano); znaczenia W/E/P spoza dokumentów to propozycja, edytowana w jednym pliku.
- Do sprawdzenia ręcznie: sens i brzmienie tekstów PL/EN oraz podział kodów w zakresach E-4xxx.
- Długi: punkt 3 zakresu (plik `.ts` PL i `tools/i18n.sh` z pylupdate5/lrelease) czeka na kopię ekranu (sesja 005) i środowisko Qt: zadanie dla Codex.
## 006 — Rdzeń: model stanu maszyny i atrapa (2026-10-18)
- Model-Author: Claude (Sonnet 5.5).
- Zrobione: `cnc/model.py` (niezmienna migawka, świeżość), `cnc/linuxcnc_reader.py` (leniwy import, mapowanie po nazwach stałych, wstrzykiwany moduł), `cnc/fake.py` (atrapa z wirtualnym zegarem), `docs/RDZEN.md`; 30 nowych testów (21 atrapa, 9 czytnik), `make lint test`: 77 OK.
- Decyzje: pozycje w układzie maszynowym; błąd nadążania w atrapie = 0 (dynamika w Plant); po E-stop i wyłączeniu bazowanie jest kasowane (uproszczenie).
- Do sprawdzenia ręcznie: czytnik na prawdziwym RIP (znaczenie `gcodes[0]`/`mcodes[0]`, `stat.axis`, `stat.limit`, `spindle[0]`). NIEZWERYFIKOWANE NA PRAWDZIWYM LINUXCNC; zadanie dla Codexa.
- Długi: brak tabeli narzędzi i G92 w atrapie i `work_position`; brak jednostek G20.
## 009 — Specyfikacja wirtualnej maszyny Plant (2026-10-18)
- Model-Author: Claude (Sonnet 5.5). Niezależny od PR #5 i #6 (konflikt tylko na końcu DZIENNIK/DONE).
- Zrobione: `docs/PLANT.md` (architektura z mermaid, protokół LRT-NET v1 z tabelą ramki i regułami, model osi, typy napędów i CiA 402, `machine.yaml`, `plant.yaml`, scenariusze, odporność, kryteria jakości, plan sesji 010–024, 061, 082), `docs/wymagania/MACIERZ.md` (22 REQ, generowana z tabel wymagań), `tests/test_plant_spec.py` (11 testów: pokrycie REQ, parsowanie przykładów YAML, rozmiary ramek przez `struct`, CRC32); `make lint test`: 58 OK.
- Decyzje (PROPOZYCJA): układ ramki z nagłówkiem 20 B i magic `LR`; `torque_pct` w jednostce 0,1 %; watchdog 50 ms domyślnie; kody błędów napędów mapowane na E-4200…E-4203.
- Do sprawdzenia ręcznie: sensowność parametrów przykładowych i kolejności pól ramki przed sesją 016/017 (komponent HAL w C).
- Długi: model nieweryfikowany na sprzęcie; liczby w przykładach są typowe, nie pomiarowe.

## Sesja 010 — schemat i walidacja machine.yaml — 2026-10-18
- Model-Author: Claude.
- Zrobione: `core/linumert/machine/schema.py` (Pydantic v2, błędy po polsku ze ścieżką pola, `load_machine`), `validate.py` (24 reguły spójności, zbiera wszystkie błędy), 5 przykładów w `config/machines/`, `tests/test_machine_config.py` (42 testy, w tym 36 negatywnych REQ-VM-11 i REQ-VM-01).
- Zależność: pydantic (MIT) w pyproject i LICENCJE.md.
- Założenia (PROPOZYCJA): kolejność bazowania — X/Y nie przed Z; krańcówka nie dalej niż soft limit, ogranicznik za krańcówką; portal (wiele napędów) wymaga `gantry_square` i `gantry_max_skew`.
- Nie zweryfikowano: szablony napędów (`stepper_open_loop`, `servo_cia402`, `vfd_modbus`) powstaną w sesji napędów Plant; do tego czasu `validate_machine` nie sprawdza ich istnienia (parametr `drive_templates`).
## Sesja 011 — Plant: rdzeń dynamiki osi (C) — 2026-10-18
- Model-Author: Claude (Sonnet 5.5).
- Zrobione: `plant/core/axis.h/.c` (oś liniowa/obrotowa sterowana momentem: bezwładność odbita, krzywa moment–prędkość, tarcie lepkie/Coulomba/statyczne, grawitacja, luz i sztywność w modelu dwuczłonowym, zderzaki sztywne i sprężyste ze zdarzeniami, podkroki wg sztywności, jawne kody błędów po polsku, przywracanie stanu przy NaN); `plant/core/Makefile` (C11, `-Wall -Wextra -Wpedantic -Werror`); `tests/lrt_test.h` (framework) i `tests/test_axis.c` (23 testy, błąd względem wzorów analitycznych ≤ 1 %); `tests/test_plant_core.py` (uruchamia testy C z pytest, pilnuje braku alokacji i I/O); krok `make test-c` w `ci.yml`.
- Weryfikacja: `make -C plant/core test` 23/23; `ruff` czysty; `pytest` 51 przeszło (z `PYTHONPATH=core`); dodatkowo ręcznie: build z `-fsanitize=address,undefined` bez błędów, `clang -Wconversion -Wshadow` bez ostrzeżeń.
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (zakres i uproszczenia modelu osi).
- Do sprawdzenia: krok `make test-c` w `ci.yml` (nie uruchomiony na GitHubie w chwili pisania; przy scalaniu z #3 możliwy konflikt w `ci.yml`); zgodność modelu z realną maszyną — NIEZWERYFIKOWANE NA SPRZĘCIE; progi tolerancji testów dobrane do kroków 20–100 µs.
- Długi: brak hamulca silnika (Z opada przy zerowym momencie, jeśli tarcie < grawitacja) — do sesji napędów; model nie zna kierunku odwróconego ani osi gantry (sesja 014); brak REQ-znaczników w testach C do czasu `tools/check_requirements.py` (sesja 024). Nowe zasoby i zależności: brak (tylko libc/libm), więc bez zmian w LICENCJE.md i PROVENANCE.md.

## 012 — Plant: emulacja napędów CiA 402 i krokowców — 2026-10-18
- Model-Author: Claude (Sonnet 5.5).
- Zrobione: `plant/core/drive.h/.c` (maszyna stanów CiA 402, quick stop, reakcja na awarię, reset zboczem; CSP z FF, anty-windup, limit 6072h, okno nadążania, I2t; krokowiec bez sprzężenia z utratą okresów i licznikiem `lost_steps`; krokowiec z pętlą zamkniętą; enkoder z kwantyzacją i szumem; obiekty 603Fh…60B2h; wstrzykiwanie awarii; tablica awarii X-macro); `tests/test_drive.c` (49 testów); Makefile; dwa testy Python spójności tablicy awarii z katalogiem alarmów (pomijane bez katalogu z PR #6).
- Weryfikacja: `make -C plant/core test` 23 + 49 OK; ruff czysty; pytest OK; ASan/UBSan czyste; `clang -Wconversion -Wshadow` czyste; ręczny test mutacyjny 22 mutacji — wszystkie wykryte (4 testy dopisane po ocalałych mutantach).
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (model krokowca, kody 603Fh, bazowanie odroczone, opóźnienie pomiaru).
- Do sprawdzenia: niezależny przegląd modelu krokowca i mapowania awarii (Codex); po scaleniu PR #6 uruchomić test katalogu bez pomijania; PR #10 zawiera commity PR #9 do czasu jego scalenia.
- Długi: brak hamulca; bazowanie (tryb 6) w sesji 015; brak znaczników REQ w testach C do sesji 024; wszystko NIEZWERYFIKOWANE NA SPRZĘCIE.

## 013 — Biblioteka napędów wirtualnych — 2026-10-18
- Model-Author: Claude (Sonnet 5.5; dokończenie po przerwaniu: Opus 5.5).
- Zrobione: (1) `plant/library/drives/` — 7 szablonów YAML (krokowce NEMA 23 i 34, serwo krokowe, serwa 400 W i 750 W, stół obrotowy 1:90, wrzeciono 2,2 kW; wartości przykładowe z komentarzem źródła) + `drive_template.schema.json` generowany z tabeli parametrów; (2) `linumert_plant/drive_template.py` — tabela `PARAMS` z zakresami, walidacja z polskimi komunikatami i ścieżkami pól (wszystkie błędy naraz), reguły między polami, mapowanie na `lrt_drive_params`/`lrt_axis_params`, wzory fizyczne (`max_acceleration`), `LiveParams` z dziennikiem zmian; (3) `drive_library.py` — ładowanie biblioteki, instancje `template` + `overrides` z walidacją tymi samymi zakresami, klonowanie szablonu i instancji (`based_on`, `version`), zapis; (4) CLI `python -m linumert_plant drive list|show|validate|clone|schema`; (5) rdzeń C: `lrt_axis_set_live/get_live` (masa, J wirnika, J śruby, tarcie, luz, napięcie jako mnożnik krzywej), czas modelu `lrt_axis.time`, dziennik zmian `lrt_live_log` (bufor kołowy 64 wpisy, bez alokacji); (6) `plant/core/tools/check_params.c` — narzędzie sprawdzające szablony walidatorami C i krótkim ruchem napęd+oś (`--simulate`); (7) 6 nowych testów C i `tests/test_drive_library.py` (48 przypadków) ze znacznikami `# REQ-VD-nn`.
- Weryfikacja: `make lint test test-c` zielone (ruff czysty; pytest 100 + 1 pominięty; testy C 29 osi + 49 napędu); wszystkie 7 szablonów przechodzi walidatory C i ruch 0,5 obr w pętli napęd+oś (stan OPERATION_ENABLED, bez awarii i bez utraconych kroków, błąd końcowy < 0,03 % obrotu); ASan/UBSan czyste, `clang -Wconversion -Wshadow` czyste dla `axis.c` i narzędzia.
- Decyzje: jedna PROPOZYCJA w `docs/DECYZJE.md` (format szablonu, `live:` jako lista ścieżek, typy → modele C, luz live wymaga modelu dwuczłonowego, CLI pod `linumert_plant`, brak nowych zależności).
- Do sprawdzenia ręcznie / przez drugi model: (a) po scaleniu #8 podłączyć `resolve_instances()` do ładowarki `machine.yaml` (sekcja `drives:`) — w tej sesji `machine.yaml` nie było na gałęzi; (b) po scaleniu #6 test spójności tablicy awarii z katalogiem alarmów ma przejść bez pominięcia; (c) przegląd wartości szablonów (przykładowe, NIEZWERYFIKOWANE NA SPRZĘCIE) i przybliżenia wrzeciona VFD jako serwa CSP.
- Długi: hamulec i `brake_on_fault` są tylko przechowywane (model hamulca: sesja 014+); `real:` (REQ-VD-06) — sesja 061; wiązanie Pythona z rdzeniem C (ctypes) i przekazywanie `LiveParams.c_command()` do `lrt_axis_set_live` — orkiestrator w sesji 014/016; scenariusze `drive_clone_tuning` i `heavy_table_live` oraz panel (REQ-VD-03/04, sesje 022–023) jeszcze nie istnieją; zmiana `load` w locie nie przestraja regulatorów; brak `tools/check_requirements.py` (sesja 024), więc znaczniki REQ nie są jeszcze egzekwowane w CI. Nowe zależności: brak (PyYAML już w LICENCJE.md); zasoby w PROVENANCE.md.
- Dokończenie (Claude Opus 5.5, ta sama gałąź `wip/sesja-013`): (a) scalono `origin/wip/sesja-010` (#8) do gałęzi — `drives:` w `machine.yaml` to teraz instancje szablonów: `DriveInstance` przyjmuje klucz `id` (alias `name` z sesji 010), 5 przykładowych maszyn używa szablonów z biblioteki (z przykładami `overrides`), `linumert_plant/machine_drives.py` łączy walidację maszyny, rozwiązanie instancji (błędy z indeksami pliku) i zgodność mechaniki linear/rotary z osią i wrzecionem; (b) `python -m plant drive ...` z katalogu głównego (`plant/__main__.py`) i polecenie `drive instances <machine.yaml>`; (c) API live w `drive.c`: `lrt_drive_set_live/get_live` (limit momentu 6072h, estymata J regulatora), czas modelu napędu, wspólny dziennik `plant/core/live.h/.c` dla osi i napędu; (d) testy: `tests/test_machine_drives.py` (11), 2 nowe testy C napędu (w tym fizyczny: J ×4 w locie → a = T_lim/J, błąd < 1 %).
- Weryfikacja dokończenia (WSL Ubuntu 24.04, gcc, Python 3.12 venv): `ruff` czysty; `pytest` 153 przeszło + 1 pominięty; `make test-c` 29 osi + 51 napędu; ASan/UBSan czyste. LinuxCNC nie dotyczy.
- Do sprawdzenia przez Codexa: zmiana w `core/linumert/machine/schema.py` (alias `id`) i w jednym teście sesji 010 (nazwa szablonu w przykładzie) — dotyka kodu z #8; zgodność mapowania przykładowych maszyn na szablony.
