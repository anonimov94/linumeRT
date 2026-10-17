# Sesja 006/084 · M0 Fundament, prawo, środowisko · Rdzeń: model stanu maszyny i atrapa

Kolejność: sesja 6 z 84 · poprzednia: sesja-005. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-006` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-006` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M0
Repozytorium, CI, wytyczne IP i rejestr pochodzenia, budowa LinuxCNC w środowisku agenta, kopia bazowa QtDragon, rdzeń z atrapą.

## Cel tej sesji
Model migawki stanu i adaptery dla narzędzi poza ekranem (raporty, testy, scenariusze).

## Zakres pracy
1. `core/linumert/cnc/model.py`: `AxisSnapshot`, `MachineSnapshot` (pozycje zadane/rzeczywiste, homed, limity, tryb, stan interpretera, linia, override, wrzeciono, narzędzie, offsety, aktywne G/M, błędy, znacznik świeżości).
2. `cnc/linuxcnc_reader.py`: leniwy import `linuxcnc`, mapowanie `stat` → migawka (tylko odczyt).
3. `cnc/fake.py`: atrapa z wirtualnym zegarem (ruch, bazowanie, AUTO po liniach) do testów generatorów, symulacji i scenariuszy.
4. `docs/RDZEN.md`: po co jest rdzeń i jak ekran QtVCP z niego korzysta (import bezpośredni, bez serwera).

## Kryteria akceptacji
- [ ] ≥ 12 testów atrapy
- [ ] brak importu linuxcnc przy imporcie pakietu
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 006 — Rdzeń: model stanu maszyny i atrapa` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `006 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-006` do `main` (commit z prefiksem `sesja 006:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
