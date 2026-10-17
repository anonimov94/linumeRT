# Sesja 066/084 · M5 Konfiguracja maszyn hobbystów · Automatyczna zmiana narzędzia

Kolejność: sesja 66 z 84 · poprzednia: sesja-065. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-066` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-066` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M5
machine.yaml → INI/HAL dla sim, Plant, step/dir, EtherCAT, VFD; 4/5 osi; ATC; kreator; diagnostyka napędów; asystent strojenia na Plant.

## Cel tej sesji
Remap M6 + emulacja ATC w Plant.

## Zakres pracy
1. Plant: magazyn i pozycje wymiany już istnieją (sesja 020, REQ-VM-08/09) — użyj ich, nie twórz drugiego modelu.
2. Remap M6 (sprawdź składnię 2.9) dla rack i carousel, obsługa błędów (brak zacisku → stop, E-alarm).
3. Widok Magazyn w ekranie (gniazda ↔ narzędzia z ToolDB).
4. Scenariusze `atc_rack_cycle`, `atc_clamp_fail`. Oznacz NIEZWERYFIKOWANE NA SPRZĘCIE.

## Kryteria akceptacji
- [ ] oba scenariusze dają oczekiwany wynik
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 066 — Automatyczna zmiana narzędzia` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `066 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-066` do `main` (commit z prefiksem `sesja 066:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
