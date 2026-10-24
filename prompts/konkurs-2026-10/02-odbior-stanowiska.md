# Konkurs 2 — odbiór stanowiska i kwalifikacja

> Specyfikacja historycznego kroku konkursowego. Status i powiązania z pierwotnymi
> sesjami: [wspólny rejestr](../../docs/roadmap/plan.json).

Model-Author: Codex · 2026-10-23

## Cel

Zamień obecne rozproszone kryteria odbioru symulatora, Plant, LinuxCNC i stanowiska docelowego w praktyczny, odtwarzalny proces z raportem i dowodami. Zakres obejmuje `docs/wymagania/KWALIFIKACJA_RT.md`, `docs/bezpieczenstwa/ODBIOR.md`, `docs/raporty/` oraz istniejące narzędzia/CI. Najpierw sprawdź, co już istnieje, i nie duplikuj procedur.

## Oczekiwany rezultat

Przygotuj maksymalnie użyteczny protokół odbioru obejmujący: przygotowanie i wersje, testy sim/Plant, ręczny odbiór HMI na desktopie, plan pomiarów RT/EtherCAT, testy awarii oraz jednoznaczny szablon wyników PASS/FAIL/BLOCKED. Dodaj automatyzację tylko tam, gdzie jest bezpieczna i przenośna. Jeżeli stanowiska lub sprzętu nie ma, wykonaj lokalnie wszystkie niezależne testy i pozostaw precyzyjnie oznaczone kroki właściciela — nie wymyślaj wyników pomiarów.

## Odbiór

- Każdy test ma warunki wstępne, dokładne kroki, oczekiwany wynik i regułę przerwania.
- Testy programowe są oddzielone od prób fizycznych; symulacja nie jest dowodem bezpieczeństwa ani kwalifikacji RT.
- Raport można wypełnić bez interpretowania niejasnych kryteriów; zawiera commit, sprzęt, wersje, surowe pomiary i odchylenia.
- Wykonane testy mają odtwarzalne polecenia i rzeczywiste wyniki.
- Dokumenty wskazują jawnie, co blokuje wydanie 1.0.

Oddaj wynik według wspólnej punktacji w `README.md`, używając własnego raportu w swojej gałęzi jako `raporty/02.md`. Nie dokonuj pomiarów na nieautoryzowanym/nieistniejącym sprzęcie i nie deklaruj ich jako wykonanych.
