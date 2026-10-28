# linumeRT lite

Backend dla LinuxCNC bez GUI i serwerów HTTP. Python 3.11+, trzy zależności runtime:
NumPy, Pydantic 2 i PyYAML. Docelowe środowisko: Linux; na Windows użyj WSL.

## Zakres

- CAM 2D: planowanie, wiercenie, kieszenie, rowki, kontury, grawerowanie.
- Wersjonowane `.lnx` → G-code, baza narzędzi SQLite i import/eksport tool.tbl.
- Wspólny opis maszyny/napędów i eksport INI/HAL dla **sim lub Plant**.
- Plant: dynamika C, CiA 402, UDP, bazowanie, awarie i scenariusze lockstep.
- Diagnostyczna symulacja materiału 2.5D, kolizje i raport JSON.

Poza lite: Qt/WebHMI/panele web, CAM 3D ze STL, wtyczki, ISO,
generowanie konfiguracji prawdziwego sprzętu i makr ATC. Model Plant zachowuje istniejącą
kinematykę i magazyny do regresji; nie rozwijamy nowych wariantów w lite.

## Instalacja

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c requirements-dev.lock -e '.[dev]'
```

Używaj osobnego venv dla lite: pełna edycja ma te same nazwy pakietów Pythona.
Wersje narzędzi i zależności użyte w regresji zapisano w `requirements-dev.lock`.

Zainstaluj `make` i kompilator C, jeśli chcesz uruchamiać Plant. Sam CAM,
walidacja maszyn i symulacja materiału nie wymagają LinuxCNC ani kompilatora.

## Pierwszy przebieg

```bash
linumert-lite generators
linumert-lite machine config/machines/mill_servo_table.yaml
linumert-lite compile examples/part.lnx --out build/part.ngc
linumert-lite simulate examples/cut.ngc --tool 1:40:6 --out build/report.json
linumert-lite config config/machines/mill_servo_table.yaml --target sim --out build/machine
linumert-lite config config/machines/mill_servo_table.yaml --target sim --out build/machine --write
```

`config` bez `--write` pokazuje diff i zwraca 1 przy zmianach. Zapis tworzy kopię
istniejącego katalogu; nie nadpisuje programów operatora. `.lnx` jest kompilowany atomowo:
niepoprawny program nie niszczy istniejącego wyniku.

## Podgląd w konsoli

W PowerShell, z katalogu głównego lite:

```powershell
.\tools\console.cmd
.\tools\console.cmd -Scenario estop_mid_program
.\tools\console.cmd -Raster ascii -Once
.\tools\console-hd.cmd
```

Pierwsze uruchomienie przygotowuje osobny `.venv-linux` w WSL
(`linumeRT-Debian12`; inną dystrybucję wskaż przez `-Distro`). Potrzebne są Python,
venv, make i kompilator C. Launcher `.cmd` uruchamia własny skrypt PowerShell
z jednorazową polityką wykonania dla tego procesu; ustawienia systemowe pozostają bez zmian.
Nie korzysta z fizycznego sterowania ani serwera sieciowego.

W aktywnym środowisku Linux:

```bash
python tools/console_demo.py
python tools/console_demo.py --scenario estop_mid_program
python tools/console_demo.py --plain
```

Podgląd pokazuje tabelę napędów (pozycja zadana/rzeczywista, błąd nadążania,
prędkość, moment i zgubione kroki), perspektywiczny widok XYZ i alarmy. Najpierw oblicza scenariusz
na rzeczywistym rdzeniu symulatora Plant C, potem odtwarza jego telemetrię w terminalu.
To odtwarzanie danych symulacji z atrapą mastera; nie jest monitoringiem LinuxCNC
ani fizycznej maszyny. Przy przekierowaniu wyjścia drukuje trzy statyczne klatki.
`--speed 2` przyspiesza odtwarzanie dwukrotnie; launcher przyjmuje `-Speed 2`.
Po zakończeniu ruchu można dalej oglądać i obracać scenę. `--once` / `-Once`
kończy pokaz po jednym przebiegu. `Q` lub Ctrl+C kończy pokaz.
PASS scenariusza E-STOP oznacza poprawne wykrycie oczekiwanej awarii i zatrzymania.

### Rozdzielczość i widoki terminala

Domyślnie launcher stosuje **`-Density 2`**: w klasycznej konsoli Windows zmniejsza
komórkę czcionki o połowę i ustawia co najmniej dwukrotnie więcej kolumn oraz wierszy.
Pomiar testowy: **120×30 → 240×60 komórek**, czyli cztery razy więcej komórek obrazu.
Po zamknięciu pokazu czcionka, okno i bufor wracają do poprzednich ustawień.
`-Density 1` zachowuje dotychczasowy rozmiar tekstu. Nie zmieniamy rejestru ani profili terminala.

Jeżeli host, np. Windows Terminal, nie udostępnia tej operacji, uruchom
**`tools/console-hd.cmd`**: otworzy osobną klasyczną konsolę dla pokazu HD.
Zwykły launcher wypisuje wtedy informację o ograniczeniu hosta zamiast deklarować
nieuzyskaną rozdzielczość. W Windows Terminal można też zmniejszyć tekst przez Ctrl+minus.
To zwiększenie liczby rzeczywistych komórek, nie zoom modelu ani nadpróbkowanie do tej samej siatki.

Raster Braille koduje 2×4 punkty w jednej komórce, z maską punktów, kolorem i buforem
głębi. Zwykłe znaki terminala tworzą obraz, bez okna graficznego i bibliotek renderujących.
W konsoli o szerokości co najmniej 111 znaków i wysokości 31 wierszy pojawiają się
obok głównej sceny trzy mniejsze matryce: rzuty XY, XZ i YZ. W mniejszej konsoli
całą powierzchnię wykresu zajmuje 3D. Rozmiar dopasowuje się także podczas zmiany okna.
Przykład: przy `--width 120 --height 38` główny panel ma raster 160×100 punktów.
Po podwojeniu siatki do `--width 240 --height 76`: **320×252 punktów** w panelu 3D.
Limit obszaru renderowania zwiększono do 440×150 komórek, aby nie ucinać trybu HD.

- `A/D`: obrót; `W/S`: nachylenie; `+/-`: zoom.
- `O`: automatyczna orbita; `R`: reset kamery; spacja: pauza ruchu.
- Cyjan: przebieg rzeczywisty; niebieski: pełny tor zadany; żółty: schemat narzędzia.
- Szara siatka i prostopadłościan opisują obwiednię toru, nie materiał ani bryły kolizyjne.
- `-Raster braille`, `-Raster block`, `-Raster ascii`: wybór matrycy znaków.

Rzut 3D zachowuje wspólną skalę XYZ, ma perspektywę, odniesienie osi i bufor głębi.
Przesunięcia są pokazywane względem pierwszej próbki, a dane liczbowe pozostają w układzie
telemetrii. Kamera nie zmienia ani nie skaluje danych napędów.
Znaki Braille: [tabela Unicode](https://www.unicode.org/charts/PDF/U2800.pdf).
Narzędzie jest znacznikiem schematycznym; renderer nie wykonuje CAM 3D ani obliczeń kolizji.

Regresja mechanizmu HD w Windows (ukryta konsola testowa, bez WSL i sprzętu):
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/test_console_density.ps1`.
Test sprawdza podwojenie siatki, powtórne uruchomienie i przywrócenie również po wyjątku.
API bieżącej konsoli: [Microsoft](https://learn.microsoft.com/en-us/windows/console/setcurrentconsolefontex).

Plant bez panelu:

```bash
make test-c
make -C plant/core shared
linumert-plant machine build config/machines/mill_servo_table.yaml --run
linumert-plant serve config/machines/mill_servo_table.yaml --lockstep
# Osobna próba automatyczna, bez stale działającego serwera:
python tools/run_scenario.py first_motion --no-report
```

Wheel zawiera szablony napędów i zasoby generatora konfiguracji. Rdzeń Plant C buduje
się osobno. Przy uruchomieniu z wheel ustaw `LINUMERT_PLANT_LIB` na pełną ścieżkę
`plant/core/build/libplant_core.so` z tej wersji źródeł. Scenariusze i przykładowe maszyny
należą do checkoutu źródeł.

## Granice wykonania

Eksport konfiguracji nie jest poleceniem startu ani zgodą na ruch. `linumert-headless`
jest procesem DISPLAY bez okna: tylko odpytuje LinuxCNC i czeka na zakończenie.
Nie resetuje E-STOP, nie włącza maszyny i nie potwierdza watchdoga.
Domyślnie zachowujemy `HMI_ESTOP_BYPASS = 0`. Tylko jawne `config --test-mode`
włącza dotychczasowy bypass **w konfiguracji sim/Plant**; target hardware jest odrzucany.
Do uruchomienia wygenerowanej konfiguracji potrzebne są LinuxCNC, zainstalowane komponenty
HAL z `hal/` i osobny klient poleceń/test. Wirtualne M6 potwierdza symulowany magazyn,
nie fizyczną zmianę freza.

Parser `subset` daje diagnostykę ograniczonego podzbioru G-code; pominięte konstrukcje
są opisane w `notes`. Pełna interpretacja wymaga LinuxCNC (`--source rs274`).
Symulacja nie jest funkcją bezpieczeństwa ani potwierdzeniem braku kolizji na sprzęcie.
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Rozwój

```bash
make lint           # styl i importy
make test-core      # krótkie testy kontraktów lite, CAM i danych
make test           # pełna regresja Pythona bez zewnętrznego LinuxCNC
make test-c         # fizyka i model Plant w C
make plant-matrix   # pięć zachowanych konfiguracji Plant
make wheel-check    # wheel uruchomiony poza źródłami
```

Aktualne instrukcje: `AGENTS.md`. Granice modułów i dobór testów:
[architektura](docs/ARCHITECTURE.md). Zapisane wyniki: [VALIDATION.md](VALIDATION.md).
Historyczna pełna edycja: commit `a593d6d4c55f503fbaf4c607099f2d89c61cc670`.
Nie wznawiaj jej 84 sesji w tej gałęzi. GPL-2.0-or-later dla własnego kodu;
zachowano nagłówki i rejestr pochodzenia. Patrz `LICENSE` i `docs/PROVENANCE.md`.
