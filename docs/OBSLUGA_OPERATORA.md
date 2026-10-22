# Obsługa operatora linumeRT

Model-Author: Codex · wymagania właściciela 2026-10-19.

## Alarmy i Reset

Na samej górze ekranu są trzy wiersze ostatnich alarmów, najnowszy pierwszy.
Historia pozostaje w Diagnostyce. Pojedynczy Reset potwierdza alarmy, których przyczyny ustały.
Podwójny Reset dodatkowo potwierdza zatrzask E-STOP; fizycznie otwarty obwód safety nadal blokuje maszynę.
Symulacja materiału/kolizji raportuje zdarzenia diagnostyczne i nie wysyła E-STOP/STO ani resetu.
Nigdy nie traktujemy braku telemetrii jako symulacji.

## Specjalista

Tryb specjalisty służy do ręcznego wycofania po kolizji. JOG wymaga przytrzymania przycisku,
pracuje domyślnie wolno i ma limit 100 mm/s (6000 mm/min), także po zmianie jednostek.
Nie uruchamia automatycznie programu, wrzeciona ani ruchu MDI. Fizyczne safety, STO, krańcówki
i limity LinuxCNC pozostają nadrzędne. Wirtualny bliźniak pozwala wyjść z kolizji geometrycznej.

## Wartości liczbowe

Wymiary mają cztery miejsca po przecinku (rozdzielczość 0,0001 mm), całkowite kroki
nie dodają ułamkowych reszt. Pole przyjmuje wpis klawiaturą, zatwierdzany Enterem albo zmianą fokusu.
Przecinek lub kropka dziesiętna zależy od ustawień języka systemu.

## Symulacja i wirtualny bliźniak

Pełne HMI korzysta z LinuxCNC jako interpretera i planera. Dostępne są JOG, MDI,
M3/M4/M5, wybór poprzedniego/następnego numeru narzędzia lub wpis numeru i przycisk WYMIANA M6.
Zero detalu ustawia G54–G59. Bliźniak korzysta z konfiguracji machine.yaml i HOME z INI;
Reset symulacji odnawia materiał i wraca do HOME po potwierdzeniu operatora.
Samodzielny podgląd Zero detalu jest edytorem offline, bez ruchu i komend maszyny.

## Pierwszy start

Uruchom `tools/linumert-start.sh`, przejdź do Symulacja i naciśnij
„Uruchom / Reset symulacji → HOME”. Potwierdź odnowienie materiału i bazowanie.
Poczekaj na stan Gotowa, wybierz JOG w górnym pasku. Dla MDI i M6 wymagane jest bazowanie.
Wymianę w konfiguracji wirtualnej potwierdza magazyn symulowany; na fizycznej maszynie
obowiązuje jej procedura ręcznej wymiany/ATC. Zero detalu jest dostępne w szynie obszarów;
„Wczytaj bazę z maszyny” pobiera wybrany G54–G59: aktywny układ ze STATUS,
pozostałe z PARAMETER_FILE bieżącej konfiguracji. Odczyt nie zmienia zer ani nie wykonuje ruchu.

Po kolizji model raportuje położenie i kod diagnostyczny; nie zatrzymuje sterownika.
Operator może zatrzymać program przyciskiem Stop. Specjalista nadal udostępnia ograniczony JOG,
bez obchodzenia fizycznych wejść i limitów. Zakończ specjalistę po wycofaniu.
Zmiana trybu nie włącza komend safety z procesu symulacji.
Zakresy osi LinuxCNC nadal obowiązują, również w symulacji. Klawiatura w specjaliście: 10 mm/s.

`[LINUMERT] VIRTUAL_MODE=1` oznacza konfigurację bez fizycznych wyjść napędów.
Nie ustawiaj tej flagi w konfiguracji podłączonej maszyny. Brak flagi oznacza tryb fizyczny.

## D38 — wycofanie i powrót w pauzie

Produkcja → „Wycofaj Z w pauzie”, „Powrót do ścieżki”, „Powrót i wznów”.
Najpierw wstrzymaj program i poczekaj na zatrzymanie. Wybierz wysokość dodatniego ruchu Z
oraz posuw w mm/min. Wrzeciono pozostaje włączone; to nie jest tryb wymiany narzędzia.
Wycofanie musi mieścić się w zakresie Z. Funkcja jest podłączona w wirtualnym sim/Plant.

Program pozostaje w pauzie AUTO; nie ma Abort, MDI, G40 ani ponownego włączania korekcji.
External offset przesuwa oś Z poza torem interpretera, więc G41/G42 i kolejka ruchu
pozostają zachowane. Powrót prowadzi w Z do tego samego skorygowanego punktu, po czym
„Powrót i wznów” wznawia oryginalny program. Sam „Powrót” pozostawia pauzę.
Nie wykonuje helisy ani zakładki i nie zastępuje podglądu helisy w Symulacji.

Wymagane: zbazowane XYZ/trivkins, G17/G94, stabilna pauza, aktywna korekcja posuwu,
niezmienione narzędzie/układy i włączone wrzeciono. Gwintowanie i cykle są poza zakresem.
Polecenia ruchu QtVCP są blokowane podczas wycofania; wznowienie jest możliwe dopiero,
gdy rzeczywisty i żądany offset Z wynoszą zero. Zmiana programu, narzędzia, modalności,
utrata pauzy lub sprzężenia zwrotnego wstrzymuje operację bez ślepego opuszczania.
Po takim błędzie wyłącz maszynę; poprzednie wznowienie jest anulowane.

Przerwanie programu przez Abort/E-STOP, wymiana narzędzia i odzyskiwanie po wyłączeniu
nie są obsługiwane przez ten mechanizm. NIEZWERYFIKOWANE NA SPRZĘCIE.
Model-Author: Codex.

## Kontrola pętli i szacowanie czasu

„Program” → „Sprawdź składnię” sprawdza zapis G-code, wyrażenia oraz parowanie
`WHILE/ENDWHILE`, `REPEAT/ENDREPEAT`, `IF/ENDIF` bez wykonywania pętli.
Poprawna składnia nie potwierdza zakończenia programu. Porównania w LinuxCNC mają
operatory `EQ`, `NE`, `LT`, `LE`, `GT`, `GE` (np. `[#1 LT 10]`, nie `[#1<10]`).

`o100 while [1]` jest poprawne i może kończyć się przez `o100 break`.
Bez osiągalnego wyjścia pełny czas programu jest nieokreślony. Nie da się rozstrzygnąć
zakończenia każdej pętli na podstawie samego tekstu programu.

„Produkcja” → szacowanie czasu i szacowanie w „Cyklach” analizują program poza wątkiem
ekranu. Analiza ma limit 20 sekund i 8 MiB danych; po przekroczeniu limitu pokazuje
komunikat, bez częściowego czasu i bez potwierdzenia poprawności całego programu.
Limit może też osiągnąć duży, skończony program. Pętle skończone są dozwolone.
Samodzielny interpreter ma osobne pliki robocze i nie współdzieli tabeli narzędzi
z działającym sterowaniem. Model-Author: Codex.

## Historia komunikatów w Diagnostyce

W Diagnostyce filtr poziomu oraz pole wyszukiwania zawężają historię po treści,
kodzie lub dacie. Lista pokazuje do 200 najnowszych pasujących komunikatów;
„Eksport CSV…” zapisuje wszystkie pasujące wpisy (UTF-8, separator średnik).
Czas zawiera datę i strefę czasową komputera. Reset alarmów nie usuwa historii.

Historia zachowuje ostatnie 1000 komunikatów między uruchomieniami. Każdy plik INI
ma osobną bazę w katalogu danych użytkownika: zwykle
`~/.local/share/linumert/diagnostic-<identyfikator>.sqlite3`; dokładna ścieżka jest
w podpowiedzi pod licznikiem wpisów. Przy braku miejsca, uszkodzeniu lub blokadzie
bazy komunikaty pozostają widoczne w pamięci i pojawia się jawna informacja o braku
zapisu. Nie oznacza to zachowania nowych wpisów po zamknięciu ekranu.

Historia opisuje zdarzenia, a nie bieżący stan alarmów ani potwierdzenie usunięcia
awarii. Na małym ekranie Diagnostykę można przewijać. Model-Author: Codex.

## Szukanie narzędzi

Narzędzia → pole wyszukiwania przyjmuje fragment opisu lub danych tabeli, np. `T12`,
`P3`, średnicę albo nazwę typu. Wielkość liter nie ma znaczenia. Obok można wybrać
typ lub „Bez typu”; oba filtry działają razem. Licznik pokazuje liczbę widocznych
narzędzi względem całej bazy. „Wszystkie typy” i puste wyszukiwanie odsłaniają całą listę.
Filtrowanie nie wybiera innego narzędzia, nie zmienia danych w edytorze i nie zapisuje tabeli.
Wybrane narzędzie może zostać ukryte przez filtr; edytor nadal pokazuje jego numer T.
Model-Author: Codex.

Odświeżenie listy po zmianie bazy zachowuje zaznaczenie według numeru T i nie przełącza
edytora na narzędzie, które zajęło poprzedni numer wiersza. Nie nadpisuje niezapisanych
pól, również gdy wybrane T jest ukryte przez filtr. Jeśli T usunięto z bazy, zaznaczenie
znika; pola edytora pozostają do decyzji operatora. Samo odświeżanie niczego nie zapisuje.

## Eksport bazy narzędzi

Narzędzia → „Eksport całej bazy CSV…” zapisuje wszystkie narzędzia z bazy,
również ukryte przez filtry. Niezapisane pola edytora nie trafiają do pliku.
CSV w UTF-8 zawiera parametry geometrii, korekcje, kierunek, oprawki i dane trwałości
w formacie zgodnym z `ToolDB.import_csv`. Nie zawiera historii edycji ani samych
plików STL (tylko ich zapisane ścieżki). Nie jest kopią całej konfiguracji maszyny.
Anulowanie pozostawia dane bez zmian; błąd eksportu wyświetla komunikat.
Operacja nie zmienia tabeli LinuxCNC ani aktywnego narzędzia. Model-Author: Codex.

## Dane narzędzia poza formularzem

Edycja istniejącego T zachowuje parametry tokarskie i korekcje osi inne niż Z,
których formularz nie udostępnia. Oprawka, trwałość i zużycie mają własne pola;
ścieżka STL jest dostępna dla typu specjalnego. „Nowe” zeruje formularz.
Zmiana numeru T przy wypełnionym formularzu używa widocznych wartości. Nowy T
nie przejmuje niewidocznych parametrów tokarskich ani korekcji pozostałych osi.
Model-Author: Codex. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Narzędzie specjalne STL

Po wybraniu typu „Specjalne (STL)” pojawia się wymagane pole „Model STL” i przycisk
„Wybierz…”. Można też wpisać ścieżkę ręcznie. Anulowanie wyboru nie czyści pola;
„Nowe” zaczyna bez ścieżki poprzedniego narzędzia. „Zapisz” korzysta z dotychczasowej
walidacji oraz bazy narzędzi. Zapisywana jest ścieżka, bez kopiowania pliku i bez
sprawdzania poprawności siatki. Model powinien mieć oś Z i czoło w 0.

Obecna symulacja nadal używa walca zastępczego, również po wskazaniu STL.
Nie potwierdza to zgodności kolizji z rzeczywistą bryłą pliku. Przy małym oknie
edytor można przewijać pionowo; długie wiersze formularza zawijają się.
Model-Author: Codex.

## Gdy tabela narzędzi nie daje się zapisać

Brak statusu LinuxCNC blokuje „Zapisz” i „Usuń”, tak samo jak trwający program.
Powód pojawia się w edytorze i alarmach. Błąd zapisu pliku lub bazy również jest
pokazywany; po nim ekran nie wysyła przeładowania tabeli do CNC.

Baza narzędzi może już zawierać zmianę, mimo że zapis `tool.tbl` nie powiódł się.
Dotyczy to również usunięcia rekordu. Przed dalszą pracą sprawdź bazę i `tool.tbl`,
usuń przyczynę błędu i uzgodnij tabelę z LinuxCNC. Komunikat błędu nie potwierdza
wycofania zmiany ani synchronizacji z CNC. Model-Author: Codex.
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Historia zmian narzędzia

Narzędzia → „Historia T…” otwiera historię numeru T widocznego w edytorze.
Działa również po usunięciu narzędzia z bazy. Lista pokazuje do 100 ostatnich wpisów,
najnowsze na górze: czas UTC, dodanie/zmianę/usunięcie/import i źródło.
Wybór wpisu pokazuje wyłącznie zmienione pola w kolumnach „Przed” i „Po”.
„—” oznacza brak wartości. Zamknij i otwórz ponownie, aby odświeżyć podgląd.

Jest to historia bazy, nie potwierdzenie zapisania `tool.tbl` ani wczytania tabeli
przez LinuxCNC. Pomaga porównać dane po błędzie zapisu, ale nie przywraca zmian
i nie wysyła komend CNC. Nieznany T pokazuje pustą historię, a błąd odczytu lub
uszkodzony wpis — komunikat. Model-Author: Codex.

## Oprawka i ręczne dane trwałości

W edytorze narzędzia można podać nazwę/typ oprawki, planowaną trwałość oraz zużycie
w minutach. W „Trwałość planowana” wartość 0/„—” oznacza brak ustalonego planu.
Zużycie 0 jest poprawną wartością. Dane odczytują się z bazy; dopiero „Zapisz” je utrwala.
„Nowe” zaczyna bez oprawki i planu, z zużyciem 0.

Zużycie jest wpisem ręcznym: ten widok nie nalicza automatycznie minut obróbki.
Przekroczenie planowanej trwałości nie blokuje programu. W bazie i imporcie CSV
trwałość musi być dodatnią skończoną liczbą albo pusta, a zużycie skończoną liczbą
nieujemną. Nieprawidłowe dane są odrzucane bez zmiany rekordu. Model-Author: Codex.

## Niepoprawne dane przy imporcie i eksporcie narzędzi

Średnica i korekcje muszą być skończonymi liczbami, a średnica nieujemna.
Parametry tokarskie I/J są liczbami skończonymi; orientacja Q musi być całkowita
w zakresie 0…9. Wartość Q2.5 jest odrzucana, nie zaokrąglana. Pola JSON parametrów,
korekcji i tokarki muszą zawierać obiekty z nazwami pól, nie listy ani wartości null.

Błędny import CSV nie zapisuje części wsadu. Eksport `tool.tbl` sprawdza również
rekordy już istniejące w bazie; odmowa walidacji pozostawia dotychczasowy plik
bez zmian. Przy odmowie z HMI nie następuje przeładowanie tabeli CNC; odczytaj
komunikat i popraw dane przed dalszą pracą. Model-Author: Codex.
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Korekcja średnicy a tabela LinuxCNC

Dla narzędzia z nominalnym parametrem d eksportowana średnica D wynosi d + korekcja
średnicy (`d_wear`). Przykład: 6 mm i −0,02 mm dają D=5,98 mm, czyli promień 2,99 mm
używany przez G41/G42. Korekcja dotyczy średnicy, więc zmiana promienia jest dwukrotnie
mniejsza. Bez nominalnej geometrii zwykłe pole D pozostaje wartością tabeli.

Niezerowa korekcja wymaga nominalnego d; średnica po korekcji musi być dodatnia.
Przy imporcie `tool.tbl` D jest już wartością po korekcji: zachowana korekcja jest
odejmowana, aby wyliczyć nominalne d. Powtarzanie importu nie dolicza jej ponownie.
Eksport/import tabeli dla maszyny calowej przelicza wartości z bazy w mm; dokładność
zapisu to sześć miejsc po przecinku w jednostce tabeli. Model-Author: Codex.
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Jednostki bazy i tabeli narzędzi

Baza narzędzi i pola długości edytora są w mm. Plik `tool.tbl` jest odczytywany
i zapisywany w jednostkach `[TRAJ]LINEAR_UNITS` z INI: mm albo inch. Dotyczy to
pierwszego importu, utworzenia tabeli z danych startowych oraz „Zapisz” i „Usuń”.
Kąty A/B/C i I/J nie są skalowane. Podpowiedź licznika tabeli podaje jej jednostkę.
Przykład: D0.25 i Z2 w tabeli calowej odpowiadają D=6,35 mm i Z=50,8 mm w bazie.

Nieznane jednostki powodują odmowę przed zapisem, zamiast założenia mm.
Przy braku ustawienia jednostek pozostaje dotychczasowy domyślny mm.
Proces symulacji również normalizuje długości do mm, zgodnie z opisem poniżej.
Pełny ręczny odbiór maszyny calowej pozostaje osobnym punktem. Model-Author: Codex.
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Jednostki procesu symulacji na żywo

Pozycja XYZ, początek przygotówki z WCS oraz długość i średnica narzędzia z tabeli
LinuxCNC są przeliczane z jednostek maszyny na mm. Modele maszyny, przygotówka,
widok i ślad końcówki używają wspólnych wartości fizycznych; 1 cal odpowiada 25,4 mm.
Nie trzeba zmieniać wymiarów modelu ani przygotówki po zmianie profilu mm/inch.
Jednostkę określa `TRAJ/LINEAR_UNITS`, a nie bieżące G20/G21 programu.

Nieznane jednostki zatrzymują uruchomienie procesu symulacji z komunikatem błędu.
Nie jest to blokada ruchu ani polecenie E-STOP. Testy porównują geometrię i usuwany
materiał, lecz nie zastępują ręcznego odbioru calowego HMI/obrabiarki.
Model-Author: Codex. NIEZWERYFIKOWANE NA SPRZĘCIE.
