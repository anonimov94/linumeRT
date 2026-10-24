# Prompt startowy sesji (Claude lub Codex)

Model-Author: Claude · 2026-10-18. Stały tekst: **nie zawiera stanu** (statusy są w
[`roadmap/plan.json`](roadmap/plan.json), przekazanie w [`NASTEPNA_SESJA.md`](NASTEPNA_SESJA.md)). Zmieniaj go tylko wtedy, gdy zmieniają się zasady.

Wklej na początku sesji:

> Kontynuuj projekt linumeRT (repo `anonimov94/linumeRT`; LinuxCNC 2.9 + ekran na bazie QtDragon,
> Debian 12, wirtualna obrabiarka Plant). Przeczytaj `docs/PROMPT_NOWEJ_SESJI.md` i postępuj według niego.

## 1. Start (kolejno, oszczędnie)
1. `CLAUDE.md` (kontrakt; ma pierwszeństwo przed promptem sesji) i `docs/WSPOLPRACA_MODELI.md` (zasady pracy).
2. `docs/NASTEPNA_SESJA.md`: linia `Tura:`, stan PR, następna praca, środowisko, otwarte sprawy.
3. `prompts/LOCK` i otwarte PR (`gh pr list`). Nie wchodź w świeżą turę drugiego modelu (≤ 2 h od pushu).
4. `docs/DECYZJE.md` (część dotycząca zakresu sesji) i ostatnie trzy wpisy `docs/DZIENNIK.md`.
5. Przeczytaj `docs/roadmap/plan.json`: jedyne źródło statusów i powiązań zakresu. Wybierz najniższą
   nieukończoną sesję 001–084, jej rozszerzenia i prompt `prompts/sesja-NNN.md`, uwzględniając zależności
   oraz bieżące polecenie właściciela. DONE jest widokiem generowanym, nie harmonogramem.
   Zastosuj sekcję „Lekcja projektu — pilnowanie założeń i kolejności” w `WSPOLPRACA_MODELI.md`.
   Przed kodowaniem podaj ID pierwotnej sesji, kryterium/bramkę, otwarte zależności i mały rezultat.
   Nowy pomysł zapisany jako rozszerzenie nie zmienia kolejności; jawne polecenie właściciela
   odnotuj wraz z wpływem na wcześniejsze bramki. Jeśli istnieje gałąź `wip/sesja-NNN`, kontynuuj ją.
6. Zajmij turę: `prompts/LOCK` = `<model> · sesja NNN · <UTC> · <opis>`, linia `Tura:` = w toku; commit, push.

## 2. Praca
- Małe kroki; po każdym: lint i testy → commit (`Model-Author: Claude|Codex`) → push → linia w
  „Stan zatrzymania” w `NASTEPNA_SESJA.md`. Draft PR po pierwszym kroku.
- Definition of Done (`CLAUDE.md` §11): testy, jawne błędy, brak blokowania RT, dokumentacja,
  `docs/LICENCJE.md` / `docs/PROVENANCE.md`, wymagania REQ w `docs/wymagania/MACIERZ.md`.
- LinuxCNC: blokada zasobu `python tools/lock.py acquire linuxcnc --model <model> --note "..."` (D30).
- Rzeczy dotyczące prawdziwego sprzętu oznaczaj `NIEZWERYFIKOWANE NA SPRZĘCIE`. Autokontroli nie nazywaj
  niezależnym przeglądem.

## 3. Zamknięcie sesji (obowiązkowe)
1. `make lint test` (oraz `test-c`, testy `-m linuxcnc`, jeśli dotyczy) zielone; wszystko wypchnięte; PR gotowy.
2. Wpis w `docs/DZIENNIK.md` i aktualizacja właściwego rekordu `docs/roadmap/plan.json`
   (status, postęp, pozostały zakres i dowody), następnie `python3 tools/roadmap.py`;
   decyzje w `docs/DECYZJE.md`. DONE, spis promptów i widoki roadmapy są generowane.
3. `docs/NASTEPNA_SESJA.md`: przekazanie i środowisko zaktualizowane, bez powielania statusów roadmapy;
   `Tura:` = oddana; `prompts/LOCK` pusty; blokady zasobów zwolnione.
4. Użytkownikowi: jakie kryterium pierwotnego planu domknięto, co nadal pozostaje,
   link do PR, co sprawdzić ręcznie i jeden następny krok zgodny z kolejnością planu.

Sesję przerwaną w połowie opisz dodatkowo w `prompts/START-NNN.md` (kroki do zrobienia); po jej ukończeniu
przenieś plik do `prompts/archiwum/`.
