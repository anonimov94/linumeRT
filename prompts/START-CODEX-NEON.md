# START — Codex: dokończenie Classic × Neon w linumeRT (podgląd na żywo + zmiana skórek)

Model-Author: Claude · 2026-10-24 · zlecenie właściciela: „daj ChatGPT zadanie dokończenia tego, co
zacząłeś, żeby działało w linumeRT i można było zmieniać skórki”. Ty jesteś Codex. Pracujesz na
komputerze właściciela (Windows + WSL, VNC, LinuxCNC 2.9 w Debianie 12) — masz to, czego Claude nie
miał: prawdziwy interpreter `gcode`, NML i ekran.

## Zanim zaczniesz (krótko)
1. `CLAUDE.md`, `docs/WSPOLPRACA_MODELI.md` (aktualizacja 2026-10-20: osobny checkout, bez globalnego
   LOCK), `docs/NASTEPNA_SESJA.md` → sekcja **„Dla Codex: Classic × Neon”**.
2. Baza: gałąź `claude/neon-render` (3 commity Claude na `codex/editor-live-validation`).
   Pracuj na **`codex/neon-live`** odgałęzionej od niej; draft PR po pierwszym kroku.
3. Przeczytaj tylko potrzebne fragmenty:
   - `core/linumert/programs/toolpath.py` — `Toolpath`, `PreviewCanon`, `load_ngc`, `locate()`,
   - `screens/linumert/linumert_neon_view.py` — `PathScene(live=True)`, `follow()`, widoki,
   - `screens/linumert/linumert_neon_render.py` — presety, `SettingsStore`,
   - `screens/linumert/linumert_skin_classic.py`, `linumert_skin_monitor.py`, `linumert_skin_status.py`.
4. Demo bez LinuxCNC: `python3 tools/dev/neon-preview.py` oraz
   `python3 tools/dev/skin-preview.py --skin classic-digital --theme neon-punk --language pl`.

## Co już działa (nie przepisuj)
- Classic Digital rysuje role `toolpath` (detal, śledzi narzędzie) i `machine` (cała maszyna) rendererem
  QPainter ze wspólną sceną: strefy START (lime) / KONIEC (magenta), następny punkt z DTG, oś programu.
- Sposób renderowania per widok (⚙): presety Ekonomiczny/Zrównoważony/Wysoki + przełączniki, profil
  QSettings `linumeRT/podglad-neon`, warstwy wypiekane, regulator jakości. Motyw `neon-punk`.
- Dane: program demo `config/sim/nc_files/linumert_neon_demo.ngc` (offline). `PreviewCanon` jest
  napisany według interfejsu `gcode.parse` 2.9, ale **nigdy nie był uruchomiony z prawdziwym `gcode`**.

## Zadania (kolejność = priorytet; każde = osobny krok, commit, push)

### N1. `PreviewCanon` z prawdziwym interpreterem
- Test `@pytest.mark.linuxcnc` w `tests/test_toolpath.py`: `load_ngc(linumert_neon_demo.ngc)` daje te same
  ruchy co `demo_toolpath()` (liczba ruchów, linie, końce ±0.001 mm, długości łuków ±0.5 %, posuwy).
- Sprawdź i popraw: jednostki posuwu (`set_feed_rate` — cale/min czy mm/min?), `sequence_number` vs
  numer linii pliku (`stat.motion_line`), offsety G5x/G92, łuki G2/G3 z P, cykle G81/G83, `o<…> call`.
- Brakujące metody canon, których wymaga `gcode.parse` 2.9, dodaj jawnie (nie przez `__getattr__`,
  jeśli muszą coś zwracać). Wynik pomiaru jednostek wpisz w docstring `PreviewCanon`.

### N2. Podgląd na żywo w monitorze skórek (tylko odczyt)
- `linumert_skin_status.py`: dodaj do próbki `file`, `motion_line`, `g5x_offset`, `g92_offset`,
  `rotation_xy`, `distance_to_go`, `dtg` (mm, walidacja jak dla pozycji, limit rozmiaru ścieżki pliku).
  Rozszerz testy `tests/test_skin_status.py` (pola, NaN, brak pliku).
- `linumert_skin_monitor.py`: gdy `file` się zmieni → `load_ngc` **poza wątkiem GUI** (osobny proces
  z timeoutem, jak `run_interpreter`), potem `PathScene(toolpath, live=True)` dla Classic; co próbkę
  `scene.follow(motion_line, pozycja_G53 − g5x − g92)`. DTG w etykiecie bierz z `stat.distance_to_go`.
- Brak programu / błąd interpretera → uczciwy napis w widoku („Program niewczytany” / treść błędu),
  bez sceny demo udającej sterowanie (D36). Monitor nadal bez kanału komend, HAL i heartbeat.
- Materiał w trybie live: OK, liczony z pozycji (bez wpływu na LinuxCNC).

### N3. Zmiana skórek i motywów
- Monitor i podgląd: przełączenie skórki/motywu/języka w „Ustawienia” przebudowuje ekran bez utraty
  sceny (ta sama `PathScene` przekazywana do nowej skórki; nie tworzyć drugiego timera).
- Classic × Neon ma działać we wszystkich 5 motywach; `neon-punk` także w 3 pozostałych skórkach
  (paleta). Rozszerz `tools/dev/skin-check.py` o 5. motyw i zrób galerię zrzutów (1280×800, 1920×1080)
  do `docs/raporty/neon/`.
- Ustawienia renderowania (⚙) mają przetrwać zmianę skórki i restart (QSettings).
- Launcher: w `tools/iso/.../usr/local/bin/linumert` i `tools/linumert-start.sh` dodaj wybór
  „Monitor Classic × Neon” (`skin-monitor.py --skin classic-digital --theme neon-punk --language pl`).
  Zmiana Containerfile → podbij `IMG_REV`.

### N4. Odbiór na prawdziwym ekranie
- LinuxCNC sim + `linumert_neon_demo.ngc` w AUTO, monitor Classic × Neon obok: nagranie lub 3 zrzuty
  (start, środek, koniec programu) z widocznym następnym punktem i DTG zgodnym z DRO głównego HMI.
- Zmierz czas klatki na VNC/WSLg dla 3 presetów (HUD pokazuje ms/klatkę) i wpisz do raportu.
- Gdy coś odstaje od pomiarów Claude (WSL offscreen: detal 3–7 ms), zapisz w „Dla Claude:”.

## Kryteria akceptacji
- `tools/dev/wsl-test.sh` zielone; `--linuxcnc` z nowym testem N1 zielone; ruff, `check_requirements`.
- Monitor śledzi prawdziwy program: numer punktu, linia N i DTG zgodne z LinuxCNC (±0.01 mm).
- Zmiana skórki/motywu działa w monitorze i podglądzie; ustawienia ⚙ przetrwały restart.
- Raport `docs/raporty/neon/README.md` (zrzuty, pomiary), wpis w `docs/DZIENNIK.md`, PR do bazy
  `codex/editor-live-validation` (albo `main`, jeśli ta już scalona), `Model-Author: Codex`.

## Zasady (bez wyjątków)
- Monitor i podgląd są tylko do odczytu: zero komend LinuxCNC, pinów HAL, sygnału życia.
- LinuxCNC jest jedynym interpreterem — nie pisz własnego parsera G-code.
- Wygląd z `docs/design/tokens.yaml` (motyw `neon-punk` i role `sciezka` są PROPOZYCJĄ w DECYZJE).
- Nie skipuj i nie oznaczaj testów jako niestabilne. Sprzęt: `NIEZWERYFIKOWANE NA SPRZĘCIE`.
- Pytania projektowe i wyniki → `docs/NASTEPNA_SESJA.md`, sekcja „Dla Claude:”.
