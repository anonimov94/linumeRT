# Sesja 031/084 · M2 Ekran linumeRT na bazie QtDragon · AUTO i wznowienie od linii

Kolejność: sesja 31 z 84 · poprzednia: sesja-030. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-031` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-031` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M2
Własny system projektowy i kompozycja ekranu, tryby, JOG/MPG, MDI, AUTO, narzędzia, zerowanie i sonda, zmiana narzędzia, alarmy, role, PL/EN.

## Cel tej sesji
Tryb AUTO i poprawiony run-from-line.

## Zakres pracy
1. Start/Pauza/Stop, pojedynczy blok, opcjonalny stop, override posuwu/szybkiego/wrzeciona, postęp i czas.
2. Wznowienie od linii: przed startem okno z podsumowaniem stanu modalnego w tej linii (narzędzie, układ, wrzeciono, posuw) i opcją „uruchom wrzeciono i potwierdź narzędzie” — odpowiedź na znane ograniczenie QtDragon. Użyj mechanizmów LinuxCNC (sprawdź dokumentację run-from-line / `task_plan_synch`), opisz ograniczenia.
3. Scenariusz Plant `auto_pause_resume` i `run_from_line`.

## Kryteria akceptacji
- [ ] scenariusze przechodzą
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 031 — AUTO i wznowienie od linii` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `031 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-031` do `main` (commit z prefiksem `sesja 031:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
