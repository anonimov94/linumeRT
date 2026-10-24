# Sesja 080/084 · M6 Wtyczki, instalator, alfa · Przegląd IP przed wydaniem

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 80 z 84 · poprzednia: sesja-079. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-080` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-080` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M6
Wtyczki deklaratywne, instalator dla Debiana 12 + LinuxCNC 2.9, dokumentacja, przegląd IP przed wydaniem, regresja na Plant, wydanie alfa.

## Cel tej sesji
Przygotowanie do listy §9.

## Zakres pracy
1. Audyt PROVENANCE.md vs pliki w repo (skrypt: każdy plik graficzny/font ma wpis).
2. Audyt licencji zależności (pip-licenses itp.) → LICENCJE.md; zgodność z GPL-2.
3. Pakiet przeglądu podobieństwa v0.5 (nasze zrzuty + pytania), bez zrzutów cudzych sterowań.
4. `docs/prawne/NAZWA.md`: instrukcja wyszukania nazwy **linumeRT** (i znaku graficznego) w UPRP, EUIPO, WIPO Global Brand Database (klasy do potwierdzenia przez prawnika, np. 7, 9, 42) z polami na wyniki; agent nie przesądza o wyniku.
5. Wypełnij LISTA_PRZED_WYDANIEM.md w części, którą może wykonać agent; resztę oznacz „decyzja użytkownika/prawnika”.

## Kryteria akceptacji
- [ ] skrypt audytu PROVENANCE przechodzi
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 080 — Przegląd IP przed wydaniem` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-080` do `main` (commit z prefiksem `sesja 080:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
