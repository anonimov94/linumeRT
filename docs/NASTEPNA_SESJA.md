# Stan projektu i przekazanie

Tura: Codex · od 2026-10-20 · stan: w toku

Model-Author: Codex. Bieżące polecenie właściciela: dokończyć rozpoczęte prace,
bez rozpoczynania nowych sesji roadmapy; po scaleniu launcher i lista usterek na tydzień.

## Odbiór integracji

PR #56 łączy #48, #50, #54, #55 i #56 oraz niescalone Cykle Claude (7a71581).
Zachowana historia wszystkich gałęzi, również historyczna aktualizacja codex/hmi-01.
Kod 4ca3f57: pełne CI PASS — Debian 12: 849 testów + 81 LinuxCNC, C: 108 także z ASan/UBSan,
42 kroki HMI, scenariusze 9 + matrix 5, wymagania bez błędów. Raport: [P0](raporty/prototypy/P0-2026-10-20.md).
Ostatni commit uzupełnia wyłącznie dokumentację wynikami; scalenie w toku.

Działają: ekrany HMI, edycja kopii G-code, diagnostyczna symulacja bez komend safety,
audyt deklaracji/HAL offline, generatory, raport HTML, narzędzia/czas/NgcGui w Cyklach.
Kieszenie są prototypem wejścia pionowego; sesja 041 pozostaje częściowa.
Nie deklarować odbioru sprzętu ani ręcznych prób na pulpicie właściciela.

## Następny dozwolony krok

Launcher HMI + QtDragon + LinuxCNC, test uruchamiania, lista braków na 21–27.10.2026.
Nie zaczynać nowych sesji 027…084. Porządkowy job usuwa tylko gałęzie zawarte w main,
z lease dla ich SHA, po zielonym CI main. Autokontrola, bez niezależnego przeglądu.

## Środowisko

Pełny bliźniak: tools/linumert-start.sh; QtDragon: --classic; Plant: --plant.
Ta sesja lokalna blokuje sieć, pulpit, Podman i LeakSanitizer; wynik runtime pochodzi z CI.
Podgląd Qt offscreen działa. Lokalna tabela narzędzi /home/dell/linumeRT pozostawiona użytkownikowi.
