# Wspólna praca nad linumeRT

Przeczytaj: `CLAUDE.md` (kontrakt), `docs/DECYZJE.md`, **`docs/WSPOLPRACA_MODELI.md`**
(jedyne źródło zasad współpracy), `docs/NASTEPNA_SESJA.md` (czyja tura, stan, zadania),
trzy ostatnie wpisy `docs/DZIENNIK.md` i prompt z `prompts/`.

Skrót (szczegóły w `WSPOLPRACA_MODELI.md`):
- Claude i Codex pracują na zmianę, nigdy równolegle: linia `Tura:` w `NASTEPNA_SESJA.md` i `prompts/LOCK`.
- Małe kroki: po każdym commit i push; draft PR od pierwszego kroku; limit tokenów może przerwać w każdej chwili.
- Oszczędzaj tokeny: czytaj zakresy i `diff --stat`, nie całe pliki; bez subagentów.
- `Model-Author:` w każdym commicie i PR; autokontrola to nie niezależny przegląd.
- Scala model niebędący autorem; wyjątek D25 (drugi model niedostępny) z adnotacją w PR.
