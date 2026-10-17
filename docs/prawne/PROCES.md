# Proces IP w codziennej pracy

Wdraża `WYTYCZNE_IP.md` §4 i §7. Kontrakt: `CLAUDE.md` §7. Dokument jest listą kontrolną projektu, nie opinią prawną.

## 1. Specyfikacja funkcjonalna osobno od wyglądu
- Najpierw opis w `docs/wymagania/`: co operator ma zrobić, jakie dane potrzebuje, jakie tryby i sekwencje.
- Wygląd powstaje osobno, wyłącznie z `docs/design/tokens.yaml`, ikon i znaku linumeRT.
- Do pracy nie używamy zrzutów ekranów ani materiałów cudzych sterowań jako wzoru wykonawczego.

## 2. Własny system projektowy
- Paleta, fonty, siatka, ikony, kompozycja (lewa szyna obszarów, górny pasek trybu, dolny pasek akcji) i komunikaty są własne.
- Nowy ekran: opisz funkcję → zaprojektuj w tym samym systemie → makieta w `docs/design/makiety/`.
- Podobieństwo wynikające z funkcji technicznej (tryby, G54…, cykle) wolno zachować, ale zapisz uzasadnienie w `docs/DECYZJE.md`.

## 3. Rejestr pochodzenia (`docs/PROVENANCE.md`)
- Każdy nowy zasób (ikona, font, grafika, biblioteka, kod z innego projektu) dostaje wiersz **w tym samym commicie**.
- Pola: zasób, typ, autor, data, źródło, licencja, zakres użycia, ścieżka. Zależności: dodatkowo `docs/LICENCJE.md`.
- Kod z LinuxCNC/QtDragon: zachowaj nagłówki GPL, oznacz zmiany, zapisz commit upstream w `UPSTREAM.md`.
- Test `tests/test_ip_guard.py` blokuje plik w `docs/design/` bez wpisu.

## 4. Historia projektowania
- Decyzje w `docs/DECYZJE.md` (z uzasadnieniem), przebieg w `docs/DZIENNIK.md`, makiety i commity zostają w historii git.
- Nie przepisujemy historii (bez force-push na `main`).

## 5. Przegląd podobieństwa
- Przed wydaniem (sesja 080) przegląd ekranów przez osobę, która nie projektowała interfejsu.
- Porównujemy całą kompozycję i wrażenie całości, nie pojedyncze przyciski.
- Wynik zapisz w `docs/prawne/LISTA_PRZED_WYDANIEM.md` (pole „dowód”).

## 6. Procedura przy wątpliwości (§7 wytycznych)
1. Wstrzymaj dany element.
2. Zapisz w `docs/DECYZJE.md` jako PROPOZYCJA: źródło i dokładny zakres planowanego użycia.
3. Ustal, czy element jest czysto funkcjonalny, czy ma charakterystyczną formę graficzną lub tekstową.
4. Sprawdź licencję, rejestry praw i warunki umowne; w razie potrzeby konsultacja z prawnikiem IP/IT lub rzecznikiem patentowym.
5. Do czasu wyjaśnienia zrób niezależną alternatywę i idź dalej.

## 7. Nazwy
- Zakazane nazwy producentów: `ZAKAZANE_NAZWY.txt`; zakazane słowa i zamienniki: `docs/SLOWNIK.md`. Pilnuje ich `tests/test_ip_guard.py`.
- Wyjątek: `docs/` (rzeczowe porównania, bez sugerowania powiązania) i `docs/prawne/`.
- Nazwy kluczowe dla marki (linumeRT) przed premierą: wyszukiwanie w UPRP, EUIPO, WIPO (sesja 080).
