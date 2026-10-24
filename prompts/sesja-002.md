# Sesja 002/084 · M0 Fundament, prawo, środowisko · Wytyczne IP i rejestr pochodzenia

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 2 z 84 · poprzednia: sesja-001. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-002` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-002` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M0
Repozytorium, CI, wytyczne IP i rejestr pochodzenia, budowa LinuxCNC w środowisku agenta, kopia bazowa QtDragon, rdzeń z atrapą.

## Cel tej sesji
Wdrożyć `docs/prawne/WYTYCZNE_IP.md` jako obowiązujący proces.

## Zakres pracy
1. Przeczytaj `docs/prawne/WYTYCZNE_IP.md` (wytyczne użytkownika). Utwórz `docs/prawne/PROCES.md`: jak w codziennej pracy stosujemy §4 (specyfikacja funkcjonalna osobno od wyglądu, własny system projektowy, rejestr pochodzenia, historia projektowania, przegląd podobieństwa, procedura §7).
2. `docs/PROVENANCE.md`: tabela (zasób, typ, autor, data, źródło, licencja, zakres użycia, ścieżka). Wpisz istniejące: `docs/design/marka/*`, `docs/design/ikony/*`, `docs/design/makiety/*`, `docs/design/tokens.yaml` (autor: projekt linumeRT, 2026-10-17, własne), fonty IBM Plex Sans i JetBrains Mono (OFL-1.1, gdy dodane).
3. `docs/prawne/LISTA_PRZED_WYDANIEM.md`: lista §9 jako checklista z polami „kto, kiedy, dowód”.
4. `tests/test_ip_guard.py`: skanuje `core/`, `screens/`, `plant/`, `hal/`, `config/` pod kątem nazw z `docs/prawne/ZAKAZANE_NAZWY.txt` (jedna nazwa w linii, bez rozróżniania wielkości liter) i słów zakazanych ze SLOWNIK.md; wyjątek tylko `docs/prawne/`.
5. `docs/SLOWNIK.md`: terminy projektu i zakazane z zamiennikami.
6. Sprawdź, że w repo nie ma odwołań do wcześniejszych materiałów projektu ani zrzutów cudzych sterowań (test).

## Kryteria akceptacji
- [ ] test_ip_guard przechodzi
- [ ] PROVENANCE.md ma wpisy dla wszystkich plików w docs/design
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 002 — Wytyczne IP i rejestr pochodzenia` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-002` do `main` (commit z prefiksem `sesja 002:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
