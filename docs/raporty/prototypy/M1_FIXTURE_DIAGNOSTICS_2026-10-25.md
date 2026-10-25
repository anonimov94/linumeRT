# M1 — diagnostyka timeoutów fixture

Model-Author: Codex · 2026-10-25. Autokontrola, bez niezależnego przeglądu.
NIEZWERYFIKOWANE NA SPRZĘCIE. LEGACY-RUNTIME i G1 pozostają partial.

Po FAIL serii #152 (main 276f34c) dodano do drivera test_plant_linuxcnc:
etap, NML position/actual_position/velocity/task/interp/limit/homed/joints,
błędy error_channel oraz dotychczasowe wyniki programów. Timeout zapisuje
snapshot, a atexit zapisuje driver_diagnostics.json także po asercji.
To odczyty userspace; nie są śladem RT ani chwilą wyzwolenia błędu.
Nie zmieniono progów, timeoutów, ruchów, modelu ani regulatorów.

Fixture zachowuje driver.log oraz opróżnia scalony stdout/stderr LinuxCNC do
linuxcnc-console.log w osobnym wątku. Po zatrzymaniu sprawdza koniec kolektora;
przy poprawnym końcu wymaga pliku JSON, etapu complete i braku snapshot_error.
Trzy testy offline obejmują wymuszony timeout/asercję, brak NML i zapis logu.
Po korekcie test usuwa __file__ przed wywołaniem hooka. Wynik: 3 PASS, ruff PASS,
jawne -m 'not linuxcnc'; nie uruchamiały lokalnego LinuxCNC.

## Lokalna próba 110e7d6 — diagnostyka nieodebrana

Jeden test istniejącej fixture zakończył się PASS w 137,32 s, ale autokontrola
artefaktów ujawniła NameError: __file__ podczas atexit. JSON nie powstał.
Test ruchu PASS nie oznaczał odbioru diagnostyki; nie zaliczono jej jako PASS.
Zachowano log drivera z wyjątkiem, JUnit i hashe w
[M1_FIXTURE_DIAGNOSTICS_2026-10-25.json](M1_FIXTURE_DIAGNOSTICS_2026-10-25.json).
Scalony log konsoli LinuxCNC ma 0 bajtów w tej próbie; nie zawiera dowodów awarii.
Pełne pliki: /home/codex/linumert-m1-fixture-diagnostics-20261025/build/acceptance.
Obie lease Codex/m1-fixture-diagnostics-58277 zwolnione, oba katalogi puste,
proces narzędzia 33797 zakończony. Nie powtórzono pełnej serii M1.

Poprawka c217745 wyznacza ścieżkę z sys.argv[0] przed zamknięciem interpretera,
zachowuje ją w argumencie hooka i wymaga diagnostycznego JSON w fixture.
Odbiór runtime poprawionej wersji i wymagane CI pozostają otwarte w #153.
Żaden wynik nie ustala przyczyny wcześniejszego LIMIT_TRIP lub historycznego X.
