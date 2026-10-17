# Sesja 017/084 · M1 Wirtualna obrabiarka Plant · Komponent HAL lrt_net

Kolejność: sesja 17 z 84 · poprzednia: sesja-016. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-017` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-017` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Komponent `hal/lrt_net.comp` (C, halcompile) dla uspace.

## Zakres pracy
1. Wzoruj się na sposobie, w jaki hm2_eth używa UDP w uspace (tylko dokumentacja i ogólna idea; własny kod): gniazdo nieblokujące otwierane w `rtapi_app_main`, w funkcji RT: wysłanie ramki, odbiór odpowiedzi poprzedniego cyklu, brak alokacji.
2. Piny na oś w układzie zbliżonym do lcec CiA 402 (controlword, statusword, target-position, actual-position, mode, error-code) + piny skalowania; piny I/O i wrzeciona; piny diagnostyczne (utracone ramki, opóźnienie).
3. Komponent `hal/lrt_cia402.comp`: obsługa maszyny stanów CiA 402 po stronie mastera (enable/fault reset) z pinami zgodnymi z kontraktem D05 — używany także z lcec w M5. Sprawdź, czy istnieje gotowy komponent GPL o tej funkcji w linuxcnc-ethercat; jeśli tak, opisz porównanie i zdecyduj (DECYZJE).
4. Testy: kompilacja z atrapą nagłówków HAL w CI; z LinuxCNC (jeśli dostępny) — `halcompile --install` i test z serwerem Plant na localhost.
5. W `lrt_cia402`: sekwencja bazowania w napędzie (tryb 6) i piny zredukowanego momentu do bazowania na zderzak (sesja 015).

## Kryteria akceptacji
- [ ] komponent kompiluje się
- [ ] dokumentacja pinów w HAL_KONTRAKT.md
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 017 — Komponent HAL lrt_net` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `017 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-017` do `main` (commit z prefiksem `sesja 017:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
