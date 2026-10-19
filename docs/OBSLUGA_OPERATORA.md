# Obsługa operatora linumeRT

Model-Author: Codex · wymagania właściciela 2026-10-19.

## Alarmy i Reset

Na samej górze ekranu są trzy wiersze ostatnich alarmów, najnowszy pierwszy.
Historia pozostaje w Diagnostyce. Pojedynczy Reset potwierdza alarmy, których przyczyny ustały.
Podwójny Reset dodatkowo potwierdza zatrzask E-STOP; fizycznie otwarty obwód safety nadal blokuje maszynę.
Symulacja może resetować emulowane zdarzenia; nigdy nie traktujemy braku telemetrii jako symulacji.

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
