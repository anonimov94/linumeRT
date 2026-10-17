# Sesja 001/084 · M0 Fundament, prawo, środowisko · Szkielet repozytorium, CI i licencja

Kolejność: sesja 1 z 84 · poprzednia: brak (to pierwsza sesja). Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-001` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-001` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M0
Repozytorium, CI, wytyczne IP i rejestr pochodzenia, budowa LinuxCNC w środowisku agenta, kopia bazowa QtDragon, rdzeń z atrapą.

## Cel tej sesji
Utworzyć szkielet monorepo zgodny z CLAUDE.md §3.

## Zakres pracy
1. `pyproject.toml`: pakiet `linumert` z `core/`, Python ≥ 3.11; zależności: numpy, pyyaml; dev: pytest, ruff. Pakiety `simulation`, `plant/server` jako osobne pakiety w tym samym repo.
2. Katalogi z §3 z `README.md` w każdym (1–3 zdania, co tam trafi).
3. `Makefile`: install, lint, test, test-c (no-op do sesji 010), test-linuxcnc (no-op do sesji 003).
4. `.github/workflows/ci.yml`: Python 3.11, `make install lint test`.
5. `LICENSE`: pełny tekst GPL-2.0, nagłówek w README „GPL-2.0-or-later dla własnego kodu”; `docs/LICENCJE.md` (tabela zależności); `.gitignore` (Python, `*.qcow2`, `*.img`, `*.vdi`, `*.TGZ`, `/state`).
6. Sprawdź, że w repo nie ma pliku z licencją „Paid Reuse” i dodaj test, który to pilnuje.

## Kryteria akceptacji
- [ ] `make install lint test` przechodzi
- [ ] README ma „Szybki start”
- [ ] test licencji przechodzi
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 001 — Szkielet repozytorium, CI i licencja` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `001 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-001` do `main` (commit z prefiksem `sesja 001:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
