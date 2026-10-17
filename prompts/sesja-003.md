# Sesja 003/084 · M0 Fundament, prawo, środowisko · Spike: LinuxCNC 2.9 w środowisku agenta

Kolejność: sesja 3 z 84 · poprzednia: sesja-002. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-003` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-003` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M0
Repozytorium, CI, wytyczne IP i rejestr pochodzenia, budowa LinuxCNC w środowisku agenta, kopia bazowa QtDragon, rdzeń z atrapą.

## Cel tej sesji
Zbudować LinuxCNC 2.9 (run-in-place, uspace) w kontenerze agenta i opisać wynik (D20).

## Zakres pracy
1. `tools/ci/build-linuxcnc.sh`: klon gałęzi `2.9` z github.com/LinuxCNC/linuxcnc (płytko), instalacja zależności przez apt (na podstawie `debian/configure` i `debian/control`; zapisz listę pakietów w skrypcie), `./autogen.sh && ./configure --with-realtime=uspace --disable-check-runtime-deps && make -j$(nproc)` w `src/`, katalog docelowy `~/.cache/linuxcnc-2.9` (pomiń, gdy już zbudowany).
2. Uruchom `scripts/rip-environment` i `linuxcnc` z przykładową konfiguracją sim w trybie headless (DISPLAY = `halui` lub skrypt czekający) oraz sprawdź `python3 -c 'import linuxcnc'`.
3. Spróbuj uruchomić QtDragon pod `xvfb-run` i zrobić zrzut ekranu (`import -window root` lub Qt grab) → `docs/raporty/spike_qtdragon.png`.
4. Zmierz czas budowy i zapisz w `docs/raporty/SPIKE_LINUXCNC.md` (co działa, co nie, błędy, obejścia).
5. Workflow GitHub Actions `linuxcnc.yml` z cache katalogu budowy (uruchamiany ręcznie i co tydzień).
6. Uaktualnij D20 w DECYZJE.md: PRZYJĘTA (działa) lub ODRZUCONA z opisem planu B.

## Kryteria akceptacji
- [ ] SPIKE_LINUXCNC.md z jednoznacznym wynikiem
- [ ] jeśli działa: `make test-linuxcnc` uruchamia smoke test sim
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Poza zakresem
Nie modyfikuj kodu LinuxCNC.

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 003 — Spike: LinuxCNC 2.9 w środowisku agenta` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `003 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-003` do `main` (commit z prefiksem `sesja 003:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
