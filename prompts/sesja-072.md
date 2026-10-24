# Sesja 072/084 · M5 Konfiguracja maszyn hobbystów · Bufor i bramka G5 (prototyp v0.4)

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 72 z 84 · poprzednia: sesja-071. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-072` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-072` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M5
machine.yaml → INI/HAL dla sim, Plant, step/dir, EtherCAT, VFD; 4/5 osi; ATC; kreator; diagnostyka napędów; asystent strojenia na Plant.

## Cel tej sesji
Domknąć M5.

## Zakres pracy
1. `tools/check_examples.py`: generacja + scenariusze dla 5 przykładów.
2. Raport prototypu v0.4, `docs/raporty/G5.md` z sekcją „Pierwszy prawdziwy napęd: kryteria wyboru”.

## Kryteria akceptacji
- [ ] raport v0.4
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 072 — Bufor i bramka G5 (prototyp v0.4)` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-072` do `main` (commit z prefiksem `sesja 072:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
