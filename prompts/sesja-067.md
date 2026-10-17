# Sesja 067/084 · M5 Konfiguracja maszyn hobbystów · Kreator konfiguracji maszyny

Kolejność: sesja 67 z 84 · poprzednia: sesja-066. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-067` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-067` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M5
machine.yaml → INI/HAL dla sim, Plant, step/dir, EtherCAT, VFD; 4/5 osi; ATC; kreator; diagnostyka napędów; asystent strojenia na Plant.

## Cel tej sesji
Kreator Qt dla roli serwis.

## Zakres pracy
1. Wygląd wg `docs/design/makiety/05_kreator_konfiguracji.png`. Kroki: maszyna → napędy → wrzeciono → magazyn → limity/bazowanie → pulpit → podsumowanie (diff) → generuj.
2. Wariant „wygeneruj też plant.yaml” do testu nowej maszyny na Plant przed sprzętem.
3. Przywracanie poprzedniej konfiguracji.

## Kryteria akceptacji
- [ ] test modelu kreatora
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 067 — Kreator konfiguracji maszyny` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `067 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-067` do `main` (commit z prefiksem `sesja 067:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
