# Cel: pełny cykl zadania obróbkowego w linumeRT

2026-11-05 · Model-Author: Codex.
Właściciel zlecił rozwój czterech poziomów w głównym projekcie i scalanie
ukończonych porcji do `main`. Osobna edycja lite nie jest docelowym produktem.

`program + maszyna + narzędzia + ustawienie detalu → prepare → verify → run → report`

To specyfikacja zakresu. Statusy, pozostałe kryteria i dowody są wyłącznie w
`docs/roadmap/plan.json`: VERTICAL-PREPARE, VERTICAL-VERIFY, VERTICAL-RUN, VERTICAL-REPORT.
Rekordy rozszerzają pierwotne sesje; nie zamykają ich ani wcześniejszych bramek.

## Odbiór całego celu

Operator przygotowuje detal z planowaniem, kieszenią i wierceniem w WebHMI,
weryfikuje go, wykonuje w LinuxCNC sim/Plant i otrzymuje raport porównawczy.
Utrwalony pakiet pozwala odtworzyć wejścia, kontrole i wynik. Każdy poziom dostarcza
użyteczną porcję operatorowi; API/CLI używają tej samej logiki co WebHMI.

LinuxCNC pozostaje jedynym interpreterem i planerem wykonania. Symulacja materiału
jest diagnostyką. Zachowujemy kontrakty operatora, E-STOP/STO, Reset i watchdog HAL.
Przygotowanie zadania nie uruchamia maszyny ani nie nadaje zezwolenia na ruch.
Testy sim/Plant, odbiór pulpitu i kwalifikacja sprzętu mają osobne wyniki.

## Poziom 1 — przygotowanie zadania

Zakres pierwotny: 032/039/040/041/043/062; zależności operatora: 028/029.
Widok WebHMI „Zadanie”: wybór programu, maszyny i narzędzi, ustawienie detalu,
przygotowanie pakietu oraz lista wyników kontroli. API i adapter CLI umożliwiają regresję.

Wejścia: wersjonowany `.lnx`, `machine.yaml`, istniejąca baza narzędzi SQLite,
układ detalu i jego położenie względem maszyny. Baza operatora jest czytana bez
tworzenia brakującego pliku i bez niejawnej migracji.

Pakiet v1: G-code, tool.tbl w jednostkach maszyny, kopia programu i modelu maszyny,
snapshot używanych narzędzi, ustawienie detalu, raport przygotowania i manifest SHA-256.
Komplet powstaje przed publikacją; wcześniejsze wyniki i źródła nie są nadpisywane.

Kontrole: schematy i przypięte generatory, model/napędy, narzędzia (istnienie, typ,
średnica, długość ostrza, obroty, kierunek), jednostki i spójność ustawienia detalu.
Zapisujemy też kontrole oczekujące na interpreter, zamiast nadawać im PASS.

Kryteria odbioru:

- Przykładowy detal daje kompletny, deterministyczny pakiet jednym działaniem WebHMI.
- Niepoprawne narzędzie, geometria lub jednostki blokują publikację z przyczyną i krokiem.
- Baza, jej historia, źródła i istniejący pakiet pozostają zachowane również po błędzie.
- Manifest wiąże dokładną treść wejść i wersje generatorów; zmiana pliku jest wykrywana.
- Raport rozróżnia przygotowanie od jeszcze niewykonanych kontroli toru i wykonania.

## Poziom 2 — weryfikacja zadania

Zakres pierwotny: 044/049/051/052/055; zależność: przygotowany pakiet poziomu 1.
Widok WebHMI: weryfikacja, postęp, czas, alarmy i przyczyny odrzucenia z linią programu.

Weryfikacja integralności pakietu, następnie izolowany rs274 z tabelą narzędzi,
ustawieniem detalu i konfiguracją maszyny. Limity osi sprawdzamy na pełnym torze,
w tym ekstremach łuków, z uwzględnieniem G5x/G92, jednostek i korekcji długości.
Dalej materiał, kolizje, obciążenia i szacowany czas z tego samego wejścia.

Kryteria odbioru:

- Brak interpretera, błąd lub niepełna interpretacja nie daje pozytywnego werdyktu.
- Przekroczenie zakresu, kontakt G0, kolizja i niepełne dane narzędzia mają jawny wynik.
- Zmieniony pakiet jest odrzucany przed kontrolą i nie dostaje statusu verified.
- Poprawny detal przechodzi rs274 i diagnostykę; przypadki błędne są odrzucane.
- Backend Python/C porównujemy w całym przepływie z udokumentowaną tolerancją.

## Poziom 3 — wykonanie w LinuxCNC sim/Plant

Zakres pierwotny: 028/029/049/053/061; zależność: niezmieniony pakiet verified.
Operator widzi gotowość, program, operację/linię, postęp oraz działające
Start/Pauza/Wznów/Stop. Wykorzystujemy wspólną bramę WebHMI i kontrakt sterowania.

Nadzorca wiąże instancję, konfigurację i tabelę narzędzi z pakietem oraz zapisuje
telemetrię. Przygotowanie lub weryfikacja nigdy nie włącza ruchu. Start respektuje
istniejące warunki gotowości i resetu; testowy rozruch symulatora jest osobny i jawny.
Pierwszy odbiór dotyczy sim/Plant; nie kwalifikuje fizycznej maszyny.

Kryteria odbioru:

- Start pakietu niezweryfikowanego, zmienionego lub przy niespełnionych blokadach jest odrzucony.
- Pauza/wznowienie, przerwanie, E-STOP, utrata klienta i timeout dają rozróżnialne wyniki.
- Awaria nie resetuje E-STOP ani nie odtwarza ruchu automatycznie.
- Telemetria pochodzi z rzeczywistej instancji LinuxCNC/Plant; mock jest osobno oznaczony.
- Odbiór automatyczny i kliknięcie przebiegu WebHMI mają zapisane dowody.

## Poziom 4 — ocena wykonania

Zakres pierwotny: 024/049/052/053/068; zależność: przebieg poziomu 3.
Widok WebHMI: wynik zadania i raport JSON do ponownego odczytu bez aktywnej maszyny.

Raport wiąże manifest, kontrole i przebieg. Zawiera czas przewidywany/rzeczywisty,
tor zadany/rzeczywisty, błąd nadążania max/RMS osi, alarmy z czasem i linią,
zakończenie programu oraz przerwy i ograniczenia telemetrii.

Kryteria odbioru:

- Jednostki i oś czasu są uzgadniane jawnie, bez dopasowania ukrywającego błąd.
- Wynik odróżnia zakończenie, przerwanie, awarię i niepełny zapis; brak danych nie daje PASS.
- Znane wymuszenia błędu i alarmu są wykrywane oraz przypisane do właściwego przebiegu.
- Zgodność z kontraktem precyzji projektu jest wykazana na danych LinuxCNC sim/Plant.

## Integracja i kolejność

1. Kontrakt pakietu i odczyt narzędzi; minimalne użyteczne przygotowanie w WebHMI.
2. Interpreter/limity, następnie materiał i kolizje; odbiór poprawnych i błędnych zadań.
3. Wykonanie przez istniejące sterowanie WebHMI, z telemetrią i obsługą przerwań.
4. Raport i końcowy detal przechodzący poziomy 1–4.

Prace z lite są materiałem do selektywnej integracji, nie scaleniem usunięć pełnej edycji.
Przed przeniesieniem kernela C uzgadniamy go z istniejącą gałęzią
`claude/natywne-przyspieszenia`; nie utrzymujemy dwóch implementacji tej samej funkcji.
Otwarte #211/#212/#213 oraz przenoszenie wspólnych napędów z `claude/scal-lite`
uwzględniamy przy doborze plików i baz; ich zakończenia nie deklarujemy tym dokumentem.
Każda ukończona porcja: testy, odbiór operatora jeśli dotyczy, dokumentacja, PR i merge commit do main.
