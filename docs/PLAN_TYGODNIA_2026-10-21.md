# Lista do wykonania: 21–27 października 2026

Model-Author: Codex. Polecenie właściciela: dokończyć rozpoczęte prace; nie zaczynać nowych sesji.
Ta lista obejmuje braki w już rozpoczętych obszarach. Właściciel następnie polecił realizować
plan 21–27 bez czekania na odpowiedź, aż do „stop”. Stan początkowy zapisano w tabeli;
wyniki dopisywane są poniżej po testach. Nie dodano rowków, konturów ani nowych kamieni roadmapy.

| Termin | Priorytet | Funkcja i stwierdzony stan | Jak odtworzyć / dowód | Kryterium ukończenia |
|---|---|---|---|---|
| 21.10 | P1 | Kieszenie: rampa i helisa niezaimplementowane | Cykle → kieszeń; formularz i generator obsługują wyłącznie wejście pionowe | Jawny wybór wejścia, walidacja geometrii, golden, rs274, materiał i Plant; brak niekontrolowanego zagłębiania |
| 22.10 | P1 | Kieszenie: obrót, zadany promień naroży, kierunek skrawania, naddatki i wykańczanie niezaimplementowane | Brak parametrów w `PocketRect/PocketCircle.fields`; sesja 041 pozostaje częściowa | Parametry działają w podglądzie i G-code; testy granic i objętości oraz odbiór LinuxCNC/Plant |
| 23.10 | P1 | Cykle: brak otwierania/zapisu .lnx i edycji wybranego kroku | Widok ma dodawanie i usuwanie ostatniego kroku oraz zapis .ngc; ograniczenie opisane w module | Zapis/wczytanie .lnx bez utraty danych, edycja wybranego kroku i ponowna walidacja narzędzi |
| 24.10 | P1 | D38: wycofanie w pauzie i powrót po helisie/łuku niezaimplementowane | Jest projekt `design/WZNOWIENIE.md`; brak `programs/resume.py` i przycisków tej operacji | Pierwsza działająca porcja zgodna z projektem: podgląd, symulacja, blokady i testy; nie utożsamiać ze zwykłym Pause/Resume, które przechodzi test |
| 25.10 | P2 | Czas obróbki: brak czasu pozostałego i kalibracji względem Plant | „Szacuj czas” działa; wynik jest górnym oszacowaniem ze stopem w narożach | Porównanie czasów z Plant, opis błędu modelu i widoczny czas pozostały; zmiana programu unieważnia wynik |
| 26.10 | P2 | Raport symulacji: zrzut widoku 3D niepodłączony do eksportu z HMI; oś czasu częściowa | Przycisk Raport wysyła ścieżkę; HTML ma mapę z góry, nie zrzut widoku operatora | Eksport zrzutu bieżącego widoku i zgodnej osi zdarzeń; test faktycznego kliknięcia oraz poprawności pliku |
| 27.10 | P1 | Launcher i HMI na pulpicie właściciela: odbiór ręczny niewykonany z sesji agenta | Sandbox blokuje Podman, gniazda i pulpit; skróty zainstalowane, parser systemowy i tryby testowane automatycznie | Uruchomić HMI/Plant/QtDragon ze skrótów, bazowanie, JOG, MDI, M3/M5/M6, program, raport i zamknięcie; dołączyć zrzuty i ponowić regresję |

Dodatkowa otwarta część PR #48: deklaracje i audyt HAL są offline. Bramka startu/eksportu
dla konfiguracji hardware oraz fizyczne I/O wymagają osobnego odbioru sprzętowego.
Nie są objęte wynikiem symulatora ani obietnicą uruchomienia w tym tygodniu bez sprzętu.

Odbiór zamkniętej porcji: [raport P0](raporty/prototypy/P0-2026-10-20.md).
Przetestowane: HMI (42 kroki), edytor G-code, podstawowe generatory, prototypy kieszeni,
walidacja narzędzi, szacowanie czasu, eksport podprogramów, LinuxCNC/Plant/VFD i watchdogi.
Kolizje materiału są diagnostyczne, zgodnie z poleceniem właściciela z 20.10; brak E-STOP
z procesu symulacji jest zamierzonym zachowaniem, a nie usterką.

Realizacja 21.10: wejście `plunge/ramp/helix` i kąt w formularzu, automatyczna geometria
wewnątrz kieszeni, limit 20 000 bloków. Helisa o średnicy nie większej niż D frezu
nie pozostawia rdzenia. Rampa i helisa schodzą od powierzchni / poprzedniej warstwy
posuwem zagłębiania; podgląd XY pokazuje wejście. Golden, objętość, geometria i Plant
sprawdzane automatycznie; odbiór rs274 w CI jest wymagany przed scaleniem.

Realizacja 22.10: obrót prostokąta, promień naroża (0 oznacza minimalne D/2), CW/CCW,
naddatki ścian/dna i jawne wykańczanie z oddzielnym posuwem. Bez wykańczania naddatki
pozostają. Wykańczanie ścian jest wykonywane warstwami, a dna pełną ścieżką na końcu;
naddatek dna nie może przekroczyć kroku Z. Kierunek dla kieszeni i M3: CCW współbieżny,
CW przeciwbieżny ([przykład producenta narzędzi](https://videos.sandvik.coromant.com/cost-effective-solutions-for-face)).
Test materiału sprawdza objętość, całe dno i brak cięcia poza obrysem. Odstęp prostokątnych
pierścieni uwzględnia również przekątną, aby nie zostawiać wysp przy 90% kroku bocznego.
CI obejmuje wykonanie obu kieszeni z helisą i wykańczaniem na LinuxCNC + Plant.
Nowa geometria jest wersją 2 generatorów. Wersja 1 w rejestrze pozostaje niezmienna,
a golden sprawdza G-code istniejących programów. Punkty 21–22 odbierane są wspólnym PR.

Realizacja 23.10: lista kroków, „Zmień wybrany”, „Otwórz .lnx…” i „Zapisz .lnx…”.
Zapis atomowy, bez utraty komentarzy, przygotówki, jednostek, wyłączonych kroków i wersji.
Nieznany generator/wersja, błędny JSON albo parametry odrzucają otwarcie bez naruszenia
bieżącego programu. Edycja ponawia kontrolę narzędzi i unieważnia czas; eksport .ngc
używa wspólnego kompilatora. Testy przycisków Qt i roundtrip wykonywane automatycznie.
