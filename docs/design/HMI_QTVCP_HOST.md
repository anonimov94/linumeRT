# HMI inspirowane skórkami — pierwszy host QtVCP

Model-Author: Codex · 2026-10-25. Kod de6b06d. Odbiór prowadzi Claude na
laptopie EndeavourOS, zgodnie z bieżącym poleceniem właściciela.

Skórki są kierunkiem wizualnym; nie wymagamy odwzorowania obrazów 1:1 ani
czterech kompletnych aplikacji. Ten krok montuje istniejące komponenty prezentacji
w działającym hoście QtVCP. Docelową kompozycję rozwijamy według zadań operatora.

## Co jest zaimplementowane

- Widok HMI wybierany w obszarze Wygląd; zapis jest stosowany przy kolejnym starcie.
  Przy braku zapisu pozostaje dotychczasowy widok. Zmienna środowiskowa może jawnie
  nadpisać wybór w odizolowanej próbie odbioru.
- Stan z istniejącego STATUS QtVCP; bez drugiego procesu odczytu NML.
- G53 w mm/°, bieżące okno kodu programu i alarm z istniejącej powłoki.
- Start/Wstrzymaj/Stop przez istniejące przyciski hosta. Ponowny odczyt przed
  kliknięciem, istniejące bramki modelu i aktywność przycisków; błąd odczytu blokuje
  konsolę. Bez nowych wywołań ACTION lub pinów HAL.
- Stałe globalne alarmy, E-STOP/watchdog, tryby i sterowanie ręczne pozostają
  własnością powłoki. Grzyb wewnątrz inspiracyjnej konsoli jest opisowym wskaźnikiem;
  działający grzyb jest na stałym pasku hosta.
- Nawigacja nagłówka prowadzi do istniejących stron Program/Narzędzia/Diagnostyka/
  Wygląd/Maszyna, z dotychczasowymi uprawnieniami. Konfiguracja pozostaje na szynie hosta. Zmiana rodziny wyłącznie
  przy kolejnym starcie; nie włączono przełączania kompozycji w czasie ruchu.
- Classic korzysta z istniejącego asynchronicznego loadera ścieżki i sceny Neon.
  Pozostałe niepodłączone sceny zachowują jawny komunikat, bez demonstracyjnej
  trajektorii udającej wykonanie maszyny.

## Uruchomienie do odbioru Claude

Gałąź `codex/skin-qtvcp-host` zawiera także pomocniczą poprawkę kart z #161.
Uruchomić w oddzielnym checkoutcie i istniejącym środowisku LinuxCNC, z zachowaniem
obecnych procedur współdzielonych zasobów. Odbiór selektora: uruchomić normalnie poniższym poleceniem, wejść w Wygląd →
Widok HMI, wybrać rodzinę i zapisać. Zamknąć oraz ponownie uruchomić HMI zgodnie
z dotychczasową procedurą stanowiska. Zapis sam nie restartuje żadnego procesu.

```sh
./tools/linumert-start.sh --no-update
```

Ustawienie jest w `~/.config/linumert/operator-view.json` (osobno od palety), ścieżkę
można izolować zmienną `LINUMERT_OPERATOR_PREFERENCES`. Niepoprawny/brakujący plik
zachowuje dotychczasową powłokę. Opcja „Dotychczasowy widok” pozwala do niej wrócić.

Przykład jawnego nadpisania wyboru dla pojedynczej próby sim:

```sh
LINUMERT_OPERATOR_SKIN=classic-digital \
LINUMERT_OPERATOR_THEME=neon-punk \
./tools/linumert-start.sh --no-update
```

Alternatywy rodziny: industrial-pro, cyberdeck, organic-vector. Język jest pobierany
z INI przez istniejący host. Bez zmiennej rodziny launcher używa wyboru zapisanego w GUI. Brak wyboru zachowuje powłokę.
Nie używać `--skin`: ta historyczna opcja uruchamia osobny podgląd/monitor.

## Zakres odbioru

1. Start sim bez wyjątków, HMI obecne; globalny E-STOP i alarmy widoczne również
   po powiększeniu panelu. Odtworzyć/porównać timeout E-STOP zapisany w raporcie #161.
2. G53/znak/jednostki i brak nieistniejących osi; załadowany plik i jego linie,
   zmiana programu/wyładowanie. Brak przykładowego programu w live.
3. Start, pauza, Stop i odmowy w E-STOP/bez bazowania/bez programu; brak podwójnych
   komend. Utrata statusu blokuje konsolę, globalny tor zatrzymania pozostaje dostępny.
4. Nawigacja bez ruchu; dostęp do istniejących narzędzi/diagnostyki/konfiguracji
   z uprawnieniami. Wpis i Tab, brak utraty zmian.
5. Ścieżka Classic/Neon na rzeczywistym programie; pozostałe sceny uczciwie opisane.
   Rozmiary 1280×800 i 1920×1080, czytelność i cele dotykowe.
6. Pełne lint/test i właściwe próby LinuxCNC; zrzuty i wyniki do raportu.

## Stan weryfikacji

Wykonano przegląd kodu i parsowanie składni dwóch zmienionych modułów. Nowego hosta
nie uruchamiano i nie testowano lokalnie — odbiór powierzony Claude. Nie jest to
ukończenie SKIN-02/04/05/06 ani sesji 028. Bez nowych zależności. NIEZWERYFIKOWANE
NA SPRZĘCIE. Nie scalać na podstawie samych wcześniejszych testów pomocniczego układu.


## Odbiór Claude i poprawka selektora — 2026-10-25

Komentarz PR #163 z 17:53 UTC: bab3866 startuje na laptopie EndeavourOS w
Classic Digital; make lint PASS, 1359 testów offline PASS / 110 pominiętych,
check_requirements PASS. Brak selektora był zgłoszoną luką; pozostałe trzy rodziny
nie były wtedy odebrane wizualnie. To nie jest pełny odbiór wszystkich funkcji.

Kod 9167442 dodaje selektor w Wyglądzie oraz zapis przy następnym starcie.
Nowy zakres: wybrać każdą rodzinę z GUI, zapisać, ponownie uruchomić, sprawdzić
rzeczywistą rodzinę/DRO/program/konsolę i wrócić do dotychczasowego widoku.
Sprawdzić błąd zapisu, uszkodzony plik, pierwszeństwo jawnej zmiennej i brak
przełączenia/komend maszyny podczas zapisu. Parsowanie składni PASS; GUI i testy
nowej wersji powierzono Claude, bez ponawiania lokalnych prób przez Codex.


## Nawigacja rodzin — krok 7dc2649

Po potwierdzeniu selektora 2ae9103 przez Claude dodano odmienne malowanie szyny
na wszystkich stronach hosta: Classic ma cyfrową typografię i podkreślenie,
Industrial ramy z gradientem i lampką, Cyberdeck cięte naroża i wersaliki,
Organic obłe kształty i łuk. Pozostają natywne QToolButton i istniejące połączenia
nawigacji. Fokus ma własny widoczny obrys. Ramy stałych pasków i promienie klawiszy
trybu dopasowują się do rodziny; nie zmieniono osobnych selektorów E-STOP/alarmów.
Paleta nawigacji korzysta z tego samego słownika kolorów co istniejąca powłoka.

Do odbioru Claude: każda rodzina na 1280×768 i 1920×1080, widoczność różnic,
pełne etykiety i fokus Tab, kliknięcia wszystkich obszarów, zmiana palety i powrót
do dotychczasowego widoku. Składnia/diff sprawdzone; nowej wersji nie uruchamiano.
Rozszerzenie HMI-OWNER-SKINS obejmuje również pełną kompozycję nakładki i dwa
prostokątne podglądy symulacji. Ten krok ich nie implementuje ani nie zalicza.

## Dopasowanie do małego ekranu — 2026-10-26

Osadzony widok korzysta ze stałego nagłówka, alarmów, trybów i paska akcji QtVCP.
Powtórzony nagłówek i konsola studium skórek są ukryte w hoście, dzięki czemu dolne
karty nie wychodzą poza ekran. Monitor samodzielny zachowuje własne paski.
Regresja składa cztery rodziny z rzeczywistym Qt, zmienia 1280×768 → 1920×1080
→ 1280×768 i wymaga braku przewijania całej strony oraz widoczności wszystkich kart.
5 testów PASS, sprawdzony zrzut Classic Digital; odbiór live osobno.

## Odczyty monitora — 2026-10-26

F pokazuje rzeczywistą prędkość toru (`current_vel`, mm/min), S zadane obroty
(`spindle[0].speed`, rpm; nie jest to sprzężenie tachometru). T pochodzi z
`tool_in_spindle`, D i L z tabeli narzędzi; L oznacza podpisany offset Z z tabeli.
Po utracie statusu wartości są czyszczone. Program pochodzi z pliku wczytanego
przez loader ścieżki; aktywna linia jest zaznaczona według `motion_line`.
Cyberdeck korzysta z tej samej sceny Neon co Classic; widok XYZ jest poglądowy.
