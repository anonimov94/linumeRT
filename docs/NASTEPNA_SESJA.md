# Stan projektu i przekazanie

Tura: Codex · od 2026-10-21 · stan: praca nad planem 21–27

Model-Author: Codex. Bieżące polecenie właściciela: dokończyć rozpoczęte prace,
bez rozpoczynania nowych sesji roadmapy; po scaleniu launcher i lista usterek na tydzień.
Następnie właściciel polecił kontynuować realizację planu 21–27, także bez odpowiedzi,
aż do wyraźnego „stop”. Zakres tej listy jest autoryzowany; pozostała roadmapa pozostaje zamrożona.

## Odbiór integracji

PR #56 łączy #48, #50, #54, #55 i #56 oraz niescalone Cykle Claude (7a71581).
Zachowana historia wszystkich gałęzi, również historyczna aktualizacja codex/hmi-01.
Kod 4ca3f57: pełne CI PASS — Debian 12: 849 testów + 81 LinuxCNC, C: 108 także z ASan/UBSan,
42 kroki HMI, scenariusze 9 + matrix 5, wymagania bez błędów. Raport: [P0](raporty/prototypy/P0-2026-10-20.md).
PR #56 scalony do main (e3c7bab); wcześniejsze PR automatycznie oznaczone jako scalone.

Działają: ekrany HMI, edycja kopii G-code, diagnostyczna symulacja bez komend safety,
audyt deklaracji/HAL offline, generatory, raport HTML, narzędzia/czas/NgcGui w Cyklach.
Kieszenie: rozwijane wejście rampą i helisą w ramach 21.10; sesja 041 pozostaje częściowa.
Nie deklarować odbioru sprzętu ani ręcznych prób na pulpicie właściciela.

## Następny dozwolony krok

Launcher HMI + QtDragon + LinuxCNC gotowy; testy uruchamiania przechodzą, skróty zainstalowane.
Launcher #57 scalony (1fd6f3e), Debian PASS: 853 + 81 LinuxCNC. Kieszenie 21–22 w #58,
.lnx/edycja 23 w #59 — odbiór CI w toku. Lokalnie przygotowano podgląd D38 (24, wykonanie
nadal otwarte) oraz ETA i pomiar Plant (25); kolejne: raport 26 i odbiór 27. Każdą zakończoną porcję
testować i scalać do main; nie deklarować niewykonanego odbioru ręcznego jako zaliczonego.
Lista i kryteria: [21–27.10.2026](PLAN_TYGODNIA_2026-10-21.md). Odbiór pulpitu pozostaje otwarty.
Nie zaczynać nowych sesji 027…084. Porządkowy job usuwa tylko gałęzie zawarte w main,
z lease dla ich SHA, po zielonym CI main. Autokontrola, bez niezależnego przeglądu.

## Środowisko

Pełny bliźniak: tools/linumert-start.sh; QtDragon: --classic; Plant: --plant.
Ta sesja lokalna blokuje sieć, pulpit, Podman i LeakSanitizer; wynik runtime pochodzi z CI.
Podgląd Qt offscreen działa. Lokalna tabela narzędzi /home/dell/linumeRT pozostawiona użytkownikowi.
