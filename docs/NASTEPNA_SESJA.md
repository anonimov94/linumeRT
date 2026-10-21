# Stan projektu i przekazanie

Tura: Codex · od 2026-10-21 · stan: D38 w toku

Model-Author: Codex. Ostatnie polecenie: sprawdzić stan i dokończyć plan 21–27;
pozostała roadmapa bez nowych sesji.

## Stan scalania

W main są #56 (integracja rozpoczętych prac), #57 (launcher), #58 (kieszenie v2),
#59 (pliki .lnx/edycja kroków) i #60 (podgląd D38, ETA, raport z bieżącym widokiem).
Kod #60: 5f290103, merge 4ba90a0. PR #61 domyka dokumentację odbioru i rejestr sesji 041.
Bieżący wynik scalenia #61 sprawdzać w GitHub; dokument nie deklaruje scalenia przed jego wykonaniem.

## Wynik i granice odbioru

[Raport planu](raporty/prototypy/PLAN-21-27-2026-10-21.md):
Debian 12/LinuxCNC CI 39510750194 PASS — 915 testów + 96 LinuxCNC,
12 subtestów PASS, 9 pominięć. Ogólne CI 39510750346 PASS.
Kieszenie, .lnx, ETA i raport odebrane automatycznie; D38 odebrane wyłącznie jako podgląd.
Rzeczywiste external offsets i automatyczne wznowienie D38 pozostają niewdrożone.
Punkt 27 — próby na pulpicie właściciela — nadal OTWARTY; protokół jest w raporcie.
Nie utożsamiać wyników CI z ręcznym odbiorem pulpitu lub fizycznej obrabiarki.

## Uruchomienie

Pełny bliźniak: `tools/linumert-start.sh`; QtDragon: `--classic`; Plant: `--plant`.
Podgląd offline nie zastępuje pełnego HMI. Skróty i launcher są już scalone.
Nie uruchamiać równocześnie kilku konfiguracji na jednej instancji LinuxCNC.

## Środowisko tej sesji

Chmura, bez pulpitu właściciela i bez lokalnego LinuxCNC. Repo lokalne z poprzednich tur
jest niepełną kopią plików, nie checkoutem Git. Zwykły Git nie łączy się przez proxy;
odczyt i zapis GitHub działają konektorem. Nie ponawiać blokujących prób udostępniania sieci.
Wyniki runtime powyżej pochodzą ze sprawdzonego CI.
Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Bieżące zlecenie — D38 retract/powrót z G41/G42

Właściciel zlecił wykonanie wycofania i powrotu z zachowaniem korekcji narzędzia.
Gałąź codex/pause-retract: pauza AUTO bez Abort, Z przez external offsets; interpreter
zachowuje kolejkę, modalność i G41/G42. Przyciski w Produkcji; powrót czeka na rzeczywiste zero.
Pięć testów lokalnych (model i widgety Qt) OK. Integracja LinuxCNC/Plant i odbiór CI do wykonania.
Nie deklarować obsługi powrotu po Abort/E-STOP ani odbioru sprzętu. Model-Author: Codex.
