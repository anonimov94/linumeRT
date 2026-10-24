# Sesja 045/084 · M3 Programowanie dialogowe · Panel programu dialogowego

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 45 z 84 · poprzednia: sesja-044. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-045` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-045` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M3
Format .lnx, generatory cykli, panel dialogowy z podglądem 2D, biblioteka podprogramów o-word, integracja z plikami QtDragon.

## Cel tej sesji
Panel QtVCP (osobna zakładka/obszar).

## Zakres pracy
1. Wygląd wg `docs/design/makiety/02_program_dialogowy.png`. Lista kroków: dodaj z kategorii, przesuń, duplikuj, wyłącz, usuń.
2. Formularz generowany z `fields` (QWidgets: liczba z jednostką i klawiaturą, wybór, przełącznik, wybór narzędzia z ToolDB filtrowany typem), walidacja z opóźnieniem 300 ms, błędy przy polach.
3. Generuj → .ngc, zapis/odczyt .lnx, otwarcie wyniku w AUTO.
4. Test logiki panelu bez GUI (model widoku) + zrzut, jeśli dostępny.

## Kryteria akceptacji
- [ ] model widoku testowany
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 045 — Panel programu dialogowego` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-045` do `main` (commit z prefiksem `sesja 045:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
