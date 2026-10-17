# Sesja 004/084 · M0 Fundament, prawo, środowisko · Konfiguracja sim 3 osie z QtDragon

Kolejność: sesja 4 z 84 · poprzednia: sesja-003. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-004` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-004` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M0
Repozytorium, CI, wytyczne IP i rejestr pochodzenia, budowa LinuxCNC w środowisku agenta, kopia bazowa QtDragon, rdzeń z atrapą.

## Cel tej sesji
Konfiguracja `config/sim/linumert_xyz/` z QtDragon i kontraktem sygnałów D05.

## Zakres pracy
1. Na bazie przykładowej konfiguracji QtDragon z LinuxCNC 2.9 (sprawdź pliki `configs/sim/qtdragon/`) utwórz własne INI/HAL: trivkins, X 0..600, Y 0..400, Z −120..0 mm, `sim_spindle`, symulowane bazowanie, `DISPLAY = qtvcp qtdragon`. Zachowaj nagłówki licencyjne i wpisz pochodzenie w PROVENANCE.md.
2. Sygnały `linumert.j0.pos-cmd`, `.pos-fb`, `.enable`, `linumert.spindle.*`, `linumert.io.estop-ok` itd. — opis w `docs/HAL_KONTRAKT.md`.
3. tool.tbl (5 narzędzi), 3 programy testowe w `config/sim/nc_files/`.
4. `docs/SIM_WSL.md`: uruchomienie w WSL (WSLg) z pakietów LinuxCNC lub z budowy RIP; typowe problemy.
5. Test: walidacja INI (configparser) i obecność sygnałów kontraktu; z markerem linuxcnc — uruchomienie headless na 20 s.

## Kryteria akceptacji
- [ ] HAL_KONTRAKT.md opisuje wszystkie sygnały
- [ ] test walidacji przechodzi
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 004 — Konfiguracja sim 3 osie z QtDragon` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `004 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-004` do `main` (commit z prefiksem `sesja 004:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
