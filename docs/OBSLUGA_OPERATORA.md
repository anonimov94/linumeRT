# Obsługa operatora linumeRT

Model-Author: Codex · wymagania właściciela 2026-10-19.

## Alarmy i Reset

Na samej górze ekranu są trzy wiersze ostatnich alarmów, najnowszy pierwszy.
Historia pozostaje w Diagnostyce. Pojedynczy Reset potwierdza alarmy, których przyczyny ustały.
Podwójny Reset dodatkowo potwierdza zatrzask E-STOP; fizycznie otwarty obwód safety nadal blokuje maszynę.
Symulacja materiału/kolizji raportuje zdarzenia diagnostyczne i nie wysyła E-STOP/STO ani resetu.
Nigdy nie traktujemy braku telemetrii jako symulacji.

## Specjalista

Tryb specjalisty służy do ręcznego wycofania po kolizji. JOG wymaga przytrzymania przycisku,
pracuje domyślnie wolno i ma limit 100 mm/s (6000 mm/min), także po zmianie jednostek.
Nie uruchamia automatycznie programu, wrzeciona ani ruchu MDI. Fizyczne safety, STO, krańcówki
i limity LinuxCNC pozostają nadrzędne. Wirtualny bliźniak pozwala wyjść z kolizji geometrycznej.

## Wartości liczbowe

Wymiary mają cztery miejsca po przecinku (rozdzielczość 0,0001 mm), całkowite kroki
nie dodają ułamkowych reszt. Pole przyjmuje wpis klawiaturą, zatwierdzany Enterem albo zmianą fokusu.
Przecinek lub kropka dziesiętna zależy od ustawień języka systemu.
Pola posuwu JOG, obrotów, numeru narzędzia, pozycji i wymiarów obsługują zaznaczanie
oraz wklejanie; klawisze w polu nie uruchamiają JOG. F1/F2/Esc zachowują funkcje maszyny.
Krok JOG można wybrać z listy albo wpisać samodzielnie (0 = ruch ciągły).
Procentowe korekcje F, G0 i wrzeciona w Produkcji również przyjmują wpis klawiaturą;
suwak oraz przyciski +/− nadal działają. Korekcja jest wysyłana po zatwierdzeniu wpisu,
a odświeżanie statusu nie nadpisuje edytowanej wartości. Obowiązują zakresy konfiguracji.

## Symulacja i wirtualny bliźniak

Pełne HMI korzysta z LinuxCNC jako interpretera i planera. Dostępne są JOG, MDI,
M3/M4/M5, wybór poprzedniego/następnego numeru narzędzia lub wpis numeru i przycisk WYMIANA M6.
Zero detalu ustawia G54–G59. Bliźniak korzysta z konfiguracji machine.yaml i HOME z INI;
Reset symulacji odnawia materiał i wraca do HOME po potwierdzeniu operatora.
Samodzielny podgląd Zero detalu jest edytorem offline, bez ruchu i komend maszyny.

## Pierwszy start

Uruchom `tools/linumert-start.sh`, przejdź do Symulacja i naciśnij
„Uruchom / Reset symulacji → HOME”. Potwierdź odnowienie materiału i bazowanie.
Poczekaj na stan Gotowa, wybierz JOG w górnym pasku. Dla MDI i M6 wymagane jest bazowanie.
Wymianę w konfiguracji wirtualnej potwierdza magazyn symulowany; na fizycznej maszynie
obowiązuje jej procedura ręcznej wymiany/ATC. Zero detalu jest dostępne w szynie obszarów;
„Wczytaj bazę z maszyny” pobiera wybrany G54–G59: aktywny układ ze STATUS,
pozostałe z PARAMETER_FILE bieżącej konfiguracji. Odczyt nie zmienia zer ani nie wykonuje ruchu.

Po kolizji model raportuje położenie i kod diagnostyczny; nie zatrzymuje sterownika.
Operator może zatrzymać program przyciskiem Stop. Specjalista nadal udostępnia ograniczony JOG,
bez obchodzenia fizycznych wejść i limitów. Zakończ specjalistę po wycofaniu.
Zmiana trybu nie włącza komend safety z procesu symulacji.
Zakresy osi LinuxCNC nadal obowiązują, również w symulacji. Klawiatura w specjaliście: 10 mm/s.

`[LINUMERT] VIRTUAL_MODE=1` oznacza konfigurację bez fizycznych wyjść napędów.
Nie ustawiaj tej flagi w konfiguracji podłączonej maszyny. Brak flagi oznacza tryb fizyczny.

## D38 — wycofanie i powrót w pauzie

Produkcja → „Wycofaj Z w pauzie”, „Powrót do ścieżki”, „Powrót i wznów”.
Najpierw wstrzymaj program i poczekaj na zatrzymanie. Wybierz wysokość dodatniego ruchu Z
oraz posuw w mm/min. Wrzeciono pozostaje włączone; to nie jest tryb wymiany narzędzia.
Wycofanie musi mieścić się w zakresie Z. Funkcja jest podłączona w wirtualnym sim/Plant.

Program pozostaje w pauzie AUTO; nie ma Abort, MDI, G40 ani ponownego włączania korekcji.
External offset przesuwa oś Z poza torem interpretera, więc G41/G42 i kolejka ruchu
pozostają zachowane. Powrót prowadzi w Z do tego samego skorygowanego punktu, po czym
„Powrót i wznów” wznawia oryginalny program. Sam „Powrót” pozostawia pauzę.
Nie wykonuje helisy ani zakładki i nie zastępuje podglądu helisy w Symulacji.

Wymagane: zbazowane XYZ/trivkins, G17/G94, stabilna pauza, aktywna korekcja posuwu,
niezmienione narzędzie/układy i włączone wrzeciono. Gwintowanie i cykle są poza zakresem.
Polecenia ruchu QtVCP są blokowane podczas wycofania; wznowienie jest możliwe dopiero,
gdy rzeczywisty i żądany offset Z wynoszą zero. Zmiana programu, narzędzia, modalności,
utrata pauzy lub sprzężenia zwrotnego wstrzymuje operację bez ślepego opuszczania.
Po takim błędzie wyłącz maszynę; poprzednie wznowienie jest anulowane.

Przerwanie programu przez Abort/E-STOP, wymiana narzędzia i odzyskiwanie po wyłączeniu
nie są obsługiwane przez ten mechanizm. NIEZWERYFIKOWANE NA SPRZĘCIE.
Model-Author: Codex.

## Kontrola pętli i szacowanie czasu

„Program” → „Sprawdź składnię” sprawdza zapis G-code, wyrażenia oraz parowanie
`WHILE/ENDWHILE`, `REPEAT/ENDREPEAT`, `IF/ENDIF` bez wykonywania pętli.
Poprawna składnia nie potwierdza zakończenia programu. Porównania w LinuxCNC mają
operatory `EQ`, `NE`, `LT`, `LE`, `GT`, `GE` (np. `[#1 LT 10]`, nie `[#1<10]`).

`o100 while [1]` jest poprawne i może kończyć się przez `o100 break`.
Bez osiągalnego wyjścia pełny czas programu jest nieokreślony. Nie da się rozstrzygnąć
zakończenia każdej pętli na podstawie samego tekstu programu.

„Produkcja” → szacowanie czasu i szacowanie w „Cyklach” analizują program poza wątkiem
ekranu. Analiza ma limit 20 sekund i 8 MiB danych; po przekroczeniu limitu pokazuje
komunikat, bez częściowego czasu i bez potwierdzenia poprawności całego programu.
Limit może też osiągnąć duży, skończony program. Pętle skończone są dozwolone.
Samodzielny interpreter ma osobne pliki robocze i nie współdzieli tabeli narzędzi
z działającym sterowaniem. Model-Author: Codex.
