# Sesja 003 — LinuxCNC 2.9 RIP/uspace

Model-Author: Codex · 2026-10-18

## Wynik

**DZIAŁA w środowisku deweloperskim WSL2 / Ubuntu 24.04.** LinuxCNC zbudowano
bez zmian w kodzie upstream. Import modułu, symulacja trzech osi, bazowanie,
ruch MDI i ekran QtDragon pod Xvfb zostały wykonane rzeczywiście.
D20: PRZYJĘTA dla testów funkcjonalnych. Docelowy system pozostaje Debian 12.

NIEZWERYFIKOWANE NA SPRZĘCIE. Użyto POSIX non-realtime, bez `make setuid`.
Test nie potwierdza deterministyczności RT, sterowników fizycznych ani Plant,
który powstaje w następnych sesjach.

## Odtworzenie

Źródło: https://github.com/LinuxCNC/linuxcnc, gałąź `2.9`, commit
`a33293f46575c809e082e0806e79ab996f982513`. Cache lokalny:
`~/.cache/linuxcnc-2.9`. Python 3.12.3, kompilacja `make -j12`.

```bash
bash tools/ci/build-linuxcnc.sh --install-deps
bash tools/ci/build-linuxcnc.sh
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python tools/agent_tests/run.py --model Codex --linuxcnc
```

Osobno: `make test-linuxcnc PYTHON=.venv/bin/python`. Ten cel ładuje
`scripts/rip-environment`, uruchamia Xvfb 1440×1100 i testy z markerem linuxcnc.
Brak budowy kończy się błędem. Skrypt budowy ponownie używa zgodnego cache;
nie aktualizuje samodzielnie istniejącego checkoutu. Zmiana rewizji upstream
wymaga jawnego fetch/checkout lub nowego katalogu `LINUXCNC_DIR`.

## Dowody i ograniczenia

- Import z `lib/python/linuxcnc.so` zbudowanego RIP zakończony powodzeniem.
- 47 testów bazowych przeszło; ruff i kontrola diffu bez błędów.
- Smoke sim: upstream `configs/sim/axis/axis.ini` w kopii tymczasowej,
  DISPLAY=halui, reset symulowanego E-STOP, włączenie, bazowanie XYZ,
  `G20 G90 G53 G0 X1 Y1 Z-1`, sprawdzenie położenia z tolerancją 0,001 cala,
  wyłączenie maszyny. Nie jest to docelowa konfiguracja linumeRT z sesji 004.
- QtDragon: upstream `qtdragon_metric.ini`, programowy OpenGL,
  gotowość pinów HAL i okna, zrzut `spike_qtdragon.png`. Zrzut pokazuje ekran
  upstream, nie docelowy wygląd linumeRT.
- Logi i JSON wspólnego runnera są lokalnie w `state/test-runs/`; CI publikuje
  je wraz ze zrzutem i diagnostyką pytest jako artefakt.
- Testy uruchamiano z terminalu pulpitu VNC na localhost:5911.

## Napotkane problemy

1. `debian/configure no-docs` ostrzega o nierozpoznanej wersji Ubuntu 24.04.
   Listę zależności oparto na wygenerowanym `debian/control` i doprecyzowano
   przez rzeczywistą kompilację. Brak `a2x` wymagał AsciiDoc, DocBook i xsltproc.
   Czysty runner CI ujawnił dodatkowo brak `docbook-xml` (DTD) przy instalacji
   bez rekomendacji; dodano go jawnie wraz z `libxml2-utils`.
2. Wywołanie `linuxcnc.stat().poll()` zanim powstanie pamięć narzędzi ustawia
   w upstream trwały dla procesu stan błędu `mmap_available`. Gotowość sprawdza
   osobny krótki proces; właściwy klient powstaje dopiero po sukcesie próby.
3. Konfiguracje upstream zawierają symlinki, także nieużywane historyczne
   odnośniki. Test zachowuje symlinki i kopiuje przykładowe `nc_files`.
4. W przykładzie QtDragon pozostały ostrzeżenia opcjonalnego podglądu PDF
   (brak python3-poppler-qt5) oraz ścieżek NGCGUI/PROGRAM_PREFIX. Nie blokują
   ekranu; konfiguracja sesji 004 powinna ustawić własne poprawne ścieżki.
5. Zatrzymywanie całej grupy sygnałem SIGTERM powodowało awarię Qt podczas
   zamykania. Test zamyka okno komunikatem WM_DELETE_WINDOW, wyłącza dialog
   potwierdzenia tylko w tymczasowym qtdragon.pref i kontroluje log.
6. Zdarzały się przekroczenia okresu pętli symulacji pod WSL. To środowisko
   funkcjonalnych testów non-realtime, nie pomiar opóźnień docelowego jądra RT.

## Automatyzacja

`.github/workflows/linuxcnc.yml`: ręcznie, co poniedziałek 04:23 UTC oraz
dla PR zmieniających narzędzia integracyjne. Cache uwzględnia SHA upstream,
wersję systemu, architekturę i skrypt budowania. Instalacja zależności jest
wykonywana również przy trafieniu cache. Każdy przebieg ponawia testy.

## Pomiar i końcowy stan lokalny

Pełna kompilacja po `make clean`: **50 s** (autogen + configure + make -j12,
bez apt i klonowania). Wcześniejsza przebudowa przyrostowa: 14 s.
Końcowy runner lokalny: PASS — 47 testów bazowych i 2 integracyjne, lint/diff OK.
Raport: `state/test-runs/20261018T060319.515034Z-Codex/report.json`.
Na polecenie właściciela zakończono pracę przed ukończeniem CI LinuxCNC.
CI Python przeszło; PR #3 pozostaje otwarty. Sesja 003 nie jest jeszcze w DONE.

## Weryfikacja na Debianie 12 (Model-Author: Claude, 2026-10-18, D31)

Laptop właściciela (EndeavourOS), podman bez roota, obraz `debian:bookworm`: zależności przez
`build-linuxcnc.sh --install-deps` (root w obrazie), budowa jako zwykły użytkownik
(`--userns=keep-id`), jak w CI.

- Budowa RIP uspace: OK, commit upstream `a33293f46575c809e082e0806e79ab996f982513`,
  `build_seconds=30` (sam `make` po `configure`), Python 3.11.2.
- `tools/ci/test-linuxcnc.sh`: 49 passed; `test_qtdragon_screen` wymaga ekranu — pod
  `xvfb-run` 3/3 przebiegi zielone (2 passed w `tests/test_linuxcnc.py`), bez segfaultu przy zamykaniu.
- `make lint test test-c` (gałąź scalona z `main`): ruff czysty, pytest 432 passed.
- CI run 39121565345 był czerwony nie z powodu LinuxCNC (oba testy PASSED), lecz kroku
  `git diff --check`: w kontenerze nie było gita przed `actions/checkout`, więc brak `.git`.
  Poprawka: krok „Install git” przed checkoutem w `linuxcnc.yml`.
- Pakiety linuxcnc.org 2.9.10 (`tools/dev/linuxcnc-gui.sh`, gałąź Claude) służą do podglądu GUI;
  RIP z tego skryptu — do `halcompile` i CI.
