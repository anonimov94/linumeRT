# Prompt startowy: sesja 022, panel Plant i pulpit MPG (równolegle z 024 i 025)

Model-Author: Claude · 2026-10-18. Najpierw [`START-PODZIAL.md`](START-PODZIAL.md) (zasady, worktree, testy),
potem pełny zakres w [`sesja-022.md`](sesja-022.md), z jedną zmianą: **punkt 3 (przyciski awarii)
przechodzi do sesji 023**, bo API awarii (`linumert_plant/faults.py`) powstaje równolegle w sesji 024.

## Zakres w tej sesji
1. Panel jako podpakiet `plant/server/linumert_plant/panel/` (FastAPI + WebSocket, statyczne pliki panelu w
   pakiecie), polecenie `python -m linumert_plant panel` albo opcja `serve --panel PORT`. Zależności
   (`fastapi`, `uvicorn`, do testów `httpx`) w opcjonalnej grupie `panel` w `pyproject.toml`; panel bez nich
   = czytelny błąd, nie wyjątek przy imporcie `linumert_plant`.
2. Telemetria z serwera (pozycja zadana i rzeczywista, błąd nadążania, moment, prędkość, zgubione kroki)
   bez blokowania pętli ramek: bufor pierścieniowy, panel czyta kopię, odświeżanie ≤ 20 Hz, okno 10 s.
   Wykresy uPlot (MIT): plik dołączony do pakietu, wpis w LICENCJE i PROVENANCE.
3. Suwaki parametrów `live` napędu (mechanizm z sesji 013), presety: zapis i odczyt.
4. Wirtualny pulpit: MPG (impulsy), wybór osi, krok, Start/Stop posuwu, przełącznik kluczykowy jako wejścia
   do LinuxCNC przez LRT-NET (bity wejść ramki v1; mapowanie w `plant.yaml`, opis w `docs/PLANT.md`).
5. Nagrywanie przebiegu do CSV.
6. Wygląd: `docs/design/makiety/06_panel_plant.png`, kolory wyłącznie z `docs/design/tokens.yaml`.

## Kryteria akceptacji
Z `sesja-022.md` (bez punktu 3). Dodatkowo: test API panelu na porcie z zakresu 47810–47819 albo 0; test
„zmiana masy w panelu zmienia przyspieszenie”; test wejść pulpitu przez atrapę mastera (`plant/server/test_master.py`);
`wsl-test.sh --linuxcnc` zielony (zmieniasz `server.py`).
