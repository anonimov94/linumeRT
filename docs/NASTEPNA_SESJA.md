# Stan projektu i przekazanie

Tura: Codex · od 2026-10-20 · stan: w toku

Model-Author: Codex, aktualizacja Claude (koniec 2026-10-19). Bieżący stan jest w tym pliku; historia w DZIENNIK.md.
Zasady: [WSPOLPRACA_MODELI.md](WSPOLPRACA_MODELI.md), kontrakt operatora:
[OBSLUGA_OPERATORA.md](OBSLUGA_OPERATORA.md), D36/D37.

## Wykonane HMI

Start, Maszyna, Bazowanie, Zero detalu 3D (prostopadłościan, walec, rura, odlew 360°),
Narzędzia, Program (wybór/podgląd/wczytanie), Symulacja, Produkcja, Diagnostyka.
Trzy ostatnie alarmy u góry; Reset zachowuje aktywne przyczyny, podwójny potwierdza zatrzask HAL.
Pola wymiarów: 4 miejsca po przecinku, wpis ręczny. JOG/MDI, M3/M4/M5,
wybór T i WYMIANA M6 w Maszyna i Symulacja. Wirtualna wymiana potwierdza handshake HAL.
Specjalista: wolny JOG, maks. 100 mm/s; klawiatura 10 mm/s bez przyspieszania Shiftem.
Wycofanie z kolizji geometrycznej tylko w jawnym bliźniaku i trybie MANUAL.
Reset symulacji odnawia materiał i bazuje do HOME z INI. Fizyczne safety i limity pozostają aktywne.

## Git i testy

PR #44 scalony; #45: integracja Symulacji/Narzędzi Claude. #46: zintegrowany zakres HMI Codex.
Zmiany #46 wypychane po małych testowanych krokach, z zachowaniem poprawki Claude 8b2bc17.
Testy Debian 12: widgety, geometria, model, symulacja, kontrakt HAL, IP i wymagania przechodzą.
Pełny lokalny pytest ograniczony blokadą gniazd sieciowych (EPERM); wynik sieci/LinuxCNC daje CI.
Samotest pełnego HMI ma 42 kroki, w tym MDI/M3/M5/M6 w Symulacji. Przed merge sprawdź oba workflow.
Nie uznawaj otwartego podglądu offline za uruchomione pełne HMI.

## Uruchomienie

- Pełny bliźniak: `tools/linumert-start.sh` (Debian 12 w Podmanie, LinuxCNC).
- Edytor offline: `bash tools/dev/preview-zero.sh` — bez CNC, zapis tylko tymczasowy.
- Lokalnie Codex: `/home/dell/Projekty/linumeRT-codex-hmi`; Claude: osobny checkout.
- Sandbox Codexa blokuje sieć i dostęp do pulpitu; nie omijaj ograniczeń. GUI podglądu sprawdzamy offscreen.
- Testy: `tools/dev/debian-container.sh make lint test test-c test-san`; pełne CNC przez CI/środowisko Claude.

## Dalej

1. Scalić PR #47 po zielonym CI (Cykle, Program: Sprawdź/Edytuj, E-STOP dwukanałowy NC, generatory, STL, D38).
2. **D38 wznowienie obróbki**: `core/linumert/programs/resume.py` (punkt wejścia z zakładką, helisa, łuk),
   sprawdzenie w `linumert_sim`, external offsets dla pauzy, przyciski w HMI ([`design/WZNOWIENIE.md`](design/WZNOWIENIE.md)).
3. Raport HTML symulacji i oś czasu zdarzeń (059, 057); walidacja generatorów z bazą narzędzi (040).
4. Usunąć scalone gałęzie (limit właściciela: 5 gałęzi, 2 PR; Claude ma usuwanie zablokowane).
5. Dalszy plan: `prompts/README.md` (stan częściowy 040, 042, 055–059 oznaczony); weryfikacja sprzętu — właściciel.

## Audyt safety — 2026-10-20, PR #48 (Codex, sesja chmurowa)

Polecenie właściciela: PC w torze zezwolenia; symulacja bez safety. Audyt:
[bezpieczenstwo/README.md](bezpieczenstwo/README.md). Etap 1 na codex/safety-separation:
kontrakt wypchnięty c528144, proces symulacji bez komend CNC d8d5fda; 3 unittest lokalnie OK.
Dla Claude: przejrzeć #48 i CI; nie przywracać E-STOP z procesu materiału/kolizji przy integracji #47.
Zakres usunięcia emulacji w Plant czeka na odpowiedź właściciela; nie zmieniono jego łańcucha.
Następnie jawny profil sprzętowy i kontrakt I/O/nadzoru PC; brak gotowej konfiguracji hardware.
Stan zatrzymania: dokumentacja i pierwszy krok kodu wypchnięte, pełny odbiór Debian 12/GUI przez CI
oraz środowisko lokalne. LOCK pusty; bez lokalnej instancji LinuxCNC.

### Kolejny krok roadmapy safety — 2026-10-20

PR #48: deklaracje profili i walidator CLI (92df198), bez podłączenia do startu CNC/eksportu.
Przykład config/hardware/safety-contract.ini.example ma puste piny i jest celowo odrzucany.
CI b626235: ogólne OK, LinuxCNC 68/69 — samotest naciskał M3 przed odświeżeniem interp HMI.
Poprawka synchronizacji i regresja: 6047a13; zachowane interlocki. Lokalnie 9 nowych unittest OK.
Dla Claude: przejrzeć PR #48; wynik CI dla finalnego SHA, potem integracja kontroli na granicy
startu profilu hardware i analiza rzeczywistych połączeń I/O. Plant nadal czeka na określenie zakresu.
Stan zatrzymania: krok wypchnięty; żadnej deklaracji odbioru sprzętu. LOCK pusty.

### Zadania offline — 2026-10-20, Codex

Właściciel: wykonywać możliwe punkty bez LinuxCNC, kolejność dowolna.
PR #48: audyt tekstowych HAL 18b612e i CLI --hal-from-ini/--hal 2055611.
Lokalnie 19 nowych unittest OK. Narzędzie nie uruchamia HAL, nie kwalifikuje sprzętu.
Dalej: CI/review tego SHA; ewentualna integracja kontroli na granicy startu hardware,
rozszerzenie analizy grafu i dalsze funkcje offline. Protokół ODBIOR.md pozostaje pusty.
Zakres Plant nadal nierozstrzygnięty; jego watchdogi i tor HAL nie zmienione.
Stan zatrzymania: kod/testy/dokumentacja wypchnięte; LOCK pusty.

## Stan zatrzymania — interpreter, PR #49 · 2026-10-20

Model-Author: Codex. Właściciel zlecił kontynuację niezależnych zadań w chmurze bez PC.
`03591cf`: cytowanie ścieżek RIP/G-code, exec i kontrola kodu procesu; 4 testy lokalne OK.
CI w toku; osobna gałąź od main, niezależna od safety PR #48. Następny krok: odbiór CI.

Aktualizacja 2026-10-20: PR #48 cc4ec133 — CI 342 i LinuxCNC 96 SUCCESS.
PR #49 scalony do main (7243acc); tutaj włączony z zachowaniem obu zestawów dokumentacji.
Dla Claude: autokontrola PR #48/#49 bez niezależnego przeglądu; potrzebny przegląd wsteczny.

Integracja z main 1987f28 (#47/#53): eksport STL/HTML i SimLog zachowane, symulacja diagnostyczna.
Trzy testy diagnostyki po scaleniu OK. Właściciel ponownie zlecił kontynuację; CI nowego SHA w toku.
