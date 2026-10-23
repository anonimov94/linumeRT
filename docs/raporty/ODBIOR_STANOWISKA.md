# Odbiór stanowiska linumeRT

Model-Author: Codex · 2026-10-23 · GPL-2.0-or-later.
Procedura wykonawcza; nie potwierdza odbioru konkretnego stanowiska.

## Źródła i granice

Kryteria wydania i T1–T7 pochodzą z [KWALIFIKACJA_RT](../wymagania/KWALIFIKACJA_RT.md).
Tor fizyczny ma własny [ODBIOR](../bezpieczenstwo/ODBIOR.md) i
[kontrakt](../bezpieczenstwo/README.md); nie zastępuj ich testami Plant.
Wskazana w prompcie ścieżka `docs/bezpieczenstwa/ODBIOR.md` jest omyłką:
obowiązuje katalog `bezpieczenstwo`. [G1](G1.md),
[P0](prototypy/P0-2026-10-20.md) i [odbiór planu](prototypy/PLAN-21-27-2026-10-21.md)
pozostają dowodami historycznymi dla podanych tam SHA, a nie dla nowego wydania.
Pełny QtVCP i podglądy skórek offline mają odrębne zakresy.

## Przygotowanie i zasady wyniku

1. Skopiuj [szablon](SZABLON_ODBIORU.md) do nowego katalogu wyników;
   nadaj identyfikator `YYYYMMDDTHHMMSSZ-stanowisko-SHA`. Nie nadpisuj poprzednich prób.
2. Wpisz wszystkie pola metryki. Zarchiwizuj INI, HAL, machine.yaml, tool.tbl,
   parametry i firmware wraz z sumami SHA-256; usuń sekrety z kopii udostępnianych.
   Zapisz `git rev-parse HEAD`, `git status --porcelain`, `git diff --binary`,
   `uname -a`, `cat /etc/os-release`, `python3 --version`, `python3 -m pip freeze`.
   Nie wpisuj samego SHA przy lokalnych zmianach; dołącz też pliki nieśledzone użyte w próbie.
3. Zapisz wersje LinuxCNC (także SHA RIP), Qt, sterownika GPU, obrazu kontenera i zależności.
   Dla sprzętu dodatkowo metryka T1–T7 i zatwierdzony plan prób fizycznych.
4. Testy A/B wykonuj tylko w odizolowanym sim/Plant bez fizycznego I/O.
   Osobne checkouty, katalogi budowania, porty i DISPLAY; gdy instancja współdzielona:
   `python3 tools/lock.py acquire linuxcnc --model Codex --note "odbior stanowiska"`.
   Odmowa blokady = BLOCKED; po zamknięciu własnej instancji zwolnij przez `release`.

Każda karta ma: warunki, czynności, oczekiwanie, regułę przerwania oraz dowód.
Wynik początkowy zawsze **BLOCKED — niewykonane**. PASS wymaga spełnienia wszystkich
kryteriów i kompletu dowodów. FAIL oznacza zaobserwowaną niezgodność; brak środowiska,
narzędzia, zatwierdzonego progu lub dowodu oznacza BLOCKED. Nie zamieniaj FAIL w BLOCKED
po przerwaniu nieudanej próby. Zapisz pierwotny wynik, poprawkę i osobną powtórkę.
Pominięcie pytest nie jest PASS: przypisz je do karty i uzasadnij zakres albo zostaw BLOCKED.
Wynik grupy: dowolny FAIL → FAIL; inaczej dowolny BLOCKED → BLOCKED; inaczej PASS.
Zakończenie dokumentacji procedury nie oznacza kwalifikacji stanowiska.

## A — testy programowe bez fizycznych wyjść

Warunek wspólny: czysty checkout, Python ≥3.11 z `.[dev]`, kompilator C, zapis do
nowego katalogu wyników; Qt/Xvfb dla testów UI. Komendy z katalogu repozytorium.
Zapisuj stdout/stderr i kod wyjścia każdej komendy, również po błędzie.
Istniejący `tools/agent_tests/run.py` zbiera SHA, stan drzewa, platformę, komendy,
logi i częściowy `report.json`; nie twórz drugiego runnera.

| ID | Dodatkowy warunek i dokładne czynności | Oczekiwanie / dowód | Przerwanie |
|---|---|---|---|
| A1 | `python3 tools/agent_tests/run.py --model Codex`; następnie `python3 tools/check_requirements.py -v` | Runner i kontrola REQ: kod 0; zachowaj `state/test-runs/<id>/`, liczbę testów i listę pominięć. Pokrycie REQ nie dowodzi wykonania testów | Błąd polecenia: FAIL danej kontroli, zachowaj log; brak zależności: BLOCKED właściwej karty |
| A2 | `make test-c test-san` | Obie komendy kod 0, zero raportów ASan/UBSan; pełny log | Raport sanitizera: FAIL; brak obsługi sanitizera: BLOCKED, nie wyłączaj go dla uzyskania PASS |
| A3 | `make plant-matrix`; raporty w `build/raporty/`; sprawdź także sekcję Zdarzenia każdego HTML | Kod 0; wszystkie kryteria każdego scenariusza i każdej maszyny PASS, liczba i nazwy w raporcie. W scenariuszach bez celowego wstrzyknięcia nie może być nieoczekiwanych CRASH/COVER_CRASH. Dla awarii porównaj zdarzenia z zadeklarowanym oczekiwaniem | Niezgodność lub nieoczekiwana kolizja: FAIL nawet przy kodzie 0; niepełny zestaw: BLOCKED |
| A4 | LinuxCNC 2.9 RIP, Xvfb, wyłącznie konfiguracje testowe; `python3 tools/agent_tests/run.py --model Codex --linuxcnc` | Wszystkie kontrole kod 0; osobna grupa `linuxcnc` bez nieuzasadnionych pominięć; zachowaj też zrzuty i dane z katalogów pytest | Brak RIP/DISPLAY/blokady: BLOCKED; błąd integracji: FAIL, zamknij wyłącznie własne procesy |
| A5 | Podman, przygotowany obraz startera i Xvfb, bez sprzętu; `bash tools/dev/sim-e2e.sh` | Kod 0, demo faktycznie kończy się T11 + IDLE, druga próba raportuje K-302; dowody w `build/sim-e2e/` | Błąd drivera lub niedokończony program: FAIL; brak środowiska: BLOCKED |

A4 obejmuje ponownie A1–A3, więc nie trzeba uruchamiać obu wariantów runnera.
W CI odpowiadają temu `.github/workflows/ci.yml` i `linuxcnc.yml`.
Zapisz URL przebiegu, **head SHA** i pobierz artefakty `raporty-scenariuszy` /
`linuxcnc-evidence` zanim wygasną; zielony status innego SHA nie zalicza próby.
Workflow LinuxCNC filtruje ścieżki: PR wyłącznie dokumentacyjny może go nie uruchomić.
W takim przypadku wykonaj A4 lokalnie albo jawnie zleć workflow dla właściwej gałęzi.
Nie traktuj braku zadania CI jako PASS.
A5 jest dodatkową próbą obróbki i diagnostyki kolizji; skrypt ustawia
`HMI_ESTOP_BYPASS=1` wyłącznie w tymczasowej konfiguracji bez sprzętu.
Nie zalicza toru zezwolenia ani testów Plant z niezmienionym postgui z A4.

## B — ręczny odbiór pulpitu na sim/Plant

Warunek wspólny: A4 PASS, pulpit właściciela, zapisane rozdzielczość/skala/GPU,
brak sprzętowego I/O, widoczne statusy LinuxCNC i Plant. Zapisuj zrzut przed/po,
log aplikacji oraz wartości odczytów. Parametry ruchów poniżej dotyczą wyłącznie
domyślnego wirtualnego XYZ; inna konfiguracja wymaga zapisania własnych wartości
w granicach modelu **przed** próbą. Reguła wspólna: przy nieoczekiwanym ruchu/stanie,
zawieszeniu albo błędzie przerwij własną symulację i zapisz FAIL; nie kontynuuj sekwencji.

| ID | Dokładne kroki | Oczekiwany wynik / próg PASS |
|---|---|---|
| B1 | Z repo uruchom kolejno `tools/linumert-start.sh --no-update`, `--plant --no-update`, `--classic --no-update`; zamknij każdą przed kolejną | Odpowiednio pełne HMI sim, HMI Plant z połączeniem, QtDragon; po zamknięciu brak własnych pozostawionych procesów/okien; kolejny start działa |
| B2 | W Plant wykonaj Reset, załącz i bazuj wszystkie osie; JOG X+ krokiem 1 mm, X− 1 mm; w MDI `G21 G91 G1 X1 F60`, następnie `G1 X-1` i `G90` | Bazowanie wszystkich osi potwierdzone statusem; kierunki i przesunięcia ±1 mm, powrót z błędem ≤0,01 mm w odczycie ustalonym; zwolnienie JOG kończy ruch |
| B3 | W Plant wpisz liczbę posuwu 120, obrotów 600, krok JOG 0,1; przełącz fokus; `M3 S600`, `M5`, `T1 M6` z potwierdzeniem wirtualnej wymiany | Pola nie tracą cyfr po odświeżeniu; zadane S=600, M5 zatrzymuje wirtualne wrzeciono, status T1 po M6; brak wiszącego dialogu |
| B4 | Otwórz dostarczone `config/sim/nc_files/linumert_demo.ngc`, Start, Pauza, Wznów, poczekaj do końca | W pauzie status PAUSED, po wznowieniu postęp i koniec interpreter IDLE z T11; samo IDLE po Abort/błędzie nie zalicza próby |
| B5 | W pustych Cyklach wybierz Planowanie: X max=100, Y max=50, głębokość całkowita=1, średnica=50 mm, reszta domyślna; Dodaj krok → Zapisz .lnx → Otwórz .lnx → Szacuj czas. Zaznacz krok, zmień X max na 90 i kliknij Zmień wybrany. Następnie w Symulacji obróć kamerę, wyeksportuj raport i otwórz HTML | Wczytane dane identyczne; edycja unieważnia poprzedni czas; raport zawiera aktualną kamerę i zdarzenia z B4; zapisz oba `.lnx` i HTML jako dowody. Nie uruchamiaj wygenerowanego cyklu w tej próbie |
| B6 | W trakcie wirtualnego przejazdu naciśnij grzyb HMI, spróbuj Start; potwierdź Reset i ponownie załącz bez Start | Odebranie zezwolenia widoczne w statusie; Start w E-STOP odrzucony; reset i ponowne załączenie same nie wznawiają programu |

To rozwinięcie punktu 27 [odbioru planu](prototypy/PLAN-21-27-2026-10-21.md).
Automatyczne kliknięcia Qt ani screenshot podglądu offline nie zastępują B1–B6.

## C — awarie programowe

Warunki A3; tylko atrapa mastera, brak LinuxCNC i sprzętu. Uruchom:

```sh
python3 tools/run_scenario.py link_loss drive_fault_mid_program estop_mid_program --master mock --out build/odbior/awarie
```

PASS C1: kod 0 i wszystkie kryteria wszystkich trzech raportów PASS; zachowaj HTML
oraz stdout. Kryteria i momenty wstrzyknięcia są w odpowiadających plikach
`plant/scenarios/*.yaml`, dołącz ich kopie/sumy. FAIL choćby jednego kryterium kończy
próbę; nie osłabiaj watchdogów ani limitów. C1 nie dowodzi reakcji fizycznego napędu.
Pełny dysk i utratę telemetrii na docelowym stanowisku kwalifikuje osobno T5.

## D — wykonawczy plan T1–T7 na docelowym sprzęcie

**NIEZWERYFIKOWANE NA SPRZĘCIE.** Wykonuje właściciel z osobą odpowiedzialną za
maszynę. Bez zatwierdzonego projektu, oceny ryzyka, warunków ograniczenia ruchu,
działającego toru ochronnego i przyrządów wszystkie karty D pozostają BLOCKED.
Nie wyprowadzaj komend do rzeczywistych wyjść z niniejszego dokumentu.
Plan określa wcześniej sygnały/piny, kanały pomiarowe, narzędzia i dokładne polecenia
dla wersji zainstalowanych na stanowisku. Brak tych danych = BLOCKED przed startem.
Nie ingeruj w obwody pod napięciem ani nie wywołuj awarii na niezabezpieczonej osi.

W każdej karcie: zanotuj start/koniec UTC, czas monotoniczny, liczbę próbek, okres,
jednostki, definicję wielkości, rozdzielczość i niepewność przyrządu, surowe dane,
histogram, minimum/maksimum i licznik błędów przed/po. Histogram bez surowych próbek
lub liczników utraty danych nie wystarcza. Ustal granice koszyków przed próbą.
Czas wykonania wątku i fazę wybudzenia mierz oddzielnie; pomiar userspace nie dowodzi RT.

Domyślna propozycja kampanii do zatwierdzenia: trzy powtórki po 60 min każdego
wariantu T1/T2/T7, T3 60 min, T4 każdy przejazd trzy razy, T5 każda awaria trzy razy,
T6 ciągłe 72 h (24 h tylko z uzasadnieniem osoby zatwierdzającej). Są to parametry
kampanii, a nie dodatkowe obowiązujące wymagania. Zapisz zaakceptowane czasy i progi
przed pomiarami; bez zatwierdzenia BLOCKED. Zmiana konfiguracji wymaga nowej kampanii.

| ID | Warunki dodatkowe i kolejność czynności | Oczekiwanie / dowody | Reguła przerwania |
|---|---|---|---|
| T1 | Bez zezwolenia na ruch; zapisz BIOS, CPU/IRQ affinity, governor, NIC/driver, kernel PREEMPT_RT; zmierz latencję narzędziem RT w spoczynku, potem osobno CPU, GPU, dysk, USB, sieć i łącznie; zapisz generator, wersję, parametry i intensywność każdego obciążenia | Wszystkie powtórki w ustalonym budżecie latencji hosta; maksimum i histogram dla każdego wariantu; budżet hosta ustal osobno, nie utożsamiaj go z czasem pracy servo | Przekroczenie progu lub luka pomiarowa: zakończ wariant; FAIL przy przekroczeniu, BLOCKED przy braku pomiaru |
| T2 | T1 PASS; cykl servo 1000 µs, zatwierdzone kanały pomiaru; spoczynek, pełne HMI, symulacja i zapis SQLite, następnie razem; zapisz użyte INI i obciążenie | Robocze progi z KWALIFIKACJA_RT po zatwierdzeniu: czas pracy ≤800 µs, bezwzględna faza ≤50 µs, zero niewyjaśnionych deadline miss; surowa seria obu wielkości | Próg przekroczony: FAIL i przerwij; brak rozdzielności czasu pracy/fazy: BLOCKED |
| T3 | T2 PASS, zatwierdzona mapa PDO/oczekiwany WKC, ruch zablokowany; przeprowadź INIT→PREOP→SAFEOP→OP według planu, porównaj stany i liczniki; zmierz DC/synchronizację, skonfigurowany watchdog i stany CiA402 | Wszystkie slave w oczekiwanym stanie; rzeczywisty WKC zgodny z oczekiwanym w każdej próbce; brak niewyjaśnionych strat PDO i błędów sync; progi DC i watchdog wpisane w metrykę | Niezgodne PDO, WKC lub stan: FAIL, zakończ przejście; brak progów DC: BLOCKED |
| T4 | T3 i odbiór toru fizycznego PASS; bez narzędzia/detalu, zatwierdzony ograniczony zakres i prędkość; pojedynczo każda oś, następnie wszystkie: kierunek, zadany odcinek mierzony zewnętrznie, bazowanie i próby limitów według planu | Kierunek i jednostki zgodne; błąd skali, powtarzalność bazy, droga po zadziałaniu limitu w liczbowych granicach wpisanych przed próbą; niezależny pomiar położenia | Nieoczekiwany ruch lub przekroczenie granicy: przerwanie zatwierdzonym torem, FAIL; dalsze osie wstrzymane |
| T5 | T4 PASS; ustalone bezpieczne warunki dla każdej awarii; kolejno zawieszenie HMI, zanik heartbeat/PC, utrata EtherCAT, błąd napędu, deadline miss, utrata telemetrii i pełny **wydzielony** wolumin danych testowych; między próbami przywróć bazowy stan | Każda awaria wykryta, reakcja w indywidualnym zatwierdzonym budżecie, komunikat bez fałszywego stanu aktualnych danych; po powrocie/reset bez samoczynnego ruchu; pomiar od bodźca do końca reakcji + log | Niespełniona reakcja: FAIL, przerwij kampanię; nie zapełniaj dysku OS ani nie zawieszaj PC bez niezależnego zabezpieczenia i planu |
| T6 | T5 PASS; stałe docelowe ustawienia, zatwierdzony program i zestaw obciążeń; rejestruj ciągle przez zaakceptowane 24–72 h, również temperatury i throttling | Pełny czas bez luk i niewyjaśnionych anomalii; progi T2/T3 zachowane, temperatury i throttling zgodne z wpisanymi granicami | Utrata logowania, restart lub naruszenie progu kończy przebieg; nie sumuj krótszych prób do ciągłej |
| T7 | T2 PASS; ta sama sesja pomiaru RT, plik ze 100000 segmentów o zapisanej sumie; uruchom renderowanie, obrót i zoom w ustalonym scenariuszu, potem pełne obciążenie T2 | Limit renderera ≤30 FPS; brak przekroczeń T2/T3; zapisz czasy klatek, maksymalny zastój i wcześniej przyjęty próg płynności. Sam FPS nie dowodzi izolacji RT | Próg RT/płynności przekroczony: FAIL; brak pomiaru równoległego lub licznika segmentów: BLOCKED |

Dla T5 dołącz podpisany [odbiór toru](../bezpieczenstwo/ODBIOR.md), w tym stałe
0/1 heartbeat, reset fizyczny, powrót energii, wrzeciono i oś pionową. Nie przypisuj
PL/SIL na podstawie tego protokołu. Lista nie zastępuje planu walidacji maszyny.

## E — blokady wydania 1.0

Wypełnij osobno bramki w szablonie. 1.0 pozostaje BLOCKED przy braku dowodów CSP
na sprzęcie, pełnej kampanii RT/EtherCAT, odbioru toru fizycznego, pulpitu docelowego,
reakcji na utratę telemetrii, powtarzalnej instalacji/aktualizacji/rollbacku oraz
manifestu/licencji. Błąd któregokolwiek wymaganego kryterium daje FAIL wydania.
| ID | Warunki i dokładne kroki | Oczekiwanie i reguła przerwania |
|---|---|---|
| E1 | Odtwarzalna kopia stanowiska bez wyjść; zapisz wersję bazową i kopię danych z sumami, zainstaluj kandydata, sprawdź start i odczyt danych, wykonaj rollback, porównaj dane z kopią początkową. Wersje, polecenia instalatora i kryteria migracji wpisz do planu przed próbą | Start obu wersji i dane zgodne z przyjętymi kryteriami; logi i sumy przed/po. Błąd lub utrata danych: FAIL, przerwij i zachowaj kopię. Brak wspieranej ścieżki lub poleceń: BLOCKED |
| E2 | Zebrane karty A–E1 i podpisany odbiór fizyczny; porównaj SHA każdego dowodu z manifestem kandydata, sprawdź dokumentację, `docs/LICENCJE.md`, `docs/PROVENANCE.md` i `docs/prawne/LISTA_PRZED_WYDANIEM.md` | Komplet dowodów dla tej konfiguracji i brak otwartych blokad licencji. Niezgodny SHA: przerwij ocenę, BLOCKED do powtórki; stwierdzona niezgodność licencji: FAIL |

Brak nowego pomiaru pozostaje jawną blokadą; historyczne P0/G1 ani zielone CI
nie potwierdzają gotowości fizycznej obrabiarki.
