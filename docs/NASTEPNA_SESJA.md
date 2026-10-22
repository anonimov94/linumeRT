# Stan projektu i przekazanie

Tura: Codex · 2026-10-22 · stan: realizacja ciągła w chmurze.

Model-Author: Codex. Bieżące polecenie właściciela: małe użyteczne tematy możliwe
w chmurze → testy → push → scalenie po zielonym CI → kolejny temat, aż do „stop”.
Każdy temat ma osobną gałąź i PR. Dawne ograniczenie do zamykania rozpoczętych prac
zostało zastąpione tym poleceniem. Odbiór pulpitu właściciela pozostaje oddzielny.

## Stan scalania

Audyt pętli: właściciel wpisał `while [1]` i wybrał szacowanie czasu; journal wskazuje
SIGBUS w libtooldata. Trwa naprawa `codex/bounded-offline-interpreter`, checkout
`~/Projekty/linumeRT-interpreter-fix`: limity danych/czasu oraz prywatna tabela narzędzi
rs274, aby analiza offline nie dotykała działającej sesji LinuxCNC.
PR #66: izolacja obu ścieżek (czas i kontrola), 20 s/8 MiB, sprzątanie grupy procesów;
108 testów lokalnych PASS, w tym kliknięcie przycisku przy zalewaniu wyjścia. Dodano próby obu analiz na pętli bez końca przy działającym pełnym QtVCP/Plant
oraz skończony WHILE i WHILE [1] z BREAK; następnie CI LinuxCNC.

Odbiór pulpitu ujawnił brak `sim_toolchange.in` przy starcie Plant z pełnym QtVCP.
Naprawa: `codex/plant-hmi-toolchange`, checkout `~/Projekty/linumeRT-plant-hmi-fix`.
Minimalną poprawkę HAL zastosowano także lokalnie w `~/linumeRT`, aby właściciel mógł
ponowić start z `--plant --no-update`. Nowy test uruchamia faktyczny ekran Plant
(HMI i klasyczny) z niezmienionym postgui oraz bez obejścia E-STOP; odbiór w kontrolach PR.

Dopracowanie planu 21–27: [PR #64](https://github.com/anonimov94/linumeRT/pull/64),
osobny checkout `~/Projekty/linumeRT-plan-21-27`. ETA zapamiętuje korekcję F/G0 do końca
przebiegu; D38-A odczytuje ustawienia INI i sprawdza wysokość po zaokrągleniu HAL.
Lokalnie 50 testów funkcji PASS + 10 subtestów, złożenie HMI PASS, 108 testów C PASS,
lint i kontrola wymagań PASS. Pełna próba lokalna ujawniła blokadę gniazd sieciowych;
wynik odbioru Debian/LinuxCNC należy sprawdzić w kontrolach PR #64 przed scaleniem.
Punkt 27 pozostaje otwarty: ponownie potwierdzono blokadę Podmana przez `/run/user/1000`.

W main są #56 (integracja), #57 (launcher), #58 (kieszenie v2), #59 (.lnx),
#60 (podgląd D38, ETA i raport), #61 (odbiór) oraz
[scalony PR #62](https://github.com/anonimov94/linumeRT/pull/62)
(D38-A: wycofanie Z i powrót w pauzie z zachowaniem G41/G42 oraz G43).
Merge #62: `979c6725d8cb682a9e841fe571d4eedbc6cbb22a`.
Przy kontroli GitHuba 2026-10-21 brak otwartych PR i zgłoszeń; jedyna gałąź to main.

## Wynik i granice odbioru

Kod #62 `400eb8fac3540ed735d7aacd20feae5ff9a44e5b`:
[Debian 12/LinuxCNC PASS](https://github.com/anonimov94/linumeRT/actions/runs/39626463088)
— 921 testów, 22 subtesty, 9 pominięć; osobno 98 testów LinuxCNC PASS.
10 wariantów wycofania/powrotu obejmuje sim/Plant, G40/G41/G42, G20/G21 i G43.
[Ogólne CI main PASS](https://github.com/anonimov94/linumeRT/actions/runs/39629276081).
Wcześniejsze wyniki i protokół pulpitu: [raport planu](raporty/prototypy/PLAN-21-27-2026-10-21.md).

D38-A zachowuje kolejkę i modalność przy pauzie AUTO bez Abort. Wznowienie wymaga
rzeczywistego i żądanego offsetu zero oraz błędu nadążania <=0,005 mm.
Odzyskiwanie po Abort/E-STOP, powrót po wymianie narzędzia i wykonanie helisy z zakładką
pozostają niewdrożone. Podgląd helisy nie wykonuje ruchu.
Punkt 27 — ręczny odbiór pulpitu — nadal OTWARTY; odbiór sprzętowy również niewykonany.
Nie utożsamiać wyników CI z ręcznym odbiorem pulpitu lub fizycznej obrabiarki.

## Uruchomienie na EndeavourOS

Kopia właściciela: `~/linumeRT` (main). Zachowano lokalne T12 w `tool.tbl`.
Menu aplikacji: linumeRT / linumeRT + Plant / linumeRT — QtDragon.

```sh
~/linumeRT/tools/linumert-start.sh
~/linumeRT/tools/linumert-start.sh --plant
~/linumeRT/tools/linumert-start.sh --classic
```

Pierwsze polecenie uruchamia HMI na symulatorze LinuxCNC; `--plant` dodaje wirtualną
obrabiarkę. Uruchamiać kolejno, po zamknięciu poprzedniej instancji.
Skrypt korzysta z Podmana i kontenera Debian 12; nie wymaga instalacji LinuxCNC na hoście Arch.

## Środowisko i pozostałe prace

Lokalny EndeavourOS, sesja agenta z ograniczeniami sandboxa. Zwykły Git nie rozwiązuje
nazwy GitHuba, konektor GitHub działa. Obiekty pobrano konektorem, zweryfikowano ich SHA
i zaktualizowano main przez fast-forward z zachowaniem historii. Skróty odświeżono.
Podman nie może utworzyć katalogu w `/run/user/1000`; pełnego okna nie uruchomiono.
Wyniki runtime pochodzą z CI. Następny krok: ręczny protokół pulpitu z raportu planu.
Stare kopie robocze w `~/Projekty` i ich nieśledzone dokumenty pozostawiono bez zmian;
zawierają historyczne wyniki oczekujące na CI, które zastąpił raport w main.
Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Codex — historia diagnostyczna, 2026-10-22

Nowe polecenie właściciela: rozwijać najprostsze lub nierozpoczęte obszary.
Gałąź `codex/diagnostic-history`: trwała historia komunikatów Diagnostyki (SQLite),
filtr poziomu, wyszukiwanie i eksport CSV. Odrębna baza dla każdej konfiguracji INI;
1000 wpisów, widok do 200 pasujących; błędy zapisu dają jawny tryb tylko w pamięci.
Lokalnie 7 testów trwałości/filtrów/awarii/Qt PASS; dodano próbę złożonej Diagnostyki
na małym ekranie, przewijanie i dokumentację. PR #68: pełne CI wymagane przed scaleniem.
Wynik odbioru i sprawdzony SHA utrzymywać w opisie PR #68. PR #67 (pola liczbowe) pozostawiony bez zmian. Model-Author: Codex.

Uzupełnienie kroku: pola filtrów korzystają z palety tokenów; siedem testów lokalnych
ponownie PASS. Kod i dokumentacja są wypchnięte do PR #68; końcowy odbiór przez CI.

## Codex — kolejne małe tematy, 2026-10-22

Właściciel zlecił ciąg: wdrożenie → testy → push/scalenie → następny temat, aż do stop.
Historia diagnostyczna #68 scalona jako 2abeae7; odbiór Debian 944 + 101 LinuxCNC PASS.
Gałąź codex/tool-filters: wyszukiwanie T/P/opis/dane i filtr typu w widoku Narzędzia.
Pierwszy test Qt z rzeczywistą bazą SQLite PASS: filtry nie zapisują bazy/tool.tbl,
nie wysyłają komend CNC i nie przełączają edytowanego narzędzia. Następny krok:
odbiory CI i scalenie; wynik oraz SHA w opisie PR. Model-Author: Codex.

PR #69 scalony jako cb60edb: filtry narzędzi, Debian 945 + 101 LinuxCNC PASS.
Kolejny temat: codex/tool-refresh — zaznaczenie według T przy zmianie listy, bez
nadpisywania niezapisanych pól; usunięty T czyści zaznaczenie. Zlikwidowano ostrzeżenia
Qt o ponownym wstawianiu istniejących komórek. Test regresyjny odtworzył błąd na starym
kodzie, po poprawce lokalnie PASS. Kolejny krok: pełne CI i scalenie; wynik i SHA w PR.

Kolejny mały temat: codex/tool-export — eksport wszystkich zapisanych narzędzi do CSV
z widoku Narzędzia, niezależnie od filtrów. Bez zapisów bazy/tool.tbl i komend CNC.
Dwa testy Qt/SQLite PASS, obejmują odtworzenie geometrii/korekcji, anulowanie i błędy.
Szkic PR zależy od poprawki odświeżania #70; scalić dopiero po niej i pełnym CI.
Wynik i sprawdzony SHA utrzymywać w opisie PR. Model-Author: Codex.

Codex: codex/tool-integer-format naprawia obcinanie zer w liczbie ostrzy i maksymalnych
obrotach tabeli (12000→12, 10→1). Zera usuwane tylko po kropce dziesiętnej.
Test starego kodu FAIL; trzy testy Qt lokalnie PASS po poprawce. Szkic następuje po #71;
scalanie kolejno, po pełnym CI. Wynik i SHA w opisie PR. Model-Author: Codex.

PR #70 scalony jako 37d78f6: 945 + 101 LinuxCNC PASS, 25 subtestów, 9 pominięć.
#71 (eksport CSV) i #72 (format liczb) mają zielone CI ogólne; trwa LinuxCNC.
Codex: codex/tool-preserve-metadata chroni dane nieedytowane przez formularz:
oprawkę, trwałość, STL, parametry tokarskie i korekcje inne niż Z. Zmiana tworzy
rekord na podstawie bieżącego T w bazie; nowe T ma własne wartości domyślne.
Regresja starego kodu FAIL; cztery testy Qt/SQLite lokalnie PASS. Szkic następuje po #72.
Scalić kolejno po pełnym CI; wynik i sprawdzony SHA w PR. NIEZWERYFIKOWANE NA SPRZĘCIE.

Codex: codex/tool-stl-picker udostępnia pole i wybór pliku dla typu Specjalne STL.
Formularz odczytuje/zapisuje ścieżkę, oznacza wymagane pole i wyświetla ograniczenie:
symulacja nadal używa walca zastępczego, bez analizy siatki STL.
Edytor przewijany, długie wiersze zawijane; pięć testów Qt/SQLite lokalnie PASS,
w tym okno 1200×600, dostęp do zapisu i brak obcięcia etykiet. Szkic następuje po #73.
Wynik pełnego CI i sprawdzony SHA w PR. Model-Author: Codex.

#71 scalony jako 8cf3508 (946 + 101 LinuxCNC PASS), #72 jako 4c9d16e (947 + 101),
#73 jako 88855a0 (948 + 101); każdy z 25 subtestami i 9 pominięciami. #74 ma zielone
CI ogólne, trwa LinuxCNC. Codex: codex/tool-write-errors obsługuje błędy pliku/SQLite
przy zapisie/usuwaniu i blokuje edycję przy braku statusu CNC (konstruktor lub poll).
Baza może być zmieniona przed błędem tool.tbl; komunikat wymaga sprawdzenia obu,
bez udawania rollbacku. Sześć testów Qt/SQLite lokalnie PASS; szkic następuje po #74.
Wynik pełnego CI i sprawdzony SHA w PR. Model-Author: Codex. NIEZWERYFIKOWANE NA SPRZĘCIE.

#74 scalony jako 519dbca: 949 + 101 LinuxCNC PASS, 25 subtestów, 9 pominięć.
#75 ma zielone CI ogólne; trwa LinuxCNC. Codex: codex/tool-history udostępnia
historię bazy dla numeru T z edytora (także usuniętego), do 100 najnowszych wpisów.
Dialog pokazuje zmienione pola przed/po, czas UTC i źródło. Bez przywracania danych
ani potwierdzania synchronizacji z CNC. ToolDB.history ma opcjonalny limit w SQL,
z zachowaniem dotychczasowej kolejności i API bez limitu. Dziewięć testów lokalnie PASS;
szkic następuje po #75. Wynik pełnego CI i sprawdzony SHA w PR. Model-Author: Codex.

#76 (historia narzędzia) ma zielone CI ogólne; trwa LinuxCNC. Codex:
codex/tool-life-fields udostępnia nazwę oprawki, planowaną trwałość i ręczne zużycie
w minutach. Brak automatycznego naliczania i blokady po przekroczeniu planu.
Core odrzuca błędne/nieskończone czasy również przy CSV. Trzynaście testów lokalnie PASS;
podgląd i obsługa operatora zaktualizowane. Szkic następuje po #76.
Wynik pełnego CI i sprawdzony SHA w PR. Model-Author: Codex.

#75 scalony jako feded36: 950 + 101 LinuxCNC PASS, 25 subtestów i 9 pominięć.
#76 i #77 mają zielone CI ogólne, trwa LinuxCNC. Codex: codex/tool-numeric-validation
odrzuca niepoprawne średnice/korekcje, orientację Q i struktury JSON przed zapisem;
eksport sprawdza również istniejące rekordy przed podmianą tool.tbl. Dwie regresje
na starym kodzie FAIL; 17 testów lokalnie PASS. Odmowa walidacji w HMI ma obsługę,
bez komend przeładowania. Szkic następuje po #77; wynik i sprawdzony SHA w PR.
Model-Author: Codex. NIEZWERYFIKOWANE NA SPRZĘCIE.

#76 scalony jako 11b413b (953 + 101 LinuxCNC PASS, 30 subtestów), #77 jako dfa3d51
(957 + 101 PASS, 45 subtestów); po 9 pominięć. #78 ma zielone CI ogólne; trwa LinuxCNC.
Codex: codex/tool-diameter-wear stosuje d_wear do D eksportowanego do tool.tbl.
Import D odejmuje zachowaną korekcję przy wyliczaniu nominalnego d, bez kumulowania
zużycia; wartości zerowe/ujemne po korekcji i korekcja bez nominalnego d są odrzucane.
21 testów lokalnie PASS, zgodność z rzeczywistym Cutter i powtarzany import mm/cale.
Dodano cztery próby G41/G42 z rzeczywistym rs274 do odbioru w CI (lokalnie niewykonane).
Szkic następuje po #78; wynik i sprawdzony SHA w PR. Model-Author: Codex.
NIEZWERYFIKOWANE NA SPRZĘCIE.

#78 scalony jako f6de5c9: 961 + 101 LinuxCNC PASS, 67 subtestów i 9 pominięć.
#79 ma zielone CI ogólne; trwa LinuxCNC, w tym nowe G41/G42. Codex:
codex/tool-table-units uwzględnia TRAJ/LINEAR_UNITS przy pierwszym imporcie tabeli,
eksporcie danych startowych oraz Zapisz/Usuń w HMI. Baza i pola długości pozostają
w mm; kąty bez skalowania, nieznane jednostki blokują operację przed zapisem.
26 testów lokalnie PASS; próby rs274 rozszerzone o maszynę calową (do odbioru w CI).
Znany osobny dług: Live.sample/WCS/reload_tools czytają wartości CNC bez przeliczenia
na mm. Pełnej symulacji calowej jeszcze nie zaliczono. Szkic następuje po #79.
Wynik i sprawdzony SHA w PR. Model-Author: Codex. NIEZWERYFIKOWANE NA SPRZĘCIE.

#79 scalony jako bba7b02: 965 + 105 LinuxCNC PASS, 71 subtestów, 9 pominięć;
wszystkie cztery nowe G41/G42 z korekcją PASS. #80 ma zielone CI ogólne; trwa LinuxCNC.
Codex: codex/sim-live-units przelicza XYZ, WCS i Z/D narzędzi z jednostek maszyny
na mm używane przez silnik, widok i ślad końcówki. Błędne jednostki dają zdarzenie
error przed uruchomieniem odczytu i wątku poleceń. 30 lokalnych testów PASS (21 core/sim
na Pythonie 3.12 i 9 Qt na 3.13), w tym identyczne usunięcie materiału mm/inch.
Regresja starego kodu FAIL. Szkic następuje po #80; pełny wynik CI i SHA w PR.
Pełnego ręcznego odbioru calowego HMI/obrabiarki nie zaliczono. Model-Author: Codex.
NIEZWERYFIKOWANE NA SPRZĘCIE.

#80 scalony jako f5c04f4: 970 + 109 LinuxCNC PASS, 75 subtestów i 9 pominięć;
osiem prób G41/G42 mm/inch PASS. #81 ma zielone CI ogólne; trwa LinuxCNC.
Codex: codex/sim-stock-wcs wybiera świeży status dla aktywnego układu przygotówki,
zamiast starych parametrów z pliku. Inny WCS korzysta z zapisanych parametrów;
brak jego danych lub błąd poll daje error bez zastąpienia dotychczasowego materiału.
Regresja starego kodu FAIL; 32 lokalne testy PASS (23 core/sim, 9 Qt).
Szkic następuje po #81; pełny wynik CI i SHA w PR. Model-Author: Codex.
NIEZWERYFIKOWANE NA SPRZĘCIE.

#81 i #82 mają zielone CI ogólne, trwa LinuxCNC. Codex: codex/tool-unsaved-state
pokazuje bursztynowy napis „niezapisane” po edycji, także liczby przed zatwierdzeniem.
Load/Zapis czyszczą wskaźnik, Nowe oznacza nowy formularz; filtry/refresh go zachowują.
Kolejna edycja usuwa poprzednie potwierdzenie sukcesu, ale zachowuje błąd zapisu.
Usunięcie ma własne potwierdzenie zamiast starego „zapisane”. 33 testy lokalnie PASS,
w tym rzeczywiste kliknięcia Qt/zapis SQLite, klawiatura i podgląd. Szkic po #82.
Nie dodano jeszcze potwierdzenia porzucenia edycji przy wyborze innego T lub Nowe.
Wynik pełnego CI i sprawdzony SHA w PR. Model-Author: Codex.
