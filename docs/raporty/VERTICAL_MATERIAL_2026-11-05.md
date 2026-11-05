# Diagnostyka materiału przygotowanego zadania

Model-Author: Codex · 2026-11-05. Autokontrola, bez niezależnego przeglądu.
Pełny projekt linumeRT, WebHMI i wspólny backend; bez osobnej edycji lite.

## Zakres pierwszej porcji

Po integralności pakietu, ponownej kompilacji, rs274 i uzgodnieniu dokładnych callbacków
uruchamiany jest osobny proces diagnostyki z nice co najmniej10. Nie odczytuje kontrolera,
nie otwiera NML/HAL, nie zmienia E-STOP, STO, enable ani heartbeat. CLI i API używają
tej samej kompozycji; rdzeń nie importuje symulacji. Wynik nadal jest częściowy.

- Tor float64/mm z wykonanych callbacków LinuxCNC, bez parsera podzbioru i MoveList float32.
  G5x/G92/obrót/TLO zachowują fizyczną pozycję nosa. Syntetyczne N0 ustala początek,
  nie tworzy przejazdu przez materiał. TCP = nos minus rzeczywista długość wybranego T.
- Maszyna z zamrożonych machine.yaml i drives.json. Bez odczytu aktualnej biblioteki
  szablonów, domyślnej siły osi i zastępczej mocy wrzeciona. Strefy zakazane są przeszkodami.
- Profile flat/drill_118 wymagają jawnych wymiarów ostrza i oprawki, spójnej długości Z,
  kierunku, liczby ostrzy i maksimum RPM. Braki dają wynik niepełny, nie zastępczy walec.
- Materiał 2.5D: komórka0,25mm (z ograniczeniem liczby komórek), próbki co najwyżej0,25mm
  i0,05s, błąd cięciwy łuku co najwyżej0,005mm. Same współrzędne toru pozostają double.
  Siatka materiału jest przybliżeniem diagnostycznym, nie odbiorem dokładności pozycjonowania.
- Ciągłe konserwatywne obwiednie przejazdów przeciw zadeklarowanym bryłom obejmują także
  cienką przeszkodę między próbkami. Prostokątna obwiednia walca może dawać fałszywy kontakt
  przy narożu. Łuki mają dodatkowe powiększenie obwiedni o błąd cięciwy.
- Reguły materiału, części nietnących i obciążeń korzystają z istniejącego SimEngine;
  stan na początku odcinka zachowuje nowy G0/G1 oraz RPM, bez dziedziczenia poprzedniego M3.

## Wyniki checkpointu

Pierwsze3 rzeczywiste testy RIP PASS: pełny detal face/pocket/drill w Pythonie i C,
niekompletna geometria oprawki po pozytywnym interpreterze oraz imadło z K-304 i linią.
Pierwsza regresja:61 PASS,6 subtestów PASS. Nowe testy dodatkowe i odbiór GUI w toku;
te liczby nie stanowią końcowego odbioru porcji.

Wynik zawiera objętość usuniętą, dolne oszacowanie czasu ruchów, maksima obciążeń,
zdarzenia K-3xx z linią/T/pozycją, zakres brył i rozdzielczości oraz wybrany backend.
Raport jest osobnym niezmiennym plikiem, powiązanym job_id; pakiet pozostaje bez zmian.
Błąd/timeout/urwany JSON procesu nie daje dodatniej diagnostyki.

## Ograniczenia i pozostały odbiór

Nie odgadujemy mocowań i wymiarów czujników z samej pozycji punktowej. Model obejmuje
zadeklarowane bryły i strefy; ręczne ruchy operatora podczas zmiany narzędzia nie są
ruchem interpretera. Nieobsługiwany profil, postój DWELL lub niepełny model daje wynik
niepełny. Czas nie obejmuje przyspieszeń, wygładzania, zwłok i ręcznej zmiany narzędzia.
Materiał i siły są modelem diagnostycznym, nie funkcją bezpieczeństwa.

Pozostają końcowe testy, kliknięty odbiór WebHMI/CLI/JSON, pomiar całego przepływu Python/C,
CI i scalenie. Powiązanie początku/T0 z wykonaniem oraz poziomy3–4 pozostają osobne.
NIEZWERYFIKOWANE NA SPRZĘCIE.
