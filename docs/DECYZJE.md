# Dziennik decyzji linumeRT

Ten plik ma pierwszeństwo przed promptami sesji. Wymagania techniczne: `docs/wymagania/`.
Format: decyzja · uzasadnienie · status (PRZYJĘTA / PROPOZYCJA / ODRZUCONA / ZASTĄPIONA).

## Wersja 2 — 2026-10-17 (QtDragon, wirtualna maszyna, wytyczne IP)

| # | Decyzja | Uzasadnienie | Status |
|---|---|---|---|
| D01 | LinuxCNC jest jedynym interpreterem i planerem ruchu. linumeRT to ekran + rdzeń narzędzi nad LinuxCNC. | Własny planer to lata pracy. | PRZYJĘTA |
| D02 | Ekran operatora na bazie **QtDragon** (QtVCP, PyQt5 przez qtpy). Kopia `qtvcp copy` w `screens/linumert/`, rozszerzenia przez handler-patch, `UPSTREAM.md` z commitem źródłowym. | Dojrzały, sprawdzony na maszynach ekran z sondowaniem, zmianą narzędzia, 5 osiami; zalecany na forum LinuxCNC. | PRZYJĘTA (zastępuje web-first z v1) |
| D03 | Klient webowy operatora odłożony na kolejne półrocze (zdalny podgląd / tablet). pygame i QtPyVCP odrzucone. | Jeden ekran naraz; skupienie na wartości. | PRZYJĘTA |
| D04 | EtherCAT: IgH + linuxcnc-ethercat (lcec) ≥ 1.15 z CiA 402. Bez własnego sterownika EtherCAT. | Gotowe, działa z Leadshine i Rtelligent. | PRZYJĘTA |
| D05 | Kontrakt sygnałów HAL `linumert.jN.*` / `linumert.spindle.*` / `linumert.io.*` — ten sam dla sim, Plant (lrt_net), step/dir i EtherCAT. Zmiana napędu = zmiana tylko plików `net`. | Prototyp testowany na Plant przechodzi na sprzęt bez zmian w ekranie. | PRZYJĘTA |
| D06 | RS485 tylko dla wrzeciona i I/O (hy_vfd, mb2hal). | Modbus nie jest deterministyczny. | PRZYJĘTA |
| D07 | Napędy: EtherCAT CiA 402 (CSP), step/dir (Mesa, parport z ostrzeżeniem), sim, Plant. | Sprzęt hobbystów + testy. | PRZYJĘTA |
| D08 | 3 osie jako pierwsze; 4/5 osi przez kinematyki LinuxCNC i przykłady QtDragon xyzac; symulacja 4/5 osi tylko ścieżka. | Realny zakres. | PRZYJĘTA |
| D09 | Symulacja: ścieżka, czas, mapa wysokości 2.5D (3 osie), reguły K-301/302/303/310/320/321. | Własny silnik 5 osi to rok pracy. | PRZYJĘTA |
| D10 | Widok 3D symulacji: pyqtgraph.opengl w procesie UI, dane z procesu symulacji; ścieżka na żywo — grafika QtVCP. | Spójność z Qt. | PRZYJĘTA (zastępuje three.js) |
| D11 | Wtyczki społeczności deklaratywne (plugin.toml + szablon); Python tylko dla Zaufanych. | Bezpieczeństwo. | PRZYJĘTA |
| D12 | `.lnx` = JSON z wersją schematu; przygotówka w `.lnx` i jako `;@STOCK` w `.ngc`. | — | PRZYJĘTA |
| D13 | Narzędzia: SQLite jako źródło prawdy; `tool.tbl` eksportowany atomowo. | — | PRZYJĘTA |
| D14 | Licencja: własny kod GPL-2.0-or-later; dystrybucja całości z kodem LinuxCNC/QtDragon na GPL-2.0. Licencja „Paid Reuse Source-Available” z `PythonProjects/LICENSE` **nie ma zastosowania** (niezgodna z GPL). | Ekran pochodny QtDragon musi być GPL. | PRZYJĘTA |
| D15 | Własny system projektowy i słownik; zakaz nazw producentów w UI i marketingu (docs/prawne/WYTYCZNE_IP.md). | Wytyczne IP z 17.10.2026. | PRZYJĘTA |
| D16 | Toczenie poza zakresem (QtDragon_lathe pozostaje dostępny jako ekran LinuxCNC). | Priorytet frezarek. | PRZYJĘTA |
| D17 | Harmonogram: zaplanowane zadanie co 5 h; każde uruchomienie robi jedną sesję lub wznawia przerwaną; blokada `prompts/LOCK`; praca zapisywana krokami na `wip/`. | Wykorzystanie odnawianych limitów konta. | PRZYJĘTA |
| D18 | Testy prototypów na **wirtualnej maszynie Plant** (VM-B) połączonej siecią wewnętrzną z VM-A (LinuxCNC). Protokół LRT-NET (UDP, ramka na cykl servo). Prawdziwy sprzęt — po zakupie. | Brak sprzętu, potrzeba realistycznych testów. | PRZYJĘTA |
| D19 | Model Plant: inercja odbita, krzywa moment–prędkość, tarcie, grawitacja Z, luz, emulacja napędu CiA 402 (CSP, okno błędu nadążania), krokowiec z gubieniem kroków, serwo krokowe z alarmem, krańcówki, bazowanie, sonda, VFD, ATC, pulpit MPG. Parametry zmienne na żywo. | Testy zachowania przy ograniczeniach przyspieszenia i bezwładności. | PRZYJĘTA |
| D21 | Nazwa projektu: **linumeRT** — dokładnie ta pisownia (małe „linume”, wielkie „RT”). Pakiet Pythona i identyfikatory: `linumert`; sygnały HAL `linumert.*`; repo `anonimov94/linumeRT`. Przed publiczną premierą: wyszukanie w UPRP, EUIPO, WIPO (sesja 080). | Decyzja właściciela 17.10.2026. | PRZYJĘTA |
| D22 | Identyfikacja wizualna v1: `docs/design/marka/` (znak, logotyp, tablica marki), `docs/design/tokens.yaml`, `docs/design/ikony/`, makiety `docs/design/makiety/01–09`. Kompozycja własna: lewa szyna obszarów, górny pasek trybu i stanu, dolny pasek dużych akcji. Stare plansze (v0, układ z kolumną softkeyów) usunięte. | Spójny, własny wygląd zgodny z wytycznymi IP. | PRZYJĘTA |
| D23 | Wirtualna obrabiarka konfigurowalna i biblioteka kopiowalnych napędów wirtualnych zgodnie ze specyfikacją `docs/wymagania/WIRTUALNA_OBRABIARKA.md` (REQ-VD, REQ-VM, REQ-QA). Kamień M1 rozszerzony do 18 sesji (009–026); plan ma 84 sesje. Pokrycie wymagań pilnuje `tools/check_requirements.py` w CI. | Wymaganie właściciela 17.10.2026: testy prototypów na maszynie wirtualnej o konfiguracji odpowiadającej realnym maszynom DIY. | PRZYJĘTA |
| D20 | Spike budowania LinuxCNC 2.9 (RIP) w środowisku agenta. Jeśli działa — testy integracyjne i zrzuty ekranu w każdej sesji; jeśli nie — testy rdzenia i Plant + test użytkownika w VM. | Agent musi móc sprawdzić swój kod. | PROPOZYCJA (wynik w sesji 003) |

## Do dyskusji (nie blokują pracy)
- Koncepcje paneli „APEX” (projekt_hmi 1–6) to inspiracja dla fizycznego pulpitu (MPG, wybór osi, krok, Start/Stop posuwu); nazwa „APEX” nie jest używana.
- Wybór pierwszego napędu testowego (EtherCAT CiA 402) i karty sieciowej.

## Zastąpione z wersji 1 (2026-10-17 rano)
- v1 D02 web-first (FastAPI + Preact) → zastąpione przez D02/D03 v2.
- v1 D10 three.js → zastąpione przez D10 v2.
- v1 D17 3 sesje w tygodniu → zastąpione przez D17 v2.

## Dopisywane przez agentów
<!-- format: - RRRR-MM-DD · sesja NNN · decyzja · uzasadnienie · PROPOZYCJA -->
- 2026-10-17 · sesja 001 · Trzy pakiety Pythona w jednym repo: `linumert` (core/linumert), `linumert_sim` (simulation/linumert_sim), `linumert_plant` (plant/server/linumert_plant); jeden `pyproject.toml` z jawną listą pakietów i `package-dir` · prefiks `linumert` spójny z D21, a układ katalogów z CLAUDE.md §3 pozostaje bez zmian · PROPOZYCJA
- 2026-10-17 · sesja 001 · Straznik IP (`tests/test_ip_guard.py`) sprawdza nazwy z `docs/prawne/ZAKAZANE_NAZWY.txt` w nazwach plików (poza `docs/prawne/`) i w treści kodu, konfiguracji i UI; `docs/` jest wyłączone z przeszukiwania treści (rzeczowe porównania wg CLAUDE.md §7) · egzekwuje kontrakt bez blokowania dokumentacji · PROPOZYCJA
- 2026-10-17 · sesja 002 · Słowa zakazane (zamienniki) mieszkają w bloku ```zakazane w `docs/SLOWNIK.md` i są egzekwowane testem razem z listą nazw producentów; skanowane: kod, UI, konfiguracja, narzędzia, testy i pliki w korzeniu, wyjątek `docs/` · jedno źródło listy, bez duplikatów w kodzie · PROPOZYCJA
- 2026-10-17 · sesja 002 · Plik graficzny lub font bez wiersza w `docs/PROVENANCE.md` oraz obraz poza `docs/design/`, `screens/`, `fonts/`, `plant/server/` łamie test strażnika IP · wymusza rejestr pochodzenia z CLAUDE.md §7 · PROPOZYCJA

- 2026-10-17 · D24 · Na polecenie właściciela Claude i Codex rozwijają projekt naprzemiennie przez PR, z jawnym oznaczeniem modelu i przeglądem drugiego modelu przed scaleniem. Zastępuje automatyczne scalanie z §10 i promptów sesji. Istniejące gałęzie sesji 001/002 są już zawarte w main. Autor: model językowy Codex. · PRZYJĘTA

- 2026-10-17 · D25 · Właściciel polecił kontynuować bez czekania na Claude do odwołania. Codex implementuje, kontroluje diff, uruchamia testy i scala przez PR; późniejszy przegląd Claude nie blokuje pracy. Commit i push po każdym ukończonym kroku. Zastępuje warunek niezależnego przeglądu przed merge z D24. Model-Author: Codex. · PRZYJĘTA
- 2026-10-18 · D26 · Właściciel: oba modele scalają PR do `main` na koniec etapu; `main` bez niedokończonego kodu; PR nie wiszą; podział pracy wg `docs/WSPOLPRACA_MODELI.md` §5 i §7 (Claude: Sonnet 5.5, Codex: astra low).
- 2026-10-18 · sesja 011 · Model osi Plant (`plant/core/axis.c`): tarcie sprowadzone do wału i działające na obciążenie (w trybie dwuczłonowym silnik nie ma tarcia własnego); luz = dwa ciała połączone sprężyną z tłumieniem poza szczeliną (domyślna sztywność 1000 N·m/rad, ζ = 0,7), a nie zderzenie sztywne; zderzak sztywny = zderzenie niesprężyste, sprężysty = sprężyna z tłumieniem; moment dostępny powyżej ostatniego punktu krzywej = 0 (hamowanie regeneracyjne tą samą krzywą); `ratio > 0` (odwrócenie kierunku robi warstwa wyżej); podkroki ograniczone do 2000 z flagą. Sesja 012 dobuduje napęd CiA 402, który liczy `torque_cmd` · Model-Author: Claude · PROPOZYCJA
- 2026-10-18 · sesja 012 · Napęd Plant (`plant/core/drive.c`): (1) krokowiec bez sprzężenia = moment `A·sin(δ_e)`, 4 pełne kroki na okres elektryczny, poślizg liczony w okresach z histerezą 0,6; (2) `lost_steps` dodatni = wirnik za polem, wielokrotność 4; (3) tłumienie krokowca ograniczone do 20 % amplitudy (inaczej maskuje poślizg), domyślne ζ = 0,2; (4) kody 603Fh i mapowanie na E-4200…E-4208 to nasze, niezweryfikowane z dokumentacją producentów napędów; (5) tryb bazowania (6) odrzucany do sesji 015, obiekty 6098h/6099h/609Ah tylko przechowywane; (6) pomiar z opóźnieniem jednego kroku (kolejność pomiar → sterowanie); (7) `tune_servo` ogranicza pasmo do 0,15/dt · Model-Author: Claude · PROPOZYCJA
