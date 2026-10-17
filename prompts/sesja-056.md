# Sesja 056/084 · M4 Symulacja i kolizje · Reguły kolizji lite

Kolejność: sesja 56 z 84 · poprzednia: sesja-055. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-056` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-056` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M4
Ścieżka, czas obróbki, przygotówka, materiał 2.5D, reguły kolizji lite, widok 3D 30 FPS, raport; walidacja czasu względem Plant.

## Cel tej sesji
K-301, K-302, K-303 (uproszczona), K-310, K-320, K-321 wg `docs/wymagania/NARZEDZIA_I_KOLIZJE.md` §3.

## Zakres pracy
1. Zdarzenia z linią, narzędziem, pozycją; opcja zatrzymania przy pierwszej kolizji.
2. Fixtures z błędnymi programami.
3. Testy pozytywne i negatywne na regułę.

## Kryteria akceptacji
- [ ] każda reguła ma 2 testy
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 056 — Reguły kolizji lite` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `056 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-056` do `main` (commit z prefiksem `sesja 056:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
