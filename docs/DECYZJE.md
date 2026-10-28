# Decyzje lite

2026-10-28 · Model-Author: Codex · polecenie właściciela: „zrób wersję lite”, bez GUI.

Osobna gałąź `codex/lite-backend`, baza `a593d6d4c55f503fbaf4c607099f2d89c61cc670`.
Pełna edycja i historia pozostają w oryginalnym checkoutcie i Git.
Zakres lite: CAM 2D i .lnx, narzędzia, walidacja/eksport konfiguracji sim/Plant,
Plant C/UDP oraz diagnostyczna symulacja materiału 2.5D. Bez GUI, HTTP, STL CAM 3D,
wtyczek, instalatora ISO i generatora konfiguracji sprzętowej/ATC.
Model i testy Plant zachowują istniejącą obsługę napędów, kinematyk oraz awarii;
nie przepisujemy fizyki i nie usuwamy zabezpieczeń w celu zmniejszenia plików.
Szablony napędów należą teraz do core; skale mają jedną implementację.
Kryteria pełnej edycji, w tym panel web i wszystkie 84 sesje, nie są kryteriami lite.
Nie deklarujemy zamknięcia dawnych bramek ani kwalifikacji RT/sprzętu.
