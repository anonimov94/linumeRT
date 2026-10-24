# Sesja 027/084 · M2 Ekran linumeRT na bazie QtDragon · Własny system projektowy ekranu

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 27 z 84 · poprzednia: sesja-026. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-027` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-027` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M2
Własny system projektowy i kompozycja ekranu, tryby, JOG/MPG, MDI, AUTO, narzędzia, zerowanie i sonda, zmiana narzędzia, alarmy, role, PL/EN.

## Cel tej sesji
Design system dla QtVCP: QSS + ikony + fonty.

## Zakres pracy
1. Źródło prawdy: `docs/design/tokens.yaml` i tablica `docs/design/marka/tablica_marki.png`. Generator `tools/gen_qss.py` (tokens.yaml → `screens/linumert/linumert.qss`).
2. Fonty IBM Plex Sans i JetBrains Mono (OFL) dołączone do ekranu, wpis w PROVENANCE.md z plikiem licencji.
3. Ikony: użyj zestawu `docs/design/ikony/*.svg` (31 ikon, obrys 1.75); brakujące dorysuj w tym samym stylu; każda w PROVENANCE.
4. Zasady: przyciski ≥ 44 px, odstęp 8 px, DRO ≥ 28 px, kolor nigdy jedynym nośnikiem.
5. Zastosuj QSS do ekranu i zrób zrzut (jeśli możliwe).

## Kryteria akceptacji
- [ ] test: każda ikona SVG ma wpis w PROVENANCE
- [ ] QSS generowany z tokenów (test)
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 027 — Własny system projektowy ekranu` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-027` do `main` (commit z prefiksem `sesja 027:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
