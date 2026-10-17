# Sesja 048/084 · M3 Programowanie dialogowe · Biblioteka podprogramów o-word

Kolejność: sesja 48 z 84 · poprzednia: sesja-047. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-048` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-048` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M3
Format .lnx, generatory cykli, panel dialogowy z podglądem 2D, biblioteka podprogramów o-word, integracja z plikami QtDragon.

## Cel tej sesji
Eksport generatorów jako podprogramy LinuxCNC.

## Zakres pracy
1. Dla wybranych cykli (kieszenie, wiercenie wzorów, rowki) wygeneruj podprogramy `o<lrt_pocket_rect> sub … endsub` w `user_macros/` z parametrami #1…#n.
2. Nagłówki zgodne z formatem NgcGui (sprawdź dokumentację), żeby działały w zakładce NgcGui QtDragon.
3. Dokumentacja wywołań w `docs/user/PODPROGRAMY.md`.
4. Test: wywołanie podprogramu przez interpreter (jeśli dostępny) lub lekser.

## Kryteria akceptacji
- [ ] podprogramy generują się z rejestru (test)
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 048 — Biblioteka podprogramów o-word` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `048 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-048` do `main` (commit z prefiksem `sesja 048:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
