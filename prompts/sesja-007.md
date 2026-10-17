# Sesja 007/084 · M0 Fundament, prawo, środowisko · Katalog alarmów i tłumaczenia

Kolejność: sesja 7 z 84 · poprzednia: sesja-006. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-007` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-007` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M0
Repozytorium, CI, wytyczne IP i rejestr pochodzenia, budowa LinuxCNC w środowisku agenta, kopia bazowa QtDragon, rdzeń z atrapą.

## Cel tej sesji
Katalog W/E/K/P i mechanizm tłumaczeń Qt.

## Zakres pracy
1. `core/linumert/alarms/catalog.yaml` + loader z walidacją: W-2104, W-2105, W-2110, W-2120, W-2130, E-1000, E-1001, E-1100, E-1200, E-4000…E-4010 (EtherCAT / LRT-NET), E-4100…E-4105 (VFD), E-4200…E-4210 (napędy CiA 402: fault, błąd nadążania, przeciążenie), K-301…K-321, P-5001…P-5010. Teksty własne PL/EN.
2. Moduł `alarms/manager.py` (raise/clear/ack/historia w pamięci) niezależny od UI.
3. Ekran: plik `.ts` dla PL, skrypt `tools/i18n.sh` (pylupdate5/lrelease), zasada: wszystkie nowe teksty przez `tr()`.
4. Testy katalogu i managera.

## Kryteria akceptacji
- [ ] kody unikalne, oba języki obecne (test)
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 007 — Katalog alarmów i tłumaczenia` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `007 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-007` do `main` (commit z prefiksem `sesja 007:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
