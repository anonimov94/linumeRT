# Classic × Neon — odbiór N1 i N4 na prawdziwym LinuxCNC (sim, AUTO)

Model-Author: Claude · 2026-10-25 · NIEZWERYFIKOWANE NA SPRZĘCIE (LinuxCNC 2.9 RIP, Debian 12 w WSL, Xvfb).
Skrypt: `tools/dev/neon_accept.py` (uruchomienie: `bash tools/dev/neon_accept.sh KATALOG`, zajmuje blokadę `linuxcnc`).
Surowe dane: `neon_accept.json` (≈1070 próbek co ~0,1 s), zrzuty 1280×800 w tym katalogu.

## Co zrobiono
- **N1**: `load_ngc(linumert_neon_demo.ngc)` z prawdziwym `gcode.parse` = `demo_toolpath()` (linie, rapidy, posuwy,
  końce ±0,001 mm, długości ±0,5 %); test `@pytest.mark.linuxcnc` w `tests/test_toolpath.py`.
  Interpreter dodaje na początku jeden ruch zerowy do punktu startu (test go pomija).
- **Przyczyny awarii wczytywania** (potwierdzone gdb / logiem):
  1. `T1 M6` bez zmapowanych danych narzędzi → SIGSEGV w `tool_mmap_mutex_get`. Mapowanie robi
     `linuxcnc.stat().poll()` (samo `stat()` nie wystarcza); bez działającego LinuxCNC słowa T/M6 są wycinane z kopii
     (numery linii bez zmian) i podgląd dostaje notatkę.
  2. `INI_FILE_NAME` w środowisku + `REMAP = M6 ngc=lrt_m6` (ścieżka podprogramów względem cwd) → błąd
     „Bad character 'g'" albo SIGSEGV, zależnie od katalogu uruchomienia monitora. `load_ngc` analizuje program
     bez INI maszyny.
  3. Brak pliku zmiennych parametrów → komunikat `link (updating variable file)`; plik tworzony wcześniej.
- **N4**: sim w AUTO z demo (bazowanie, G54 X100 Y100 Z-50, potwierdzenie M6 przez `sim_toolchange`), obok monitor
  Classic × Neon (`classic-digital`, `neon-punk`, pl). Program ukończył się (INTERP_IDLE).

## Zgodność z LinuxCNC (maszyna wstrzymana w środku programu, po 2,5 s)
| Wielkość | NML | Monitor |
|---|---|---|
| `motion_line` | 59 | 59 |
| `distance_to_go` | 2,4316 mm | 2,4316 mm |
| DRO X/Y/Z | 140,1387 / 130,1387 / −56,0 | 140,1387 / 130,1387 / −56,0 |

Zgodne dokładnie (kryterium ±0,01 mm). W ruchu próbka monitora jest starsza o 0,1–0,3 s, więc bezpośrednie
porównanie w locie (`samples` w JSON) pokazuje różnice rzędu 1–3 mm, a na granicach ruchów chwilowo większe —
to opóźnienie odczytu (osobny proces `linumert_skin_status.py` co ≥ 0,2 s), nie błąd modelu.
Uwaga: DTG modelu ścieżki (`dtg_scene`, liczone z pozycji) różni się od `stat.distance_to_go` o ok. 1–2 mm
(w pauzie: 4,44 vs 2,43 mm); widok w trybie live pokazuje wartość z LinuxCNC (`reported_dtg`).

## Czas klatki (ms/klatkę, HUD, Xvfb offscreen QPainter, scena po zakończeniu programu)
| Preset | Detal | Maszyna |
|---|---|---|
| Ekonomiczny | 2,19 | 2,87 |
| Zrównoważony | 3,21 | 2,71 |
| Wysoki | 3,73 | 3,18 |

Zbieżne z pomiarami Claude (WSL offscreen: detal 3–7 ms). To nie jest pomiar VNC/WSLg ani sprzętowego GPU.

## Uwagi dla Claude (monitor)
- Zrzuty: `01-start`, `02-srodek` (pauza), `03-koniec`, `04-preset-*`.
- Monitor pokazuje „Program niepodłączony" w panelu PROGRAM i `T —`, `F —`, `S —` w panelach Narzędzia/Posuw,
  mimo działającego LinuxCNC (próbka ma `file`, `motion_line`, pozycje; nie ma narzędzia, F, S).
- Zmiana skórek/motywów (N3) i ustawienia ⚙ po restarcie nie były przedmiotem tego odbioru.
