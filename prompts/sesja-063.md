# Sesja 063/084 · M5 Konfiguracja maszyn hobbystów · Generator EtherCAT (lcec, CiA 402)

Kolejność: sesja 63 z 84 · poprzednia: sesja-062. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-063` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-063` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M5
machine.yaml → INI/HAL dla sim, Plant, step/dir, EtherCAT, VFD; 4/5 osi; ATC; kreator; diagnostyka napędów; asystent strojenia na Plant.

## Cel tej sesji
ethercat-conf.xml + HAL dla lcec.

## Zakres pracy
1. Sprawdź dokumentację linuxcnc-ethercat ≥ 1.15 (ogólny CiA 402), zapisz źródła i niepewności w docs/ETHERCAT.md.
2. XML (master, slave per napęd, CSP, DC), HAL z `lrt_cia402` (z sesji 017) — te same sygnały co w wariancie plant.
3. Profile wstępne Leadshine / Rtelligent. Oznacz NIEZWERYFIKOWANE NA SPRZĘCIE.
4. Test: diff HAL plant vs ethercat różni się tylko warstwą napędu (test strukturalny).

## Kryteria akceptacji
- [ ] test strukturalny przechodzi
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 063 — Generator EtherCAT (lcec, CiA 402)` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `063 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-063` do `main` (commit z prefiksem `sesja 063:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
