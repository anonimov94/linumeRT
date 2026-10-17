# Sesja 041/084 · M3 Programowanie dialogowe · Generatory: kieszenie

Kolejność: sesja 41 z 84 · poprzednia: sesja-040. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-041` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-041` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M3
Format .lnx, generatory cykli, panel dialogowy z podglądem 2D, biblioteka podprogramów o-word, integracja z plikami QtDragon.

## Cel tej sesji
pocket_rect, pocket_circle.

## Zakres pracy
1. Parametry jak w planie v1 (naroża, obrót, przejścia, krok, wejście pionowe/rampa/helisa, współ/przeciwbieżne, naddatki, wykańczanie).
2. Własny algorytm offsetów; łuki G2/G3.
3. Walidacja (P-5003 itd.), preview_2d.
4. Test na Plant (marker linuxcnc lub lockstep z atrapą): wykonanie kieszeni bez przekroczenia okna błędu nadążania na profilu routera krokowego.

## Kryteria akceptacji
- [ ] golden tests
- [ ] scenariusz pocket_run (jeśli dostępny)
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 041 — Generatory: kieszenie` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `041 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-041` do `main` (commit z prefiksem `sesja 041:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
