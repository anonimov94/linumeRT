# Stan projektu i przekazanie

Tura: Codex · 2026-10-23 · stan: oddana; osobne ekrany offline, odbiór/scalenie PR #91.

## Wynik końcowy — SKIN-01

Model-Author: Codex. Polecenie właściciela 2026-10-23: po scalonych #67/#86
rozpocząć SKIN-01, testować lokalny GPU/Mesa i Debian/LinuxCNC, scalać ukończone
etapy po zielonych testach. Zastępuje niższe historyczne „bez scalania”.
Main operatora zaktualizowany do 2bfd473; wszystkie 11 lokalnych plików zachowane
(sumy SHA-256 i kopia w /tmp/linumert-skin01-backup). Osobna gałąź
codex/skin-01-renderer, checkout /tmp/linumert-skin01; bez globalnego LOCK.
PR #87, commity 37fde1a, 894c68f, e09f3f1. Krok 1: reprodukcja QPainter i degeneracji kapsli, walidacja wejścia siatki;
23 lokalne testy (z IP) PASS, lint PASS. Widok GL i launcher gotowe;
próba Radeon/Mesa PASS (24-bit depth, niezależność od kolejności, culling,
3 kamery, wireframe, obrót, 9 klatek/350 ms).
Push 894c68f: launcher/prototyp. Test Debian 12/LinuxCNC + llvmpipe/Mesa 22.3.6
również PASS (pyqtgraph 0.13.1, 24-bit depth, 8 klatek/350 ms).
Pełny lokalny Debian: 1018 pytest PASS, 10 skip, 109 deselected; check_requirements PASS (21/22 pokryte, bez błędów); lint, test-c i test-san PASS. Końcowe CI: Python, Plant matrix i LinuxCNC RIP PASS; 109 testów LinuxCNC PASS. Pierwszy CI wykrył PNG w state/, poprawiono artefakty na build/skin01 i końcowe CI jest zielone. PR #87 scalony 2026-10-23 jako b22689f. Odbiór sprzętu właściciela pozostaje niewykonany.

## Aktualne polecenie — scalanie po zakończeniu

Właściciel zezwolił teraz na scalanie ukończonych aktywnych gałęzi po testach.
To zastępuje wcześniejsze odłożenie scalania i wszystkie niższe historyczne zapisy
„bez scalania”. PR #67 zawiera poprawkę lokalizacji kroku JOG; PR #86 obejmuje
prototyp kompozycji Qt. Połączono je na gałęzi #86 do wspólnego odbioru CI;
konflikty dotyczyły wyłącznie dopisywanych wpisów dokumentacji, zachowano obie strony.
Kolejność scalenia do main: #67, następnie #86, po zielonym CI obu.
Gałęzie tool-discard-edits i design/skin-system-roadmap-2026-10-22 są już zawarte
w main (odpowiednio przodek main i PR #85); nie wymagają ponownego scalania.
Model-Author: Codex.

## GUI — aktualne polecenie właściciela 2026-10-23

Model-Author: Codex. Dziś bez scalania; poniższe dawne polecenia automatycznego
scalania nie obowiązują tej sesji. Właściciel odkłada scalanie na 2026-10-24.
Nie ustawiono automatycznego scalenia ani harmonogramu.
Gałąź `codex/skin-foundation`: SKIN-00 i niezależny kontrakt preferencji/palet.
Lokalnie 4 testy unittest PASS: 32 kombinacje, walidacja, niezmienność oraz kontrast
tekstów/statusów na panelach. Pełnego Qt/LinuxCNC nie uruchomiono na Windows/Python
3.15 (brak Qt i pytest); pełne CI pozostaje do odbioru w PR.
Następnie katalog tłumaczeń i manifesty, prototyp renderera oraz osobny launcher
kompozycji; bramki w `design/SKIN_AUDIT.md`. Aktualny ekran nie używa prototypu.

Model-Author: Codex. Bieżące polecenie właściciela: małe użyteczne tematy możliwe
w chmurze → testy → push → scalenie po zielonym CI → kolejny temat, aż do „stop”.
Każdy temat ma osobną gałąź i PR. Dawne ograniczenie do zamykania rozpoczętych prac
zostało zastąpione tym poleceniem. Odbiór pulpitu właściciela pozostaje oddzielny.

## Stan scalania

Najnowsze poprawki audytu właściciela:
- [PR #66](https://github.com/anonimov94/linumeRT/pull/66): prywatne HOME/TMPDIR/cwd
  obu analiz rs274, limity 20 s/8 MiB i brak częściowego czasu po przerwaniu pętli.
  Journal awarii wskazał SIGBUS w libtooldata (wspólne `.tool.mmap` starego rs274).
- [PR #67](https://github.com/anonimov94/linumeRT/pull/67): wpisywanie liczb przez
  router QtVCP, własny krok JOG i edytowalne korekcje F/G0/S. Status nie kasuje wpisu;
  F1/F2/Esc i zwolnienie rozpoczętego JOG zachowują obsługę maszyny.
- Odbiór lokalny klawiatury: 97 testów PASS. Samotest faktycznego QtVCP wpisuje
  posuw, obroty, narzędzie, krok, pozycję, korekcję F i linię; zapisuje stany i zrzuty.
  Pełne wyniki odbioru automatycznego są w kontrolach obu PR, autokontrola autora.
- Checkouty `~/Projekty/linumeRT-interpreter-fix` i `~/Projekty/linumeRT-numeric-fix`.
  Kopia operatora `~/linumeRT` wymaga ponownego otwarcia aplikacji po aktualizacji.
  Ręczny odbiór pulpitu (punkt 27) i odbiór sprzętowy pozostają otwarte.

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

#81 scalony jako b0fdadf (974 + 109 LinuxCNC PASS), #82 jako e6c386d (976 + 109),
oba 79 subtestów i 9 pominięć. #83 ma zielone CI ogólne, trwa LinuxCNC.
Codex: codex/tool-discard-edits chroni niezapisany formularz przy wyborze innego T/Nowe.
Domyślne Zostań (także Enter/Escape) zachowuje pola i poprzednie zaznaczenie; Odrzuć
przełącza bez zapisywania. Rekord docelowy czytany po dialogu, brak/błąd zachowuje draft.
Udany zapis nowego/klonowanego T wiąże zaznaczenie z zapisanym numerem.
35 testów lokalnie PASS, rzeczywiste okna Qt i podgląd; regresja starego kodu FAIL.
Szkic następuje po #83; wynik pełnego CI i sprawdzony SHA w PR. Model-Author: Codex.

Uzupełnienie GUI 2026-10-23: katalog wspólnych napisów EN/PL dla nawigacji,
trybów i stanów prototypu, niezależny od palety i układu. Nie tłumaczy jeszcze
wszystkich stron starego HMI. Kody alarmów pozostają identyfikatorami katalogu.
Aktualny wynik lokalny: 6 testów unittest PASS, komplet kluczy w obu językach
we wszystkich 32 kombinacjach. Bez scalania. Model-Author: Codex.

## GUI — kolejny krok 2026-10-23

Model-Author: Codex. PR #86, codex/skin-foundation: walidator manifestu API 1
oraz niezmienny model warunków przełączenia, bez integracji ACTION/HAL.
Lokalnie pytest: 20 PASS + 87 subtestów (kontrakty skórek i strażnik IP);
ruff dla zmienianych modułów/testów PASS. Narzędzia w katalogu tymczasowym,
bez zmian zależności projektu. Qt/LinuxCNC nadal niewykonane lokalnie.
Poprzednie CI: 930 PASS, 63 skip, 109 deselected, jeden błąd rejestru pochodzenia;
brakujące dokładne ścieżki dokumentów poprawione i test strażnika IP lokalnie PASS.
Następne: adapter statusu i osobny launcher prototypu; renderer wymaga próby GPU.
Bez scalania; pozostałe dawne instrukcje scalania w tym dokumencie są historyczne.

## GUI — działający podgląd offline 2026-10-23

Model-Author: Codex. Uruchomienie: python3 tools/dev/skin-preview.py (PyQt5).
Cztery kompozycje i 32 wybory skórka/paleta/język, bez sterowania maszyną.
Lokalnie 22 testy + 87 subtestów PASS; test Qt obejmuje 64 warianty rozmiarów/wyborów.
Zrzuty lokalne: build/skin-preview/ (nieśledzone pliki testowe).
Obecny ekran operatora nadal bez zmian; brak renderera 3D i adaptera CNC w prototypie.
Następnie: scena testowa renderera oraz adapter statusu do przyszłej integracji.
Nie scalać. Pełne CI aktualnego SHA sprawdzić w PR #86.

## Scalanie aktywnych gałęzi — 2026-10-23

Model-Author: Codex. Właściciel ponownie zezwolił na scalanie wszystkich ukończonych,
zweryfikowanych aktywnych gałęzi. Zastępuje wcześniejsze odłożenie scalania na jutro.
PR #67 zaktualizowano main. Lokalny Qt ujawnił utratę separatora dziesiętnego przez
QDoubleValidator z inną lokalizacją niż edytor; usunięto filtr zmieniający wpis,
walidacja pozostaje przed komendą JOG. Separatory tysięcy są odrzucane; kropka
presetrów i lokalny separator są obsługiwane. 13 testów klawiatury PASS.
Następnie: pełne CI #67 → scalenie → aktualizacja i CI #86 → scalenie.
Gałęzie tool-discard-edits i design/skin-system-roadmap-2026-10-22 już zawarte w main.

## Stan zatrzymania — podgląd skórek, 2026-10-23
Model-Author: Codex. Osobny checkout /tmp/linumert-skin-visual,
gałąź codex/skin-visual-preview, PR #89. Wzorce od właściciela zapisane w
 docs/design/referencje-skin/; obejrzano cztery obrazy. Dopasowano hierarchię paneli,
 rodziny ramek i wskaźniki; trzy sceny GL, powiększanie z zachowaniem statusu.
Odbiór GL w CI, wraz z kontrolą złożonego obrazu po przełączeniach. Lokalny Debian: lint PASS, 1018 pytest PASS,
11 skip, 109 deselected, wymagania 21/22 bez błędów. Radeon i Debian llvmpipe:
64 kombinacje PASS. Końcowy odbiór obejmuje poprawkę współdzielenia kontekstów:
indywidualny framebuffer nie wystarczał do wykrycia pustych paneli w zrzucie okna.
Końcowy Debian llvmpipe: 64 kombinacje PASS; testy zmienionego kodu 23 PASS
+ 87 subtestów. Stan końcowych kontroli i scalenia utrzymywany w PR #89.
To podgląd offline, bez poleceń CNC; pełna zgodność z makietami i SKIN-02…06 otwarte.
Następny krok: szczegółowe kontrolki rodzin i adapter statusu w osobnym hoście QtVCP.

## Aktualizacja raportu i README — 2026-10-23
Model-Author: Codex. Polecenie właściciela: nowe zrzuty w docs/raporty/hmi_sym
 i głównym README. PR #89 scalony jako 8483b81; main operatora zaktualizowany,
 lokalne pliki zachowane. PR #90: cztery świeże zrzuty podglądu Qt, odnowione
 ujęcia prawdziwego HMI/symulacji i wynik JSON. Nowy raport rozróżnia oba launchery.
Przy wykonywaniu zdjęć wykryto błąd zagnieżdżonego komentarza M4 w demo.
8675777 usuwa go i wymaga finalnego T11 + idle w odbiorze E2E; dodano regresje
leksera dla obu programów. Końcowe kontrole i scalenie raportowane w PR #90.
Dalszy zakres skórek: szczegółowe kontrolki według makiet, pełne strony i adapter QtVCP.

## Osobne ekrany według wizji — PR #91, 2026-10-23
Model-Author: Codex. Polecenie właściciela: wyraźnie odrębne ekrany, układy
 i przyciski maksymalnie zgodne z czterema obrazami pierwotnych wizji.
Osobny checkout /tmp/linumert-distinct-skins, gałąź codex/distinct-skin-screens.
Kod ekranów ea2fc39: osobne klasy/moduły Classic/Industrial/Cyberdeck/Organic,
 własne konsole, DRO, F/S, program, ramki i typografia. Native przyciski, selektor
 obrotowy, przełączniki, wskaźniki, ostrokątne i płynne metalowe obudowy.
`--skin <id>` uruchamia samodzielny ekran; Ustawienia zmieniają lokalny wygląd.
Nawigacja i powiększanie działają; kontrolki CNC nieaktywne, E-STOP nieinteraktywny.
Radeon/Mesa i Debian/llvmpipe: 128 wariantów PASS; Debian 26 testów + 87 subtestów PASS.
Zrzuty w docs/raporty/hmi_sym i README odświeżone, opisane jako offline.
Błąd wysokości Industrial 815 px przy 1280×800 usunięty; cele 44 px zachowane.
Końcowe kontrole i scalenie raportowane w PR #91. Dalszy zakres: szczegółowe modele,
 dopracowanie pozostałych detali wizji i bezpieczna integracja stanu/poleceń QtVCP.

## Konkurs 04 — integracja read-only, 2026-10-23
Model-Author: Codex. Osobny checkout /tmp/linumert-contest-04,
gałąź codex/contest-2026-10-skins. Adapter stat.poll w jednorazowym procesie,
typowany snapshot i osobny launcher tools/dev/skin-monitor.py; cztery skórki,
G53 mm/°, E-STOP z NML, bez kanału komend i bez konsumpcji error_channel.
Lokalnie 30 testów + 87 subtestów PASS. Następne: rzeczywisty LinuxCNC/Xvfb,
utrata/odzyskanie statusu, pełne testy i raport raporty/04.md. Bez scalania konkursu.

Konkurs 04 — wynik: PR #96, e1748c7 + ec78736; rzeczywisty LinuxCNC 2.9.10
sim/Xvfb PASS (brak CNC → odczyt → utrata → restart), bez komend i resetu safety.
Pełny Debian: 1039 PASS/10 skip, lint/wymagania/test-c/test-san PASS.
Końcowa prezentacja: 41 PASS + 87 subtestów. Raport `../raporty/04.md`;
świeżość producenta NML 2.9 nadal niepotwierdzona, brak kanału poleceń.
Następny krok: ocena konkursu i host QtVCP/STATUS z globalnymi kontrolkami.
Bez scalania przed wspólną oceną; końcowe kontrole i SHA utrzymywane w PR #96.
