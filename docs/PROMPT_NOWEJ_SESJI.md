# Prompt startowy nowej sesji (Claude lub Codex)

Model-Author: Claude · 2026-10-18. Wklej na początku sesji; aktualizuj stan na jej końcu.

Pracujesz nad linumeRT (repo anonimov94/linumeRT, LinuxCNC 2.9 + QtDragon, Debian 12) razem z drugim
modelem. Pracujecie na zmianę, nigdy równolegle. Użytkownik jest użytkownikiem końcowym i ocenia po efektach.

## Start
1. Przeczytaj CLAUDE.md, docs/WSPOLPRACA_MODELI.md, docs/DECYZJE.md, 3 ostatnie wpisy docs/DZIENNIK.md,
   docs/NASTEPNA_SESJA.md i prompts/LOCK.
2. Sprawdź otwarte PR-y (REST: `gh api repos/anonimov94/linumeRT/pulls`; GraphQL jest zablokowany).
3. Linia `Tura:` w NASTEPNA_SESJA.md: nie wchodź w turę drugiego modelu młodszą niż 2 h od ostatniego pusha.

## Stan (2026-10-18)
- Otwarte, niezależne względem main: #5 (006), #6 (007), #7 (009), #8 (010) — czekają na przegląd i scalenie
  przez Codexa. #4 (protokół v2) scala Codex jako pierwszy.
- #3 (sesja 003, LinuxCNC CI): wrócony do Codexa — przejście na Debian 12 (bookworm) w WSL z VNC i naprawa
  czerwonego CI (spec w komentarzu do #3). Po jego "gotowe @ SHA" drugi model przegląda ten SHA i scala.
- Po scaleniach możliwe konflikty na końcu DZIENNIK.md i prompts/DONE.md: zostaw wszystkie wpisy.
- roboCODE to osobny projekt na przyszły rok. Nie dotykać.

## Zakres
- Claude: rdzeń Pythona weryfikowalny w chmurze, specyfikacje, wymagania, IP, niezależny przegląd Codexa.
  Następna sesja = najniższy numer z prompts/ nieobecny w prompts/DONE.md i LOCK (np. 011+; 008 czeka na
  zielone CI Codexa).
- Codex: wszystko w WSL/Windows/VNC (budowa LinuxCNC, HAL/INI, skrypty, CI, testy integracyjne).
  Zlecenia dla niego: krótkie, jednoznaczne specyfikacje w komentarzu do PR lub w NASTEPNA_SESJA.md.

## Zasady
- CLAUDE.md wygrywa z promptem sesji. Definition of Done: testy, jawne błędy, brak blokowania RT,
  dokumentacja, LICENCJE/PROVENANCE, wpis w DZIENNIK.md i prompts/DONE.md.
- Małe kroki; po każdym commit i push na wip/sesja-NNN. Oszczędzaj tokeny.
- Własnych PR-ów nie scalasz — scala drugi model po sprawdzeniu (wyjątek D25: autokontrola z adnotacją).
  Nie przedstawiaj autokontroli jako niezależnego przeglądu.
- Oznaczaj `Model-Author: Claude|Codex` w commitach, PR i dzienniku. Prawdziwy sprzęt/LinuxCNC:
  `NIEZWERYFIKOWANE NA SPRZĘCIE`.
- ruff (line-length 100, B905: `zip(..., strict=True)`), pytest z `PYTHONPATH=core`.

## ZAWSZE KOŃCZ PRACĘ (obowiązkowe zamknięcie sesji)
1. Wszystko scommitowane i wypchnięte; PR otwarty; testy i lint zielone.
2. Wpis w DZIENNIK.md i prompts/DONE.md.
3. Zaktualizuj sekcję "Stan" powyżej i linię `Tura:` w NASTEPNA_SESJA.md (stan: oddana), zwolnij LOCK.
4. Zostaw drugiemu modelowi konkretne zlecenia (co sprawdzić, co scalić, co zrobić dalej).
5. Użytkownikowi podaj: co powstało, link do PR i jeden następny krok.
