# Podprogramy linumeRT `o<lrt_...>`

Model-Author: Claude · 2026-10-20 (sesja 048). Plik generowany z `core/linumert/generators/subroutines.py`
(lista parametrów); opis ręczny poniżej tabeli.

Podprogramy wykonują ten sam ruch co generatory programu dialogowego (`face_mill`, `drill_holes`) —
test `tests/test_subroutines.py` porównuje wyjście interpretera rs274 LinuxCNC 2.9 dla obu.

## Instalacja

```bash
PYTHONPATH=core python3 -m linumert.generators.subroutines ~/linuxcnc/nc_files/user_macros
```

Katalog musi być w `[RS274NGC]SUBROUTINE_PATH` pliku INI maszyny (ścieżki według konfiguracji, nie na sztywno).
Nagłówki są w układzie NgcGui (`(info: ...)`, `#<nazwa> = #n (=domyślna opis)`), więc podprogramy
pojawiają się w zakładce NgcGui QtDragon, gdy katalog jest też w `[DISPLAY]NGCGUI_SUBFILE_PATH`.

## Wywołanie

Parametry w nawiasach kwadratowych, w kolejności z tabeli; brakujące na końcu = 0 w LinuxCNC,
więc podawaj wszystkie (wartości domyślne z tabeli dotyczą NgcGui i `Subroutine.call()`).

```
o<lrt_face_mill> call [0] [0] [100] [50] [0] [2] [1] [10] [70] [2] [0] [800] [200] [5]
```

Przed wywołaniem: narzędzie i obroty (np. `T1 M6 G43 H1`, `S8000 M3`), układ detalu. Podprogram nie
włącza wrzeciona ani chłodziwa i kończy na bezpiecznej Z (wiercenie: G80 na końcu). Niepoprawne
parametry przerywają program komunikatem `(abort, ...)`. NIEZWERYFIKOWANE NA SPRZĘCIE.

## `lrt_face_mill`

linumeRT planowanie zygzakiem lub jednokierunkowo, generator face_mill v1.

| # | Parametr | Domyślnie | Opis |
|---|---|---|---|
| 1 | `x0` | 0 | X min |
| 2 | `y0` | 0 | Y min |
| 3 | `x1` | 100 | X max |
| 4 | `y1` | 50 | Y max |
| 5 | `z_top` | 0 | Z powierzchni |
| 6 | `depth` | 1 | glebokosc calkowita |
| 7 | `step_down` | 1 | glebokosc przejscia |
| 8 | `tool_d` | 10 | srednica narzedzia |
| 9 | `stepover` | 70 | krok boczny proc. D |
| 10 | `overrun` | 2 | wybieg poza krawedz |
| 11 | `one_way` | 0 | 1 = jednokierunkowo |
| 12 | `feed` | 800 | posuw F |
| 13 | `plunge` | 200 | posuw wglebny |
| 14 | `safe_z` | 5 | bezpieczna Z |

## `lrt_drill_grid`

linumeRT otwory w siatce lub rzedzie, generator drill_holes v1.

| # | Parametr | Domyślnie | Opis |
|---|---|---|---|
| 1 | `x` | 0 | X pierwszego otworu |
| 2 | `y` | 0 | Y pierwszego otworu |
| 3 | `count` | 3 | otworow w rzedzie |
| 4 | `rows` | 1 | rzedow |
| 5 | `dx` | 10 | krok X |
| 6 | `dy` | 10 | krok Y |
| 7 | `cycle` | 81 | cykl 81 82 83 73 |
| 8 | `z_top` | 0 | Z powierzchni |
| 9 | `depth` | 5 | glebokosc |
| 10 | `r_plane` | 2 | plaszczyzna R nad powierzchnia |
| 11 | `peck` | 2 | krok Q dla 83 i 73 |
| 12 | `dwell` | 0.5 | postoj P dla 82 s |
| 13 | `feed` | 100 | posuw F |
| 14 | `retract` | 98 | powrot 98 lub 99 |

## `lrt_drill_circle`

linumeRT otwory na okregu lub luku, generator drill_holes v1.

| # | Parametr | Domyślnie | Opis |
|---|---|---|---|
| 1 | `x` | 0 | X srodka |
| 2 | `y` | 0 | Y srodka |
| 3 | `radius` | 20 | promien |
| 4 | `count` | 6 | liczba otworow |
| 5 | `angle` | 0 | kat pierwszego otworu |
| 6 | `sweep` | 360 | zakres 360 = pelny okrag |
| 7 | `cycle` | 81 | cykl 81 82 83 73 |
| 8 | `z_top` | 0 | Z powierzchni |
| 9 | `depth` | 5 | glebokosc |
| 10 | `r_plane` | 2 | plaszczyzna R nad powierzchnia |
| 11 | `peck` | 2 | krok Q dla 83 i 73 |
| 12 | `dwell` | 0.5 | postoj P dla 82 s |
| 13 | `feed` | 100 | posuw F |
| 14 | `retract` | 98 | powrot 98 lub 99 |
