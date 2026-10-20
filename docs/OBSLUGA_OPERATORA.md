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
