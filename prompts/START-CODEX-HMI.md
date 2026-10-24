# Prompt startowy dla Codex: trudne problemy po HMI-PoC i D35

> Historyczne zlecenie, nie aktualna kolejka ani zasady pracy. Nierozliczone kryteria
> przeniesiono do `LEGACY-RUNTIME` i sesji nadrzędnych we
> [wspólnym rejestrze](../docs/roadmap/plan.json). Nową sesję zacznij od
> [promptu wejściowego](../docs/PROMPT_NOWEJ_SESJI.md).

Model-Author: Claude · 2026-10-19. Wklej Codexowi całość od linii „---”.

---

Kontynuujesz projekt **linumeRT** (repo `anonimov94/linumeRT`): ekran operatora na bazie QtDragon dla
LinuxCNC 2.9, Debian 12, wirtualna obrabiarka Plant (LRT-NET, UDP 1 kHz). Jesteś Codex; Claude pracował
przed tobą w chmurze bez prawdziwego pulpitu, bez VirtualBoxa i bez dostępu do linuxcnc.org / deb.debian.org.
Ty masz Windows + WSL z pełną siecią — dlatego dostajesz zadania, których Claude nie mógł domknąć.

## Zanim zaczniesz (krótko, oszczędnie)
1. Przeczytaj `CLAUDE.md` (kontrakt, ma pierwszeństwo) i `docs/WSPOLPRACA_MODELI.md` (zasady pracy).
2. `docs/NASTEPNA_SESJA.md` §1–§6 i `prompts/LOCK`; sprawdź otwarte PR (`gh pr list`). Jeśli PR #44
   (grzyb E-STOP w HMI, D35) jest jeszcze otwarty, pracuj na `main` po jego scaleniu albo na jego gałęzi.
3. Ostatnie wpisy `docs/DZIENNIK.md`: HMI-PoC (#42), HMI etap 2 i starter (#43), D35 (#44).
4. Każde zadanie = osobna gałąź `codex/<temat>` i osobny PR do `main`, w commitach i PR
   `Model-Author: Codex`. Małe kroki, push po każdym. Testy na Debianie 12 (D27): w WSL
   `tools/dev/wsl-test.sh` (z `--linuxcnc` dla testów z LinuxCNC; blokada `python tools/lock.py acquire
   linuxcnc --model Codex`). Wpis w `docs/DZIENNIK.md` na końcu każdego zadania. Autokontroli nie nazywaj
   niezależnym przeglądem. Wszystko dotyczące sprzętu: `NIEZWERYFIKOWANE NA SPRZĘCIE`.

## Zadania (kolejność = priorytet)

### 1. Łącze LRT-NET gubi ≥ 20 odpowiedzi → E-STOP (niestabilne testy z Plant)
Objaw: w `-m linuxcnc` losowo czerwone `test_scenario_linuxcnc[first_motion|rapid_vs_feed|…]`, czasem
`test_plant_vfd_linuxcnc` — także na `main` sprzed ostatnich zmian (porównanie A/B). Ekran pokazuje
przyczynę „E-STOP: przerwa łącza LRT-NET z Plant, N cykli bez odpowiedzi”. Łańcuch E-STOP w
`config/plant/linumert_plant_xyz/linumert_plant.hal` zawiera `lrt-net.0.connected` (20 cykli ciszy =
`connected = 0` = E-STOP zatrzaśnięty) — to zamierzone zachowanie bezpieczeństwa.
- Zmierz, skąd przerwa: opóźnienia wątku servo LinuxCNC (`latency-histogram`, piny `lrt-net.0.missed`,
  `reply-age`, `plant-late`) czy czas obsługi ramki w Plant (`PlantServer.handle`, Python, lockstep).
  Uwaga: wątek uspace po wywłaszczeniu nadrabia zaległe cykle seriami — to mocny podejrzany.
- Napraw u źródła (np. pętla UDP Plant w C, odbiór w `hal/lrt_net.comp` odporny na serie, priorytet
  tylko dla Plant). **Nie** podnoś `timeout-cycles` w konfiguracji produkcyjnej i nie omijaj łańcucha E-STOP.
- Kryterium: `tools/dev/wsl-test.sh --linuxcnc` z testami Plant 10× z rzędu zielone; raport w DZIENNIK.

### 2. `tests/test_hal_comps.py::test_hardstop_home_comp_in_halrun`
Czerwony u Claude na Ubuntu 24.04 + Python 3.12 (LinuxCNC RIP ze źródeł), także na `main`; w CI
(Debian 12) zielony. Ustal: środowisko (wersja Pythona, halrun, czas) czy błąd komponentu
`hal/lrt_hardstop_home.comp`. Popraw test albo komponent; uzasadnij w PR.

### 3. Starter `tools/linumert-start.sh` — pierwsze prawdziwe uruchomienie
Nigdy nie zbudował obrazu (u Claude proxy blokuje linuxcnc.org i deb.debian.org). Sprawdź na Linuksie z
podmanem (WSL Debian 12 albo Ubuntu z WSLg): `bash <(curl -fsSL https://raw.githubusercontent.com/anonimov94/linumeRT/main/tools/linumert-start.sh)`,
potem `--plant` (panel http://127.0.0.1:8080/), `--plant --vfd`, `--classic`, `--desktop`. Popraw, co nie
działa (Containerfile w skrypcie: zmiana = podbij `IMG_REV`). Zrzuty okien do `docs/raporty/hmi_poc/`,
wynik w README „Szybki start”. Test atrapy: `tests/test_launcher.py`.

### 4. Grzyb E-STOP w HMI a zamrożenie ekranu (D35)
Ekran wysyła sygnał życia co 100 ms (`linumert.hmi-heartbeat` → `watchdog` w
`config/hal/linumert_hmi_estop.hal`, limit `[LINUMERT]HMI_HEARTBEAT_TIMEOUT = 2.0` s). Zmierz najdłuższe
zamrożenie GUI przy wczytaniu dużego programu (podgląd 3D QtDragon, np. 50 000 linii G1) i przy przełączaniu
stron. Zaproponuj limit albo przeniesienie sygnału życia poza wątek GUI — **bez** osłabienia zasady
„zawieszone HMI = E-STOP” i bez obejścia `HMI_ESTOP_BYPASS` w pracy. Samotest GUI:
`tests/test_hmi_shell_gui.py` (krok 29 sprawdza E-STOP po zatrzymaniu sygnału życia).

### 5. Skrypty VirtualBox (sesja 025) — sprawdzenie w VirtualBox
`docs/VM.md` §10: `tools/vm/create-vms.ps1` na Windows (VirtualBox 7, sumy SHA-256 obrazów),
instalacja nienadzorowana VM-B z `tools/vm/preseed-plant.cfg` (pola `@@VBOX_INSERT_…@@`),
`post-install-ctl.sh` na obrazie LinuxCNC 2.9, `tools/vm/lrtnet_probe.py` z VM-A do VM-B. Wyniki pomiarów
do tabeli w `docs/VM.md` §8, poprawki skryptów z testami `tests/test_vm_scripts.py`.

## Zasady, których nie wolno łamać
- `screens/linumert/linumert_upstream_handler.py` bez zmian (wzorzec handler-patch).
- Grzyb HMI może tylko odebrać zezwolenie; reset E-STOP tylko grzybem; obwód sprzętowy nadrzędny (CLAUDE.md §6).
- Komendy maszyny z ekranu tylko przez ACTION QtVCP; wygląd tylko z `docs/design/tokens.yaml`.
- Nie skipuj, nie wyłączaj i nie oznaczaj testów jako niestabilne, żeby uzyskać zielone CI.
- Na koniec: `docs/NASTEPNA_SESJA.md` (stan, sekcja „Dla Claude:” z tym, co zostawiasz), DZIENNIK, LOCK pusty.
