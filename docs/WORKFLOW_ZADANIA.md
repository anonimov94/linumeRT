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

## Uruchomienie pierwszej porcji prepare

Brama pełnego projektu (zainstalowana grupa `panel`):

```sh
linumert-webhmi --linuxcnc --hal --postgui config/hal/linumert_webhmi_postgui.hal \
  --job-sources /dane/programy-lnx --job-machine /dane/machine.yaml \
  --job-tools /dane/tools.db --jobs-dir /dane/zadania \
  --drive-library /dane/biblioteka-napedow
```

W trybie testowym `--fake` zastępuje `--linuxcnc --hal --postgui ...`.
Cztery opcje `--job-*`/`--jobs-dir` są podawane razem. Maszyna i baza są aktywnymi
wejściami skonfigurowanymi dla tej bramy; ekran pokazuje ich nazwy. Bez konfiguracji
widok uczciwie zgłasza niedostępność. `.lnx` nie trafia do listy wykonywalnych programów CNC.
Domyślna biblioteka napędów pochodzi z pakietu `linumert.machine.drives`;
`--drive-library` pozwala wybrać inny katalog również poza checkoutem.

Ta sama logika bez uruchamiania GUI/bramy (standardowe zależności rdzenia):

```sh
linumert prepare /dane/programy-lnx/detal.lnx --machine /dane/machine.yaml \
  --tools /dane/tools.db --out /dane/zadania/detal-001 \
  --origin 50 50 -80 --offset G54 --drive-library /dane/biblioteka-napedow
```

Nazwa pakietu: litery ASCII/cyfry/`_`/`-`, 1–64 znaki, początek litera/cyfra.
Zero detalu podaje się w mm układu maszyny przed korekcją długości narzędzia.
Zakres i dowody tej porcji: [odbiór prepare](raporty/VERTICAL_PREPARE_2026-11-05.md).
Przygotowanie nie ustawia G54 w sterowaniu i nie uruchamia programu.

`linumert-job` oraz `linumert-lite prepare` wywołują tę samą implementację.
`linumert compile --machine ... --tools ...` korzysta z tego samego kompilatora,
z limitem wycofania Z wybranej maszyny i kontrolą narzędzi bez zapisu bazy.
Prepare zbiera przyczyny z całego programu przed generowaniem i publikacją pakietu.
Dane odbioru Claude z #218 są w `tests/test_prepare_acceptance.py`: jawne zero detalu,
schemat linumert.job v1, te same przypadki błędów, bez pomijania braku implementacji.

## Pierwsza porcja kontroli poziomu 2

WebHMI po przygotowaniu udostępnia „Sprawdź interpreter i ślad toru” oraz raport JSON.
Operator podaje założoną początkową pozycję nosa wrzeciona w mm układu maszyny,
z T0, G49 i G92=0. Kontrola działa offline; nie odczytuje ani nie zmienia położenia CNC.
Ten sam backend jest dostępny w CLI:

```sh
linumert preflight /dane/zadania/detal-001 --start 50 50 -5 --out /dane/preflight-001.json
```

Wymagane LinuxCNC `rs274` w PATH lub `LINUXCNC_DIR` wskazujące budowę RIP.
Pakiet jest sprawdzany przez SHA-256 oraz ponowną kompilację zapisanych wejść,
zanim jego program trafi do interpretera. Interpreter dostaje prywatne HOME/TMPDIR,
tabelę narzędzi i G54–G59 pakietu oraz wygenerowaną konfigurację offline sim.
Ta porcja obsługuje XYZ/ręczną zmianę narzędzi; nie kwalifikuje remapu sprzętowego M6.
Syntetyczny ruch N0 inicjalizuje wyłącznie interpreter; numery N1… zachowują linie programu.

Raport `linumert.job.preflight` v1 wiąże job_id, założenia, wynik interpretera,
ślad kanoniczny i wykryte przekroczenia z linią/osią. `partial` oznacza częściową
kontrolę, `rejected` odrzucenie, `unavailable` brak interpretera, `incomplete` limit
czasu/danych. CLI zwraca 0 tylko dla poprawnie ukończonej **częściowej** kontroli,
2 dla pozostałych wyników/błędu. Żaden wynik tej porcji nie nadaje `verified`.
Materiał/kolizje pozostają pending. Sam tekstowy ślad rs274 zaokrągla do czterech
miejsc w jednostkach programu, więc bez adaptera poniżej nie zalicza pełnych limitów.
Wykryte przekroczenie jest powodem odrzucenia; brak przekroczeń nie zastępuje dokładnego toru.

Manifest i dziewięć plików przygotowania pozostają niezmienione. Brama zapisuje
raporty osobno w `jobs-dir/.preflight/`; CLI odmawia istniejącego raportu oraz
zapisu wewnątrz pakietu. JSON pobrany z GUI zawiera ten sam wynik co zapis bramy.
Dowody i granice: [odbiór częściowej kontroli](raporty/VERTICAL_PREFLIGHT_2026-11-05.md).

## Dokładny tor i limity poziomu 2

Opcjonalny adapter C++17 używa API tooldata **tej samej budowy LinuxCNC 2.9 RIP** co
moduł gcode. Budowa jest jawna, poza importem i poza RT:

```sh
make -C core/native linuxcnc-tooldata LINUXCNC_DIR=/sciezka/linuxcnc-2.9
export LINUXCNC_DIR=/sciezka/linuxcnc-2.9
# Inny plik opcjonalnie: export LINUMERT_TOOL_DATA_LIB=/sciezka/liblinumert_tooldata.so
```

Po budowie te same CLI/API/WebHMI automatycznie korzystają z prywatnego gcode.parse,
z oryginalnym programem i rzeczywistymi T/M6/G43. Interpreter nie korzysta z NML/HAL
ani mapy narzędzi działającej maszyny. Adapter odmawia istniejącej .tool.mmap oraz
nieprywatnego HOME/cwd; moduł gcode musi pochodzić ze wskazanej budowy RIP.
Aktualny adapter SDK wymaga źródeł RIP (tooldata.hh nie jest publicznym nagłówkiem
instalowanego SDK); brak adaptera zachowuje jawny wynik częściowy z limitami pending.

Semantyka programu nadal wymaga rs274: gcode.parse jest interfejsem podglądu i m.in.
dopuszcza F0. Odbiornik odrzuca ruch roboczy bez dodatniego posuwu. Oba interfejsy
muszą dać tę samą kolejność, rodzaje, linie i współrzędne ruchów (uwzględniając tylko
zaokrąglenie tekstu rs274 przy porównaniu). Limity są następnie liczone z nieobciętych
wartości double w mm, z dokładnością obliczeń 0,000001 mm i ekstremami łuków.
Niepełny/niekołowy łuk daje incomplete, zamiast kontroli samych końców.

Poprawny tor dostaje `motion_limits: passed`; materiał nadal pending i całość partial.
Brak zgodności, błąd lub niepełny tor nie daje PASS. Raport zawiera dodatkowo precise_trace
i coordinate_resolution_mm. Przekroczenia mniejsze od rozdzielczości prezentacji
mają dopisek w komunikacie, dokładne wartości pozostają w JSON.
Dowody: [dokładne limity](raporty/VERTICAL_LIMITS_2026-11-05.md).
