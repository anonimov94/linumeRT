# Wspólna praca nad linumeRT

Przeczytaj `CLAUDE.md`, `docs/DECYZJE.md`, `docs/WSPOLPRACA_MODELI.md`,
ostatnie trzy wpisy `docs/DZIENNIK.md` i właściwy prompt z `prompts/`.
Realizuj kierunek właściciela: LinuxCNC, QtDragon, Plant, plan 84 sesji.
Pracujemy naprzemiennie: Codex implementuje, Claude przegląda, następnie odwrotnie.
Zmiany przez PR; autor modelowy jawny w commitach, PR i dzienniku.
Nie oznaczaj sesji jako wykonanej, dopóki nie spełnia kryteriów akceptacji.


## Aktualizacja właściciela — samodzielna praca Codex

2026-10-17 · Model-Author: Codex. Claude jest niedostępny do odwołania.
Codex kontynuuje implementację i przegląd własnych zmian przez PR oraz testy,
a następnie może scalać poprawne PR bez oczekiwania na Claude. Przegląd Claude
po powrocie jest dodatkową kontrolą, nie blokadą pracy. Nie przedstawiamy
autokontroli jako niezależnego przeglądu. Ta aktualizacja zastępuje wcześniejszy
wymóg przeglądu drugiego modelu przed każdym scaleniem.
Po każdym ukończonym kroku: commit i push; nie odkładać publikacji do końca sesji
ani do zbliżającego się limitu kontekstu/tokenów.
