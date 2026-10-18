# Sesja 029/084 · M2 Ekran linumeRT na bazie QtDragon · Tryby, JOG i pulpit MPG

Kolejność: sesja 29 z 84 · poprzednia: sesja-028. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-029` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-029` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M2
Własny system projektowy i kompozycja ekranu, tryby, JOG/MPG, MDI, AUTO, narzędzia, zerowanie i sonda, zmiana narzędzia, alarmy, role, PL/EN.

## Cel tej sesji
Ręczna obsługa i pulpit sprzętowy.

## Zakres pracy
1. Przyciski trybów JOG / MDI / AUTO, przyrosty 0.001–1 mm, ciągły, prędkość JOG, bazowanie wszystkich/pojedynczo — na bazie akcji QtVCP (`ACTION`).
2. Koncepcja fizycznego pulpitu: `docs/design/makiety/07_pulpit_operatora.png`. Pulpit przez HAL: piny w INI `[LINUMERT]` dla MPG (licznik impulsów), wyboru osi, kroku, Start/Stop posuwu, klucza poziomu dostępu; komponent `hal/lrt_pendant.comp` lub gotowe komponenty LinuxCNC (`ilowpass`, `mux`) — wybierz i opisz.
3. Wirtualny pulpit z panelu Plant (sesja 022) podłączony przez LRT-NET.
4. Scenariusz Plant `pendant_jog`: MPG obraca o 100 impulsów → oś przesuwa się o oczekiwaną drogę.

## Kryteria akceptacji
- [ ] scenariusz pendant_jog przechodzi (lub opis blokady)
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 029 — Tryby, JOG i pulpit MPG` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `029 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-029` do `main` (commit z prefiksem `sesja 029:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
