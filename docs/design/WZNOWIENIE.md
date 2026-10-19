# Wycofanie narzędzia i powrót do obróbki (PROPOZYCJA)

Model-Author: Claude · 2026-10-19 · polecenie właściciela. Status: PROPOZYCJA do planu (M2/M4).
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Cel
Operator przerywa obróbkę (pauza, M0, złamane narzędzie, E-STOP, kolizja z symulacji), odsuwa narzędzie,
ogląda, ewentualnie wymienia narzędzie, a potem wraca do obróbki tak, że:
- narzędzie nie wchodzi w materiał pionowo ani ruchem szybkim,
- dojeżdża po spirali (helisie) w Z i po łuku w XY, stycznie do ścieżki,
- wchodzi na ścieżkę **kawałek przed miejscem przerwania** (zakładka), więc nie zostaje próg ani naddatek.

## Dwa przypadki

### A. Pauza bez przerwania programu (program wciąż „w toku”)
LinuxCNC 2.9 nie pozwala jogować w pauzie, ale ma **external offsets** (`axis.L.eoffset-*`, HAL):
przesunięcie nakładane na ruch także w pauzie, bez zmiany pozycji programu.
1. **Wycofaj**: narzędzie odjeżdża przez eoffset w Z (`RETRACT_HEIGHT`, opcjonalnie w XY na bok),
   wrzeciono stop albo dalej zależnie od ustawienia.
2. **Powrót**: eoffset maleje w odwrotnej kolejności (XY, potem Z z posuwem `REENTRY_FEED`),
   wrzeciono startuje i osiąga obroty przed zejściem. Narzędzie wraca dokładnie w punkt pauzy.
3. **Wznów** = zwykłe wznowienie programu.

Wymaga: komponent HAL w konfiguracji (eoffset na Z i XY), przyciski w pasku akcji, blokada przy G33/G76.

### B. Program przerwany (abort, E-STOP, wymiana złamanego narzędzia)
Ekran sam liczy wejście i generuje G-code wznowienia (nie zwykłe „start od linii” LinuxCNC, które
dojeżdża prostą).
1. **Punkt przerwania** P_b: ostatnia pozycja narzędzia na ścieżce (zapis pozycji z procesu symulacji
   i `motion_line`) oraz stan modalny w tej linii (narzędzie, G43, układ, S, M3/M4, F, płaszczyzna, G90/G91).
2. **Punkt wejścia** P_r: punkt na ścieżce programu cofnięty o **zakładkę** `OVERLAP` wzdłuż ścieżki
   (także wewnątrz łuku G2/G3 i przez granice linii). Od P_r do P_b narzędzie przejedzie drugi raz, więc
   nie ma progu.
3. **Dojazd** (prolog G-code):
   - `G53 G0 Z0`, przywrócenie stanu modalnego, `S… M3/M4`, czas rozpędzenia wrzeciona;
   - `G0` w XY do punktu startu helisy H, nad materiałem: `Z = góra materiału + CLEARANCE`;
   - **zejście po helisie** (G2/G3 z Z) o promieniu `HELIX_RADIUS` i skoku `HELIX_PITCH` (lub kącie
     `HELIX_MAX_ANGLE`), posuw `REENTRY_FEED`, aż do głębokości P_r;
   - **dojazd po łuku** w XY (ćwiartka okręgu o promieniu `LEAD_RADIUS`), styczny do ścieżki w P_r,
     od strony materiału już zebranego; opcjonalnie łuk z końcówką helisy w jednym ruchu (G2/G3 z Z).
4. **Dalej**: reszta bieżącego odcinka od P_r, potem kolejne linie programu.
5. **Sprawdzenie przed wykonaniem**: prolog przechodzi przez silnik symulacji na bieżącym materiale
   (mapa wysokości). Jeśli helisa albo łuk wchodzą w nieusunięty materiał głębiej niż dopuszczalny
   naddatek albo kolidują z maszyną, ekran próbuje drugiej strony ścieżki i mniejszego promienia; jeśli
   nadal się nie da, proponuje wejście pionowe z posuwem wgłębnym w obszarze zebranym (z ostrzeżeniem)
   albo odmawia. Podgląd prologu w widoku Symulacja; operator potwierdza.

## Ograniczenia
- Korekcja promienia G41/G42 aktywna w P_r: dojazd łukiem jako ruch wejścia korekcji, albo odmowa.
- Cykle stałe (G81…G89, G73): wznowienie od początku bieżącego otworu, nie w środku cyklu.
- Gwintowanie (G33, G33.1, G76): bez wznowienia w środku; od początku przejścia.
- Podprogramy i pętle o-word: punkt wejścia liczony na rozwiniętej ścieżce (interpreter LinuxCNC
  w trybie podglądu), stan zmiennych z chwili przerwania — jeśli nieustalony, wznowienie od początku
  pętli z ostrzeżeniem.

## Ustawienia maszyny (`[LINUMERT]` w INI, edycja w obszarze Konfiguracja)
| Klucz | Domyślnie | Znaczenie |
|---|---|---|
| `RESUME_RETRACT_HEIGHT` | 10 mm | wycofanie w pauzie (eoffset Z) |
| `RESUME_RETRACT_XY` | 0 mm | odsunięcie w XY w pauzie (0 = tylko Z) |
| `RESUME_SPINDLE_STOP` | 1 | zatrzymać wrzeciono po wycofaniu |
| `RESUME_CLEARANCE` | 1 mm | wysokość startu helisy nad materiałem |
| `RESUME_OVERLAP` | 2 mm albo 0,2·D (większe) | zakładka przed punktem przerwania |
| `RESUME_HELIX_RADIUS` | 0,4·D | promień helisy (≤ 0,5·D dla frezów bez ostrza w środku czoła) |
| `RESUME_HELIX_PITCH` | 1 mm/obr | skok helisy (alternatywnie `RESUME_HELIX_MAX_ANGLE` = 3°) |
| `RESUME_LEAD_RADIUS` | 0,5·D | promień łuku dojazdu w XY |
| `RESUME_FEED` | 50 % F | posuw helisy i łuku |
| `RESUME_SPINDLE_DWELL` | 2 s | czas na rozpędzenie wrzeciona |

Wartości narzędziowe (D, typ) z bazy narzędzi; dla wierteł i gwintowników helisa wyłączona
(wejście osiowe).

## Plan prac (propozycja)
1. `core/linumert/programs/resume.py` (czyste funkcje + testy): ścieżka z programu (sesja 051),
   punkt wejścia z zakładką, geometria helisy i łuku, G-code prologu, reguły odmowy.
2. Sprawdzenie prologu w `linumert_sim` (mapa materiału, bryły maszyny).
3. HAL: external offsets dla pauzy (symulator, potem generator konfiguracji).
4. Ekran: przyciski Wycofaj / Powrót / Wznów od miejsca przerwania, podgląd w Symulacji, ustawienia.
5. Scenariusz e2e: przerwanie w kieszeni, wznowienie, porównanie materiału z przebiegiem bez przerwy
   (różnica ≤ 0,05 mm).
