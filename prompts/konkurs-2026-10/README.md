# Konkurs sesji linumeRT — 4 obszary projektu

Model-Author: Codex · 2026-10-23

Celem konkursu jest uzyskanie możliwie najlepszego, sprawdzalnego postępu w czterech ważnych obszarach projektu. Każda sesja ma osobny prompt i pracuje w osobnym checkoutcie/gałęzi. Sesje nie edytują wspólnych plików konkursu ani wyników innych sesji. Nie uruchamiają równolegle wspólnego LinuxCNC, Plant, DISPLAY ani katalogu budowania; przed użyciem wspólnego zasobu stosują blokady z `docs/WSPOLPRACA_MODELI.md`.

## Sesje

1. [Tor bezpieczeństwa sprzętowego](01-bezpieczenstwo.md)
2. [Odbiór stanowiska i kwalifikacja](02-odbior-stanowiska.md)
3. [Wymagania, pokrycie i luka funkcjonalna poza GUI](03-pokrycie-wymagan.md)
4. [Integracja skórek z działającym HMI](04-integracja-skorek.md)

Każda sesja zaczyna od aktualnego `origin/main`, sprawdza bieżący stan GitHub i wybiera odrębną gałąź `codex/contest-2026-10-<obszar>` (albo nazwę modelu zgodną z zasadami repo). Używa własnego worktree i nie resetuje ani nie nadpisuje pracy użytkownika. Dopuszczalne są małe commity, push i osobny PR zgodnie z zasadami projektu. Nie scala zmian konkursowych przed wspólną oceną; integracja i kolejność scalania nastąpią po ogłoszeniu wyników. Jeżeli istniejący workflow bezwzględnie wymaga scalenia zamkniętego etapu, sesja najpierw opisuje konflikt i zostawia gotowy PR do decyzji właściciela.

## Wspólna punktacja — 100 pkt

- **Wpływ na gotowość projektu (0–25):** usuwa istotną lukę z przypisanego obszaru, daje rezultat możliwy do użycia.
- **Poprawność i bezpieczeństwo (0–25):** spełnia kontrakty repozytorium, obsługuje błędy i nie tworzy fałszywych deklaracji gotowości.
- **Dowody działania (0–25):** testy adekwatne do zmiany, odtworzony test przed poprawką gdzie ma sens, wyniki jasno wskazane; sprzętowe twierdzenia wymagają rzeczywistego odbioru.
- **Jakość i kompletność (0–15):** czytelna implementacja, dokumentacja, wymagania/pochodzenie/licencje aktualne.
- **Dyscyplina zakresu i przekazanie (0–10):** osobna gałąź, brak naruszeń innych prac, raport z commit SHA, testami, ryzykiem i instrukcją odbioru.

Sędzia obniża punkty za zakres pozorny, testy pominięte lub niedostosowane, ukrywanie ograniczeń, nieuzasadnione zmiany niezwiązane z zadaniem i deklarowanie weryfikacji sprzętowej bez pomiarów. Naruszenie zasad bezpieczeństwa projektu może unieważnić wynik niezależnie od sumy. Sama liczba linii, testów lub commitów nie daje punktów.

## Oddanie pracy

Każda sesja dopisuje wyłącznie swój raport `raporty/01.md` … `raporty/04.md` na własnej gałęzi. Raport podaje: cel i zakres, najważniejsze zmiany, listę commitów/SHA/PR, dokładne polecenia i wyniki testów, nierozwiązane ryzyka, elementy niezweryfikowane, ręczne kroki odbioru oraz propozycję dalszego etapu. Nie przyznaje sobie punktów. Ocena końcowa jest porównawcza i wykonywana po zebraniu czterech raportów; sędzia ocenia każdy obszar tym samym wspólnym arkuszem, a potem porównuje kompletność i użyteczność wyników.
