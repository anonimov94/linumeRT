# Stan projektu i przekazanie

Tura: Codex · od 2026-10-21 · stan: D38-A, odbiór w PR #62

Model-Author: Codex. Bieżące polecenie: wykonać retract i powrót do toru z zachowaniem G41/G42.
Bez otwierania kolejnych etapów roadmapy.

## Stan scalania

W main są #56 (integracja rozpoczętych prac), #57 (launcher), #58 (kieszenie v2),
#59 (pliki .lnx/edycja kroków) i #60 (podgląd D38, ETA, raport z bieżącym widokiem).
Kod #60: 5f290103, merge 4ba90a0. #61 scalony do main (f4b7552f).
Bieżąca realizacja pauzy D38-A: [PR #62](https://github.com/anonimov94/linumeRT/pull/62).
Stan scalenia, sprawdzony SHA i końcowe wyniki CI są w tym PR.

## Wynik i granice odbioru

[Raport planu](raporty/prototypy/PLAN-21-27-2026-10-21.md):
Debian 12/LinuxCNC CI 39510750194 PASS — 915 testów + 96 LinuxCNC,
12 subtestów PASS, 9 pominięć. Ogólne CI 39510750346 PASS.
Kieszenie, .lnx, ETA i raport odebrane automatycznie; D38 odebrane wyłącznie jako podgląd.
Raport opisuje stan przed PR #62: external offsets i wznowienie w pauzie dodaje D38-A.
Odzyskiwanie po Abort/E-STOP i wykonanie helisy z zakładką nadal pozostają niewdrożone.
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
Sześć testów lokalnych (model i rzeczywiste widgety Qt) PASS. Testy runtime używają
prawdziwego QtVCP/LinuxCNC, sim i Plant oraz G40/G41/G42 w G20/G21 z G43.
Wyniki, pozycje i zrzuty są w CI wskazanym w PR #62; nie utożsamiać obecności testu z jego PASS.
Nie deklarować obsługi powrotu po Abort/E-STOP ani odbioru sprzętu. Model-Author: Codex.

Przed pierwszą zmianą counts kontroler czeka na potwierdzenie enable z pętli HAL.
Wznowienie wymaga rzeczywistego i żądanego offsetu zero oraz błędu nadążania <=0,005 mm.
Dostępność: zbazowane XYZ/trivkins, G17/G94, aktywna korekcja posuwu i wrzeciono włączone.
W Plant test najpierw czeka na łącze i ustalenie sprzężenia przed bazowaniem.
Scalanie dopiero po zielonym CI; końcowy wynik odbioru utrzymywać w opisie PR #62.
