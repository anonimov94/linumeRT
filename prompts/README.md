<!-- Generowane przez python3 tools/roadmap.py; edytuj docs/roadmap/plan.json. -->
# Prompty i wspólna roadmapa linumeRT

Pierwotny plan: **84 sesje M0–M6**, commit `796c6a2`. Stan na 2026-10-25: planowane: 15; w toku: 0; częściowe: 30; do odbioru: 0; ukończone: 39; zablokowane: 0.

Zakończenie części implementacji nie oznacza odbioru całej funkcji ani sprzętu.

Jedyne źródło statusów, powiązań i pozostałej pracy: [plan.json](../docs/roadmap/plan.json). Zasady aktualizacji: [instrukcja roadmapy](../docs/roadmap/README.md). Szczegóły i dowody: [PLAN.md](../docs/roadmap/PLAN.md); [widok HTML](../docs/roadmap/index.html).

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
| 001 | M0 | [Szkielet repozytorium, CI i licencja](sesja-001.md) | ukończone |
| 002 | M0 | [Wytyczne IP i rejestr pochodzenia](sesja-002.md) | ukończone |
| 003 | M0 | [Spike: LinuxCNC 2.9 w środowisku agenta](sesja-003.md) | ukończone |
| 004 | M0 | [Konfiguracja sim 3 osie z QtDragon](sesja-004.md) | ukończone |
| 005 | M0 | [Kopia bazowa ekranu QtDragon](sesja-005.md) | ukończone |
| 006 | M0 | [Rdzeń: model stanu maszyny i atrapa](sesja-006.md) | ukończone |
| 007 | M0 | [Katalog alarmów i tłumaczenia](sesja-007.md) | ukończone |
| 008 | M0 | [Bufor i bramka G0](sesja-008.md) | ukończone |
| 009 | M1 | [Specyfikacja wirtualnej maszyny Plant](sesja-009.md) | ukończone |
| 010 | M1 | [Model obrabiarki machine.yaml (jedno źródło prawdy)](sesja-010.md) | ukończone |
| 011 | M1 | [Plant: rdzeń dynamiki osi (C)](sesja-011.md) | ukończone |
| 012 | M1 | [Plant: emulacja napędów CiA 402 i krokowców](sesja-012.md) | ukończone |
| 013 | M1 | [Biblioteka napędów wirtualnych: szablony, kopiowanie, parametryzacja](sesja-013.md) | ukończone |
| 014 | M1 | [Plant: łańcuch kinematyczny, przejazdy, zderzaki, krańcówki, I/O](sesja-014.md) | ukończone |
| 015 | M1 | [Bazowanie po rozruchu: krańcówka, indeks, twardy zderzak, absolut, napęd](sesja-015.md) | ukończone |
| 016 | M1 | [Plant: serwer LRT-NET](sesja-016.md) | ukończone |
| 017 | M1 | [Komponent HAL lrt_net](sesja-017.md) | ukończone |
| 018 | M1 | [Konfiguracja LinuxCNC dla Plant (3 osie)](sesja-018.md) | ukończone |
| 019 | M1 | [Ograniczenia programowe, strefy zakazane i wyrocznia testowa](sesja-019.md) | ukończone |
| 020 | M1 | [Magazyn narzędzi, pozycje wymiany i kolizje w Plant](sesja-020.md) | ukończone |
| 021 | M1 | [Plant: wrzeciono VFD przez Modbus](sesja-021.md) | ukończone |
| 022 | M1 | [Plant: panel sterowania i pulpit MPG](sesja-022.md) | ukończone |
| 023 | M1 | [Edytor wirtualnej obrabiarki w panelu Plant](sesja-023.md) | ukończone |
| 024 | M1 | [Plant: scenariusze i raport prototypu](sesja-024.md) | ukończone |
| 025 | M1 | [Skrypty maszyn wirtualnych (VirtualBox)](sesja-025.md) | ukończone |
| 026 | M1 | [Bufor i bramka G1 (prototyp P0)](sesja-026.md) | ukończone |
| 027 | M2 | [Własny system projektowy ekranu](sesja-027.md) | ukończone |
| 028 | M2 | [Kompozycja ekranu głównego](sesja-028.md) | częściowe |
| 029 | M2 | [Tryby, JOG i pulpit MPG](sesja-029.md) | częściowe |
| 030 | M2 | [MDI i klawiatura ekranowa](sesja-030.md) | częściowe |
| 031 | M2 | [AUTO i wznowienie od linii](sesja-031.md) | częściowe |
| 032 | M2 | [Baza narzędzi z typami](sesja-032.md) | ukończone |
| 033 | M2 | [Zerowanie detalu i sonda](sesja-033.md) | częściowe |
| 034 | M2 | [Ręczna zmiana narzędzia](sesja-034.md) | częściowe |
| 035 | M2 | [Alarmy na ekranie](sesja-035.md) | częściowe |
| 036 | M2 | [Poziomy dostępu](sesja-036.md) | ukończone |
| 037 | M2 | [Język polski i angielski](sesja-037.md) | częściowe |
| 038 | M2 | [Bufor i bramka G2 (prototyp v0.1)](sesja-038.md) | planowane |
| 039 | M3 | [Format .lnx i BaseMacroGenerator](sesja-039.md) | ukończone |
| 040 | M3 | [Generatory: nagłówek, koniec, narzędzie, planowanie](sesja-040.md) | ukończone |
| 041 | M3 | [Generatory: kieszenie](sesja-041.md) | ukończone |
| 042 | M3 | [Generatory: wiercenie i gwintowanie](sesja-042.md) | częściowe |
| 043 | M3 | [Generatory: rowki, czopy, kontur](sesja-043.md) | ukończone |
| 044 | M3 | [Lekser G-code i walidacja w edytorze](sesja-044.md) | ukończone |
| 045 | M3 | [Panel programu dialogowego](sesja-045.md) | częściowe |
| 046 | M3 | [Podglądy 2D w formularzach](sesja-046.md) | częściowe |
| 047 | M3 | [Menedżer programów i pliki .lnx](sesja-047.md) | częściowe |
| 048 | M3 | [Biblioteka podprogramów o-word](sesja-048.md) | ukończone |
| 049 | M3 | [Test technologiczny na Plant](sesja-049.md) | ukończone |
| 050 | M3 | [Bufor i bramka G3 (prototyp v0.2)](sesja-050.md) | planowane |
| 051 | M4 | [Ścieżka z programu](sesja-051.md) | ukończone |
| 052 | M4 | [Proces symulacji](sesja-052.md) | ukończone |
| 053 | M4 | [Czas obróbki i porównanie z Plant](sesja-053.md) | częściowe |
| 054 | M4 | [Przygotówka](sesja-054.md) | ukończone |
| 055 | M4 | [Materiał 2.5D](sesja-055.md) | częściowe |
| 056 | M4 | [Reguły kolizji lite](sesja-056.md) | częściowe |
| 057 | M4 | [Widok 3D symulacji](sesja-057.md) | częściowe |
| 058 | M4 | [Typy narzędzi w symulacji](sesja-058.md) | częściowe |
| 059 | M4 | [Raport symulacji i eksport STL](sesja-059.md) | częściowe |
| 060 | M4 | [Bufor i bramka G4 (prototyp v0.3)](sesja-060.md) | planowane |
| 061 | M5 | [machine.yaml: napędy i wejścia rzeczywiste](sesja-061.md) | częściowe |
| 062 | M5 | [Generator INI/HAL: sim, Plant, step/dir](sesja-062.md) | częściowe |
| 063 | M5 | [Generator EtherCAT (lcec, CiA 402)](sesja-063.md) | planowane |
| 064 | M5 | [Wrzeciono RS485 w generatorze](sesja-064.md) | planowane |
| 065 | M5 | [Kinematyki 4 i 5 osi](sesja-065.md) | częściowe |
| 066 | M5 | [Automatyczna zmiana narzędzia](sesja-066.md) | częściowe |
| 067 | M5 | [Kreator konfiguracji maszyny](sesja-067.md) | planowane |
| 068 | M5 | [Test latencji i raport kwalifikacji](sesja-068.md) | planowane |
| 069 | M5 | [Diagnostyka napędów](sesja-069.md) | częściowe |
| 070 | M5 | [Łańcuch E-STOP i bezpieczeństwo](sesja-070.md) | częściowe |
| 071 | M5 | [Asystent strojenia na Plant](sesja-071.md) | planowane |
| 072 | M5 | [Bufor i bramka G5 (prototyp v0.4)](sesja-072.md) | planowane |
| 073 | M6 | [Wtyczki deklaratywne: format i silnik](sesja-073.md) | planowane |
| 074 | M6 | [Menedżer wtyczek](sesja-074.md) | planowane |
| 075 | M6 | [Panel cykli i skryptów](sesja-075.md) | planowane |
| 076 | M6 | [Repozytorium społeczności i przykłady](sesja-076.md) | planowane |
| 077 | M6 | [Instalator dla Debiana 12 + LinuxCNC 2.9](sesja-077.md) | częściowe |
| 078 | M6 | [Pierwsze uruchomienie i linumert doctor](sesja-078.md) | częściowe |
| 079 | M6 | [Dokumentacja użytkownika](sesja-079.md) | częściowe |
| 080 | M6 | [Przegląd IP przed wydaniem](sesja-080.md) | częściowe |
| 081 | M6 | [Twardnienie](sesja-081.md) | częściowe |
| 082 | M6 | [Pełna regresja na Plant](sesja-082.md) | częściowe |
| 083 | M6 | [Wydanie v0.5.0-alpha](sesja-083.md) | planowane |
| 084 | M6 | [Retrospektywa i kolejne półrocze](sesja-084.md) | planowane |

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
| HMI-OWNER-SKINS | 028 | Odrębny wygląd każdej skórki i główny ekran holograficzny | planowane |
