# Prompt startowy dla Codex CLI na laptopie z Linuksem (EndeavourOS)

Model-Author: Claude · 2026-10-19. Właściciel uruchamia Codex CLI lokalnie:

```bash
sudo pacman -S --needed git podman python nodejs npm   # raz
npm install -g @openai/codex                           # raz (albo wg instrukcji Codex CLI)
git clone https://github.com/anonimov94/linumeRT ~/linumeRT && cd ~/linumeRT
codex                                                  # i wklej całość od linii „---”
```

---

Kontynuujesz projekt **linumeRT** (repo `anonimov94/linumeRT`): ekran operatora na bazie QtDragon dla
LinuxCNC 2.9, Debian 12, wirtualna obrabiarka Plant (LRT-NET, UDP 1 kHz). Jesteś Codex i działasz
**na laptopie właściciela**: EndeavourOS (Arch), prawdziwy pulpit (X11/Wayland), podman, pełna sieć.
Claude pracuje w chmurze bez pulpitu i bez dostępu do linuxcnc.org / deb.debian.org — robisz to, czego
on nie może sprawdzić. Właściciel nie chce pytań: decyduj sam, wątpliwości zapisuj w `docs/DECYZJE.md`
jako PROPOZYCJA. Rozmowa z Claude: dopisuj wpisy na końcu `docs/ROZMOWA_MODELI.md` (nic nie usuwaj).

## Zanim zaczniesz (krótko)
1. `CLAUDE.md` (kontrakt, pierwszeństwo), `docs/WSPOLPRACA_MODELI.md`, `docs/NASTEPNA_SESJA.md` §1–§6,
   `prompts/LOCK`, ostatnie 3 wpisy `docs/DZIENNIK.md` i `docs/ROZMOWA_MODELI.md`. Otwarte PR: `gh pr list`.
2. Środowisko testowe = Debian 12 w podmanie (D27), host EndeavourOS się nie liczy:
   - bez LinuxCNC: `tools/dev/debian-container.sh make lint test test-c`
   - z LinuxCNC i oknem na pulpicie: `tools/dev/linuxcnc-gui.sh` (symulator), `tools/dev/linuxcnc-gui.sh bash`
     (powłoka z LinuxCNC 2.9 z linuxcnc.org; repo jako `/work`) → tam `pytest -m linuxcnc ...`.
   - przed testami z LinuxCNC: `python tools/lock.py acquire linuxcnc --model Codex`, po: `release`.
3. Każde zadanie = gałąź `codex/<temat>` od `main`, osobny PR, w commitach i PR `Model-Author: Codex`.
   Mały krok → commit → push. Na końcu zadania wpis w `docs/DZIENNIK.md`. Autokontroli nie nazywaj
   niezależnym przeglądem; przegląd PR robi Claude.

## Zadanie 0 — przegląd PR #44 (D35, grzyb E-STOP w HMI), jeśli jeszcze otwarty
Ponowny przegląd poprawek P1/P2 w SHA `44b2cfd` (opis: `docs/ROZMOWA_MODELI.md` wpis 10:55 UTC).
Tu masz LinuxCNC, więc **uruchom** zamiast tylko czytać:
`pytest -m linuxcnc tests/test_hmi_estop_hal.py tests/test_hmi_shell_gui.py -v` (w `linuxcnc-gui.sh bash`,
pod Xvfb albo na pulpicie). Do tego ręcznie na pulpicie: `tools/dev/linuxcnc-gui.sh linuxcnc
config/sim/linumert_xyz/linumert_xyz.ini` → wciśnij grzyb, spróbuj resetu F1/komendą, zwolnij grzyb, załącz
maszynę. Wynik („OK” albo P1/P2 z krokami odtworzenia) jako przegląd w PR #44 i wpis w ROZMOWA_MODELI.

## Zadanie 1 — starter `tools/linumert-start.sh`: pierwsze prawdziwe uruchomienie
Nigdy nie zbudował obrazu (proxy Claude). Na laptopie:
`bash <(curl -fsSL https://raw.githubusercontent.com/anonimov94/linumeRT/main/tools/linumert-start.sh)`,
potem `--plant` (panel http://127.0.0.1:8080/), `--plant --vfd`, `--classic`, `--desktop`.
Dla każdego trybu: czy okno się otwiera, czy grzyb HMI działa, czy E-STOP z Plant (panel) wymaga grzyba.
Popraw, co nie działa (Containerfile w skrypcie — każda zmiana = podbij `IMG_REV`; test atrapy
`tests/test_launcher.py`). Zrzuty okien (`tools/dev/zrzut_ekranu.py` albo zrzut pulpitu) do
`docs/raporty/hmi_poc/`, wynik i znane ograniczenia w README „Szybki start”.

## Zadanie 2 — łącze LRT-NET gubi ≥ 20 odpowiedzi → E-STOP
Objaw: losowo czerwone `tests/test_scenario_linuxcnc.py` (`first_motion`, `rapid_vs_feed`, …) i
`tests/test_plant_vfd_linuxcnc.py`; ekran: „E-STOP: przerwa łącza LRT-NET z Plant, N cykli bez odpowiedzi”.
Także na `main` sprzed D35. Łańcuch: `lrt-net.0.connected` w `config/plant/linumert_plant_xyz/linumert_plant.hal`
(20 cykli ciszy = E-STOP) — zachowanie zamierzone.
- Najpierw sprawdź, czy na laptopie (nie chmurze) w ogóle występuje: 10 przebiegów z rzędu.
- Jeśli tak: zmierz źródło — `latency-histogram` wątku servo, piny `lrt-net.0.missed`, `reply-age`,
  `plant-late`; czas `PlantServer.handle` (Python). Podejrzany: wątek uspace po wywłaszczeniu nadrabia
  zaległe cykle seriami.
- Napraw u źródła (np. odbiór w `hal/lrt_net.comp` odporny na serie, pętla UDP Plant w C, priorytet Plant).
  **Nie** podnoś `timeout-cycles` w konfiguracji produkcyjnej, nie omijaj łańcucha E-STOP.
- Kryterium: testy Plant `-m linuxcnc` 10× z rzędu zielone; liczby w DZIENNIK.

## Zadanie 3 — zamrożenie ekranu a watchdog HMI (D35)
Sygnał życia co 100 ms (`linumert.hmi-heartbeat` → `watchdog`, limit `[LINUMERT]HMI_HEARTBEAT_TIMEOUT = 2.0` s).
Na prawdziwym pulpicie zmierz najdłuższe zamrożenie GUI: wczytanie programu 50 000 linii G1 (podgląd 3D
QtDragon), przełączanie stron nakładki, zmiana rozmiaru okna. Jeśli przekracza ~1 s: zaproponuj i wdroż
rozwiązanie (np. sygnał życia z wątku, który i tak wykrywa zawieszenie pętli Qt — nie „wieczny” wątek
niezależny od GUI) **bez** osłabienia „zawieszone HMI = E-STOP” i bez `HMI_ESTOP_BYPASS` w pracy.
Uzasadnienie w `docs/DECYZJE.md`, test w `tests/test_hmi_shell_gui.py` (krok 29 = E-STOP po zatrzymaniu sygnału).

## Zadanie 4 — `tests/test_hal_comps.py::test_hardstop_home_comp_in_halrun`
Czerwony u Claude (Ubuntu 24.04 + Python 3.12, LinuxCNC RIP), zielony w CI (Debian 12). Uruchom w
`linuxcnc-gui.sh bash` (pakiety 2.9 z linuxcnc.org). Ustal: środowisko czy błąd `hal/lrt_hardstop_home.comp`;
popraw test albo komponent, uzasadnij w PR.

## Zadanie 5 (opcjonalne) — VirtualBox
Tylko jeśli właściciel ma VirtualBox 7 (`VBoxManage --version`). `docs/VM.md` §10: odpowiednik
`tools/vm/create-vms.ps1` dla Linuksa (jeśli brak — dopisz `create-vms.sh`), VM-B z `tools/vm/preseed-plant.cfg`,
`tools/vm/lrtnet_probe.py` z VM-A do VM-B. Pomiary do `docs/VM.md` §8, testy `tests/test_vm_scripts.py`.

## Zasady, których nie wolno łamać
- `screens/linumert/linumert_upstream_handler.py` bez zmian (handler-patch).
- Grzyb HMI może tylko odebrać zezwolenie; reset E-STOP (także emulowanego w Plant) tylko grzybem; obwód
  sprzętowy nadrzędny (CLAUDE.md §6). `HMI_ESTOP_BYPASS = 1` wyłącznie w uruchomieniach bez ekranu.
- Komendy maszyny z ekranu tylko przez ACTION QtVCP; wygląd tylko z `docs/design/tokens.yaml`.
- Nie skipuj, nie wyłączaj, nie oznaczaj testów jako niestabilne dla zielonego CI.
- Nie instaluj LinuxCNC na hoście EndeavourOS — tylko w podmanie (Debian 12).
- Wszystko o sprzęcie: `NIEZWERYFIKOWANE NA SPRZĘCIE`.
- Na koniec sesji: `docs/NASTEPNA_SESJA.md` (sekcja „Dla Claude:”), DZIENNIK, LOCK pusty, wpis w ROZMOWA_MODELI.
