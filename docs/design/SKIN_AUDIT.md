# SKIN-00 — audyt i kolejność wdrożenia

Model-Author: Codex · 2026-10-23. Gałąź robocza, bez scalania na polecenie właściciela.
Źródło: `SKIN_SYSTEM_ROADMAP.md` z gałęzi design, commit 32e8691.

## Granice obecnej prezentacji

- `screens/linumert/linumert_handler.py`: integracja QtVCP, ACTION/STATUS i piny HAL.
  Pozostaje właścicielem komend oraz heartbeat; pakiet skórki nie tworzy pinów.
- `linumert_shell.py`: QObject, montaż QStackedWidget, nawigacja, odświeżanie statusu.
  Obecny układ nie jest implementacją Classic Digital.
- `linumert_shell_model.py`: stan powłoki, tokeny i QSS. Zachować zgodność istniejących
  widoków; nowy kontrakt prezentacji powstaje w osobnym module bez importu QtVCP.
- `linumert_*_page.py`: istniejące funkcje operatora. Nie przenosić widgetów HAL
  do kilku instancji nowych widoków i nie wiązać nawigacji z komendami maszyny.
- `linumert_workpiece_view.py`: QPainter, sortowanie trójkątów średnią głębokością,
  cieniowanie przez bezwzględną składową normalnej. Ta metoda nie rozwiązuje ogólnie
  wzajemnego zasłaniania przecinających się trójkątów; zgłoszenie GPU pozostaje
  do reprodukcji. `simulation/linumert_sim/stl.py` oblicza normalne eksportu osobno.

## Kolejność od łatwych do trudnych

1. Walidowany, niezależny od Qt kontrakt preferencji: skórka, motyw i język osobno.
   Rejestr rodzin oznacza koncepcje, nie cztery gotowe aplikacje.
2. Semantyczne palety i katalog tłumaczeń; kompletność i kontrast przed integracją.
3. Manifesty, model tylko do odczytu, kontrola świeżości statusu przed przełączeniem.
   Brak telemetrii lub zatrzymania potwierdzonego przez sterownik oznacza odmowę.
4. Niezależna scena testowa renderera: głębokość, winding, normalne, degeneracje,
   kilka kamer. Zrzuty i próba GPU/Mesa na Debianie i EndeavourOS przed wyborem.
5. Osobny launcher prototypu Qt/PyQt5, pierwsza kompozycja Classic Digital,
   następnie Industrial Pro, Cyberdeck i Organic Vector; bez automatycznego
   przełączenia aktualnego ekranu operatora.
6. Odbiór pełnej macierzy 4 × 4 × 2, obu rozdzielczości i wejścia dotykowego.

## Decyzje i odbiór

Zachowujemy zamrożony stos QtVCP/PyQt5 i limit 30 FPS. Zastąpienie kompozycji
oraz rozszerzenie tokenów pozostają propozycją architektoniczną do przeglądu;
prototyp nie zmienia kontraktu produkcyjnego. SKIN-01 jest bramką przed wdrożeniem
nowego renderera, nawet jeśli prostsze kontrakty SKIN-02/03 powstaną wcześniej.
STOP, Hold, alarmy i stan E-STOP muszą pozostać dostępne przy każdym układzie.
Nie ma jeszcze odbioru nowych skórek ani renderera na docelowym komputerze.
