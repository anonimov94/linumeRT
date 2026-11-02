# linumert.machine

Model stanu maszyny, atrapa maszyny do testow oraz model machine.yaml.

| Moduł | Zawartość |
|---|---|
| `schema.py` | schemat Pydantic v2 `machine.yaml` (jedno źródło prawdy o maszynie, sesja 010) |
| `validate.py` | reguły spójności (24 reguły; błędy po polsku) |
| `configgen.py` | generator INI/HAL z machine.yaml: `plant` (lrt_net), `sim` (sesja 062) |
| `configgen_hw.py` | wyjście `hardware`: step/dir Mesa 7i96S/7i76E i port równoległy, kontrakt bezpieczeństwa |
| `config_build.py` | CLI `linumert-config build` (podgląd diff, zapis z kopią zapasową) |
| `config_files.py` | kopia zapasowa i diff katalogu konfiguracji (Codex, krok 1 sesji 062) |

Przykładowe maszyny: `config/machines/`. Opis: `docs/PLANT.md`.

Wspólny schemat odrzuca NaN oraz ±nieskończoność we wszystkich polach liczbowych
typu float (także wektorach i polach opcjonalnych), przed walidacją spójności
i budową Plant. Błędy wskazują ścieżkę pola po polsku. Obejmuje też liczby
podane jako tekst i przepełnienie, np. `1e999`. Nadpisania napędów w `overrides`
sprawdza osobno walidator szablonów, tymi samymi zakresami co bibliotekę.
Testy regresyjne: `tests/test_machine_finite.py` oraz zapis/przeładowanie w
`tests/test_editor_api.py` (REQ-VM-11, REQ-QA-03).
