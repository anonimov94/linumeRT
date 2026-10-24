# Lista do wykonania: 21–27 października 2026

> Specyfikacja i historia realizacji; nie jest osobnym harmonogramem.
> Bieżący status, pozostały zakres i powiązania (PLAN-21-22…PLAN-27 i D38-A/B):
> [wspólna roadmapa](roadmap/PLAN.md), [rejestr](roadmap/plan.json).
> Niższe datowane opisy stanu są zapisem historycznym; status aktualizuj wyłącznie w rejestrze.

Model-Author: Codex. Polecenie właściciela: dokończyć rozpoczęte prace; nie zaczynać nowych sesji.
Ta lista obejmuje braki w już rozpoczętych obszarach. Właściciel następnie polecił realizować
plan 21–27 bez czekania na odpowiedź, aż do „stop”. Stan początkowy zapisano w tabeli;
wyniki dopisywane są poniżej po testach. Nie dodano rowków, konturów ani nowych kamieni roadmapy.

| Termin | Priorytet | Funkcja i stwierdzony stan | Jak odtworzyć / dowód | Kryterium ukończenia |
|---|---|---|---|---|
| 21.10 | P1 | Kieszenie: rampa i helisa niezaimplementowane | Cykle → kieszeń; formularz i generator obsługują wyłącznie wejście pionowe | Jawny wybór wejścia, walidacja geometrii, golden, rs274, materiał i Plant; brak niekontrolowanego zagłębiania |
| 22.10 | P1 | Kieszenie: obrót, zadany promień naroży, kierunek skrawania, naddatki i wykańczanie niezaimplementowane | Brak parametrów w `PocketRect/PocketCircle.fields`; sesja 041 pozostaje częściowa | Parametry działają w podglądzie i G-code; testy granic i objętości oraz odbiór LinuxCNC/Plant |
| 23.10 | P1 | Cykle: brak otwierania/zapisu .lnx i edycji wybranego kroku | Widok ma dodawanie i usuwanie ostatniego kroku oraz zapis .ngc; ograniczenie opisane w module | Zapis/wczytanie .lnx bez utraty danych, edycja wybranego kroku i ponowna walidacja narzędzi |
| 24.10 | P1 | D38: wycofanie w pauzie i powrót po helisie/łuku niezaimplementowane | Jest projekt `design/WZNOWIENIE.md`; brak `programs/resume.py` i przycisków tej operacji | Pierwsza działająca porcja zgodna z projektem: podgląd, symulacja, blokady i testy; nie utożsamiać ze zwykłym Pause/Resume, które przechodzi test |
| 25.10 | P2 | Czas obróbki: brak czasu pozostałego i kalibracji względem Plant | „Szacuj czas” działa; wynik jest górnym oszacowaniem ze stopem w narożach | Porównanie czasów z Plant, opis błędu modelu i widoczny czas pozostały; zmiana programu unieważnia wynik |
| 26.10 | P2 | Raport symulacji: zrzut widoku 3D niepodłączony do eksportu z HMI; oś czasu częściowa | Przycisk Raport wysyła ścieżkę; HTML ma mapę z góry, nie zrzut widoku operatora | Eksport zrzutu bieżącego widoku i zgodnej osi zdarzeń; test faktycznego kliknięcia oraz poprawności pliku |
| 27.10 | P1 | Launcher i HMI na pulpicie właściciela: odbiór ręczny niewykonany z sesji agenta | Sandbox blokuje Podman, gniazda i pulpit; skróty zainstalowane, parser systemowy i tryby testowane automatycznie | Uruchomić HMI/Plant/QtDragon ze skrótów, bazowanie, JOG, MDI, M3/M5/M6, program, raport i zamknięcie; dołączyć zrzuty i ponowić regresję |

Dodatkowa otwarta część PR #48: deklaracje i audyt HAL są offline. Bramka startu/eksportu
dla konfiguracji hardware oraz fizyczne I/O wymagają osobnego odbioru sprzętowego.
Nie są objęte wynikiem symulatora ani obietnicą uruchomienia w tym tygodniu bez sprzętu.

Odbiór zamkniętej porcji: [raport P0](raporty/prototypy/P0-2026-10-20.md).
Przetestowane: HMI (42 kroki), edytor G-code, podstawowe generatory, prototypy kieszeni,
walidacja narzędzi, szacowanie czasu, eksport podprogramów, LinuxCNC/Plant/VFD i watchdogi.
Kolizje materiału są diagnostyczne, zgodnie z poleceniem właściciela z 20.10; brak E-STOP
z procesu symulacji jest zamierzonym zachowaniem, a nie usterką.

Realizacja 21.10: wejście `plunge/ramp/helix` i kąt w formularzu, automatyczna geometria
wewnątrz kieszeni, limit 20 000 bloków. Helisa o średnicy nie większej niż D frezu
nie pozostawia rdzenia. Rampa i helisa schodzą od powierzchni / poprzedniej warstwy
posuwem zagłębiania; podgląd XY pokazuje wejście. Golden, objętość, geometria i Plant
sprawdzane automatycznie; odbiór rs274 w CI jest wymagany przed scaleniem.

Realizacja 22.10: obrót prostokąta, promień naroża (0 oznacza minimalne D/2), CW/CCW,
naddatki ścian/dna i jawne wykańczanie z oddzielnym posuwem. Bez wykańczania naddatki
pozostają. Wykańczanie ścian jest wykonywane warstwami, a dna pełną ścieżką na końcu;
naddatek dna nie może przekroczyć kroku Z. Kierunek dla kieszeni i M3: CCW współbieżny,
CW przeciwbieżny ([przykład producenta narzędzi](https://videos.sandvik.coromant.com/cost-effective-solutions-for-face)).
Test materiału sprawdza objętość, całe dno i brak cięcia poza obrysem. Odstęp prostokątnych
pierścieni uwzględnia również przekątną, aby nie zostawiać wysp przy 90% kroku bocznego.
CI obejmuje wykonanie obu kieszeni z helisą i wykańczaniem na LinuxCNC + Plant.
Nowa geometria jest wersją 2 generatorów. Wersja 1 w rejestrze pozostaje niezmienna,
a golden sprawdza G-code istniejących programów. Punkty 21–22 odbierane są wspólnym PR.

Realizacja 23.10: lista kroków, „Zmień wybrany”, „Otwórz .lnx…” i „Zapisz .lnx…”.
Zapis atomowy, bez utraty komentarzy, przygotówki, jednostek, wyłączonych kroków i wersji.
Nieznany generator/wersja, błędny JSON albo parametry odrzucają otwarcie bez naruszenia
bieżącego programu. Edycja ponawia kontrolę narzędzi i unieważnia czas; eksport .ngc
używa wspólnego kompilatora. Testy przycisków Qt i roundtrip wykonywane automatycznie.

Realizacja 24.10 — pierwsza porcja: przycisk „Podgląd powrotu po helisie (D38)” w Symulacji.
Zakładka jest liczona po zmierzonym śladzie XY na stałej głębokości. Podgląd obejmuje
wycofanie Z, helisę i ćwierćokrąg styczny do odcinka śladu; nie interpretuje programu.
Próbowane są obie strony i dwa promienie. Kopia bieżącego materiału i model maszyny
odrzucają kolizje, wejście w nieusunięty materiał i przekroczenie zakresów; stan symulacji
pozostaje nietknięty. Brak danych, ruch programu, korekcja promienia i cykle dają odmowę.
Ustawienia INI: RESUME_OVERLAP, RESUME_CLEARANCE, RESUME_HELIX_PITCH i RESUME_FEED (mm/min).

**Stan pierwszej porcji przed #62:** external offsets i wykonanie powrotu były otwarte.
PR #62 dodał wycofanie Z, powrót i wznowienie w pauzie z zachowaniem kolejki i modalności.
Pierwsza porcja nie wysyła komend ruchu i nie eksportuje programu do wykonania. Wyświetlony
podgląd nie jest zgodą na automatyczny start. Obsługa HAL musi uwzględnić zachowanie
[external offsets LinuxCNC](https://linuxcnc.org/docs/2.9/html/motion/external-offsets.html).

Realizacja 25.10: Produkcja → „Szacuj czas programu”, a podczas pracy/pauzy widoczny
orientacyjny czas pozostały. Liczenie działa w tle; zmiana programu lub INI unieważnia
wynik. Pauza nie zużywa czasu modelu. ETA jest niedostępne przy korekcjach F/G0 innych
niż 100% i po starcie od linii. Przekroczenie czasu modelu daje jawny komunikat.
Model łuków wymaga G17/G94, uwzględnia limit Z helisy i odmawia niekompletnych limitów XYZ.
Nie gwarantuje czasu całego cyklu: start XYZ=0, uproszczony G64, pominięte oczekiwanie
operatora i rozpędzanie wrzeciona. Test LinuxCNC + Plant zapisuje czas oszacowany,
zmierzony i błąd względny dwóch kieszeni i planowania w `pocket_calibration.json` w artefaktach CI.
To porównanie kontrolne, bez uniwersalnego współczynnika kalibracyjnego dla wszystkich maszyn.

Realizacja 26.10: Raport pobiera bieżący obraz widoku 3D przez
[Qt grabFramebuffer](https://doc.qt.io/archives/qt-5.15/qopenglwidget.html#grabFramebuffer)
(przy zastępczym 2D — obraz tego widoku) i osadza PNG w samodzielnym HTML.
Oś czasu SVG prowadzi do tych samych zdarzeń i czasów co tabela; HMI otrzymuje ten sam
czas względny procesu symulacji. Limit 500 zdarzeń raportu pokazuje liczbę pominiętych.
Etykiety kolizji są diagnostyczne, bez sugerowania zatrzymania CNC.
Test kliknięcia Raport obejmuje rzeczywisty obraz Qt, protokół i plik HTML; osobny test
LinuxCNC CI sprawdza prawdziwy widok 3D i zmianę obrazu po obrocie kamery. Pakiet pyqtgraph
był już zależnością launchera; dodano go do środowiska testów CI.

## Stan odbioru — 2026-10-21

Porcje implementacji z punktów 21–26 są scalone (#58, #59, #60); #62 dodaje wykonanie D38-A.
Końcowy kod 5f290103: [Debian/LinuxCNC PASS](https://github.com/anonimov94/linumeRT/actions/runs/39510750194),
915 testów + 96 LinuxCNC, 12 subtestów PASS; 9 pominięć nie zaliczono jako wykonane.
[Raport z wynikami i protokołem pulpitu](raporty/prototypy/PLAN-21-27-2026-10-21.md).

D38-A (#62, merge `979c672`) wykonuje wycofanie Z przez external offsets i powrót w pauzie
AUTO, także z G41/G42 i G43. [Odbiór Debian/LinuxCNC PASS](https://github.com/anonimov94/linumeRT/actions/runs/39626463088):
921 testów + 98 LinuxCNC, 22 subtesty; 9 pominięć. Powrót po Abort/E-STOP, wymianie
narzędzia i wykonanie helisy z zakładką pozostają otwarte. Punkt 27 wymaga pulpitu właściciela.
Nie dopisano nowych sesji roadmapy ani nie zaliczono niewykonanych prób ręcznych.
Model-Author: Codex. Autokontrola, bez niezależnego przeglądu.

## Dopracowanie punktu 25 — 2026-10-21

ETA zapamiętuje użycie korekcji F/G0 innych niż 100% do końca bieżącego przebiegu,
także przed obliczeniem oszacowania. Przywrócenie 100% nie przywraca mylącego wyniku;
dostępność wraca przy następnym pełnym uruchomieniu. Całkowite oszacowanie programu
pozostaje dostępne po zakończeniu. Lokalnie: 41 testów czasu i widgetów PASS, lint PASS.

## Dopracowanie punktu 24 — 2026-10-21

D38-A odczytuje wysokość i posuw z `RESUME_RETRACT_HEIGHT` i `RESUME_RETRACT_FEED`
w INI. Błędna konfiguracja blokuje operację z komunikatem. Wysokość jest sprawdzana
po zaokrągleniu do rozdzielczości HAL; zerowe wycofanie i przekroczenie limitu przez
zaokrąglenie są odrzucane. Panel pokazuje zadaną wysokość po zaokrągleniu także na
maszynie calowej. Lokalnie 7 testów PASS i 10 subtestów, w tym kliknięcia Qt oraz INI.
Uwzględniono też obcięcie float→s32 w HAL: zadanie 1,001 mm nie może stracić impulsu
przez reprezentację binarną i utknąć w oczekiwaniu. GUI modeluje rzeczywistą konwersję,
a test LinuxCNC/Plant sprawdza żądany offset z dokładnością 0,000001 jednostki maszyny.

Wspólna autokontrola dopracowania: 50 testów funkcji PASS i 10 subtestów, osobno
złożenie HMI z eksportem raportu PASS; lint, 108 testów C i kontrola wymagań PASS.
Pełna próba lokalna: 895 PASS, 10 pominięć, 98 wyłączonych testów LinuxCNC,
22 subtesty PASS; 8 porażek i 5 błędów z zakazu tworzenia gniazd sieciowych.
Dodatkowa porażka złożenia HMI wynikała z niewidocznego pytest w procesie potomnym;
po poprawieniu środowiska bez zmiany kodu ten test przeszedł. Dwie dodatkowe
parametryzacje startu od stanu pauzy objęto późniejszym wynikiem 50 testów funkcji.
To nie jest pełny lokalny PASS. Wymagany odbiór runtime: kontrole
[PR #64](https://github.com/anonimov94/linumeRT/pull/64).

Punkt 27 ponownie sprawdzono tylko do granicy dostępnego środowiska:
`podman info` kończy się `mkdir /run/user/1000/libpod: read-only file system`.
Ręcznego protokołu pulpitu nie zaliczono. Powrót po Abort/E-STOP, wymianie narzędzia
i wykonanie helisy pozostają poza wdrożonym D38-A.
