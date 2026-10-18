# Prompty sesji agenta

Plan pracy: 84 sesje w 7 kamieniach (M0–M6). Harmonogram uruchamia agenta co 5 h; gdy limit konta jest
wyczerpany, uruchomienie nic nie robi, a następne po odnowieniu limitu bierze pierwszą niewykonaną (lub
przerwaną) sesję.

| Plik | Rola |
|---|---|
| `sesja-NNN.md` | prompt sesji: cel, zakres, kryteria akceptacji, zakończenie |
| [`DONE.md`](DONE.md) | sesje wykonane (źródło kolumny „Stan” poniżej) |
| [`BLOCKED.md`](BLOCKED.md) | sesje zablokowane po 2 nieudanych próbach |
| `LOCK` | blokada tury: `<model> · sesja NNN · <UTC> · <opis>`; pusty = wolne |
| [`archiwum/`](archiwum/README.md) | wykorzystane prompty startowe `START-NNN.md` (historia) |

Sesje ekranu (M2, 027–038) realizują docelowe HMI według kolejności pracy (D32,
[`docs/design/HMI_WORKFLOW.md`](../docs/design/HMI_WORKFLOW.md)); etapy HMI-01…06 prowadzi Codex.

Kolejność wykonania odbiega od numeracji: sesje rdzenia 032, 039 i 044 zrobiono wcześniej, bo nie
wymagały ekranu ani LinuxCNC. Bieżący stan i następny krok: [`docs/NASTEPNA_SESJA.md`](../docs/NASTEPNA_SESJA.md).

| Nr | Kamień | Tytuł | Stan |
|---|---|---|---|
| [001](sesja-001.md) | M0 | Szkielet repozytorium, CI i licencja | zrobiona |
| [002](sesja-002.md) | M0 | Wytyczne IP i rejestr pochodzenia | zrobiona |
| [003](sesja-003.md) | M0 | Spike: LinuxCNC 2.9 w środowisku agenta | zrobiona |
| [004](sesja-004.md) | M0 | Konfiguracja sim 3 osie z QtDragon | zrobiona |
| [005](sesja-005.md) | M0 | Kopia bazowa ekranu QtDragon | zrobiona |
| [006](sesja-006.md) | M0 | Rdzeń: model stanu maszyny i atrapa | zrobiona |
| [007](sesja-007.md) | M0 | Katalog alarmów i tłumaczenia | zrobiona |
| [008](sesja-008.md) | M0 | Bufor i bramka G0 | zrobiona |
| [009](sesja-009.md) | M1 | Specyfikacja wirtualnej maszyny Plant | zrobiona |
| [010](sesja-010.md) | M1 | Model obrabiarki machine.yaml (jedno źródło prawdy) | zrobiona |
| [011](sesja-011.md) | M1 | Plant: rdzeń dynamiki osi (C) | zrobiona |
| [012](sesja-012.md) | M1 | Plant: emulacja napędów CiA 402 i krokowców | zrobiona |
| [013](sesja-013.md) | M1 | Biblioteka napędów wirtualnych: szablony, kopiowanie, parametryzacja | zrobiona |
| [014](sesja-014.md) | M1 | Plant: łańcuch kinematyczny, przejazdy, zderzaki, krańcówki, I/O | zrobiona |
| [015](sesja-015.md) | M1 | Bazowanie po rozruchu: krańcówka, indeks, twardy zderzak, absolut, napęd | zrobiona |
| [016](sesja-016.md) | M1 | Plant: serwer LRT-NET | zrobiona |
| [017](sesja-017.md) | M1 | Komponent HAL lrt_net | zrobiona |
| [018](sesja-018.md) | M1 | Konfiguracja LinuxCNC dla Plant (3 osie) | zrobiona |
| [019](sesja-019.md) | M1 | Ograniczenia programowe, strefy zakazane i wyrocznia testowa | zrobiona |
| [020](sesja-020.md) | M1 | Magazyn narzędzi, pozycje wymiany i kolizje w Plant | zrobiona |
| [021](sesja-021.md) | M1 | Plant: wrzeciono VFD przez Modbus | zrobiona |
| [022](sesja-022.md) | M1 | Plant: panel sterowania i pulpit MPG | zrobiona |
| [023](sesja-023.md) | M1 | Edytor wirtualnej obrabiarki w panelu Plant | po 022 i 024 ([START-023](START-023.md)) |
| [024](sesja-024.md) | M1 | Plant: scenariusze i raport prototypu | zrobiona |
| [025](sesja-025.md) | M1 | Skrypty maszyn wirtualnych (VirtualBox) | **następna** (równolegle, [START-025](START-025.md)) |
| [026](sesja-026.md) | M1 | Bufor i bramka G1 (prototyp P0) |  |
| [027](sesja-027.md) | M2 | Własny system projektowy ekranu |  |
| [028](sesja-028.md) | M2 | Kompozycja ekranu głównego |  |
| [029](sesja-029.md) | M2 | Tryby, JOG i pulpit MPG |  |
| [030](sesja-030.md) | M2 | MDI i klawiatura ekranowa |  |
| [031](sesja-031.md) | M2 | AUTO i wznowienie od linii |  |
| [032](sesja-032.md) | M2 | Baza narzędzi z typami | zrobiona |
| [033](sesja-033.md) | M2 | Zerowanie detalu i sonda |  |
| [034](sesja-034.md) | M2 | Ręczna zmiana narzędzia |  |
| [035](sesja-035.md) | M2 | Alarmy na ekranie |  |
| [036](sesja-036.md) | M2 | Poziomy dostępu |  |
| [037](sesja-037.md) | M2 | Język polski i angielski |  |
| [038](sesja-038.md) | M2 | Bufor i bramka G2 (prototyp v0.1) |  |
| [039](sesja-039.md) | M3 | Format .lnx i BaseMacroGenerator | zrobiona |
| [040](sesja-040.md) | M3 | Generatory: nagłówek, koniec, narzędzie, planowanie |  |
| [041](sesja-041.md) | M3 | Generatory: kieszenie |  |
| [042](sesja-042.md) | M3 | Generatory: wiercenie i gwintowanie |  |
| [043](sesja-043.md) | M3 | Generatory: rowki, czopy, kontur |  |
| [044](sesja-044.md) | M3 | Lekser G-code i walidacja w edytorze | zrobiona |
| [045](sesja-045.md) | M3 | Panel programu dialogowego |  |
| [046](sesja-046.md) | M3 | Podglądy 2D w formularzach |  |
| [047](sesja-047.md) | M3 | Menedżer programów i pliki .lnx |  |
| [048](sesja-048.md) | M3 | Biblioteka podprogramów o-word |  |
| [049](sesja-049.md) | M3 | Test technologiczny na Plant |  |
| [050](sesja-050.md) | M3 | Bufor i bramka G3 (prototyp v0.2) |  |
| [051](sesja-051.md) | M4 | Ścieżka z programu |  |
| [052](sesja-052.md) | M4 | Proces symulacji |  |
| [053](sesja-053.md) | M4 | Czas obróbki i porównanie z Plant |  |
| [054](sesja-054.md) | M4 | Przygotówka |  |
| [055](sesja-055.md) | M4 | Materiał 2.5D |  |
| [056](sesja-056.md) | M4 | Reguły kolizji lite |  |
| [057](sesja-057.md) | M4 | Widok 3D symulacji |  |
| [058](sesja-058.md) | M4 | Typy narzędzi w symulacji |  |
| [059](sesja-059.md) | M4 | Raport symulacji i eksport STL |  |
| [060](sesja-060.md) | M4 | Bufor i bramka G4 (prototyp v0.3) |  |
| [061](sesja-061.md) | M5 | machine.yaml: napędy i wejścia rzeczywiste |  |
| [062](sesja-062.md) | M5 | Generator INI/HAL: sim, Plant, step/dir |  |
| [063](sesja-063.md) | M5 | Generator EtherCAT (lcec, CiA 402) |  |
| [064](sesja-064.md) | M5 | Wrzeciono RS485 w generatorze |  |
| [065](sesja-065.md) | M5 | Kinematyki 4 i 5 osi |  |
| [066](sesja-066.md) | M5 | Automatyczna zmiana narzędzia |  |
| [067](sesja-067.md) | M5 | Kreator konfiguracji maszyny |  |
| [068](sesja-068.md) | M5 | Test latencji i raport kwalifikacji |  |
| [069](sesja-069.md) | M5 | Diagnostyka napędów |  |
| [070](sesja-070.md) | M5 | Łańcuch E-STOP i bezpieczeństwo |  |
| [071](sesja-071.md) | M5 | Asystent strojenia na Plant |  |
| [072](sesja-072.md) | M5 | Bufor i bramka G5 (prototyp v0.4) |  |
| [073](sesja-073.md) | M6 | Wtyczki deklaratywne: format i silnik |  |
| [074](sesja-074.md) | M6 | Menedżer wtyczek |  |
| [075](sesja-075.md) | M6 | Panel cykli i skryptów |  |
| [076](sesja-076.md) | M6 | Repozytorium społeczności i przykłady |  |
| [077](sesja-077.md) | M6 | Instalator dla Debiana 12 + LinuxCNC 2.9 |  |
| [078](sesja-078.md) | M6 | Pierwsze uruchomienie i linumert doctor |  |
| [079](sesja-079.md) | M6 | Dokumentacja użytkownika |  |
| [080](sesja-080.md) | M6 | Przegląd IP przed wydaniem |  |
| [081](sesja-081.md) | M6 | Twardnienie |  |
| [082](sesja-082.md) | M6 | Pełna regresja na Plant |  |
| [083](sesja-083.md) | M6 | Wydanie v0.5.0-alpha |  |
| [084](sesja-084.md) | M6 | Retrospektywa i kolejne półrocze |  |

Nowa sesja startuje od [`docs/PROMPT_NOWEJ_SESJI.md`](../docs/PROMPT_NOWEJ_SESJI.md) (stały prompt) i stanu w
`docs/NASTEPNA_SESJA.md`; osobny `START-NNN.md` tworzy się tylko dla sesji przerwanej w połowie.
