<!-- Generowane przez python3 tools/roadmap.py; edytuj docs/roadmap/plan.json. -->
# Wspólny plan linumeRT

Pierwotny plan: **84 sesje M0–M6**, commit `796c6a2`. Stan na 2026-10-26: planowane: 15; w toku: 0; częściowe: 30; do odbioru: 0; ukończone: 39; zablokowane: 0.

Zakończenie części implementacji nie oznacza odbioru całej funkcji ani sprzętu.

## Kamienie pierwotnego planu

| Kamień | Cel | Kryterium bramki (cel, nie wynik odbioru) |
|---|---|---|
| M0 — Fundament, prawo, środowisko | Repozytorium, CI, wytyczne IP i rejestr pochodzenia, budowa LinuxCNC w środowisku agenta, kopia bazowa QtDragon, rdzeń z atrapą. | G0: CI zielone; ekran `linumert` (kopia QtDragon) startuje w LinuxCNC sim; wynik spike'a budowania LinuxCNC zapisany. |
| M1 — Wirtualna obrabiarka Plant | Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami. | G1: LinuxCNC (VM-A) bazuje każdą metodą i wykonuje program na Plant (VM-B); wszystkie REQ-VD/VM/QA z WIRTUALNA_OBRABIARKA.md mają zielone testy (check_requirements.py). |
| M2 — Ekran linumeRT na bazie QtDragon | Własny system projektowy i kompozycja ekranu, tryby, JOG/MPG, MDI, AUTO, narzędzia, zerowanie i sonda, zmiana narzędzia, alarmy, role, PL/EN. | G2: prototyp v0.1 przechodzi zestaw scenariuszy operatora na Plant; przegląd podobieństwa ekranów wykonany. |
| M3 — Programowanie dialogowe | Format .lnx, generatory cykli, panel dialogowy z podglądem 2D, biblioteka podprogramów o-word, integracja z plikami QtDragon. | G3: program z 5 krokami generuje .ngc, który wykonuje się na Plant bez alarmów; czasy i błędy nadążania w raporcie. |
| M4 — Symulacja i kolizje | Ścieżka, czas obróbki, przygotówka, materiał 2.5D, reguły kolizji lite, widok 3D 30 FPS, raport; walidacja czasu względem Plant. | G4: szacowany czas różni się od czasu na Plant o ≤ 10 %; K-301/K-302 wykrywane na plikach testowych. |
| M5 — Konfiguracja maszyn hobbystów | machine.yaml → INI/HAL dla sim, Plant, step/dir, EtherCAT, VFD; 4/5 osi; ATC; kreator; diagnostyka napędów; asystent strojenia na Plant. | G5: 5 przykładowych maszyn działa na Plant (w tym 5 osi i ATC); konfiguracje sprzętowe oznaczone jako niezweryfikowane. |
| M6 — Wtyczki, instalator, alfa | Wtyczki deklaratywne, instalator dla Debiana 12 + LinuxCNC 2.9, dokumentacja, przegląd IP przed wydaniem, regresja na Plant, wydanie alfa. | G6: instalacja na czystej VM, pełna regresja scenariuszy zielona, lista kontrolna IP §9 wypełniona, nazwa linumeRT sprawdzona w rejestrach. |

## Sesje 001–084

| ID | Kamień | Zakres | Stan |
|---|---|---|---|
| 001 | M0 | [Szkielet repozytorium, CI i licencja](../../prompts/sesja-001.md) | ukończone |
| 002 | M0 | [Wytyczne IP i rejestr pochodzenia](../../prompts/sesja-002.md) | ukończone |
| 003 | M0 | [Spike: LinuxCNC 2.9 w środowisku agenta](../../prompts/sesja-003.md) | ukończone |
| 004 | M0 | [Konfiguracja sim 3 osie z QtDragon](../../prompts/sesja-004.md) | ukończone |
| 005 | M0 | [Kopia bazowa ekranu QtDragon](../../prompts/sesja-005.md) | ukończone |
| 006 | M0 | [Rdzeń: model stanu maszyny i atrapa](../../prompts/sesja-006.md) | ukończone |
| 007 | M0 | [Katalog alarmów i tłumaczenia](../../prompts/sesja-007.md) | ukończone |
| 008 | M0 | [Bufor i bramka G0](../../prompts/sesja-008.md) | ukończone |
| 009 | M1 | [Specyfikacja wirtualnej maszyny Plant](../../prompts/sesja-009.md) | ukończone |
| 010 | M1 | [Model obrabiarki machine.yaml (jedno źródło prawdy)](../../prompts/sesja-010.md) | ukończone |
| 011 | M1 | [Plant: rdzeń dynamiki osi (C)](../../prompts/sesja-011.md) | ukończone |
| 012 | M1 | [Plant: emulacja napędów CiA 402 i krokowców](../../prompts/sesja-012.md) | ukończone |
| 013 | M1 | [Biblioteka napędów wirtualnych: szablony, kopiowanie, parametryzacja](../../prompts/sesja-013.md) | ukończone |
| 014 | M1 | [Plant: łańcuch kinematyczny, przejazdy, zderzaki, krańcówki, I/O](../../prompts/sesja-014.md) | ukończone |
| 015 | M1 | [Bazowanie po rozruchu: krańcówka, indeks, twardy zderzak, absolut, napęd](../../prompts/sesja-015.md) | ukończone |
| 016 | M1 | [Plant: serwer LRT-NET](../../prompts/sesja-016.md) | ukończone |
| 017 | M1 | [Komponent HAL lrt_net](../../prompts/sesja-017.md) | ukończone |
| 018 | M1 | [Konfiguracja LinuxCNC dla Plant (3 osie)](../../prompts/sesja-018.md) | ukończone |
| 019 | M1 | [Ograniczenia programowe, strefy zakazane i wyrocznia testowa](../../prompts/sesja-019.md) | ukończone |
| 020 | M1 | [Magazyn narzędzi, pozycje wymiany i kolizje w Plant](../../prompts/sesja-020.md) | ukończone |
| 021 | M1 | [Plant: wrzeciono VFD przez Modbus](../../prompts/sesja-021.md) | ukończone |
| 022 | M1 | [Plant: panel sterowania i pulpit MPG](../../prompts/sesja-022.md) | ukończone |
| 023 | M1 | [Edytor wirtualnej obrabiarki w panelu Plant](../../prompts/sesja-023.md) | ukończone |
| 024 | M1 | [Plant: scenariusze i raport prototypu](../../prompts/sesja-024.md) | ukończone |
| 025 | M1 | [Skrypty maszyn wirtualnych (VirtualBox)](../../prompts/sesja-025.md) | ukończone |
| 026 | M1 | [Bufor i bramka G1 (prototyp P0)](../../prompts/sesja-026.md) | ukończone |
| 027 | M2 | [Własny system projektowy ekranu](../../prompts/sesja-027.md) | ukończone |
| 028 | M2 | [Kompozycja ekranu głównego](../../prompts/sesja-028.md) | częściowe |
| 029 | M2 | [Tryby, JOG i pulpit MPG](../../prompts/sesja-029.md) | częściowe |
| 030 | M2 | [MDI i klawiatura ekranowa](../../prompts/sesja-030.md) | częściowe |
| 031 | M2 | [AUTO i wznowienie od linii](../../prompts/sesja-031.md) | częściowe |
| 032 | M2 | [Baza narzędzi z typami](../../prompts/sesja-032.md) | ukończone |
| 033 | M2 | [Zerowanie detalu i sonda](../../prompts/sesja-033.md) | częściowe |
| 034 | M2 | [Ręczna zmiana narzędzia](../../prompts/sesja-034.md) | częściowe |
| 035 | M2 | [Alarmy na ekranie](../../prompts/sesja-035.md) | częściowe |
| 036 | M2 | [Poziomy dostępu](../../prompts/sesja-036.md) | ukończone |
| 037 | M2 | [Język polski i angielski](../../prompts/sesja-037.md) | częściowe |
| 038 | M2 | [Bufor i bramka G2 (prototyp v0.1)](../../prompts/sesja-038.md) | planowane |
| 039 | M3 | [Format .lnx i BaseMacroGenerator](../../prompts/sesja-039.md) | ukończone |
| 040 | M3 | [Generatory: nagłówek, koniec, narzędzie, planowanie](../../prompts/sesja-040.md) | ukończone |
| 041 | M3 | [Generatory: kieszenie](../../prompts/sesja-041.md) | ukończone |
| 042 | M3 | [Generatory: wiercenie i gwintowanie](../../prompts/sesja-042.md) | częściowe |
| 043 | M3 | [Generatory: rowki, czopy, kontur](../../prompts/sesja-043.md) | ukończone |
| 044 | M3 | [Lekser G-code i walidacja w edytorze](../../prompts/sesja-044.md) | ukończone |
| 045 | M3 | [Panel programu dialogowego](../../prompts/sesja-045.md) | częściowe |
| 046 | M3 | [Podglądy 2D w formularzach](../../prompts/sesja-046.md) | częściowe |
| 047 | M3 | [Menedżer programów i pliki .lnx](../../prompts/sesja-047.md) | częściowe |
| 048 | M3 | [Biblioteka podprogramów o-word](../../prompts/sesja-048.md) | ukończone |
| 049 | M3 | [Test technologiczny na Plant](../../prompts/sesja-049.md) | ukończone |
| 050 | M3 | [Bufor i bramka G3 (prototyp v0.2)](../../prompts/sesja-050.md) | planowane |
| 051 | M4 | [Ścieżka z programu](../../prompts/sesja-051.md) | ukończone |
| 052 | M4 | [Proces symulacji](../../prompts/sesja-052.md) | ukończone |
| 053 | M4 | [Czas obróbki i porównanie z Plant](../../prompts/sesja-053.md) | częściowe |
| 054 | M4 | [Przygotówka](../../prompts/sesja-054.md) | ukończone |
| 055 | M4 | [Materiał 2.5D](../../prompts/sesja-055.md) | częściowe |
| 056 | M4 | [Reguły kolizji lite](../../prompts/sesja-056.md) | częściowe |
| 057 | M4 | [Widok 3D symulacji](../../prompts/sesja-057.md) | częściowe |
| 058 | M4 | [Typy narzędzi w symulacji](../../prompts/sesja-058.md) | częściowe |
| 059 | M4 | [Raport symulacji i eksport STL](../../prompts/sesja-059.md) | częściowe |
| 060 | M4 | [Bufor i bramka G4 (prototyp v0.3)](../../prompts/sesja-060.md) | planowane |
| 061 | M5 | [machine.yaml: napędy i wejścia rzeczywiste](../../prompts/sesja-061.md) | częściowe |
| 062 | M5 | [Generator INI/HAL: sim, Plant, step/dir](../../prompts/sesja-062.md) | częściowe |
| 063 | M5 | [Generator EtherCAT (lcec, CiA 402)](../../prompts/sesja-063.md) | planowane |
| 064 | M5 | [Wrzeciono RS485 w generatorze](../../prompts/sesja-064.md) | planowane |
| 065 | M5 | [Kinematyki 4 i 5 osi](../../prompts/sesja-065.md) | częściowe |
| 066 | M5 | [Automatyczna zmiana narzędzia](../../prompts/sesja-066.md) | częściowe |
| 067 | M5 | [Kreator konfiguracji maszyny](../../prompts/sesja-067.md) | planowane |
| 068 | M5 | [Test latencji i raport kwalifikacji](../../prompts/sesja-068.md) | planowane |
| 069 | M5 | [Diagnostyka napędów](../../prompts/sesja-069.md) | częściowe |
| 070 | M5 | [Łańcuch E-STOP i bezpieczeństwo](../../prompts/sesja-070.md) | częściowe |
| 071 | M5 | [Asystent strojenia na Plant](../../prompts/sesja-071.md) | planowane |
| 072 | M5 | [Bufor i bramka G5 (prototyp v0.4)](../../prompts/sesja-072.md) | planowane |
| 073 | M6 | [Wtyczki deklaratywne: format i silnik](../../prompts/sesja-073.md) | planowane |
| 074 | M6 | [Menedżer wtyczek](../../prompts/sesja-074.md) | planowane |
| 075 | M6 | [Panel cykli i skryptów](../../prompts/sesja-075.md) | planowane |
| 076 | M6 | [Repozytorium społeczności i przykłady](../../prompts/sesja-076.md) | planowane |
| 077 | M6 | [Instalator dla Debiana 12 + LinuxCNC 2.9](../../prompts/sesja-077.md) | częściowe |
| 078 | M6 | [Pierwsze uruchomienie i linumert doctor](../../prompts/sesja-078.md) | częściowe |
| 079 | M6 | [Dokumentacja użytkownika](../../prompts/sesja-079.md) | częściowe |
| 080 | M6 | [Przegląd IP przed wydaniem](../../prompts/sesja-080.md) | częściowe |
| 081 | M6 | [Twardnienie](../../prompts/sesja-081.md) | częściowe |
| 082 | M6 | [Pełna regresja na Plant](../../prompts/sesja-082.md) | częściowe |
| 083 | M6 | [Wydanie v0.5.0-alpha](../../prompts/sesja-083.md) | planowane |
| 084 | M6 | [Retrospektywa i kolejne półrocze](../../prompts/sesja-084.md) | planowane |

## Rozszerzenia włączone do pierwotnych sesji

Nie są kolejnym harmonogramem. Ich status dotyczy tylko wskazanego kroku.

| ID (dawny alias) | Sesje nadrzędne | Zakres | Stan |
|---|---|---|---|
| HMI-01 | 005, 027 | Mapa widgetów i kontrakt QtDragon | częściowe |
| HMI-02 | 028, 029, 030 | Powłoka i nawigacja | częściowe |
| HMI-03 | 032, 033, 034 | Zero detalu i narzędzia | częściowe |
| HMI-04 | 031, 044, 045, 047, 057 | Program, symulacja i produkcja | częściowe |
| HMI-05 | 035, 069 | Diagnostyka i alarmy | częściowe |
| HMI-06 | 038 | Odbiór ekranów | częściowe |
| D38-A | 031 | Wycofanie i powrót w pauzie | ukończone |
| D38-B | 031 | Odzyskiwanie i powrót helisą z zakładką | częściowe |
| PLAN-21-22 | 041 | Kieszenie v2 | ukończone |
| PLAN-23 | 045, 047 | Pliki .lnx i edycja kroków | ukończone |
| PLAN-24 | 031 | Podgląd D38 | ukończone |
| PLAN-25 | 053 | ETA i kalibracja trzech programów | ukończone |
| PLAN-26 | 057, 059 | Raport z aktualnym widokiem i osią zdarzeń | ukończone |
| PLAN-27 | 026, 038, 077 | Ręczny odbiór pulpitu | do odbioru |
| SKIN-00 | 027 | Audyt kontraktów i decyzja architektoniczna | częściowe |
| SKIN-01 (085) | 057 | Prototyp renderera 3D | ukończone |
| SKIN-02 | 028, 070 | Skin API, host i kanały CNC | częściowe |
| SKIN-03 | 027, 037 | Palety, EN/PL i preferencje | częściowe |
| SKIN-04 | 028 | Classic Digital i Industrial Pro | częściowe |
| SKIN-05 | 028 | Cyberdeck i Organic Vector | częściowe |
| SKIN-06 | 038, 060 | Odbiór skórek i renderera | częściowe |
| SKIN-PREVIEW (086) | 028, 057 | Podgląd czterech kompozycji | ukończone |
| SKIN-GALLERY (087) | 079 | Zrzuty i galeria | ukończone |
| SKIN-OFFLINE (088) | 028 | Cztery osobne ekrany offline | ukończone |
| KONKURS-01 (Konkurs-01) | 061, 070 | Bramka konfiguracji przed exec LinuxCNC | ukończone |
| KONKURS-02 | 026, 068, 072, 082 | Procedura i audyt odbioru stanowiska | ukończone |
| KONKURS-03 | 010, 061, 066 | Audyt luk i odrzucanie NaN/inf | ukończone |
| KONKURS-04 (K04) | 028, 037 | Monitor skórek read-only | ukończone |
| ISO-INTEGRATION (K05) | 077 | Bramka sim/Plant i monitor w obrazie ISO | ukończone |
| ISO-ACCEPTANCE | 077, 078 | Odbiór i publikacja obrazu | częściowe |
| OD-01 | 024, 066, 072, 082 | Macierz Plant nie może przechodzić z nieoczekiwaną kolizją | ukończone |
| EDITOR-VALIDATION | 044, 047 | Walidacja bieżącej treści i wyszukiwanie | ukończone |
| LEGACY-RUNTIME | 017, 025, 026, 070, 077, 082 | Diagnostyka uruchomień z dawnych promptów startowych | częściowe |
| ROADMAP-UNIFICATION | 001, 084 | Jeden rejestr planu i migracja statusów | ukończone |
| LIMITS-PREFLIGHT | 031, 051 | Kontrola limitów osi przed startem programu | częściowe |
| ORIGIN-WIZARD | 033, 054 | Kreator zera detalu na przygotówce | częściowe |
| M6-G43 | 034, 066 | Automatyczna korekta długości narzędzia po M6 | częściowe |
| PLANT-SUBSTEPS | 049, 063 | Plant: wynik niezależny od podkroków całkowania | ukończone |
| HMI-OWNER-SKINS | 028 | Odrębny wygląd każdej skórki i główny ekran holograficzny | częściowe |

## Postęp, pozostały zakres i dowody

### 001 — Szkielet repozytorium, CI i licencja

**ukończone**. 2026-10-17 | Szkielet monorepo: pyproject, katalogi z README, Makefile, CI, LICENSE (GPL-2), LICENCJE, PROVENANCE, testy licencji/IP/układu; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-001.md](../../prompts/sesja-001.md).

### 002 — Wytyczne IP i rejestr pochodzenia

**ukończone**. 2026-10-17 | Proces IP, słownik, rejestr pochodzenia (52 wpisy), lista przed wydaniem, rozszerzony strażnik IP; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-002.md](../../prompts/sesja-002.md).

### 003 — Spike: LinuxCNC 2.9 w środowisku agenta

**ukończone**. 2026-10-18 | LinuxCNC 2.9 RIP (uspace) w środowisku agenta: budowa, testy, CI na Debianie 12 (debian:bookworm); PR #3 i #26; Codex, dokończenie Claude (D31)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-003.md](../../prompts/sesja-003.md).

### 004 — Konfiguracja sim 3 osie z QtDragon

**ukończone**. 2026-10-18 | Konfiguracja sim linumert_xyz (QtDragon, kontrakt sygnałów D05, bazowanie latch release), HAL_KONTRAKT, SIM_WSL; PR #24; Claude (D31)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-004.md](../../prompts/sesja-004.md).

### 005 — Kopia bazowa ekranu QtDragon

**ukończone**. 2026-10-18 | Ekran screens/linumert: kopia QtDragon 2.9.10 (commit 86cdca7), handler-patch, UPSTREAM.md, DISPLAY = qtvcp linumert, zrzut G0; PR #25; Claude (D31)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-005.md](../../prompts/sesja-005.md).

### 006 — Rdzeń: model stanu maszyny i atrapa

**ukończone**. 2026-10-18 | Rdzeń cnc: niezmienna migawka stanu, czytnik linuxcnc.stat (wstrzykiwany moduł), atrapa z wirtualnym zegarem, 30 testów, docs/RDZEN.md; PR #5; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-006.md](../../prompts/sesja-006.md).

### 007 — Katalog alarmów i tłumaczenia

**ukończone**. 2026-10-24 | Katalog alarmów i manager PL/EN (2026-10-18) oraz mechanizm Qt: screens/linumert/linumert_i18n.py (translate(), .qm albo .ts bez lrelease, język z INI/env), screens/linumert/i18n/linumert_pl.ts, tools/i18n.sh (pylupdate5/lrelease), tools/i18n_check.py; pierwsze teksty przez translate(): panel alarmów; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [tests/test_alarms.py](../../tests/test_alarms.py), [tests/test_i18n.py](../../tests/test_i18n.py), [prompts/sesja-007.md](../../prompts/sesja-007.md).

### 008 — Bufor i bramka G0

**ukończone**. 2026-10-18 | Bramka G0: sprzątanie po testach LinuxCNC (61/61 w jednym przebiegu), czytnik rdzenia na RIP (zaległość 006), docs/raporty/G0.md, architektura w README; PR #35; Claude

Bramka automatyczna: `automatic_pass`; odbiór stanowiska osobno.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [docs/raporty/G0.md](../raporty/G0.md), [prompts/sesja-008.md](../../prompts/sesja-008.md).

### 009 — Specyfikacja wirtualnej maszyny Plant

**ukończone**. 2026-10-18 | Specyfikacja Plant (docs/PLANT.md), protokół LRT-NET v1, macierz 22 REQ, testy spójności; PR #7; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-009.md](../../prompts/sesja-009.md).

### 010 — Model obrabiarki machine.yaml (jedno źródło prawdy)

**ukończone**. 2026-10-18 | Schemat machine.yaml (Pydantic v2), 24 reguły spójności, 5 przykładowych maszyn, 42 testy; PR #8; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-010.md](../../prompts/sesja-010.md).

### 011 — Plant: rdzeń dynamiki osi (C)

**ukończone**. 2026-10-18 | Plant: rdzeń dynamiki osi w C (bezwładność, krzywa momentu, tarcie, grawitacja, luz, zderzaki), 23 testy C, make test-c w CI; PR #9; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-011.md](../../prompts/sesja-011.md).

### 012 — Plant: emulacja napędów CiA 402 i krokowców

**ukończone**. 2026-10-18 | Plant: napęd CiA 402 (CSP, krokowiec otwarty/zamknięty, awarie E-42xx) w C, 49 testów; PR #10; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-012.md](../../prompts/sesja-012.md).

### 013 — Biblioteka napędów wirtualnych: szablony, kopiowanie, parametryzacja

**ukończone**. 2026-10-18 | Biblioteka napędów wirtualnych: 7 szablonów YAML + JSON Schema, instancje drives: w machine.yaml (id/template/overrides), CLI drive clone, parametry w locie; REQ-VD-01…05; PR #11; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-013.md](../../prompts/sesja-013.md).

### 014 — Plant: łańcuch kinematyczny, przejazdy, zderzaki, krańcówki, I/O

**ukończone**. 2026-10-18 | Plant: machine.c (osie i napędy, gantry z alarmem rozjazdu, łańcuch kinematyczny, zderzaki, krańcówki, indeks, E-STOP, sonda, I/O 32 bity), build_machine.py + ctypes; REQ-VM-02…05; PR #12; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-014.md](../../prompts/sesja-014.md).

### 015 — Bazowanie po rozruchu: krańcówka, indeks, twardy zderzak, absolut, napęd

**ukończone**. 2026-10-18 | Bazowanie po rozruchu (REQ-VM-07): enkoder przyrostowy/absolutny z baterią (E-4211), tryb 6 w napędzie, start losowy, plik stanu, gantry, atrapa mastera, hal/lrt_hardstop_home.comp; PR #13; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-015.md](../../prompts/sesja-015.md).

### 016 — Plant: serwer LRT-NET

**ukończone**. 2026-10-18 | Plant: serwer LRT-NET (kodek v1, UDP lockstep/realtime, watchdog E-4003, stan bezpieczny, SHA-256 śladu, ślad CSV/JSONL, master testowy); 10 000 ramek bez strat; REQ-QA-03/04; PR #17; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-016.md](../../prompts/sesja-016.md).

### 017 — Komponent HAL lrt_net

**ukończone**. 2026-10-18 | Komponenty HAL lrt_net + lrt_cia402 (LRT-NET v1 w C), test halrun + Plant; PR #27; Claude (D31)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-017.md](../../prompts/sesja-017.md).

### 018 — Konfiguracja LinuxCNC dla Plant (3 osie)

**ukończone**. 2026-10-18 | config/plant/linumert_plant_xyz: LinuxCNC ↔ Plant, bazowanie na krańcówkach, test e2e, tools/dev/plant-gui.sh; PR #28; Claude (D31)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-018.md](../../prompts/sesja-018.md).

### 019 — Ograniczenia programowe, strefy zakazane i wyrocznia testowa

**ukończone**. 2026-10-18 | Wyrocznia Plant REQ-VM-06: soft limits i strefy zakazane, scenariusze softlimit/forbidden_zone z LinuxCNC; PR #29; Claude (D31)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-019.md](../../prompts/sesja-019.md).

### 020 — Magazyn narzędzi, pozycje wymiany i kolizje w Plant

**ukończone**. 2026-10-18 | Plant: magazyn narzędzi (regał/karuzela/parasol), zacisk, osłona, czujnik długości, kolizje CRASH; REQ-VM-08…10; PR #30; Claude (D31)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-020.md](../../prompts/sesja-020.md).

### 021 — Plant: wrzeciono VFD przez Modbus

**ukończone**. 2026-10-18 | Plant: wrzeciono VFD — model, hy_vfd (pty), Modbus TCP, usterki; wariant LinuxCNC _vfd z prawdziwym hy_vfd (M3/M4/M5); PR #32; Claude (D31)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-021.md](../../prompts/sesja-021.md).

### 022 — Plant: panel sterowania i pulpit MPG

**ukończone**. 2026-10-18 | Plant: panel web (FastAPI/WS, uPlot) — telemetria 10 s, parametry live i presety, CSV, wirtualny pulpit MPG jako bity LRT-NET; PR #37; Claude (Opus 5.5)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-022.md](../../prompts/sesja-022.md).

### 023 — Edytor wirtualnej obrabiarki w panelu Plant

**ukończone**. 2026-10-18 | Plant: edytor maszyny (drzewo, walidacja, wersje, przeładowanie bez restartu), widok 3D z modelu, zakładki Napędy i Awarie, scenariusz edit_reload; PR #39; Claude (Opus 5.5)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-023.md](../../prompts/sesja-023.md).

### 024 — Plant: scenariusze i raport prototypu

**ukończone**. 2026-10-18 | Plant: awarie (faults.py), scenariusze z atrapą mastera i z LinuxCNC, raport HTML/SVG, run_scenario, check_requirements w make test, job plant-matrix; PR #38; Claude (Opus 5.5)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-024.md](../../prompts/sesja-024.md).

### 025 — Skrypty maszyn wirtualnych (VirtualBox)

**ukończone**. 2026-10-19 | Skrypty VM: create-vms.ps1 (VBoxManage, SHA-256, unattended VM-B), post-install ctl/plant (usługa linumert-plant, socat dla hy_vfd), docs/VM.md, lrtnet_probe; Plant przyjmuje nową sesję mastera; PR #41; Claude (Opus 5.5)

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-025.md](../../prompts/sesja-025.md).

### 026 — Bufor i bramka G1 (prototyp P0)

**ukończone**. 2026-10-20 | Odbiór automatyczny Plant P0/G1: pełne CI Debian 12/LinuxCNC, C+ASan/UBSan, scenariusze, raport P0 i checklista ręczna; PR #56; Codex

Bramka automatyczna: `automatic_pass`; odbiór stanowiska osobno.

Pozostaje: Odbiór ręczny VM/Plant pozostaje otwarty; automatyczny P0 PASS nie zamyka odbioru stanowiska ani sprzętu.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [docs/raporty/G1.md](../raporty/G1.md), [prompts/sesja-026.md](../../prompts/sesja-026.md).

### 027 — Własny system projektowy ekranu

**ukończone**. 2026-10-24 | Rozliczenie promptu 027: tokens.yaml źródłem prawdy; QSS powłoki generowany z tokenów (linumert_shell_model.shell_qss, test kolorów/44 px) + tools/gen_qss.py do zrzutu; fonty IBM Plex Sans i JetBrains Mono (OFL) w screens/linumert/fonts, rejestrowane przy starcie ekranu i podglądu skórek; 31 ikon z wpisami PROVENANCE (test_ip_guard); skórki korzystają z kontraktu palet (linumert_skin_contract); Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [tests/test_design_system.py](../../tests/test_design_system.py), [tests/test_hmi_shell_model.py](../../tests/test_hmi_shell_model.py), [tests/test_ip_guard.py](../../tests/test_ip_guard.py), [prompts/sesja-027.md](../../prompts/sesja-027.md).

### 028 — Kompozycja ekranu głównego

**częściowe**. Powłoka HMI i nawigacja działają. Na polecenie właściciela 2026-10-25 priorytet przeniesiono na M2. Uzupełniono wymaganą specyfikację funkcjonalną SPEC_EKRAN_GLOWNY.md: dane operatora, hierarchia, brak ruchu od nawigacji i macierz dowodów odbioru. To specyfikacja, nie odbiór GUI ani zamknięcie skórek. Odbiór 6ecda95: 111 testów offline PASS, 1 SKIP, istniejący test GUI 45 kroków PASS na 1280×768. Zrzut ujawnił brak yaml w procesie QtVCP i zastępczą tabelę Narzędzia: pełny odbiór nadal otwarty. Samotest rozszerzono o obecność własnych stron tools/cycles, aby nie zaliczał fallbacku. Kolejny odbiór ad17702 po cnc_environment(): tools/cycles=true i 45 kroków PASS. PageStack e2dde87 izoluje rozmiar aktywnej strony; regresja Qt i złożenie HMI 2 PASS, ponowny test GUI 45 kroków PASS. Start nadal przewija poziomo; nie potwierdzono pełnego dopasowania 1280×768. PR #161: adaptacyjne kolumny kart Start i Narzędzia; pełne złożenie Qt 1280→1920→1280 bez poziomego przewijania, wpis i Tab oraz zachowanie formularza po zmianie układu potwierdzone testami. Samodzielny edytor STL zachowuje wysokość 600 px. 2026-10-25 (Claude): obszar „Wygląd” w działającym HMI — pięć palet, edytor dziesięciu ról kolorów, podgląd na żywo, zapis i reset, kontrola czytelności (kontrast WCAG, znaczenie E-STOP/ostrzeżeń); 23 testy, zrzuty w LinuxCNC (docs/raporty/hmi_appearance). Prawdziwe skórki (układy) nadal otwarte. 2026-10-25 (Claude): panel ruchu ręcznego i MDI widoczny w 1280×768 bez przewijania (w JOG/MDI na górze prawej kolumny strony Maszyna); test regresji tests/test_machine_page_layout.py. 2026-10-25 (Claude): pola formularzy, listy i pola liczbowe powłoki w ciemnym stylu z tokenów (strzałki z własnych ikon). 2026-10-26: dwukolumnowa szyna na niskim ekranie, znak marki, kody alarmów ze źródła i formularz Symulacji bez poziomego przewijania; 9 testów Qt PASS. Pełny odbiór HMI nadal otwarty. Kolejny odbiór: wszystkie karty czterech rodzin w 1280×768, 218 testów Qt/IP i 101 subtestów PASS; host Cyberdeck 45 kroków live PASS / 61,22 s. Raport HMI_CLOSEOUT_2026-10-26. Pełna sesja pozostaje partial. CI e9ed723: 1542 testy + 184 subtesty oraz 154 live PASS, wszystkie kontrole SUCCESS; #169 scalony 3c20817. Pozostaje odbiór pulpitu i pozostałych kryteriów całej 028. Odbiór właściciela: ogólne działanie podglądu potwierdzone, zgłoszony czerwony X w odznaczonych checkboxach. Poprawka rysuje pustą ramkę także w dialogach; 55 testów Qt/modelu PASS.

Pozostaje: Pełny odbiór kompozycji i nowych skórek; HMI-02, SKIN-04…06. Odbiór wizualny i klawiaturowy pozostałych kluczowych podstron 1280×768 oraz live QtVCP po zmianie układu; Start/Narzędzia odebrane w rzeczywistym Qt z atrapą CNC.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [docs/design/SPEC_EKRAN_GLOWNY.md](../design/SPEC_EKRAN_GLOWNY.md), [docs/raporty/G2/M2_028_2026-10-25.md](../raporty/G2/M2_028_2026-10-25.md), [docs/raporty/G2/M2_RESPONSIVE_2026-10-25.md](../raporty/G2/M2_RESPONSIVE_2026-10-25.md), [screens/linumert/linumert_appearance.py](../../screens/linumert/linumert_appearance.py), [screens/linumert/linumert_appearance_page.py](../../screens/linumert/linumert_appearance_page.py), [tests/test_appearance.py](../../tests/test_appearance.py), [docs/user/WYGLAD.md](../user/WYGLAD.md), [docs/raporty/hmi_appearance/wyglad_neon_punk.png](../raporty/hmi_appearance/wyglad_neon_punk.png), [tests/test_machine_page_layout.py](../../tests/test_machine_page_layout.py), [docs/raporty/G2/HMI_CLOSEOUT_2026-10-26.md](../raporty/G2/HMI_CLOSEOUT_2026-10-26.md), [prompts/sesja-028.md](../../prompts/sesja-028.md).

### 029 — Tryby, JOG i pulpit MPG

**częściowe**. JOG, tryby i edytowalny krok dostępne w HMI.

Pozostaje: Rozliczyć MPG i pełny scenariusz odbioru 029.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-029.md](../../prompts/sesja-029.md).

### 030 — MDI i klawiatura ekranowa

**częściowe**. MDI i klawiatura dostępne.

Pozostaje: Potwierdzić cały zakres oryginalnego promptu na docelowym pulpicie.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-030.md](../../prompts/sesja-030.md).

### 031 — AUTO i wznowienie od linii

**częściowe**. AUTO, ETA oraz wycofanie/powrót w pauzie D38-A wdrożone (#62).

Pozostaje: D38-B: odzyskiwanie po Abort/E-STOP lub wymianie narzędzia i wykonanie helisy/łuku z zakładką; pełny odbiór run-from-line.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-031.md](../../prompts/sesja-031.md).

### 032 — Baza narzędzi z typami

**ukończone**. 2026-10-18 | Baza narzędzi (rdzeń): 10 typów z walidacją, SQLite z migracjami i historią, tool.tbl bez strat (sprawdzone w rs274 LinuxCNC 2.9), CSV; ekran w sesji ekranu; PR #16; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-032.md](../../prompts/sesja-032.md).

### 033 — Zerowanie detalu i sonda

**częściowe**. Zero detalu G54–G59 i model przygotówki dostępne. Claude 2026-10-25: G54–G59.3 (G10 L2 P1–P9, wybór układu, obrót R, ruch do zera detalu ±0,01 mm, parametry w pliku zmiennych) oraz sondowanie G38.2/G38.3 Z i narożnika X/Y na LinuxCNC 2.9 + wygenerowany Plant (test linuxcnc); powtarzalność < 0,001 mm; błąd bezwzględny Z −0,011, X +0,016, Y +0,010 mm (luz 10 µm modelu napędów) — kryterium ≤ 0,01 mm niespełnione dla Z i X. docs/user/SONDOWANIE.md. Claude 2026-10-25: kalibracja sondy na wzorcu (stała poprawka na oś/kierunek, core/linumert/programs/probe_calibration.py): na Plant pięć par oś/kierunek skalibrowanych w jednym miejscu ściany i sprawdzonych w innym (przesunięcie 20 mm) daje błąd po poprawce ≤ 0,01 mm (0,000 mm w modelu deterministycznym); model napędów bez zmian. Brak jeszcze ekranu kalibracji w HMI. Claude 2026-10-25: scenariusze Plant probe_z_touchplate i probe_corner (plant/scenarios, master linuxcnc, REQ-VM-09) z kryteriami probed/probe_repeat/probe_tripped; na LinuxCNC RIP oba PASS (błąd bezwzględny ±0,02 mm, powtarzalność ≤ 0,002 mm, po kalibracji ≤ 0,01 mm).

Pozostaje: Scenariusz dla sondy płytkowej (probe.type plate) na LinuxCNC: konfiguracja istnieje tylko dla mill_servo_table (box). Logika sondy QtDragon (Basic/Versa) w nowym stylu i klik przez GUI na pulpicie; ręczny odbiór G54–G59.3 w HMI. Ekran kalibracji sondy w HMI (D36) i wykorzystanie poprawki w cyklach sondowania; kalibracja na sprzęcie.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [tests/test_work_offsets_probe_linuxcnc.py](../../tests/test_work_offsets_probe_linuxcnc.py), [tests/plant_session.py](../../tests/plant_session.py), [docs/user/SONDOWANIE.md](../user/SONDOWANIE.md), [core/linumert/programs/probe_calibration.py](../../core/linumert/programs/probe_calibration.py), [tests/test_probe_calibration.py](../../tests/test_probe_calibration.py), [tests/test_probe_calibration_linuxcnc.py](../../tests/test_probe_calibration_linuxcnc.py), [plant/scenarios/probe_z_touchplate.yaml](../../plant/scenarios/probe_z_touchplate.yaml), [plant/scenarios/probe_corner.yaml](../../plant/scenarios/probe_corner.yaml), [tests/test_probe_scenarios.py](../../tests/test_probe_scenarios.py), [prompts/sesja-033.md](../../prompts/sesja-033.md).

### 034 — Ręczna zmiana narzędzia

**częściowe**. M6 i integracja sim_toolchange z Plant dostępne.

Pozostaje: Rozliczyć dialog ToolDB, anulowanie W-2130 i opcjonalne wycofanie Z.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-034.md](../../prompts/sesja-034.md).

### 035 — Alarmy na ekranie

**częściowe**. Panel alarmów i trwała historia diagnostyczna z filtrami/CSV (#68).

Pozostaje: Pełne mapowanie kodów napędów/VFD i scenariusze alarmów z promptu.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-035.md](../../prompts/sesja-035.md).

### 036 — Poziomy dostępu

**ukończone**. 2026-10-24 | Role operator/technolog/serwis, PIN scrypt w SQLite (nigdy jawnie), blokada po błędach, audyt, CLI; przycisk roli i logowanie PIN w HMI; blokada edycji narzędzi/offsetów (technolog) i Konfiguracji/pełnego QtDragon (serwis). Opcjonalny klucz pulpitu: API Session.set_key, pin HAL do podłączenia z pulpitem; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [tests/test_access.py](../../tests/test_access.py), [tests/test_access_ui.py](../../tests/test_access_ui.py), [docs/OBSLUGA_OPERATORA.md](../OBSLUGA_OPERATORA.md), [prompts/sesja-036.md](../../prompts/sesja-036.md).

### 037 — Język polski i angielski

**częściowe**. Katalog EN/PL prototypu skórek istnieje. Mechanizm .ts/translate() z sesji 007 gotowy (Claude, 2026-10-24).

Pozostaje: Pełne tłumaczenie produkcyjnego HMI .ts/.qm, przełącznik i formaty jednostek; dług 007.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-037.md](../../prompts/sesja-037.md).

### 038 — Bufor i bramka G2 (prototyp v0.1)

**planowane**. Brak potwierdzonego zakończenia zakresu.

Bramka automatyczna: `open`; odbiór stanowiska osobno.

Źródła: [prompts/sesja-038.md](../../prompts/sesja-038.md).

### 039 — Format .lnx i BaseMacroGenerator

**ukończone**. 2026-10-18 | Format .lnx (Pydantic + lnx_schema.json), ;@STOCK, BaseMacroGenerator, deterministyczny kompilator .lnx → .ngc (golden, rs274), alarmy P-5011…P-5015; PR #14; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-039.md](../../prompts/sesja-039.md).

### 040 — Generatory: nagłówek, koniec, narzędzie, planowanie

**ukończone**. 2026-10-20 | Generatory header/program_end/tool_change/face_mill (#47) + walidacja kroków z bazą narzędzi (typ, średnica, skok, długość ostrza, obroty, kierunek; P-5207…P-5211, compile_program(tools=…)); Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-040.md](../../prompts/sesja-040.md).

### 041 — Generatory: kieszenie

**ukończone**. 2026-10-21 | Kieszenie v2: pionowo/rampa/helisa, naroża, obrót, CW/CCW, naddatki i wykańczanie; v1 niezmienne; golden, materiał bez wysp, rs274 i wykonanie na LinuxCNC + Plant; 882 + 94 LinuxCNC PASS; PR #58; Codex

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-041.md](../../prompts/sesja-041.md).

### 042 — Generatory: wiercenie i gwintowanie

**częściowe**. Generatory wiercenia/gwintowania istnieją.

Pozostaje: Odbiór wszystkich wzorów, cykli, walidacji i podglądu przez GUI.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-042.md](../../prompts/sesja-042.md).

### 043 — Generatory: rowki, czopy, kontur

**ukończone**. 2026-10-24 | contours.py: slot_linear, slot_arc, stud_rect, stud_circle, contour (G41.1/G42.1, dojazd/odjazd styczny, P-5010 z numerem segmentu), preview_2d, w menu Cykli; golden 5 programów, weryfikacja materiałem StockMap, test rs274 w CI; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [tests/test_gen_contours.py](../../tests/test_gen_contours.py), [tests/golden/contours_contour.ngc](../../tests/golden/contours_contour.ngc), [prompts/sesja-043.md](../../prompts/sesja-043.md).

### 044 — Lekser G-code i walidacja w edytorze

**ukończone**. 2026-10-18 | Lekser G-code LinuxCNC (P-5101…P-5111, linia/kolumna, słowa O), kontrola w rs274; 44 próbki zgodne z LinuxCNC 2.9; przycisk Sprawdź w sesji ekranu; PR #15; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-044.md](../../prompts/sesja-044.md).

### 045 — Panel programu dialogowego

**częściowe**. Panel Cykle: formularze, lista, edycja i pliki .lnx (#59).

Pozostaje: Komplet operacji kroków, walidacja przy polach i kryteria oryginalnego promptu.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-045.md](../../prompts/sesja-045.md).

### 046 — Podglądy 2D w formularzach

**częściowe**. Widżet Preview2D i podgląd ścieżek dostępne.

Pozostaje: Wszystkie prymitywy, wymiary i preview_2d wszystkich generatorów.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-046.md](../../prompts/sesja-046.md).

### 047 — Menedżer programów i pliki .lnx

**częściowe**. Wybór programów i odczyt/zapis .lnx dostępne.

Pozostaje: Pełny menedżer, szablony i odbiór bezpiecznych operacji plikowych.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-047.md](../../prompts/sesja-047.md).

### 048 — Biblioteka podprogramów o-word

**ukończone**. 2026-10-24 | 6 podprogramów o<lrt_...> z nagłówkiem NgcGui (planowanie, wiercenie siatka/okrąg, kieszeń prostokątna i okrągła, rowek prosty), zgodność ruchu z generatorami w rs274 (CI), eksport z Cykli, docs/user/PODPROGRAMY.md; Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [tests/test_subroutines.py](../../tests/test_subroutines.py), [docs/user/PODPROGRAMY.md](../user/PODPROGRAMY.md), [prompts/sesja-048.md](../../prompts/sesja-048.md).

### 049 — Test technologiczny na Plant

**ukończone**. Wybrane cykle na LinuxCNC + Plant (#58/#60); tools/suite_cycles.py: 10 przypadków generatorów (planowanie, wiercenie G81/G83, kieszenie, rowki, czopy, kontur) × router_gantry_steppers i mill_servo_table, warianty A (G0 z machine.yaml) i B (G0 ≤ 3000 mm/min): 40/40 PASS po poprawce Plant (interpolacja celu CSP w podkrokach, PLANT-SUBSTEPS). Wcześniejsze zgubione kroki routera i E-4201 frezarki przy G0 były artefaktem modelu, nie generatorów.

Pozostaje: Kontur z korekcją G41.1/G42.1 na Plant z LinuxCNC (atrapa jedzie bez korekcji; rs274 w CI).

Źródła: [tools/suite_cycles.py](../../tools/suite_cycles.py), [tests/test_suite_cycles.py](../../tests/test_suite_cycles.py), [docs/raporty/suite_cycles.md](../raporty/suite_cycles.md), [docs/raporty/plant_substeps.md](../raporty/plant_substeps.md), [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-049.md](../../prompts/sesja-049.md).

### 050 — Bufor i bramka G3 (prototyp v0.2)

**planowane**. Brak potwierdzonego zakończenia zakresu.

Bramka automatyczna: `open`; odbiór stanowiska osobno.

Źródła: [prompts/sesja-050.md](../../prompts/sesja-050.md).

### 051 — Ścieżka z programu

**ukończone**. simulation/linumert_sim/path.py: MoveList (start/end float32, line/tool int32, kind int8, feed float32), łuki G17/G18/G19 z linią śrubową na cięciwach z błędem ≤ 0,01 mm, PathCanon dla gcode.parse oraz zapasowy interpreter podzbioru (G0–G3, IJK/R, G20/21, G90/91, G90.1/91.1, T/M6, G81/82/83/73 z G98/G99) z notatkami zamiast zgadywania. 10 programów golden z M3; z LinuxCNC 2.9 (RIP) 9 programów bez korekcji zgodnych z rs274 co do linii, końców i długości. Naprawiony brak canon.parameter_file (TypeError w gcode.parse, także w core load_ngc).

Pozostaje: Podłączenie MoveList do procesu symulacji i widoku 3D (052/057). Korekcja G41/G42 i o-word call tylko przez rs274 (podzbiór zapisuje notatkę).

Źródła: [simulation/linumert_sim/path.py](../../simulation/linumert_sim/path.py), [tests/test_sim_path.py](../../tests/test_sim_path.py), [tests/test_toolpath.py](../../tests/test_toolpath.py), [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-051.md](../../prompts/sesja-051.md).

### 052 — Proces symulacji

**ukończone**. Symulacja live (osobny proces, nice 10) z wcześniejszych sesji, a teraz także offline: simulation/linumert_sim/offline.py (ścieżka 051 → SimEngine: materiał, K-3xx, czas G0/G1, objętość usunięta) i worker.py — proces potomny spawn z nice ≥ 10, kolejka zadań, anulowanie zadania bieżącego i oczekującego, cache wyników po SHA-256 wejścia (pamięć + pliki JSON), wątek pomocniczy z callbackiem; most sygnałów Qt screens/linumert/linumert_sim_worker.py. MoveList z obrotami wrzeciona (S, M3/M4/M5; rs274 przez LineCode.spindle/speed).

Pozostaje: Podłączenie workera offline do strony Symulacja ekranu i widoku 3D (057). Czas z przyspieszeniami i porównanie z Plant (053).

Źródła: [simulation/linumert_sim/offline.py](../../simulation/linumert_sim/offline.py), [simulation/linumert_sim/worker.py](../../simulation/linumert_sim/worker.py), [screens/linumert/linumert_sim_worker.py](../../screens/linumert/linumert_sim_worker.py), [tests/test_sim_worker.py](../../tests/test_sim_worker.py), [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-052.md](../../prompts/sesja-052.md).

### 053 — Czas obróbki i porównanie z Plant

**częściowe**. ETA oraz porównanie trzech programów z Plant: błąd 2,22–4,46% (#60).

Pozostaje: Pełny wynik per narzędzie/krok i odbiór zakresu modelu; wyniki nie są ogólną gwarancją ±10%.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-053.md](../../prompts/sesja-053.md).

### 054 — Przygotówka

**ukończone**. 2026-10-20 | Przygotówka: ;@STOCK, dialog Symulacja, K-321 (wcześniej) + cel sondy Plant z przygotówki (tools/stock_probe.py); Claude

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-054.md](../../prompts/sesja-054.md).

### 055 — Materiał 2.5D

**częściowe**. Materiał 2.5D i obróbka na żywo działają.

Pozostaje: Pełny odbiór dokładności objętości ±2% i wydajności.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-055.md](../../prompts/sesja-055.md).

### 056 — Reguły kolizji lite

**częściowe**. Kolizje diagnostyczne na żywo działają.

Pozostaje: Pełna macierz reguł i tryb offline; nie przywracać komend E-STOP z symulacji.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-056.md](../../prompts/sesja-056.md).

### 057 — Widok 3D symulacji

**częściowe**. Widok 3D, kamery i raportowa oś zdarzeń działają.

Pozostaje: Interaktywna oś czasu/skok do linii i benchmark 100 000 segmentów; SKIN-01/06.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-057.md](../../prompts/sesja-057.md).

### 058 — Typy narzędzi w symulacji

**częściowe**. Profile narzędzi działają; specjalne STL używa walca zastępczego.

Pozostaje: Pełne profile i K-303, obwiednia STL oraz odbiór stemplowania.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-058.md](../../prompts/sesja-058.md).

### 059 — Raport symulacji i eksport STL

**częściowe**. Eksport HTML z aktualnym obrazem, osią zdarzeń oraz STL istnieje (#60).

Pozostaje: Spójna droga offline „Symuluj” z panelu dialogowego i plików.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-059.md](../../prompts/sesja-059.md).

### 060 — Bufor i bramka G4 (prototyp v0.3)

**planowane**. Brak potwierdzonego zakończenia zakresu.

Bramka automatyczna: `open`; odbiór stanowiska osobno.

Źródła: [prompts/sesja-060.md](../../prompts/sesja-060.md).

### 061 — machine.yaml: napędy i wejścia rzeczywiste

**częściowe**. Schemat maszyny i deklaracje wdrożenia hardware; sekcja real: szablonów napędów (REQ-VD-06): stepgen z czasami impulsów, ethercat_cia402 z PDO, vfd_modbus (hy_vfd/mb2hal), pwm — we wszystkich 7 szablonach biblioteki; machine.yaml: target plant|sim|hardware i sekcja hardware (interfejs parport/mesa/ethercat, karta 7i96s/7i76e, kanały napędów, port falownika); hardware_plan() — sterownik, kanał i skala impulsów z mechaniki szablonu. 22/22 wymagań pokrytych.

Pozostaje: Pulpit (MPG, przyciski) i E-STOP rzeczywisty w sekcji hardware. Raport konkursu 03.

Źródła: [plant/server/linumert_plant/drive_real.py](../../plant/server/linumert_plant/drive_real.py), [core/linumert/machine/schema.py](../../core/linumert/machine/schema.py), [plant/library/drives/README.md](../../plant/library/drives/README.md), [tests/test_drive_real.py](../../tests/test_drive_real.py), [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-061.md](../../prompts/sesja-061.md).

### 062 — Generator INI/HAL: sim, Plant, step/dir

**częściowe**. Codex: rozpoczęto po scaleniu integracji #125 (b2ee924), na jawne polecenie właściciela. Krok 1: kopia całej istniejącej konfiguracji do unikalnego katalogu, diff bez zapisu, odmowa nieprawidłowych ścieżek i dowiązań; 8 testów Windows/Python3.12 PASS. Claude: szablony INI/HAL plant i sim z machine.yaml (golden: plant = ręczna konfiguracja Plant instrukcja po instrukcji), wyjście hardware step/dir (Mesa 7i96S/7i76E, port równoległy z ostrzeżeniem, hy_vfd, [SAFETY]; przechodzi deployment --hal-from-ini; odmowa bez E-STOP), CLI linumert-config build z podglądem i kopią zapasową; wygenerowany sim bramy uruchomiony i zbazowany w LinuxCNC 2.9 RIP. Claude 2026-10-25: wygenerowany Plant (mill_servo_table, --target plant) uruchomiony bezpośrednio w LinuxCNC 2.9 RIP z serwerem Plant: włączenie, bazowanie wszystkich osi, ruch MDI X50 (tests/test_configgen_plant_linuxcnc.py, marker linuxcnc, pod blokadą). NIEZWERYFIKOWANE NA SPRZĘCIE.

Pozostaje: Nazwy pinów Mesa i całe wyjście hardware: NIEZWERYFIKOWANE NA SPRZĘCIE. EtherCAT (063), wrzeciono PWM/mb2hal (064).

Źródła: [core/linumert/machine/config_files.py](../../core/linumert/machine/config_files.py), [tests/test_config_files.py](../../tests/test_config_files.py), [core/linumert/machine/configgen.py](../../core/linumert/machine/configgen.py), [core/linumert/machine/configgen_hw.py](../../core/linumert/machine/configgen_hw.py), [core/linumert/machine/config_build.py](../../core/linumert/machine/config_build.py), [tests/test_configgen.py](../../tests/test_configgen.py), [tests/test_configgen_cli.py](../../tests/test_configgen_cli.py), [tests/test_configgen_hw.py](../../tests/test_configgen_hw.py), [config/hardware/router_gantry_mesa.example.yaml](../../config/hardware/router_gantry_mesa.example.yaml), [tests/test_configgen_plant_linuxcnc.py](../../tests/test_configgen_plant_linuxcnc.py), [prompts/sesja-062.md](../../prompts/sesja-062.md).

### 063 — Generator EtherCAT (lcec, CiA 402)

**planowane**. Brak potwierdzonego zakończenia zakresu.

Źródła: [prompts/sesja-063.md](../../prompts/sesja-063.md).

### 064 — Wrzeciono RS485 w generatorze

**planowane**. Brak potwierdzonego zakończenia zakresu.

Źródła: [prompts/sesja-064.md](../../prompts/sesja-064.md).

### 065 — Kinematyki 4 i 5 osi

**częściowe**. Plant ma bazową kinematykę maszyn wieloosiowych.

Pozostaje: Pełna fizyka osi obrotowych, generator kinematyk, DRO/TCP i five_axis_demo.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-065.md](../../prompts/sesja-065.md).

### 066 — Automatyczna zmiana narzędzia

**częściowe**. Model magazynu i zacisku Plant istnieje.

Pozostaje: Remap M6, widok magazynu, scenariusze ATC i walidacja geometrii/stref wymiany.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-066.md](../../prompts/sesja-066.md).

### 067 — Kreator konfiguracji maszyny

**planowane**. Brak potwierdzonego zakończenia zakresu.

Źródła: [prompts/sesja-067.md](../../prompts/sesja-067.md).

### 068 — Test latencji i raport kwalifikacji

**planowane**. Brak potwierdzonego zakończenia zakresu.

Źródła: [prompts/sesja-068.md](../../prompts/sesja-068.md).

### 069 — Diagnostyka napędów

**częściowe**. Diagnostyka HMI i historia komunikatów dostępne.

Pozostaje: Dekoder CiA402, wykresy napędów, ethercat slaves/master i test fault.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-069.md](../../prompts/sesja-069.md).

### 070 — Łańcuch E-STOP i bezpieczeństwo

**częściowe**. Łańcuch HMI/HAL, watchdog, audyt i bramka przed startem wdrożone (#93).

Pozostaje: Pełny generator i odbiór toru sprzętowego oraz niezależnego nadzoru PC; bez osłabiania kontraktu safety.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-070.md](../../prompts/sesja-070.md).

### 071 — Asystent strojenia na Plant

**planowane**. Brak potwierdzonego zakończenia zakresu.

Źródła: [prompts/sesja-071.md](../../prompts/sesja-071.md).

### 072 — Bufor i bramka G5 (prototyp v0.4)

**planowane**. Brak potwierdzonego zakończenia zakresu.

Bramka automatyczna: `open`; odbiór stanowiska osobno.

Źródła: [prompts/sesja-072.md](../../prompts/sesja-072.md).

### 073 — Wtyczki deklaratywne: format i silnik

**planowane**. Brak potwierdzonego zakończenia zakresu.

Źródła: [prompts/sesja-073.md](../../prompts/sesja-073.md).

### 074 — Menedżer wtyczek

**planowane**. Brak potwierdzonego zakończenia zakresu.

Źródła: [prompts/sesja-074.md](../../prompts/sesja-074.md).

### 075 — Panel cykli i skryptów

**planowane**. Brak potwierdzonego zakończenia zakresu.

Źródła: [prompts/sesja-075.md](../../prompts/sesja-075.md).

### 076 — Repozytorium społeczności i przykłady

**planowane**. Brak potwierdzonego zakończenia zakresu.

Źródła: [prompts/sesja-076.md](../../prompts/sesja-076.md).

### 077 — Instalator dla Debiana 12 + LinuxCNC 2.9

**częściowe**. Starter kontenerowy, live-build ISO i integracja sim/Plant/monitora (#97).

Pozostaje: Instalator /opt, update/rollback/uninstall, idempotencja, odbiór live USB/instalacji i latencji.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-077.md](../../prompts/sesja-077.md).

### 078 — Pierwsze uruchomienie i linumert doctor

**częściowe**. Raport środowiska doctor działa offline i w HMI.

Pozostaje: Wersje/działanie LinuxCNC/HAL, uprawnienia, Plant, latencja i kreator pierwszego uruchomienia.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-078.md](../../prompts/sesja-078.md).

### 079 — Dokumentacja użytkownika

**częściowe**. Instrukcje uruchomienia, wybranych funkcji i zrzuty istnieją.

Pozostaje: Komplet podręcznika dla zakresu 079; nie dokumentować planowanych funkcji jako działających.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-079.md](../../prompts/sesja-079.md).

### 080 — Przegląd IP przed wydaniem

**częściowe**. Strażnik IP, licencje i provenance istnieją.

Pozostaje: Pełny audyt przed wydaniem, przegląd podobieństwa i wyniki sprawdzenia nazwy.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-080.md](../../prompts/sesja-080.md).

### 081 — Twardnienie

**częściowe**. Część walidacji, ograniczeń i bezpiecznych operacji plikowych wdrożona.

Pozostaje: Pełny przegląd uprawnień/nasłuchu/limitów oraz pip-audit i raport.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-081.md](../../prompts/sesja-081.md).

### 082 — Pełna regresja na Plant

**częściowe**. CI Python/C/LinuxCNC i macierz Plant istnieją.

Pozostaje: suite_all 3× PASS i naprawa OD-01: zielona macierz mimo CRASH/COVER_CRASH.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [prompts/sesja-082.md](../../prompts/sesja-082.md).

### 083 — Wydanie v0.5.0-alpha

**planowane**. Brak potwierdzonego zakończenia zakresu.

Bramka automatyczna: `open`; odbiór stanowiska osobno.

Źródła: [prompts/sesja-083.md](../../prompts/sesja-083.md).

### 084 — Retrospektywa i kolejne półrocze

**planowane**. Brak potwierdzonego zakończenia zakresu.

Źródła: [prompts/sesja-084.md](../../prompts/sesja-084.md).

### HMI-01 — Mapa widgetów i kontrakt QtDragon

**częściowe**. Handler-patch i powłoka istnieją.

Pozostaje: Rozliczyć pełną inwentaryzację i odbiór etapu.

Źródła: [docs/design/HMI_WORKFLOW.md](../design/HMI_WORKFLOW.md), [screens/linumert/UPSTREAM.md](../../screens/linumert/UPSTREAM.md).

### HMI-02 — Powłoka i nawigacja

**częściowe**. Działające widoki i testy automatyczne opisano w dzienniku.

Pozostaje: Pełne kryteria HMI i odbiór pulpitu pozostają do rozliczenia.

Źródła: [docs/design/HMI_WORKFLOW.md](../design/HMI_WORKFLOW.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### HMI-03 — Zero detalu i narzędzia

**częściowe**. Działające widoki i testy automatyczne opisano w dzienniku.

Pozostaje: Pełne kryteria HMI i odbiór pulpitu pozostają do rozliczenia.

Źródła: [docs/design/HMI_WORKFLOW.md](../design/HMI_WORKFLOW.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### HMI-04 — Program, symulacja i produkcja

**częściowe**. Działające widoki i testy automatyczne opisano w dzienniku.

Pozostaje: Pełne kryteria HMI i odbiór pulpitu pozostają do rozliczenia.

Źródła: [docs/design/HMI_WORKFLOW.md](../design/HMI_WORKFLOW.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### HMI-05 — Diagnostyka i alarmy

**częściowe**. Działające widoki i testy automatyczne opisano w dzienniku.

Pozostaje: Pełne kryteria HMI i odbiór pulpitu pozostają do rozliczenia.

Źródła: [docs/design/HMI_WORKFLOW.md](../design/HMI_WORKFLOW.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### HMI-06 — Odbiór ekranów

**częściowe**. Działające widoki i testy automatyczne opisano w dzienniku.

Pozostaje: Pełne kryteria HMI i odbiór pulpitu pozostają do rozliczenia.

Źródła: [docs/design/HMI_WORKFLOW.md](../design/HMI_WORKFLOW.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### D38-A — Wycofanie i powrót w pauzie

**ukończone**. PR #62: external offsets, zachowanie modalności i testy sim/Plant PASS. PR #102: poprawka zależności QtVCP i test pełnego HMI (pauza, podgląd, raport, rzeczywiste wycofanie Z 2 mm/powrót/wznowienie), Debian PASS.

Źródła: [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md), [docs/raporty/HMI_PAUSE_RUNTIME_2026-10-24.md](../raporty/HMI_PAUSE_RUNTIME_2026-10-24.md), [tests/test_hmi_runtime_linuxcnc.py](../../tests/test_hmi_runtime_linuxcnc.py), [PR](https://github.com/anonimov94/linumeRT/pull/102).

### D38-B — Odzyskiwanie i powrót helisą z zakładką

**częściowe**. Geometria i diagnostyczny podgląd istnieją. Awaria otwierania podglądu w systemowym Pythonie QtVCP naprawiona w PR #102; nie dodaje wykonania helisy.

Pozostaje: Wykonanie po Abort/E-STOP/wymianie narzędzia i pełny odbiór; podgląd nie wykonuje ruchu.

Źródła: [docs/design/WZNOWIENIE.md](../design/WZNOWIENIE.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md), [docs/raporty/HMI_PAUSE_RUNTIME_2026-10-24.md](../raporty/HMI_PAUSE_RUNTIME_2026-10-24.md).

### PLAN-21-22 — Kieszenie v2

**ukończone**. Rampa/helisa, geometria i wykańczanie; #58, odbiór automatyczny PASS.

Źródła: [docs/PLAN_TYGODNIA_2026-10-21.md](../PLAN_TYGODNIA_2026-10-21.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### PLAN-23 — Pliki .lnx i edycja kroków

**ukończone**. PR #59: odbiór automatyczny wskazanego kroku PASS.

Źródła: [docs/PLAN_TYGODNIA_2026-10-21.md](../PLAN_TYGODNIA_2026-10-21.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### PLAN-24 — Podgląd D38

**ukończone**. PR #60: odbiór podglądu PASS; wykonanie pozostaje w D38-B.

Źródła: [docs/PLAN_TYGODNIA_2026-10-21.md](../PLAN_TYGODNIA_2026-10-21.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### PLAN-25 — ETA i kalibracja trzech programów

**ukończone**. PR #60: pomiary i testy ETA PASS.

Źródła: [docs/PLAN_TYGODNIA_2026-10-21.md](../PLAN_TYGODNIA_2026-10-21.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### PLAN-26 — Raport z aktualnym widokiem i osią zdarzeń

**ukończone**. PR #60: odbiór raportu PASS.

Źródła: [docs/PLAN_TYGODNIA_2026-10-21.md](../PLAN_TYGODNIA_2026-10-21.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### PLAN-27 — Ręczny odbiór pulpitu

**do odbioru**. Protokół przygotowany. Ręcznie potwierdzone przez właściciela 2026-10-24 (SHA 4bc7a14, potem 27b9245): punkty 1–6 i 8 (pełny ekran, Plant, bazowanie/JOG/MDI, M3/M5/M6, program z pauzą i wznowieniem, cykle .lnx, brak pozostałej instancji po zamknięciu). Punkt 7 (raport HTML) i skróty QtDragon/Plant z menu aplikacji niesprawdzone.

Pozostaje: Sprawdzić raport HTML (przycisk Raport w widoku symulacji, domyślnie ~/raport_symulacji.html), skróty QtDragon i Plant z menu oraz dołączyć zrzuty i log.

Źródła: [docs/PLAN_TYGODNIA_2026-10-21.md](../PLAN_TYGODNIA_2026-10-21.md), [docs/raporty/prototypy/PLAN-21-27-2026-10-21.md](../raporty/prototypy/PLAN-21-27-2026-10-21.md).

### SKIN-00 — Audyt kontraktów i decyzja architektoniczna

**częściowe**. Audyt i niezależne kontrakty istnieją.

Pozostaje: Rozstrzygnąć propozycję zmiany prezentacji; nie zmienia zamrożonego stosu.

Źródła: [docs/design/SKIN_SYSTEM_ROADMAP.md](../design/SKIN_SYSTEM_ROADMAP.md), [docs/design/SKIN_AUDIT.md](../design/SKIN_AUDIT.md).

### SKIN-01 — Prototyp renderera 3D

**ukończone**. PR #87: prototyp i testy GPU/Mesa PASS; odbiór docelowego HMI należy do SKIN-06.

Źródła: [docs/design/SKIN_SYSTEM_ROADMAP.md](../design/SKIN_SYSTEM_ROADMAP.md), [docs/design/SKIN_AUDIT.md](../design/SKIN_AUDIT.md), [prompts/sesja-085.md](../../prompts/sesja-085.md).

### SKIN-02 — Skin API, host i kanały CNC

**częściowe**. Manifesty, kontrola przełączenia i monitor read-only istnieją. N1/Codex: prawdziwy gcode potwierdza posuwy G20/G21 i fizyczne numery linii; naprawiony parameter_file. Demo z T1 M6 ujawnia SIGSEGV w tooldata, pełny odbiór pozostaje otwarty. Opcjonalny host QtVCP de6b06d: istniejące STATUS, przyciski cyklu i globalny tor alarmów/E-STOP; implementacja do odbioru Claude na EndeavourOS. Skórki są luźną inspiracją według uściślenia właściciela 2026-10-25. Claude/bab3866: start Classic Digital na EndeavourOS oraz lint/1359 offline/check_requirements PASS; pozostałe rodziny wizualnie otwarte. 9167442 dodaje wybór czterech rodzin z Wyglądu i zapis na następny start; nowy krok do ponownego odbioru Claude.

Pozostaje: Produkcyjny host, kanał poleceń i potwierdzenie świeżości danych.

Źródła: [docs/design/SKIN_SYSTEM_ROADMAP.md](../design/SKIN_SYSTEM_ROADMAP.md), [docs/design/SKIN_AUDIT.md](../design/SKIN_AUDIT.md), [tests/test_toolpath.py](../../tests/test_toolpath.py), [docs/design/HMI_QTVCP_HOST.md](../design/HMI_QTVCP_HOST.md).

### SKIN-03 — Palety, EN/PL i preferencje

**częściowe**. Prototyp palet, tłumaczeń i preferencji istnieje.

Pozostaje: Pełna integracja i odbiór produkcyjnego GUI.

Źródła: [docs/design/SKIN_SYSTEM_ROADMAP.md](../design/SKIN_SYSTEM_ROADMAP.md), [docs/design/SKIN_AUDIT.md](../design/SKIN_AUDIT.md).

### SKIN-04 — Classic Digital i Industrial Pro

**częściowe**. Odrębne ekrany offline i monitor read-only.

Pozostaje: Pełne sterowanie i komplet widoków produkcyjnych.

Źródła: [docs/design/SKIN_SYSTEM_ROADMAP.md](../design/SKIN_SYSTEM_ROADMAP.md), [docs/design/SKIN_AUDIT.md](../design/SKIN_AUDIT.md).

### SKIN-05 — Cyberdeck i Organic Vector

**częściowe**. Odrębne ekrany offline i monitor read-only.

Pozostaje: Pełne sterowanie, komplet widoków i adaptacyjne układy.

Źródła: [docs/design/SKIN_SYSTEM_ROADMAP.md](../design/SKIN_SYSTEM_ROADMAP.md), [docs/design/SKIN_AUDIT.md](../design/SKIN_AUDIT.md).

### SKIN-06 — Odbiór skórek i renderera

**częściowe**. Macierze prototypów GL testowane.

Pozostaje: Pełny odbiór 4×4×2, rozdzielczości/dotyk, LinuxCNC/Plant, safety i pulpit.

Źródła: [docs/design/SKIN_SYSTEM_ROADMAP.md](../design/SKIN_SYSTEM_ROADMAP.md), [docs/design/SKIN_AUDIT.md](../design/SKIN_AUDIT.md).

### SKIN-PREVIEW — Podgląd czterech kompozycji

**ukończone**. PR #89: podgląd i odbiór 64 wariantów GL.

Źródła: [docs/design/SKIN_AUDIT.md](../design/SKIN_AUDIT.md), [docs/DZIENNIK.md](../DZIENNIK.md).

### SKIN-GALLERY — Zrzuty i galeria

**ukończone**. PR #90: nowe zrzuty i README.

Źródła: [docs/design/SKIN_AUDIT.md](../design/SKIN_AUDIT.md), [docs/DZIENNIK.md](../DZIENNIK.md).

### SKIN-OFFLINE — Cztery osobne ekrany offline

**ukończone**. PR #91: launcher --skin i 128 wariantów GL; bez integracji sterowania.

Źródła: [docs/design/SKIN_AUDIT.md](../design/SKIN_AUDIT.md), [docs/DZIENNIK.md](../DZIENNIK.md).

### KONKURS-01 — Bramka konfiguracji przed exec LinuxCNC

**ukończone**. PR #93 scalony: bramka profilu i ograniczony audyt HAL.

Źródła: [prompts/konkurs-2026-10/raporty/01.md](../../prompts/konkurs-2026-10/raporty/01.md), [prompts/konkurs-2026-10/01-bezpieczenstwo.md](../../prompts/konkurs-2026-10/01-bezpieczenstwo.md).

### KONKURS-02 — Procedura i audyt odbioru stanowiska

**ukończone**. PR #94 scalony: procedura i dowody; odbiór A3 FAIL OD-01, T1–T7 otwarte.

Źródła: [prompts/konkurs-2026-10/raporty/02.md](../../prompts/konkurs-2026-10/raporty/02.md), [prompts/konkurs-2026-10/02-odbior-stanowiska.md](../../prompts/konkurs-2026-10/02-odbior-stanowiska.md).

### KONKURS-03 — Audyt luk i odrzucanie NaN/inf

**ukończone**. PR #95 scalony: odrzucanie NaN/inf; real mapping i geometria ATC nadal otwarte.

Źródła: [raporty/03.md](../../raporty/03.md), [prompts/konkurs-2026-10/03-pokrycie-wymagan.md](../../prompts/konkurs-2026-10/03-pokrycie-wymagan.md).

### KONKURS-04 — Monitor skórek read-only

**ukończone**. PR #96 scalony: odczyt NML; nie kończy SKIN-02/04…06.

Źródła: [raporty/04.md](../../raporty/04.md), [prompts/konkurs-2026-10/04-integracja-skorek.md](../../prompts/konkurs-2026-10/04-integracja-skorek.md).

### ISO-INTEGRATION — Bramka sim/Plant i monitor w obrazie ISO

**ukończone**. PR #97: bramka sim/Plant i monitor; PR #101 (iso/fix-live-login) dodaje konto linumert, user-setup/sudo i jawny autologin. Debian 12: rzeczywiste tworzenie konta, hasło, UID i idempotencja PASS; budowa końcowego ISO w kontrolach PR #101.

Źródła: [docs/DZIENNIK.md](../DZIENNIK.md), [.github/workflows/iso.yml](../../.github/workflows/iso.yml), [tools/iso/test-live-login.sh](../../tools/iso/test-live-login.sh), [docs/raporty/ZAMKNIECIE_GALEZI_2026-10-24.md](../raporty/ZAMKNIECIE_GALEZI_2026-10-24.md), [PR](https://github.com/anonimov94/linumeRT/pull/101).

### ISO-ACCEPTANCE — Odbiór i publikacja obrazu

**częściowe**. Implementacja ISO istnieje. Na polecenie właściciela 2026-10-25 odświeżono README i generowaną z rejestru tabelę M0–M6; 23 testy roadmapy/konfiguracji ISO PASS w Debianie. Uruchomiono budowę obrazu do testów laptopa: workflow 40181951376, źródła main c0281596a54a6911b344edf8709edabed8748090. Budowa/publikacja i SHA-256 oczekują weryfikacji; boot/instalacja/RT laptopa pozostają osobnym odbiorem. Właściciel 2026-10-25 uruchomił najnowsze ISO na laptopie: podgląd skórek i serwer Plant działają, ale normalne HMI QtVCP kończy się SIGSEGV podczas startu Plant (LinuxCNC 2.9.10, Debian RT). SHA konkretnego ISO nie jest w raportach. Odbiór startu HMI niezaliczony; surowe raporty i hashe zachowano. Launcher w #156 włącza faulthandler, 11 testów ISO PASS; oczekiwanie na próbę --safe i nowy debug, bez deklaracji przyczyny GPU. Niezależna próba Qt potwierdziła usterkę --safe: QT_XCB_GL_INTEGRATION=none odbiera prawidłowy kontekst QGLWidget wymagany przez QtDragon; z programowym Mesa i xcb_glx kontekst jest prawidłowy. Poprawiono flagi --safe, regresja uruchamia atrapę launchera i rzeczywisty widget; 12 testów ISO PASS. Nie dowodzi to przyczyny pierwotnej awarii laptopa; weryfikacja właściciela nadal otwarta. Właściciel potwierdził, że poprawiona próba bez --safe (software Mesa/xcb_glx/faulthandler) nadal się zamyka. Korekta GL nie rozwiązała zgłoszonego startu; oczekiwany nowy debug/report z tracebackiem. Nie uznaje się pierwotnego raportu za wynik nowej próby.

Pozostaje: Zweryfikować obraz main, SHA-256, live/instalację; publikacja ręczna zgodnie z D39. Ustalić przyczynę SIGSEGV QtVCP na ISO właściciela i odebrać rzeczywisty start normalnego HMI; działający podgląd/serwer nie zastępują tego kryterium.

Źródła: [tools/iso/build.sh](../../tools/iso/build.sh), [.github/workflows/iso.yml](../../.github/workflows/iso.yml), [README.md](../../README.md), [PR](https://github.com/anonimov94/linumeRT/actions/runs/40181951376), [docs/raporty/G2/ISO_HMI_CRASH_2026-10-25/README.md](../raporty/G2/ISO_HMI_CRASH_2026-10-25/README.md).

### OD-01 — Macierz Plant nie może przechodzić z nieoczekiwaną kolizją

**ukończone**. Przyczyna: losowy start (seed 1) w router_atc_rack lądował wewnątrz magazynu. Start omija bryły kolizyjne (emulacja xorshift rdzenia C, zmiana tylko przy kolizji), a matrix_smoke wymaga braku CRASH i COVER_CRASH; macierz 5/5 po 4 kryteria, 1116 testów PASS.

Źródła: [prompts/konkurs-2026-10/raporty/02.md](../../prompts/konkurs-2026-10/raporty/02.md), [tests/test_start_collision.py](../../tests/test_start_collision.py), [plant/scenarios/matrix_smoke.yaml](../../plant/scenarios/matrix_smoke.yaml), [plant/server/linumert_plant/build_machine.py](../../plant/server/linumert_plant/build_machine.py).

### EDITOR-VALIDATION — Walidacja bieżącej treści i wyszukiwanie

**ukończone**. PR #98: walidacja niezapisanej treści, lista błędów z przejściem do linii i wyszukiwanie/zamiana z Undo; Qt w Debianie: 60 testów zakresu PASS, zrzut rzeczywistego dialogu. Końcowe CI i SHA w PR.

Źródła: [PR](https://github.com/anonimov94/linumeRT/pull/98), [screens/linumert/linumert_program_editor.py](../../screens/linumert/linumert_program_editor.py), [tests/test_hmi_workflow_widgets.py](../../tests/test_hmi_workflow_widgets.py).

### LEGACY-RUNTIME — Diagnostyka uruchomień z dawnych promptów startowych

**częściowe**. Testy runtime i launchery rozwijano później; stare listy nie są nowym harmonogramem. 2026-10-24: przyczyna zrywania LRT-NET przy zakładkach panelu Plant znaleziona i usunięta (parsowanie biblioteki napędów w procesie Plant blokowało pętlę UDP przez GIL; teraz CSafeLoader, cache wg mtime, krótszy interwał GIL). Odtworzenie lokalne: przed poprawką RTT maks. 242 ms i 130 zgubionych ramek, po poprawce 11,9 ms i 0. Właściciel potwierdził na pulpicie (2026-10-24): przełączanie kart panelu Plant nie zrywa już łącza. Odbiór WSL 2026-10-24: d643a97 7 przebiegów PASS, 8. FAIL (nadążanie X); aktualny 8b255cd 5 przebiegów PASS, 6. FAIL (KeyboardInterrupt podczas bazowania first_motion, rapid_vs_feed nieukończony). Dziesięć kolejnych przebiegów niezaliczone; raport M1_REPEAT_2026-10-24.md. 2026-10-25: zachowywanie katalogu diagnostycznego i logów LinuxCNC/Plant; celowane first_motion PASS. Jedna para prób, ta sama masa/napędy: limit przyspieszenia XY 1000 → 500 mm/s², próbka maksimum X 0,1112 → 0,0762 mm (5/5 kryteriów w obu). Nie zmieniono progów ani konfiguracji produkcyjnej. Historyczny skok 0,3 mm pozostaje niewyjaśniony; raport M1_FIRST_MOTION_2026-10-25.md. Doprecyzowanie właściciela: sam fizyczny uchyb przy rozpędzaniu i hamowaniu nie jest błędem systemowym; Plant służy do doboru maksymalnych użytecznych przyspieszeń i hamowania dla G0 oraz bardzo szybkich G1 przy kontrolowanym uchybie. Diagnostyka przed T0: przy odebraniu błędu bazowania zachowuje stan jointów NML, odczyty łącza HAL i czas odbioru; 8 testów diagnostyki PASS w Debianie. Odczyty sekwencyjne poza RT, bez deklaracji zsynchronizowanego śladu ani przyczyny uchybu. Celowany pomiar 6a64abe: błąd Z w pierwszym bazowaniu odtworzony i zachowany w SETUP_ERROR (przy odbiorze homing=1, uchyb NML 0,43 mm; odczyt poza RT nie ustala przyczyny). Po istniejącym retry program 5/5 PASS, X 0,11211 mm. Raport M1_SETUP_2026-10-25.md; bez zmiany modelu/ramp/progów i bez odbioru pełnej serii. Opcjonalny sampler HAL na końcu servo-thread: kanały X/Z, CiA402 i LRT-NET, numeracja próbek i kontrola overruns; 19 testów diagnostyki/trace PASS w Debianie. Celowany odbiór samplera na 23caa5f: 70 697 ciągłych próbek, 0 overruns i opróżnione FIFO. Zaczyna się zadanie Z przy drive-enabled=0, potem f-error 0,51 przekracza limit 0,5; pierwszy drive-enabled=1 po retry. Wymaga audytu kolejności enable/CiA402/homing; nie jest to atomowy pomiar fizyczny Plant/NML ani ustalenie przyczyny historycznego X. Audyt gotowości: statusword 512 to NOT_READY | REMOTE; runner czekał tylko na task ON przed home. Dodano oczekiwanie na enabled wszystkich czterech napędów i jawne przerwanie przy braku gotowości; fizyka, boot-time, progi i retry bez zmian. 24 testy bez LinuxCNC PASS; odbiór runtime poprawki otwarty (pierwsza próba live nieważna: błędna selekcja mimo blokady Claude 033, zgłoszona w przekazaniu). Końcowy odbiór poprawki gotowości d223909: LinuxCNC CI 40179788254, 147 live PASS, w tym pierwsze bazowanie bez retry/puste setup_errors oraz rzeczywisty sampler. Pozostałe kontrole zielone; #141/#142 scalone. Lokalny incydent pozostaje nieważny, nie zaliczony jako PASS. Audyt historycznej bazy X: d643a97 miał Plant substeps=1 i rdzeń sprzed #116; obecnie substeps=4. Program, machine.yaml, próg, drive.c i lrt_net.comp identyczne; różnica integracji nie dowodzi przyczyny 0,3 mm. Ancestry i hashe zachowane w M1_X_BASELINE_2026-10-25.md/JSON, bez live testów. Analiza offline zachowanego śladu X: w 2010 próbkach ruchu f-error odpowiada cmd-fb z poprzedniego końca cyklu z resztą około 0,000001 mm po zaokrągleniu CSV; źródło LinuxCNC potwierdza kolejność. To interpretacja fazy, nie wyjaśnienie historycznego 0,3 mm ani dokładność fizyczna. Raport M1_X_PHASE_2026-10-25.md/JSON i analizator z testami odmowy dla uszkodzonych danych. Trzy celowane first_motion na 2a0ce52 po gotowości #142: każda 5/5 kryteriów PASS, pierwsze bazowanie bez retry/setup_errors, ciągłe ślady z overruns=0. Maks. X 0,109818 / 0,108127 / 0,112558 mm. Nie odtworzono historycznego 0,3 mm, bez deklaracji przyczyny lub pełnej serii. Raport M1_CURRENT_X_2026-10-25.md/JSON. Instrumentowany odbiór 8a3656f zakończony FAIL: trzy pełne przebiegi po 13 PASS; czwarty ERROR w fixture test_plant_linuxcnc przed softlimit, timeout warunku IDLE/prędkość/X100. Brak końcowego NML i śladu tego modułu nie pozwala ustalić przyczyny; Plant LIMIT_TRIP bez czasu/osi. Seria zatrzymana, obie lease zwolnione. JUnit, hashe manifestów i 12 ukończonych śladów ponownie sprawdzone w autokontroli; raport M1_REPEAT_2026-10-25.md/JSON. Dziesięć kolejnych przebiegów nadal niezaliczone; następna diagnostyka timeoutu drivera, bez ślepej pełnej serii. Diagnostyka fixture #153: NML/etap/błędy i logi przy timeoutach; 3 testy offline PASS. Lokalny test ruchu 110e7d6 PASS, ale JSON niepowstały przez __file__ przy atexit: diagnostyka nieodebrana. Poprawka c217745 zapisuje ścieżkę wcześniej i wymaga JSON w fixture. CI a78a2f1 / run40199421896: 151 live PASS, w tym ta fixture z wymaganiem JSON/stage complete/braku snapshot_error; pozostałe kontrole zielone. Odbiór diagnostyki potwierdzony, nie pełnej serii M1. Raport M1_FIXTURE_DIAGNOSTICS_2026-10-25.md/JSON. obór przyspieszeń z budżetu uchybu (tools/tune_accel.py, 2026-10-25): Plant mill_servo_table_y2 w budżecie 0,2 mm — X/Y ok. 17 100, Z ok. 5 400 mm/s² (obecne 1000/1000/500); router krokowy ograniczony utratą kroków (X/Y ok. 3 800, Z ok. 9 400, wynik Z niemonotoniczny). Wartości modelu, w machine.yaml bez zmian; raport M1_ACCEL_TUNING_2026-10-25.md. Na polecenie właściciela (2026-10-25) zalecone przyspieszenia wpisano do machine.yaml (frezarka X/Y 2000, Z 2500 (17100/5400 z atrapy przekraczało próg w LinuxCNC); router krokowy X/Y 3820, Z 4000 mm/s² (9440 z narzędzia gubiło kroki w stud_circle)) i do ręcznych INI Plant; scenariusze heavy_table_live/edit_reload mają stały ruch porównawczy accel 1000, test substeps używa przyspieszeń referencyjnych. Biblioteka maszyn w panelu Plant (API: lista, kopia, zmiana nazwy, kosz, aktywacja, edycja YAML); interfejs w panelu w toku. Seria 10 przebiegów M1 na nowych wartościach otwarta.

Pozostaje: Ustalić źródło historycznego uchybu X 0,3 mm, oddzielając dynamikę masy/napędu od opóźnienia LRT-NET i tolerancji testu. Brak gotowości przed pierwszym bazowaniem Z naprawiono w runnerze i odebrano w CI, bez zmian fizyki/boot-time/progów; nie wyjaśnia to historycznego X. Następnie ponowić wymaganą serię 10 kolejnych przebiegów PASS; dotychczasowe serie WSL mają wynik FAIL. Przyznana kolizja procesów dotyczy późniejszej serii, nie wcześniejszego uchybu X. Zmierzyć najdłuższe zamrożenie GUI i heartbeat (50 000 linii G1), VirtualBox na docelowym stanowisku.

Źródła: [prompts/START-CODEX-HMI.md](../../prompts/START-CODEX-HMI.md), [prompts/START-CODEX-LINUX.md](../../prompts/START-CODEX-LINUX.md), [tests/test_library_cache.py](../../tests/test_library_cache.py), [plant/server/linumert_plant/drive_library.py](../../plant/server/linumert_plant/drive_library.py), [plant/server/linumert_plant/serve.py](../../plant/server/linumert_plant/serve.py), [docs/raporty/prototypy/M1_REPEAT_2026-10-24.md](../raporty/prototypy/M1_REPEAT_2026-10-24.md), [docs/raporty/prototypy/M1_REPEAT_2026-10-24.json](../raporty/prototypy/M1_REPEAT_2026-10-24.json), [docs/raporty/prototypy/M1_FIRST_MOTION_2026-10-25.md](../raporty/prototypy/M1_FIRST_MOTION_2026-10-25.md), [docs/raporty/prototypy/M1_FIRST_MOTION_2026-10-25.json](../raporty/prototypy/M1_FIRST_MOTION_2026-10-25.json), [docs/raporty/prototypy/M1_SETUP_2026-10-25.md](../raporty/prototypy/M1_SETUP_2026-10-25.md), [docs/raporty/prototypy/M1_SETUP_2026-10-25.json](../raporty/prototypy/M1_SETUP_2026-10-25.json), [plant/server/linumert_plant/scenario_trace.py](../../plant/server/linumert_plant/scenario_trace.py), [tests/test_scenario_trace.py](../../tests/test_scenario_trace.py), [docs/raporty/prototypy/M1_SERVO_TRACE_2026-10-25.md](../raporty/prototypy/M1_SERVO_TRACE_2026-10-25.md), [docs/raporty/prototypy/M1_SERVO_TRACE_2026-10-25.json](../raporty/prototypy/M1_SERVO_TRACE_2026-10-25.json), [docs/raporty/prototypy/M1_DRIVE_READY_2026-10-25.md](../raporty/prototypy/M1_DRIVE_READY_2026-10-25.md), [docs/raporty/prototypy/M1_X_BASELINE_2026-10-25.md](../raporty/prototypy/M1_X_BASELINE_2026-10-25.md), [docs/raporty/prototypy/M1_X_BASELINE_2026-10-25.json](../raporty/prototypy/M1_X_BASELINE_2026-10-25.json), [plant/server/linumert_plant/scenario_trace_analysis.py](../../plant/server/linumert_plant/scenario_trace_analysis.py), [tests/test_scenario_trace_analysis.py](../../tests/test_scenario_trace_analysis.py), [docs/raporty/prototypy/M1_X_PHASE_2026-10-25.md](../raporty/prototypy/M1_X_PHASE_2026-10-25.md), [docs/raporty/prototypy/M1_X_PHASE_2026-10-25.json](../raporty/prototypy/M1_X_PHASE_2026-10-25.json), [docs/raporty/prototypy/M1_CURRENT_X_2026-10-25.md](../raporty/prototypy/M1_CURRENT_X_2026-10-25.md), [docs/raporty/prototypy/M1_CURRENT_X_2026-10-25.json](../raporty/prototypy/M1_CURRENT_X_2026-10-25.json), [docs/raporty/prototypy/M1_REPEAT_2026-10-25.md](../raporty/prototypy/M1_REPEAT_2026-10-25.md), [plant/server/linumert_plant/accel_tuning.py](../../plant/server/linumert_plant/accel_tuning.py), [tools/tune_accel.py](../../tools/tune_accel.py), [tests/test_accel_tuning.py](../../tests/test_accel_tuning.py), [docs/raporty/prototypy/M1_ACCEL_TUNING_2026-10-25.md](../raporty/prototypy/M1_ACCEL_TUNING_2026-10-25.md), [plant/server/linumert_plant/panel/machine_library.py](../../plant/server/linumert_plant/panel/machine_library.py), [tests/test_machine_library.py](../../tests/test_machine_library.py).

### ROADMAP-UNIFICATION — Jeden rejestr planu i migracja statusów

**ukończone**. PR #99: jeden rejestr, generowane widoki, kontrola CI, instrukcje i migracja historii; lokalne testy i odbiór DOM PASS. Wynik CI i SHA w PR.

Źródła: [docs/roadmap/README.md](README.md), [tools/roadmap.py](../../tools/roadmap.py), [tests/test_roadmap.py](../../tests/test_roadmap.py), [PR](https://github.com/anonimov94/linumeRT/pull/99).

### LIMITS-PREFLIGHT — Kontrola limitów osi przed startem programu

**częściowe**. Przycisk 'Sprawdź limity osi' w edytorze G-code: rs274 z kopią parametrów (G54/G92, korekta długości, jednostki z INI) porównuje punkty końcowe ruchów z MIN/MAX_LIMIT; wynik w tle, lista linii z przeskokiem do edytora. Odtworzony błąd z G54 Z=-150 (linia 3, Z=-130) na rzeczywistym rs274; 7 testów + test GUI. Kontrola jest teraz automatyczna: po wczytaniu programu ekran sprawdza go w tle (limity osi, G5x/G92, korekta długości), pokazuje wynik na stronie Produkcja i pyta przed 'Cykl start', gdy program wyjdzie poza limity; informuje też o cięciu bez korekty długości (G49). Łuki ARC_FEED: sprawdzane ekstrema w płaszczyznach XY/YZ/XZ (pół okręgu, pełny okrąg, wiele obrotów), PR #172; 15 testów PASS. Obrót XY (G10 L2 R): G92, obrót, G5x, TLO jak w LinuxCNC 2.9, PR #173; 18 testów PASS.

Pozostaje: Limity osi obrotowych nie są sprawdzane. Automatyczne G43 po M6 (remap) i poprawne G43 w programie Facing z QtDragon (kod upstream) — osobna decyzja. Odbiór na pulpicie właściciela. Przegląd 2026-10-26: #172–174 wymagają poprawienia początku łuku po G92 i ekstremów helisy XZ/YZ po obrocie XY; odtworzone fałszywe wyniki bez przekroczeń.

Źródła: [core/linumert/programs/limits.py](../../core/linumert/programs/limits.py), [tests/test_limits.py](../../tests/test_limits.py), [tests/test_limits_units.py](../../tests/test_limits_units.py), [tests/test_hmi_workflow_widgets.py](../../tests/test_hmi_workflow_widgets.py), [screens/linumert/linumert_program_editor.py](../../screens/linumert/linumert_program_editor.py), [screens/linumert/linumert_preflight.py](../../screens/linumert/linumert_preflight.py), [screens/linumert/linumert_shell.py](../../screens/linumert/linumert_shell.py), [docs/raporty/PR_REVIEW_2026-10-26.md](../raporty/PR_REVIEW_2026-10-26.md).

### ORIGIN-WIZARD — Kreator zera detalu na przygotówce

**częściowe**. Przycisk 'Kreator zera detalu…' na stronie Zero detalu: klikalny widok przygotówki z góry (4 narożniki i środek, góra/dół), położenie przygotówki na stole (narożnik X/Y, wierzch Z), pobranie pozycji narzędzia jako zera, kontrola zakresów osi z INI; wynik trafia do formularza, osobny przycisk zapisuje G5x. 10 punktów zera w Workpiece (bounds, fit_issues); testy rdzenia i GUI (Debian 12), zrzut dialogu.

Pozostaje: Odbiór na pulpicie właściciela i na maszynie wirtualnej (G10 L2 po kreatorze). Środki krawędzi, przygotówki obrócone i wizualne przesuwanie myszą w widoku 3D. Powiązanie z linią ;@STOCK programu (ORIGIN/OFFSET) i sondowaniem narożnika (033).

Źródła: [screens/linumert/linumert_origin_wizard.py](../../screens/linumert/linumert_origin_wizard.py), [core/linumert/programs/workpiece.py](../../core/linumert/programs/workpiece.py), [tests/test_workpiece.py](../../tests/test_workpiece.py), [tests/test_hmi_workflow_widgets.py](../../tests/test_hmi_workflow_widgets.py).

### M6-G43 — Automatyczna korekta długości narzędzia po M6

**częściowe**. Remap M6 w INI sim i Plant (macros/lrt_m6.ngc): wbudowane M6, potem G43 H<narzędzie z T> albo G49 dla T0, jak w sterownikach przemysłowych. Kontrola limitów uwzględnia remap maszyny. Test rs274 z INI maszyny (T2 M6 -> 80 mm, T0 M6 -> 0), pełny przebieg e2e programu demo z 6 wymianami (306 s, bez kolizji).

Pozostaje: Odbiór na pulpicie właściciela, w tym ręczna wymiana w oknie QtDragon. Program Facing z QtDragon (kod upstream) ma G49 i nie wywołuje M6, więc korekta nie jest włączana; osobna decyzja. Remap dla ATC (066) razem z magazynem narzędzi.

Źródła: [config/sim/linumert_xyz/macros/lrt_m6.ngc](../../config/sim/linumert_xyz/macros/lrt_m6.ngc), [tests/test_m6_remap.py](../../tests/test_m6_remap.py), [core/linumert/programs/linuxcnc_check.py](../../core/linumert/programs/linuxcnc_check.py).

### PLANT-SUBSTEPS — Plant: wynik niezależny od podkroków całkowania

**ukończone**. Cel CSP z cyklu mastera interpolowany liniowo w podkrokach rdzenia C (lrt_machine_step_cycle, jak 60C2h/stepgen); domyślnie 4 podkroki. Atrapa: frezarka i router PASS dla n = 2–16 (wcześniej E-4201 i ~1560 zgubionych kroków przy n ≥ 2–4). Raport docs/raporty/plant_substeps.md.

Pozostaje: Obciążenie CPU Plant realtime przy 4 podkrokach na VM-B (odbiór właściciela). Generator EtherCAT (063): 60C2h = okres wątku serwo.

Źródła: [plant/core/machine.c](../../plant/core/machine.c), [plant/core/tests/test_machine.c](../../plant/core/tests/test_machine.c), [tools/plant_substeps.py](../../tools/plant_substeps.py), [docs/raporty/plant_substeps.md](../raporty/plant_substeps.md).

### HMI-OWNER-SKINS — Odrębny wygląd każdej skórki i główny ekran holograficzny

**częściowe**. Polecenie właściciela 2026-10-25 po odbiorze #163 (SHA 2ae9103): selektor widoku HMI działa; wybór rodziny nie zmienia jeszcze wyraźnie wyglądu. 7dc2649: odmienne malowanie geometrii i typografii wspólnej nawigacji każdej rodziny, dopasowanie ram stałych pasków; te same strony i sygnały Qt. Kod po kontroli składni, odbiór wizualny/fokusu/kontrastu powierzony Claude; pełna kompozycja i podglądy nieukończone. Przegląd 76fed49: usuwanie starej sceny przy zmianie pliku/utracie STATUS, ponowne wczytanie po odzyskaniu i poprawny opis pauzy. Regresja do wykonania przez Claude; bez zmiany statusu odbioru. 2026-10-26: Cyberdeck ma obok siebie dwa prostokątne podglądy Neon pod własną nakładką narożników; wspólna scena, narzędzie i model poglądowy XYZ. Regresja zachowuje scenę po zmianie rodziny/motywu; zrzut Qt sprawdzony. Odbiór live nowej kompozycji pozostaje otwarty. Cyberdeck odebrany w AUTO: linia/DTG/DRO zgodne z NML, program/T1/D6/S12000 widoczne, 3 presety 2,95–4,31 ms; osadzony host 45 kroków PASS. Macierz GL 160 kombinacji PASS. Pozostaje odrębny odbiór pulpitu i pełnej roadmapy skórek. #169 scalony 3c20817 po pełnym zielonym CI e9ed723 (154 live PASS).

Pozostaje: Odbiór nowego układu na pulpicie właściciela: porównanie czterech rodzin przy 1280×768 i 1920×1080, dotyk i klawiatura. Pełna kwalifikacja scen/renderera ze SKIN-02/04…06; bieżący Cyberdeck używa QPainter Neon i poglądowego XYZ, nie modelu kolizji Plant.

Źródła: [PR](https://github.com/anonimov94/linumeRT/pull/163#issuecomment-6401257406), [docs/design/SKIN_SYSTEM_ROADMAP.md](../design/SKIN_SYSTEM_ROADMAP.md), [screens/linumert/linumert_skin_navigation.py](../../screens/linumert/linumert_skin_navigation.py), [docs/design/HMI_QTVCP_HOST.md](../design/HMI_QTVCP_HOST.md), [screens/linumert/linumert_skin_cyberdeck.py](../../screens/linumert/linumert_skin_cyberdeck.py), [docs/raporty/G2/HMI_CLOSEOUT_2026-10-26.md](../raporty/G2/HMI_CLOSEOUT_2026-10-26.md).

