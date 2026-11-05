# Wydajność ścieżek obliczeniowych poza RT — 2026-11-05

Model-Author: Claude. Gałąź `claude/natywne-przyspieszenia`. Wszystko poza RT (CLAUDE.md §5);
symulacja nadal jako osobny proces z `nice` ≥ 10. NIEZWERYFIKOWANE NA SPRZĘCIE (pomiar dotyczy
obliczeń na PC, nie sterowania maszyną).

## Jak mierzono

- WSL `linumeRT-Debian12`, Python 3.11.2, numpy 2.4.6, gcc 12.2, 12 wątków, czyste klony w
  `~/linumert-test` (nie `/mnt/c`), `nice -n 10`, RIP LinuxCNC 2.9 w środowisku (moduł `gcode`),
  ale LinuxCNC nie działa.
- Skrypt: `tools/bench_wydajnosc.py` (`time.perf_counter`, najlepszy z 3 przebiegów; `--profile`
  daje cProfile). Kolumny: **przed** = `main` 91af65b z tym samym skryptem; **python** = ta gałąź
  z `LINUMERT_NATIVE=0` (ścieżka referencyjna, z wektoryzacją numpy); **natywna** = ta gałąź
  z biblioteką C. „×” = przed / natywna.
- Programy: `config/sim/nc_files/linumert_*.ngc` (pliki z `T`/`M6` bez działającego LinuxCNC
  idą przez interpreter podzbioru — próba rs274 w procesie potomnym kończy się awarią, por.
  DZIENNIK 2026-11-01) oraz programy z generatorów: kieszeń 60×40×6 + planowanie 100×80 +
  kreskowanie krzyżowe (500 odcinków) i płaskorzeźba z syntetycznego STL 40×40 mm, 1458 trójkątów,
  frez kulisty D3, krok 0,1 mm, odstęp 0,5 mm (32 644 odcinki).
- Symulacja offline (`linumert_sim.offline.simulate`) mierzona ze źródłem ścieżki, które
  zadziałało (bez kosztu nieudanej próby rs274); czas obejmuje odczyt ścieżki.

Porównanie po integracji do pełnego projektu, wraz z surowymi danymi i ograniczeniami:
[NATIVE_INTEGRATION_2026-11-05.md](NATIVE_INTEGRATION_2026-11-05.md).
Opis historycznej metody powyżej pochodzi od Claude; nowy pomiar Codex porównuje
Python/C na aktualnym kodzie, nie odtwarza kolumny „przed” z main 91af65b.

## Co spowalniało (pomiar przed zmianą)

cProfile na `main` (czasy z profilerem są ok. 1,5–2× dłuższe):

| Zadanie | Funkcja | Udział | Dlaczego |
|---|---|---:|---|
| `plan_relief` (24,8 s) | `ball_tip_height` × 32 481 punktów | 99 % | ok. 30 wywołań numpy na punkt, z czego 13 s to same redukcje na małych tablicach; filtr trójkątów liczony od nowa dla każdego punktu |
| `simulate` kieszeń+planowanie (4,1 s) | `StockMap.cut` → `_stamp` (40 957 stempli) | 79 % | pętla próbek w Pythonie, na każdą kilkanaście operacji numpy na oknie kilkuset komórek |
| `simulate` płaskorzeźba (5,1 s) | `StockMap.cut` 48 %, `SimEngine._loads` 20 %, odczyt ścieżki 12 % | | jak wyżej oraz sumy okna mocy po generatorach (1,6 mln iteracji) |

Poniżej progu 100 ms na typowym programie albo poza naszym kodem (bez zmian):

- `read_stl` binarny 7 ms, `section_xy` 22 ms (50 880 trójkątów), eksport materiału `write_stl`
  26 ms, `Toolpath.locate` 1,4 ms; `read_stl` ASCII 124 ms przy 12 640 trójkątach (limit 8 MiB
  ≈ 33 tys. trójkątów, ok. 0,3 s) — kandydat na wektoryzację, rzadka operacja importu;
- brama WebHMI `Gateway.step` 42 µs na obieg przy 50 Hz (0,2 % jednego rdzenia);
- ramka Plant LRT-NET 103 µs przy okresie 1000 µs: rdzeń dynamiki jest już w C, reszta to
  kodowanie ramek i CRC w Pythonie; mieści się w budżecie;
- `gcode.parse` (rs274) 150–170 ms: start procesu potomnego i interpreter LinuxCNC;
- `parse_subset` i `MoveListBuilder` (`path.py`, ok. 0,65 s na 32 tys. linii) oraz `make_move`
  (`toolpath.py`, ok. 0,66 s na 32 tys. ruchów, podgląd ekranu Qt): PR #212 zmienia oba pliki,
  więc zostawione do czasu jego scalenia (następny krok: wiersze tablic zamiast krotek, bez C).

## Co zmieniono

1. **Wektoryzacja przed C.** `ball_tip_heights` w `relief.py`: te same działania na parach
   punkt × trójkąt, porcjami po 256 punktów z kandydatami z obwiedni porcji. To ścieżka zapasowa
   bez biblioteki. `SimEngine._loads`: okno mocy w osobnych kolejkach liczb (`sum()` po kolejce
   zamiast po generatorze — ta sama kolejność dodawania, ten sam wynik).
2. **C tam, gdzie numpy nie pomaga.** `core/native/` (C11, libc/libm, bez alokacji i I/O):
   `lrt_zmap_cut` — cała pętla próbek przejazdu (zależność danych: każda próbka obniża mapę przed
   następną) i `lrt_relief_heights` — wysokość kuli dla wszystkich punktów. Wiązanie ctypes
   `core/linumert/native.py`; `StockMap.cut` i `plan_relief` wybierają C, gdy biblioteka jest
   zbudowana, inaczej Python.
3. **Zgodność.** C wykonuje działania w kolejności numpy (`-ffp-contract=off`; norma wektora
   sprawdzona: numpy liczy `(a²+b²)+c²`), więc wysokości płaskorzeźby, cały program G-code
   płaskorzeźby i mapa materiału są identyczne bitowo. Jedyna różnica: suma objętości w stemplu
   (numpy sumuje float32 parami, C w double) — błąd względny ≤ 1e-6, jawny w
   `tests/test_native.py`. Zdarzenia K-3xx i czasy symulacji identyczne.

Profilowanie można odtworzyć opcją `--profile` skryptu. W tym raporcie nie dołączono
surowego profilu historycznego; opis funkcji powyżej zachowuje pierwotną analizę Claude.

## Testy

- `make -C core/native test`: 7 testów C z wartościami analitycznymi (płaszczyzny, ściana,
  krawędź, objętość wgłębienia frezem płaskim, profil kulisty i dno, części nietnące, argumenty).
- `tests/test_native.py`: C kontra Python na tych samych danych (wysokości dla 4 promieni,
  program płaskorzeźby, 6 typów narzędzi na mapie walcowej z wrzecionem, 2 symulacje offline).
- `make test-c`: testy C Plant i `core/native` oraz testy symulacji i CAM z `LINUMERT_NATIVE=1`.

Wyniki po integracji: [odbiór i pomiar](NATIVE_INTEGRATION_2026-11-05.md).
Nie zaliczają pełnej weryfikacji pakietu ani kwalifikacji sprzętu.
