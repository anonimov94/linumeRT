# Sesja 025/084 · M1 Wirtualna obrabiarka Plant · Skrypty maszyn wirtualnych (VirtualBox)

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 25 z 84 · poprzednia: sesja-024. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-025` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-025` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
`tools/vm/` + `docs/VM.md`.

## Zakres pracy
1. PowerShell `tools/vm/create-vms.ps1` (VBoxManage): VM-A `linumert-ctl` (2–4 vCPU, 4 GB RAM, ISO LinuxCNC 2.9 — użytkownik pobiera sam, skrypt sprawdza sumę), VM-B `linumert-plant` (2 vCPU, 2 GB, Debian 12 netinst + plik preseed), sieć wewnętrzna `lrtnet`, host-only do panelu 8080 i SSH.
2. `tools/vm/post-install-ctl.sh` (instaluje repo, buduje komponenty HAL, konfiguracja plant) i `post-install-plant.sh` (zależności, usługa systemd `linumert-plant`).
3. Uwagi: Hyper-V/WSL a VirtualBox na Windows, wydajność, RT w VM nie jest prawdziwym RT (oczekiwany jitter) — Plant pracuje w trybie ramkowym, więc to akceptowalne.
4. `docs/VM.md` krok po kroku dla użytkownika (zrzuty niepotrzebne, komendy do skopiowania).

## Kryteria akceptacji
- [ ] skrypty przechodzą shellcheck / PSScriptAnalyzer (jeśli dostępny)
- [ ] VM.md kompletny
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 025 — Skrypty maszyn wirtualnych (VirtualBox)` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-025` do `main` (commit z prefiksem `sesja 025:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
