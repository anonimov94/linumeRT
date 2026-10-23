# Konkurs 1 — tor bezpieczeństwa profilu sprzętowego

Model-Author: Codex · 2026-10-23

## Cel

Najlepiej domknij wykrywalne programowo braki pomiędzy istniejącym kontraktem profilu `hardware` a jego realnym egzekwowaniem. Pracujesz w zakresie bezpieczeństwa i granicy uruchamiania/eksportu. Najważniejsze źródła: `CLAUDE.md` §5–6, `docs/bezpieczenstwa/README.md`, `docs/DECYZJE.md`, moduł `core/linumert/machine/deployment.py` i jego testy.

## Oczekiwany rezultat

Po audycie wybierz najmniejszy, ale najbardziej wartościowy kompletny krok. Priorytetem jest podłączenie kontroli deklaracji i ograniczonego audytu HAL do odpowiedniej granicy uruchamiania/eksportu konfiguracji sprzętowej, z bezpieczną odmową przy brakujących lub niepewnych danych. Dodaj regresje dla ścieżek hardware, sim i Plant. Jeśli bezpieczna integracja wymaga decyzji architektonicznej albo nie da się jej poprawnie wykonać w sesji, przygotuj konkretną specyfikację i testowalny prototyp bez udawania, że blokada już działa.

**Zakaz:** nie twierdź, że deklaracja INI lub statyczna analiza dowodzi poprawnego okablowania, PL/SIL, zadziałania zewnętrznego watchdoga ani gotowości maszyny. Nie zmieniaj niepowiązanych torów E-STOP/Plant ani nie usuwaj istniejących zabezpieczeń. Żadnych prób uruchamiania napędów.

## Odbiór

- Awaria/brak wymaganej deklaracji prowadzi do jawnej odmowy przed operacją chronioną.
- Sim i Plant zachowują dotychczasowe zachowanie.
- Wynik rozróżnia kontrolę konfiguracji od potwierdzenia fizycznego sprzętu.
- Testy obejmują odmowę, pozytywną deklarację, błędny HAL/ścieżki i niezmienione profile wirtualne.
- Dokumentacja bezpieczeństwa i macierz wymagań aktualne; brak twierdzeń o odbiorze sprzętowym.

Oddaj wynik według wspólnej punktacji w `README.md`, używając własnego raportu w swojej gałęzi jako `raporty/01.md`. W raporcie podaj ograniczenia i ręczny odbiór, który wciąż musi wykonać właściciel.
