# Wznowienie sprintu WebHMI 028/029 — 2026-10-27

Model-Author: Codex. Przekazanie na polecenie właściciela: „wypychaj, zostało 4% tokenów”.

## Najpierw

Czytaj CLAUDE.md → WSPOLPRACA_MODELI.md → NASTEPNA_SESJA.md i rejestr.
Kod jest wypchnięty: PR #193, gałąź codex/team-sprint-20261027,
HEAD b7e316868235e95c9fd9104ccc3aa2033f43ca67. Osobny checkout:
/home/dell/Projekty/linumeRT-team-sprint-20261027. To przekazanie nie zmienia HEAD
tej gałęzi i nie przerywa działającego CI. Nie scalać przed zielonymi kontrolami.

## Nadrzędne polecenia właściciela

- Zespoły i raporty: WYŁĄCZNIE darmowe czaty już zalogowane w przeglądarce.
  Nie uruchamiać dodatkowych sesji Claude, płatnych API ani subagentów Codex jako
  zastępstwa zespołu. Reguła jest w osobnym commicie 9342e6c w PR #193:
  docs/WSPOLPRACA_MODELI.md i docs/DECYZJE.md. Początkowy kod wykonali agenci
  Codex; dalsze delegowanie zakończono. Nie przypisywać im innych tożsamości.
- Pozycje 0,0001 mm; obliczenia 0,000001 mm; błąd pozycjonowania <0,001 mm
  akceptowalny. Kontrakt i zaostrzony test live w b7e3168 (CLAUDE/DECYZJE/driver).
- Pierwotny termin sprintu: 14:43–15:43 UTC; nowy próg wymagał ponowienia CI.
  Bez deklarowania wdrożenia przed scałeniem ani zamykania MPG/HAL/sprzętu/M2.

## Co działa i dowody

Web: ciągły i przyrostowy JOG .001/.01/.1/1 mm lub stopni; jeden ruch na gest,
jog_keepalive bez powtarzania, własność sesji, deadman .4s, STOP i retry.
Przyrost wymaga ON/MANUAL/IDLE/bazowania i właściwych limitów. API mm/deg,
konwersja prędkości i drogi dla maszyn calowych.

- Lokalnie 1692 PASS, 139 SKIP; Node 31 PASS; C109/109; REQ22/22.
- Rzeczywisty LinuxCNC sim po progu<.001mm: 1 PASS8,25s. DRO=NML,
  +1mm zmierzony jako0,9999994167mm; deadman zatrzymuje długi krok po~.212mm;
  odmowa w MDI i STOP po rozłączeniu. To nie jest odbiór sprzętu.
- Aktualny Brave1280×768: pojedyncze .1mm podczas przytrzymania, keepalive,
  release/blur STOP, rozłączenie i WebGL PASS. Osobny test braku bazowania:
  ciągły dostępny, przyrost zablokowany z powodem, przełączenie poprawne.
- CI HEADb7e3168: python1704PASS127SKIP, C109/109, REQ22/22, wheelPASS,
  plant-matrixSUCCESS. Run40526842961.
- Pełny RIP run40526843242 W TOKU przy przekazaniu. Sprawdź rzeczywisty wynik:
  gh pr checks 193; gh run view 40526843242 --log.
- Artefakty lokalne: build/team-offline.log, build/team-precision-live/,
  build/webhmi-sprint/ oraz build/team-browser/. Są w checkoutcie sprintu.

## Czaty i stan współpracy

Raporty w issue #181 co około10min. ChatGPT dostał konsultację kontraktu; pierwszy
prompt omyłkowo nazwał rolę Gemini — przypisanie skorygowano, odpowiedź pozostaje
ChatGPT. Sugestii tolerancji .01mm nie przyjmować zamiast <.001mm. Gemini otrzymało
właściwy przydział i odpowiedziało dokumentacją; pełne linki/odpowiedź do odbioru.
Grok przydziału jeszcze NIE otrzymał. Nie deklarować jego udziału.

Przeglądarka Brave na Wayland; nie ma MCP browser tools. Dostęp uzyskano przez
KDE/uinput (bez czytania cookies/haseł). Aktywna grupa kart Claude jest sterowana
równolegle i zmienia aktywne karty, co spowodowało błędne przypisanie. Pulpit był
zablokowany, potem odblokowany. Asynchroniczna prośba do właściciela o wstrzymanie
konkurencyjnego sterowania pozostaje bez odpowiedzi. NIE wysyłać kolejnych wiadomości
przez UI, dopóki dostęp nie jest skoordynowany. Nigdy nie obchodzić blokady pulpitu.
Nie otwierać dodatkowych sesji Claude.

## Następne kroki

1. Odczytać wynik pełnego CI193 właściwego SHA. Zielone → merge commit przez PR,
   oczekiwany HEADb7e3168; bez force i bez omijania kontroli. Potwierdzić main.
2. Wznowić darmowe czaty po skoordynowaniu przeglądarki; wysłać Grokowi prawdziwy
   przydział i zweryfikować odpowiedzi Gemini/ChatGPT. Uczciwy raport w #181.
3. Rozliczyć przekazanie; statusy tylko w plan.json, generować roadmapę. Nie zmieniać
   statusu całych028/029 na done. Ten plik po zakończeniu przenieść do archiwum.

Istniejący draft #192 to osobna praca ATC066, nie nowa sesja zlecona przez Codex.
Nie zmieniać lokalnej kopii operatora /home/dell/linumeRT: ma pliki użytkownika
oraz cudzą pracę ATC. Własny kontener linumert-team-sprint-tests można zakończyć;
instancje przeglądarkowych fixture zostały zakończone. Nie zabijać cudzych procesów.

Obserwacja nieblokująca, nie naprawiana w tym zakresie: nowa Starlette może logować
WebSocketDisconnected przy wysyłaniu po close. Fizyczny STOP w badanym scenariuszu
przeszedł; nie przedstawiać zerowych błędów JS jako braku błędów serwera.
