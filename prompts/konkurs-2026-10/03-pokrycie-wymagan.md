# Konkurs 3 — pokrycie wymagań i luka funkcjonalna poza GUI

Model-Author: Codex · 2026-10-23

## Cel

Ustal, gdzie projekt jako całość ma największą sprawdzalną lukę poza GUI, a następnie zamknij jedną wartościową, ograniczoną lukę w rdzeniu, Plant, generatorze, symulacji albo instalacji. Przeczytaj obowiązujące `docs/wymagania/*.md`, `tools/check_requirements.py`, odpowiednie testy i bieżący stan main. Nie wybieraj funkcji wyłącznie dlatego, że jest łatwa.

## Oczekiwany rezultat

Raport audytu identyfikuje 3 największe luki poza GUI na podstawie dowodów w kodzie/testach i macierzy REQ. Wybierz jedną o najlepszym stosunku wpływu do ryzyka i wdroż ją w osobnym, kompletnym kroku. Jeśli każda zmiana kodu wymaga nierozstrzygniętej decyzji lub sprzętu, przygotuj minimalny test/kontrakt albo precyzyjny plan i wyjaśnij blokadę. Nie zmieniaj obszaru safety-profile (konkurs 1), protokołu odbioru (konkurs 2) ani skórek/HMI (konkurs 4).

## Odbiór

- Ustalenia wskazują konkretne REQ, moduły i brakujący dowód/test, bez ogólników.
- Wybrana luka ma regresyjny test powiązany z REQ; wymagane testy i `tools/check_requirements.py` przechodzą.
- Nie usuwaj ani nie osłabiaj pokrycia wymagań, walidacji lub zabezpieczeń.
- Dokumentacja odzwierciedla rzeczywistą funkcjonalność i jej granice.
- W raporcie rozdziel wdrożony postęp od audytu i propozycji.

Oddaj wynik według wspólnej punktacji w `README.md`, używając własnego raportu w swojej gałęzi jako `raporty/03.md`. Wynik nie jest przeglądem niezależnym, jeśli wykonał go autor zmiany.
