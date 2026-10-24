# Wspólna praca nad linumeRT

Punkt wejścia każdej sesji: [`docs/PROMPT_NOWEJ_SESJI.md`](docs/PROMPT_NOWEJ_SESJI.md). Kolejność lektury:
`CLAUDE.md` (kontrakt) → `docs/WSPOLPRACA_MODELI.md` (**jedyne źródło zasad współpracy**) →
`docs/NASTEPNA_SESJA.md` (czyja tura, stan, zadania) → `docs/DECYZJE.md` → ostatnie wpisy `docs/DZIENNIK.md`
→ prompt sesji z `prompts/`.

Statusy i wspólny plan: `docs/roadmap/plan.json`; `prompts/DONE.md`, spis promptów i roadmapa HTML
są generowane przez `python3 tools/roadmap.py`, bez ręcznego dopisywania.

Skrót (szczegóły w `WSPOLPRACA_MODELI.md`):
- Claude i Codex pracują na zmianę: linia `Tura:` w `NASTEPNA_SESJA.md` i `prompts/LOCK`. Praca równoległa
  tylko wyjątkowo, w osobnych checkoutach i z blokadami zasobów (D28, D30). Od D31 cały zakres prowadzi Claude.
- Małe kroki: po każdym commit i push; draft PR od pierwszego kroku; limit tokenów może przerwać w każdej chwili.
- Oszczędzaj tokeny: czytaj zakresy i `diff --stat`, nie całe pliki; bez subagentów, chyba że właściciel poprosi.
- `Model-Author:` w każdym commicie i PR; autokontrola to nie niezależny przegląd.
- Na koniec etapu PR jest scalany do `main` (D26); `main` bez niedokończonego kodu; PR nie wiszą.
