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
