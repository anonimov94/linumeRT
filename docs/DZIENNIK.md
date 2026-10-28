# Dziennik lite

2026-10-28 · Model-Author: Codex
Wydzielono headless backend z pełnej edycji. Przeniesiono napędy do wspólnej warstwy,
usunięto GUI/HTTP i odłożone funkcje, dodano CLI oraz kontrolę granic architektury.
Wyniki weryfikacji i ograniczenia: `VALIDATION.md`.

2026-10-28 · Model-Author: Codex
Na prośbę o wizualną próbę rdzenia w konsoli dodano tools/console_demo.py i launcher
PowerShell/WSL. Odtwarzają zmierzoną telemetrię Plant C: ruch XYZ lub E-STOP,
bez GUI, HTTP i połączeń ze sprzętem. Rdzeń i wykonawca scenariuszy bez zmian.
