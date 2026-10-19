# Savoir-vivre AI przy pracy nad linumeRT

Model-Author: Codex · polecenie właściciela, D36 · 2026-10-19.

1. **Pokazuj efekt w GUI od pierwszego kroku.** Gdy funkcja ma służyć operatorowi, od razu
   dodaj jej widok do nawigacji i dostarcz minimalne użyteczne działanie.
2. Rozwijaj funkcję iteracyjnie. Użytkownik ma widzieć postęp działania przy kolejnych porcjach.
3. Oznacz stan częściowy i dostępne możliwości. Nie udawaj ukończenia ani obsługi martwych akcji.
4. Sprawdzaj rzeczywistą drogę przez GUI. Pokaż zrzut lub podgląd, nie tylko wynik testów backendu.
5. Po testach commit i push, najpóźniej po około 200 nowych liniach. Przekazuj stan drugiemu modelowi.
6. Raportuj konkretnie: co użytkownik może już zrobić, gdzie to otworzyć i co zostało.

Reguła wykonawcza jest w [CLAUDE.md §11](../CLAUDE.md); zasady współpracy modeli w
[WSPOLPRACA_MODELI.md](WSPOLPRACA_MODELI.md). Dotyczy także każdej następnej sesji i modelu.
