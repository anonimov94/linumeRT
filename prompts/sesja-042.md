# Sesja 042/084 · M3 Programowanie dialogowe · Generatory: wiercenie i gwintowanie

Kolejność: sesja 42 z 84 · poprzednia: sesja-041. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-042` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-042` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M3
Format .lnx, generatory cykli, panel dialogowy z podglądem 2D, biblioteka podprogramów o-word, integracja z plikami QtDragon.

## Cel tej sesji
Generatory otworów.

## Zakres pracy
1. Wzory pozycji: pojedyncze, lista, rząd, siatka, okrąg/łuk.
2. Cykle G81/G82/G83/G73, G84 (ostrzeżenie), G33.1 przy `spindle_sync`, R-plane, G98/G99, G80.
3. Walidacja głębokości i skoku, preview_2d.

## Kryteria akceptacji
- [ ] golden tests
- [ ] wynik używa G8x
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 042 — Generatory: wiercenie i gwintowanie` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `042 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-042` do `main` (commit z prefiksem `sesja 042:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
