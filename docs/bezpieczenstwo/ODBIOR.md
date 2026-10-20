# Odbiór toru zezwolenia fizycznej maszyny

Model-Author: Codex · 2026-10-20. **NIEZWERYFIKOWANE NA SPRZĘCIE.**
Szablon protokołu; nie instrukcja prowadzenia prób na działającej maszynie.
Plan i warunki prób ustala osoba odpowiedzialna za ocenę ryzyka maszyny.

## Dane protokołu

- Maszyna, napędy, wrzeciono, osie pionowe: do uzupełnienia.
- Ocena ryzyka i wymagane funkcje/poziomy bezpieczeństwa: do uzupełnienia.
- Rewizja schematu elektrycznego, konfiguracji i firmware: do uzupełnienia.
- Urządzenie nadzoru PC, wejścia/wyjścia, stan bez energii: do uzupełnienia.
- Przyrządy pomiarowe, wykonawca i osoba odbierająca: do uzupełnienia.
- Warunki ograniczenia ryzyka podczas prób: do uzupełnienia.

## Macierz dowodów

| Próba | Oczekiwany wynik funkcjonalny | Dowód / pomiar | Wynik |
|---|---|---|---|
| Rozruch PC i start HMI | Brak samoczynnego ruchu; zezwolenie zgodne z projektem | — | niewykonane |
| Grzyb fizyczny, każdy kanał osobno | Reakcja niezależna od PC/HMI; diagnostyka rozbieżności według projektu | — | niewykonane |
| Otwarte urządzenie ochronne | PC nie może obejść blokady ani potwierdzić jej jako zamkniętej | — | niewykonane |
| Zanik zasilania PC / awaria OS | Zewnętrzny nadzór odbiera zgodę zgodnie z projektem | — | niewykonane |
| Heartbeat stale 0 albo 1 | Brak zmian sygnału wykrywany przez zewnętrzny nadzór | — | niewykonane |
| Zawieszenie pętli GUI | Brak heartbeat HMI odbiera zgodę; HAL nie zastępuje nadzoru PC | — | niewykonane |
| Przerwa/usterka I/O lub komunikacji | Reakcja i diagnostyka zgodne z projektem urządzeń | — | niewykonane |
| Powrót sygnału / zasilania / komunikacji | Bez automatycznego wznowienia ruchu | — | niewykonane |
| Reset fizyczny i potwierdzenie software | Oddzielne role; reset nie rozpoczyna ruchu | — | niewykonane |
| STO / hamowanie / oś pionowa | Funkcje, zatrzymanie i utrzymanie obciążenia według projektu | — | niewykonane |
| Wrzeciono i energia resztkowa | Reakcja zgodna z projektem VFD i układu odłączania | — | niewykonane |
| Ponowne uruchomienie programu | Wymaga osobnego świadomego polecenia operatora | — | niewykonane |

Nie wpisuj uniwersalnego limitu reakcji w ms. Budżet wynika z oceny ryzyka i obejmuje cały tor:
wykrycie uszkodzenia, nadzór, I/O, reakcję napędu oraz ruch/energię po odebraniu zgody.
Sam czas wykonania Pythona lub okres wątku servo nie jest czasem zatrzymania maszyny.

## Co daje kontrola offline

`deployment --hal-from-ini` sprawdza kompletność deklaracji i ograniczony zbiór połączeń
tekstowych HAL. Nie mierzy powyższych reakcji, nie ustala kategorii/PL/SIL, nie sprawdza
kierunków rzeczywistych pinów, sprzężenia zwrotnego styczników ani rzeczywistego okablowania.
Wynik pozytywny nie jest odbiorem. Wynik negatywny trzeba wyjaśnić przed dalszą kwalifikacją.
