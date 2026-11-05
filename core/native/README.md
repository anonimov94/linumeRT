# core/native — natywne przyspieszenia (C11)

Model-Author: Claude · 2026-11-05

Biblioteka `liblinumert_native.so` liczy poza RT dwie pętle, które w Pythonie były za wolne
(pomiar: [`docs/raporty/WYDAJNOSC_2026-11-05.md`](../../docs/raporty/WYDAJNOSC_2026-11-05.md)):

| Funkcja C | Odpowiednik w Pythonie (referencja i zapas) | Dlaczego nie numpy |
|---|---|---|
| `lrt_zmap_cut` | `linumert_sim.zmap.StockMap.cut` | każda próbka obniża mapę przed następną (zależność danych), okna są małe, a narzut numpy na próbkę przewyższa obliczenia |
| `lrt_relief_heights` | `linumert.generators.relief.ball_tip_height` | numpy porcjami (`ball_tip_heights`) daje ok. 20×, C jeszcze ok. 10× więcej |

- Tylko libc i libm, bez alokacji i bez I/O. Nie działa w RT (CLAUDE.md §5); symulacja nadal
  jako osobny proces z `nice` ≥ 10.
- Kompilacja z `-ffp-contract=off` i z tą samą kolejnością działań co numpy, więc mapa
  materiału i wysokości frezu są identyczne bitowo z Pythonem. Objętość usunięta różni się
  tylko sumowaniem (numpy: float32, C: double) — tolerancja względna 1e-6 w testach.
- Wiązanie: `core/linumert/native.py` (ctypes). Biblioteka nie jest budowana przy imporcie;
  bez niej (Windows bez WSL, brak kompilatora) wszystko liczy się w Pythonie.

## Budowa i testy

```bash
make -C core/native shared     # build/liblinumert_native.so
make -C core/native test       # testy C (wartości analityczne)
make -C core/native test-san   # ASan/UBSan
make test-c                    # Plant + core/native + testy symulacji i CAM z biblioteką
```

`tests/test_native.py` buduje bibliotekę do katalogu tymczasowego i porównuje wynik C
z Pythonem na tych samych danych (w CI brak biblioteki to błąd, lokalnie pominięcie).
W `make test` conftest ustawia `LINUMERT_NATIVE=0` (ścieżka referencyjna), w `make test-c`
testy symulacji i CAM przechodzą z `LINUMERT_NATIVE=1`.

## Zmienne

- `LINUMERT_NATIVE=0` — wyłącza bibliotekę (ścieżka Pythona).
- `LINUMERT_NATIVE_LIB=/ścieżka/liblinumert_native.so` — inny plik biblioteki.

Zmiana wzoru w Pythonie wymaga tej samej zmiany w C (i odwrotnie); `tests/test_native.py`
wykryje rozbieżność. NIEZWERYFIKOWANE NA SPRZĘCIE (dotyczy symulacji, nie sterowania).
