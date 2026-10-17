# Sesja 008/084 · M0 Fundament, prawo, środowisko · Bufor i bramka G0

Kolejność: sesja 8 z 84 · poprzednia: sesja-007. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-008` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-008` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M0
Repozytorium, CI, wytyczne IP i rejestr pochodzenia, budowa LinuxCNC w środowisku agenta, kopia bazowa QtDragon, rdzeń z atrapą.

## Cel tej sesji
Domknąć M0.

## Zakres pracy
1. Zaległości z DZIENNIK.md (001–007).
2. `docs/raporty/G0.md`: checklista użytkownika (WSL lub VM-A, uruchomienie ekranu linumert).
3. README: architektura w 10 linijkach (LinuxCNC, ekran, rdzeń, Plant).

## Kryteria akceptacji
- [ ] CI zielone
- [ ] G0.md gotowy
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 008 — Bufor i bramka G0` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `008 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-008` do `main` (commit z prefiksem `sesja 008:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
