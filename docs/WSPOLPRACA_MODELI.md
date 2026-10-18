# Współpraca Claude i Codex (v2)

Model-Author: Claude · 2026-10-18. **Jedyne źródło zasad współpracy.** `AGENTS.md` i
`CLAUDE.md` tylko tu odsyłają; sprzeczne zapisy gdzie indziej tracą moc. Zmiana zasad =
osobny commit + wpis w `docs/DECYZJE.md`. Powód wersji 2: limity tokenów często przerywają
sesje, więc pracujemy małymi krokami, z częstym pushem i jawnym przekazaniem tury.

## 1. Tury (na zmianę, nigdy równolegle)
- Na górze `docs/NASTEPNA_SESJA.md` jest stała linia:
  `Tura: Claude|Codex · od <UTC> · stan: w toku|oddana`.
- Start: przeczytaj tę linię, `prompts/LOCK` i otwarte PR. Tura drugiego modelu „w toku"
  z ostatnim pushem starszym niż 2 h = przerwana (limit): zapisz to w dzienniku i przejmij.
  Świeżej tury nie przejmuj.
- Koniec albo zbliżający się limit: commit, push, `stan: oddana`, zwolnij LOCK.
- Przekazanie wyłącznie w plikach: sekcje „Dla Codex:" i „Dla Claude:" w
  `NASTEPNA_SESJA.md`; odpowiedź w tym samym pliku. Czat właściciela nie jest kanałem.

## 2. Blokada `prompts/LOCK`
Jedna linia: `<model> · sesja NNN · <UTC> · <opis>`. Brak pliku lub pusty = wolne.
Zakładasz na starcie, zwalniasz przy oddaniu (osobny commit `lock: zwolniony`).
Cudzego świeżego locka nie ruszaj; przerwany (>2 h bez pushu) przejmij wpisem w dzienniku.

## 3. Małe kroki i częsty push
- Krok = jedna spójna zmiana, zwykle ≤ 5 plików lub ≈ 200 linii. Po każdym kroku:
  lint i szybkie testy → commit → push. Niczego nie kumuluj lokalnie.
- Draft PR otwieraj po pierwszym kroku, nie na końcu sesji.
- Przed długą operacją (budowa, duże testy, klonowanie) wypchnij wszystko.
- Po każdym pushu dopisz jedną linię w sekcji „Stan zatrzymania" w `NASTEPNA_SESJA.md`
  (zrobione / następny krok). To tanie, a ratuje przerwaną sesję.
- Praca nieukończona żyje na gałęzi z draft PR, nigdy tylko lokalnie.

## 4. Oszczędność tokenów
- Czytaj tylko potrzebne: `git diff --stat`, `grep -n`, zakresy linii, `| tail -20`.
  Nie wypisuj całych plików ani logów; nie powtarzaj odczytów.
- GitHub przez `gh api ... --jq`, klony płytkie (`--depth 1`), bez subagentów,
  chyba że właściciel o nie poprosi.
- Pisz zwięźle: wpis w dzienniku ≤ 10 linii, raporty w plikach, w czacie 3–5 zdań.
- Zadanie, które nie mieści się w jednym kroku, podziel i zapisz podział w `NASTEPNA_SESJA.md`.

## 5. Autorstwo, przegląd, scalanie
- Commity, PR i dziennik: `Model-Author: Claude` albo `Model-Author: Codex`. Nie przypisuj
  sobie cudzej pracy. Nie nazywaj autokontroli niezależnym przeglądem.
- Zasada: PR scala model, który nie jest jego autorem, po przeglądzie (komentarz: model,
  SHA, wynik) i zielonych kontrolach.
- Wyjątek (D25): gdy drugi model jest niedostępny lub jego tura przerwana, autor może
  scalić po zielonych kontrolach i autokontroli. W PR napisz „autokontrola, bez
  niezależnego przeglądu"; drugi model robi przegląd wsteczny po powrocie (SHA scalenia).
- Zmiany wyłącznie w `docs/` mogą być scalane od razu przez autora, z adnotacją w PR.
- Merge commit (jak dotąd); nie przepisuj historii `main`.

## 6. Środowisko testowe
Polecenia i stan środowiska: `docs/NASTEPNA_SESJA.md` (nie duplikuj ich tutaj).
