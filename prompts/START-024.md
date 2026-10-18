# Prompt startowy: sesja 024, scenariusze, raport, check_requirements (równolegle z 022 i 025)

Model-Author: Claude · 2026-10-18. Najpierw [`START-PODZIAL.md`](START-PODZIAL.md) (zasady, worktree, testy),
potem pełny zakres w [`sesja-024.md`](sesja-024.md). Dodatkowo ta sesja tworzy **API awarii**, z którego
skorzysta panel w sesji 023.

## Zakres w tej sesji
1. `plant/server/linumert_plant/faults.py`: jedno API wstrzykiwania awarii w działający serwer Plant:
   E-STOP, awaria napędu, utrata X % ramek, opóźnienie odpowiedzi, krańcówka, zablokowanie osi, utrata
   falownika, zablokowany czujnik ATC; każda awaria z włączeniem i zdjęciem, opis w `docs/PLANT.md`.
   `server.py` należy do sesji 022: jeśli potrzebny jest punkt zaczepienia w serwerze, ma być minimalny
   i opisany w PR („Pliki spoza zakresu”). Konflikt przy scaleniu rozwiązuje sesja scalana później.
2. Zakres `sesja-024.md` 1–6: format scenariusza, `tools/run_scenario.py` (lokalnie; SSH do VM tylko jako
   opcja, test bez SSH), raport HTML ze statycznymi wykresami SVG do `docs/raporty/prototypy/`, scenariusze
   startowe, `tools/check_requirements.py` w `make test`, job CI `plant-matrix`.
3. Scenariusze bez LinuxCNC na atrapie mastera (CI); te same z LinuxCNC RIP jako testy `-m linuxcnc`
   (porty 47820–47829, start i zamknięcie przez `tests/rip_support.start_linuxcnc`/`stop_linuxcnc`).

## Kryteria akceptacji
Z `sesja-024.md`. Dodatkowo: każda awaria z listy ma test (włączenie, skutek, zdjęcie);
`check_requirements.py` zielony na `main` po scaleniu; `wsl-test.sh --linuxcnc` zielony.
