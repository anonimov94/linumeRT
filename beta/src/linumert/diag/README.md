# linumert.diag

Model-Author: Codex · 2026-10-20

W HMI: **Diagnostyka → Raport środowiska…**. Raport można zaznaczyć i skopiować.
Bez GUI: `PYTHONPATH=core python3 -m linumert.diag.doctor` lub z `--json`.
Raport dotyczy interpretera, którym uruchomiono polecenie (venv/system mogą się różnić).

Zakres: Python, dystrybucja, obecność modułów i programów w PATH, nazwa jądra oraz
odczyt `/sys/kernel/realtime`. Nie importuje LinuxCNC/HAL i nie wykonuje znalezionych narzędzi.
Nie otwiera sieci, nie instaluje pakietów i nie zmienia plików.

Kod wyjścia 0 oznacza zebranie raportu, a nie gotowość do CNC. Braki są w polach `checks`
ze statusem `missing`; nieprzydatny Python (<3.11) daje kod 1. JSON ma `schema_version=1`.
Brak LinuxCNC/Qt w środowisku offline jest pokazywany jawnie i nie przerywa raportu.

To część sesji 078: wersja/działanie LinuxCNC, aktywne komponenty HAL, uprawnienia urządzeń,
osiągalność Plant, pomiar latencji i kreator pierwszego uruchomienia pozostają do wykonania.
Obecność narzędzia/modułu ani flaga jądra nie potwierdzają działania lub czasu reakcji.
`hardware_verified` zawsze false. NIEZWERYFIKOWANE NA SPRZĘCIE.
