# M1 — wersja źródeł historycznego uchybu X

Model-Author: Codex · 2026-10-25. Autokontrola. Audyt źródeł i zachowanego logu,
bez ponownego uruchamiania LinuxCNC. LEGACY-RUNTIME/G1 nadal otwarte.

Historyczna próba 8: `d643a97c2f676f468b1aafe61a49053590814770`.
Porównanie: `46a15b0a7b8b14ce5af958eb421e41bc464c44e5` (main po odbiorze #142).
Log zachował 12 PASS / 1 FAIL, ukończony first_motion i maksimum X 0,3 mm przy
progu 0,2 mm, ale nie ślad cykli w chwili maksimum. Informację o źródłach uzupełniono
porównaniem SHA-256 plików z nadal istniejącego historycznego checkoutu.

## Co zmieniło się między wersjami

| Element | Historyczny d643a97 | Obecny main |
|---|---|---|
| Plant cycle_ns | 1 000 000 | 1 000 000 |
| Plant substeps | 1 | 4 |
| lrt_machine_step_cycle / interpolacja CSP #116 | brak | obecna |
| machine.yaml, first_motion YAML/NGC, hal/lrt_net.comp | identyczne pliki | identyczne pliki |
| plant/core/drive.c | identyczny plik | identyczny plik |
| servo_400w/750w | bez sekcji real | dodana wyłącznie sekcja real/PDO |

Commit `9d78470` wprowadzający interpolację i domyślne cztery podkroki nie jest
przodkiem d643a97, jest przodkiem obecnego main. Pliki machine.c i plant.yaml
w `/home/codex/linumert-m1-runtime-20261024` nadal mają dokładnie hashe wersji d643a97.
Porównanie źródeł nie zastępuje zachowania binariów i pełnego środowiska dawnej próby.

Runner LinuxCNC w obu wersjach uruchamia Plant z
`config/plant/linumert_plant_xyz/plant.yaml` i nie przekazuje `scen.substeps`
jako argumentu CLI. Rzeczywisty podział tego toru wynika z tego pliku Plant,
nie z samego domyślnego pola dataclass scenariusza. Historyczny krok integratora
wynosił zatem 1 ms, a obecny nominalnie 0,25 ms.

## Granice wniosku

Próby historyczna i obecne nie dotyczą identycznej wersji integracji numerycznej.
Nie wolno jednak uznać samej obecności #116 za wyjaśnienie 0,3 mm: poprawka
dotyczy także sposobu podawania celu w podkrokach, a dawna konfiguracja miała n=1.
W obecnym kodzie n=1 zachowuje bezpośredni cel, bez interpolacji między podkrokami.
Nie ma podstaw do przypisania dawnego maksimum samemu n-krotnemu impulsowi FF.

Bez śladu w chwili historycznego maksimum nadal nie można oddzielić wkładu
fizyki/integratora, wieku sprzężenia i obciążenia hosta. Nowa gotowość napędów
przed bazowaniem rozwiązuje wykazany problem startup Z, nie dowodzi naprawy X.
Nie zmieniono modelu, ramp ani progu. Nie wykonano pełnej serii.

## Dowody i dalszy krok

[JSON](M1_X_BASELINE_2026-10-25.json): pełne SHA rewizji, hashe porównywanych plików,
relacja przodków i hash historycznego trial-8.log. Pełny log:
`/home/codex/linumert-m1-runtime-20261024/build/m1-repeat-ready/trial-8.log`.

Następny pomiar powinien używać aktualnej wersji po gotowości napędów, jawnie
zapisanego plant.yaml oraz śladu samplera obejmującego X i wiek sprzężenia.
Najpierw można przeanalizować już zachowany ciągły ślad #141: relację uchybu
motion-controller do wartości command/feedback z poprzedniego końca cyklu.
Nie wyciągać przyczyny z porównania niespójnych faz ani podnosić progu dla PASS.
