# Sesja 046/084 · M3 Programowanie dialogowe · Podglądy 2D w formularzach

Kolejność: sesja 46 z 84 · poprzednia: sesja-045. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-046` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-046` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M3
Format .lnx, generatory cykli, panel dialogowy z podglądem 2D, biblioteka podprogramów o-word, integracja z plikami QtDragon.

## Cel tej sesji
Render preview_2d przez QPainter.

## Zakres pracy
1. Prymitywy: polyline, arc, circle, dimension, label (mm).
2. Widżet `Preview2D` (autoskalowanie, osie, przygotówka, ścieżki w kolorze akcentu).
3. Uzupełnij preview_2d we wszystkich generatorach.
4. Testy: prymitywy niepuste, render do QImage offscreen (QT_QPA_PLATFORM=offscreen).

## Kryteria akceptacji
- [ ] render offscreen działa w CI
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 046 — Podglądy 2D w formularzach` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `046 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-046` do `main` (commit z prefiksem `sesja 046:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
