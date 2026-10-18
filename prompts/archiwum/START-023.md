# Prompt startowy: sesja 023, edytor wirtualnej obrabiarki i awarie w panelu (po 022 i 024)

Model-Author: Claude · 2026-10-18. Najpierw [`START-PODZIAL.md`](START-PODZIAL.md) (zasady, worktree, testy),
potem pełny zakres w [`sesja-023.md`](../sesja-023.md).

## Warunek startu
Sesje 022 (panel) i 024 (`faults.py`, runner scenariuszy) są w `prompts/DONE.md` na `main`. Jeśli nie:
nie zaczynaj, napisz użytkownikowi, której brakuje, i zakończ.

## Zakres w tej sesji
1. Zakres `sesja-023.md` 1–8: zakładki „Maszyna” i „Napędy” w panelu (makiety 08 i 09), formularze ze
   schematu `machine.yaml`, kopiowanie szablonów napędów i różnice, podgląd 2D XY/XZ, walidacja REQ-VM-11
   przy zapisie, historia wersji, przeładowanie bez restartu tylko przy wyłączonych napędach.
2. Punkt 3 z `sesja-022.md` przeniesiony tutaj: zakładka „Awarie” z przyciskami z API `faults.py`.
3. Scenariusz `edit_reload` w formacie z sesji 024; `test_editor_api`.

## Zamknięcie (ostatnia sesja podziału)
Poza `START-PODZIAL.md` §4: zaktualizuj `docs/NASTEPNA_SESJA.md` (§1–§5, §8, linia `Tura:` = oddana) o
wyniki 022–025; przenieś `START-PODZIAL.md` do `prompts/archiwum/`; następna praca według `prompts/README.md`.
