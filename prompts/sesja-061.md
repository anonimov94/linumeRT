# Sesja 061/084 · M5 Konfiguracja maszyn hobbystów · machine.yaml: napędy i wejścia rzeczywiste

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 61 z 84 · poprzednia: sesja-060. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-061` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-061` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M5
machine.yaml → INI/HAL dla sim, Plant, step/dir, EtherCAT, VFD; 4/5 osi; ATC; kreator; diagnostyka napędów; asystent strojenia na Plant.

## Cel tej sesji
Rozszerzyć schemat z sesji 010 o sprzęt rzeczywisty — REQ-VD-06.

## Zakres pracy
1. Sekcja `real:` w szablonach napędów (REQ-VD-06): typ sterownika (stepgen_parport, stepgen_mesa, ethercat_cia402), skalowanie, mapowanie pinów lcec/hm2; wpisy dla szablonów biblioteki.
2. W machine.yaml: wybór `target: plant | sim | hardware` bez zmiany reszty opisu maszyny.
3. Wrzeciono (pwm | hy_vfd | mb2hal | ethercat), pulpit, E-STOP rzeczywisty.
4. Testy: ten sam plik generuje opis Plant i opis sprzętowy; test `# REQ-VD-06`. Oznacz NIEZWERYFIKOWANE NA SPRZĘCIE.

## Kryteria akceptacji
- [ ] test_template_real_mapping zielony
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 061 — machine.yaml: napędy i wejścia rzeczywiste` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-061` do `main` (commit z prefiksem `sesja 061:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
