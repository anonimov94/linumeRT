# Współpraca Claude i Codex

Decyzja właściciela: 2026-10-17. Autor tego wpisu: model językowy Codex.

## Przekazanie dla Claude

Od tej sesji współtworzymy linumeRT naprzemiennie. Właściciel poinformował,
że Claude będzie dostępny najwcześniej 2026-10-18 po odnowieniu limitu.
To przekazanie w repozytorium, nie potwierdzenie odebrania wiadomości.
Kontynuujemy dotychczasowe decyzje i plan 84 sesji.

## Praca i wzajemna kontrola

1. Pobierz aktualne gałęzie i sprawdź otwarte PR oraz `prompts/LOCK`.
   Nie uruchamiaj równocześnie tej samej sesji w dwóch środowiskach.
2. Najpierw przejrzyj PR drugiego modelu: wymagania, diff, testy, regresje,
   RT, ograniczenia sprzętowe. W ocenie podaj model i SHA sprawdzonego commita.
3. Implementuj na osobnej gałęzi (`codex/<temat>` dla Codex,
   `wip/sesja-NNN` dla Claude). Zapisuj i wypychaj ukończone kroki.
4. Każdy commit i opis PR oznacz `Model-Author: Codex` lub `Model-Author: Claude`.
   W dzienniku zapisuj model językowy, zakres, wyniki testów i pozostałe zadania.
   Zachowuj istniejące nagłówki autorstwa i licencji; nie przypisuj sobie cudzej pracy.
5. Otwórz PR do `main`. Wymagaj przechodzących kontroli i rzeczywistego przeglądu
   drugiego modelu przed scaleniem. Na wspólnym koncie GitHub ocena może być komentarzem
   z modelem i SHA; nie jest to formalne zatwierdzenie przez osobne konto.
6. Jeśli drugi model jest niedostępny, pozostaw PR do przeglądu. Możesz kontynuować
   niezależny zakres na kolejnej gałęzi; zależności między PR opisz jawnie.
7. Po zmianach wymagaj ponownego przeglądu aktualnego SHA. Następny model zaczyna
   od przeglądu, potem kontynuuje pierwszą niewykonaną sesję.

To zasady pracy, nie skonfigurowana ochrona gałęzi ani nowy harmonogram.
Nie zmieniamy istniejących automatyzacji bez sprawdzenia ich konfiguracji.

## Stan na 2026-10-17

- `main`: `6c713df`; sesje 001 i 002 wykonane przez wcześniejszego agenta.
- `wip/sesja-001`: 0 commitów ponad main, 5 za main.
- `wip/sesja-002`: 0 commitów ponad main, 2 za main.
- Obie istniejące gałęzie są już scalone w sensie historii; nie wymagają ponownego
  merge. Pozostawiono je jako ślad pracy.
- Następna sesja: 003, spike LinuxCNC 2.9. Nie oznaczono jej jako wykonanej.
- `prompts/LOCK` nadal wskazuje historyczną sesję 001. Przed uruchomieniem
  harmonogramu ustalić, czy jego właściciel zakończył pracę; nie usuwać w ciemno.
- Lokalny katalog główny był nieaktualną kopią dokumentacji bez własnego `.git`.
  Aktualny checkout znajduje się w `.collaboration/linumeRT/` wewnątrz niego.


## Aktualizacja właściciela — samodzielna praca Codex

2026-10-17 · Model-Author: Codex. Claude jest niedostępny do odwołania.
Codex kontynuuje implementację i przegląd własnych zmian przez PR oraz testy,
a następnie może scalać poprawne PR bez oczekiwania na Claude. Przegląd Claude
po powrocie jest dodatkową kontrolą, nie blokadą pracy. Nie przedstawiamy
autokontroli jako niezależnego przeglądu. Ta aktualizacja zastępuje wcześniejszy
wymóg przeglądu drugiego modelu przed każdym scaleniem.
Po każdym ukończonym kroku: commit i push; nie odkładać publikacji do końca sesji
ani do zbliżającego się limitu kontekstu/tokenów.
