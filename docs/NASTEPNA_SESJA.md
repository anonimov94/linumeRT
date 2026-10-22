# Stan projektu i przekazanie

Tura: Codex · od 2026-10-21 · stan: oddana po synchronizacji EndeavourOS

Model-Author: Codex. Bieżące polecenie właściciela: sprawdzić rozpoczęte prace,
dokończyć, wypchnąć i scalić zmiany oraz zaktualizować kopię na EndeavourOS.
Bez otwierania kolejnych etapów roadmapy.

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
