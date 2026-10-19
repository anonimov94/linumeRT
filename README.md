# linumeRT

![linumeRT](docs/design/marka/baner.png)

### Przemysłowy sposób pracy na Twojej frezarce CNC. Otwarty, na LinuxCNC, gotowy do testu jednym poleceniem.

**linumeRT** to ekran operatora i zestaw narzędzi dla **LinuxCNC**, zbudowany przez ludzi, którzy znają
robotę przy maszynie: od bazowania i zera detalu, przez narzędzia i program, po symulację i produkcję.
Każdy widok prowadzi operatora w kolejności, w jakiej naprawdę pracuje się na obrabiarce.

- 🛑 **Bezpieczeństwo na pierwszym miejscu** — grzyb E-STOP w HMI szeregowo w łańcuchu HAL, watchdog ekranu,
  **dwukanałowy E-STOP NC z kontrolą rozbieżności**; reset tylko świadomym potwierdzeniem.
- 🧱 **Symulacja obróbki na żywo** — materiał przygotówki ubywa tam, gdzie przejechało wirujące ostrze;
  frez palcowy, kulowy, torusowy, teowy, lizak, fazownik, wiertła, głowica, gwintownik.
- 💥 **Kolizje i przeciążenia wykrywane bezwzględnie** — kontakt bez obrotów, G0 w materiał, szyjka i oprawka,
  stół i dociski, przeciążenie wrzeciona i napędów osi z granic napędów → natychmiastowy E-STOP.
- 🧰 **Tabela narzędzi z prawdziwą geometrią** — typ, D, korekcja ±1 mm, długość, ostrza, maks. obroty,
  kierunek skrawania M3/M4, oprawka.
- 🧭 **Workflow operatora** — Start, Bazowanie, Zero detalu 3D (prostopadłościan, walec, rura, odlew),
  Program ze sprawdzaniem składni i edycją, **Cykle** (planowanie, otwory: siatka, okrąg, łuk, G81–G83/G73),
  Produkcja ze startem od linii, Diagnostyka napędów CiA 402.
- 🤖 **Wirtualny bliźniak maszyny (Plant)** — dynamika osi w C, napędy CiA 402 i krokowe, krańcówki, zderzaki,
  falownik RS485, magazyn narzędzi, wstrzykiwanie awarii. Testujesz bez ryzyka, zanim kupisz sprzęt.
- 🔁 **Jakość jak w przemyśle** — ponad 700 testów automatycznych, testy w prawdziwym HAL LinuxCNC,
  test end-to-end ekranu pod Xvfb, CI na każdym pull requeście.

> **Status:** działające HMI i wirtualny bliźniak na Debianie 12 / LinuxCNC 2.9.
> Wszystko, co dotyczy prawdziwego sprzętu, jest **NIEZWERYFIKOWANE NA SPRZĘCIE** — mówimy wprost, co sprawdziliśmy.
> [Obsługa operatora](docs/OBSLUGA_OPERATORA.md) · [Symulacja w HMI](docs/HMI_SYMULACJA.md).

![Symulacja: materiał po obróbce programu demo](docs/raporty/hmi_sym/demo_po_obrobce.png)

## Obraz live USB / ISO (komputer maszyny)

Gotowy system do wypalenia na pendrive: **Debian 12 + jądro PREEMPT_RT + LinuxCNC 2.9 + linumeRT**.
Uruchom bez instalacji (tryb live: ekran linumeRT na symulatorze, „linumeRT + Plant” z wirtualną
obrabiarką) albo zainstaluj na dysk komputera maszyny (Calamares).

- Pobierz: [Releases](https://github.com/anonimov94/linumeRT/releases) (wydania `v*`) albo najnowszy
  artefakt `linumert-iso` z [Actions → ISO live USB](https://github.com/anonimov94/linumeRT/actions/workflows/iso.yml)
  (przycisk **Run workflow** buduje obraz na żądanie, ok. 30–60 min).
- Sprawdź sumę: `sha256sum -c linumert-*.iso.sha256`.
- Wypal: `sudo dd if=linumert-*.iso of=/dev/sdX bs=4M status=progress conv=fsync` albo Etcher / Ventoy.
- Przed pracą na maszynie: test latencji (`latency-histogram`) — nie każdy komputer nadaje się do RT.
  NIEZWERYFIKOWANE NA SPRZĘCIE.

## Szybki start (Linux z podmanem, np. EndeavourOS)

Jedno polecenie pobiera `main` z GitHuba do `~/linumeRT`, instaluje `git` i `podman` (pacman/dnf/apt, z sudo),
buduje kontener Debian 12 z LinuxCNC 2.9 (pakiety linuxcnc.org) i otwiera okno LinuxCNC z ekranem linumeRT
na symulatorze:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/anonimov94/linumeRT/main/tools/linumert-start.sh)
```

Kolejne uruchomienia: z menu aplikacji („linumeRT”, „linumeRT + Plant”) albo `~/linumeRT/tools/linumert-start.sh`
(przy każdym starcie `git pull` main). Opcje:

| Polecenie | Co uruchamia |
|---|---|
| `tools/linumert-start.sh` | symulator LinuxCNC + ekran linumeRT |
| `tools/linumert-start.sh --plant` | + wirtualna obrabiarka Plant przez LRT-NET; panel Plant otwiera się w przeglądarce (http://127.0.0.1:8080/) |
| `tools/linumert-start.sh --plant --vfd` | jak wyżej, wrzeciono przez falownik (`hy_vfd`) |
| `tools/linumert-start.sh --classic` | czysty QtDragon (bez nakładki linumeRT) |
| `--no-update`, `--rebuild`, `--shell`, `--desktop`, `--dir KATALOG` | bez aktualizacji, nowy obraz kontenera, powłoka w kontenerze, tylko skróty w menu, inne repozytorium |

Pierwsze uruchomienie trwa kilka minut (obraz ok. 1,5 GB), kolejne kilkanaście sekund. W oknie: **Start** →
„Potwierdź grzybem” → „Włącz” → „Bazuj wszystkie”. W **Symulacja** przycisk
**Uruchom / Reset symulacji → HOME** przygotowuje bliźniaka po potwierdzeniu operatora.
JOG, MDI, wrzeciono M3/M4/M5 i **WYMIANA M6** są dostępne w **Maszyna** i **Symulacja**.
Na górze są trzy ostatnie alarmy i Reset. [Pełna instrukcja](docs/OBSLUGA_OPERATORA.md).

Sam edytor przygotówki bez uruchamiania LinuxCNC: `bash tools/dev/preview-zero.sh`.
To podgląd offline z zapisami tymczasowymi. [Zero detalu](docs/ZERO_DETALU.md).

![Własne Zero detalu: maszyna, odlew 360° i edytor profilu](docs/raporty/zero_detalu/offline.png)

## Co już działa (bez sprzętu, LinuxCNC 2.9 na Debianie 12)

| Obszar | Stan | Gdzie |
|---|---|---|
| LinuxCNC + ekran | symulator 3 osi z ekranem linumert (kopia bazowa QtDragon 2.9.10) | `config/sim/`, `screens/linumert/` |
| Wirtualna obrabiarka Plant | dynamika osi w C, napędy CiA 402 i krokowce, biblioteka napędów, kinematyka, krańcówki, zderzaki, bazowanie, magazyn narzędzi, kolizje, wrzeciono z falownikiem | `plant/`, [`docs/PLANT.md`](docs/PLANT.md) |
| LinuxCNC ↔ Plant | komponenty HAL `lrt_net` / `lrt_cia402`; bazowanie z losowego startu, ruch G1, wyrocznia soft limits i stref, wrzeciono przez `hy_vfd` | `hal/`, `config/plant/` |
| Rdzeń (Python) | model stanu maszyny, katalog alarmów PL/EN, `machine.yaml`, baza narzędzi, format `.lnx` i kompilator do `.ngc`, lekser G-code | `core/linumert/` |
| Ekran HMI linumeRT (D32, D34) | własne widoki workflow, trzy alarmy i Reset, JOG/MDI, wrzeciono, wymiana M6, tryb specjalisty, Zero detalu 3D i konfiguracja przygotówki | `screens/linumert/`, [`docs/design/HMI_WORKFLOW.md`](docs/design/HMI_WORKFLOW.md) |
| Uruchomienie jednym poleceniem | `tools/linumert-start.sh` (podman, Debian 12, LinuxCNC 2.9) | „Szybki start” wyżej |
| Symulacja materiału i kolizji | materiał 2.5D na żywo, 11 typów narzędzi, kolizje K-301…K-309, przeciążenia z granic napędów, eksport STL, wirtualne wycofanie po kolizji | `simulation/`, [`docs/HMI_SYMULACJA.md`](docs/HMI_SYMULACJA.md) |
| Bezpieczeństwo | grzyb HMI w łańcuchu E-STOP (D35), watchdog ekranu, dwukanałowy E-STOP NC `lrt_estop2` | `config/hal/`, `hal/lrt_estop2.comp` |
| Program i cykle | wybór, podgląd, sprawdzanie składni, edycja; generatory: nagłówek, narzędzie, planowanie, otwory, koniec | `screens/linumert/`, `core/linumert/generators/` |

## Co dalej (najbliższe zadania)

1. **Wznowienie obróbki (D38)** — wycofanie w pauzie, powrót po helisie i łuku stycznym z zakładką,
   bez naddatku ([`docs/design/WZNOWIENIE.md`](docs/design/WZNOWIENIE.md), sesja 031).
2. Raport symulacji HTML i oś czasu zdarzeń (059, 057); symulacja programu offline przed startem (051–056).
3. Programy dialogowe: kieszenie, rowki, kontur, pliki `.lnx`, walidacja z bazą narzędzi (040–047).
4. Tryby, MDI, alarmy, poziomy dostępu, PL/EN na ekranie (029–037).
5. Generator konfiguracji: step/dir, EtherCAT, RS485, 4/5 osi, ATC, kreator maszyny (061–067).
6. Wtyczki, instalator Debian 12 i **obraz live USB / ISO** do wypalenia (Debian 12 + RT + LinuxCNC + linumeRT),
   dokumentacja użytkownika, wydanie v0.5.0-alpha (073–083).

Pełny plan sesji: [`prompts/README.md`](prompts/README.md).

## Kierunek rozwoju

Docelowy ekran operatora to HMI zorganizowane według kolejności pracy przy maszynie: Start → Bazowanie →
Zero detalu → Narzędzia → Program → Symulacja → Produkcja, a obok Ręczne/MDI, Diagnostyka i Ustawienia,
ze stałym paskiem stanu, DRO i alarmami (decyzja D32, [`docs/design/HMI_WORKFLOW.md`](docs/design/HMI_WORKFLOW.md)).
Powstaje etapami HMI-01…HMI-06 na bazie obecnego ekranu QtDragon, bez zmiany sterowania LinuxCNC.

## Architektura
```
VM-A / komputer maszyny                         VM-B (Plant)
┌───────────────────────────────┐   LRT-NET    ┌──────────────────────────────┐
│ Ekran linumeRT (QtVCP)        │   UDP 1 kHz  │ model osi + napędy CiA 402   │
│ rdzeń linumert (Python)       │◄────────────►│ I/O, sonda, VFD, ATC, MPG    │
│ LinuxCNC 2.9 + HAL (lrt_net)  │  RS485/pty   │ panel web, scenariusze       │
└───────────────────────────────┘ (hy_vfd)     └──────────────────────────────┘
Na prawdziwej maszynie lrt_net zastępuje lcec (EtherCAT) lub stepgen — sygnały HAL bez zmian.
```

W 10 linijkach:
1. **LinuxCNC 2.9** jest jedynym interpreterem G-code i planerem ruchu; linumeRT go nie zastępuje.
2. **HAL** łączy LinuxCNC z napędami; kontrakt sygnałów `linumert.*` opisuje [`docs/HAL_KONTRAKT.md`](docs/HAL_KONTRAKT.md).
3. W czasie rzeczywistym działają tylko komponenty `hal/*.comp`: bez alokacji i bez blokującego I/O.
4. **Ekran** `screens/linumert/` to kopia QtDragon (QtVCP); własna logika w handlerze i osobnych modułach.
5. Ekran czyta stan przez `linuxcnc.stat` i wydaje polecenia przez `linuxcnc.command`, tak jak QtDragon.
6. **Rdzeń** `core/linumert/` (Python, bez UI): alarmy, narzędzia, `.lnx`, generatory, `machine.yaml`.
7. Rdzeń generuje wyłącznie tekst G-code i dane; ekran i narzędzia go importują.
8. **Plant** (`plant/`) to wirtualna obrabiarka: dynamika i napędy w C, serwer i wyrocznia w Pythonie.
9. LinuxCNC rozmawia z Plant przez **LRT-NET** (UDP, 1 kHz) i falownik przez RS485/pty (`hy_vfd`).
10. Jedna maszyna = jeden `machine.yaml`: z niego Plant buduje obrabiarkę, a test pilnuje zgodności INI LinuxCNC.

## Szybki start

Rdzeń i Plant bez LinuxCNC (Python ≥ 3.11, `make`, kompilator C):
```bash
python3 -m venv .venv && . .venv/bin/activate
make install      # pakiet linumert + zależności dev (pytest, ruff)
make lint test    # ruff i pytest bez LinuxCNC
make test-c       # testy rdzenia Plant w C (make test-san: z ASan/UBSan)
```
W systemowym Pythonie Debiana dodaj `PIP_FLAGS=--break-system-packages`. Wyniki wiążące: Debian 12
(`tools/dev/debian-container.sh make lint test test-c`).

LinuxCNC z wirtualną obrabiarką na pulpicie (podman, LinuxCNC 2.9 zbudowany według
[`docs/PLANT_START.md`](docs/PLANT_START.md)):
```bash
tools/dev/plant-gui.sh          # LinuxCNC + Plant + ekran linumert
VFD=1 tools/dev/plant-gui.sh    # wariant z wrzecionem przez hy_vfd i emulator falownika
```

## Dokumentacja

Pełny spis: [`docs/README.md`](docs/README.md). Agent AI zaczyna od [`docs/PROMPT_NOWEJ_SESJI.md`](docs/PROMPT_NOWEJ_SESJI.md). Najważniejsze: stan bieżący i plan scalania
[`docs/NASTEPNA_SESJA.md`](docs/NASTEPNA_SESJA.md) · decyzje [`docs/DECYZJE.md`](docs/DECYZJE.md) ·
dziennik [`docs/DZIENNIK.md`](docs/DZIENNIK.md) · wymagania [`docs/wymagania/`](docs/wymagania/) ·
wytyczne IP [`docs/prawne/WYTYCZNE_IP.md`](docs/prawne/WYTYCZNE_IP.md).

## Jak powstaje
Kod piszą agenci AI (Claude, Codex) według promptów sesji w [`prompts/`](prompts/README.md) i kontraktu
[`CLAUDE.md`](CLAUDE.md); zasady współpracy: [`docs/WSPOLPRACA_MODELI.md`](docs/WSPOLPRACA_MODELI.md).
Każda zmiana przechodzi przez pull request z oznaczeniem modelu-autora (`Model-Author:`).

Na Windows z WSL jest wspólna paczka testowa z podglądem VNC: [`tools/agent_tests`](tools/agent_tests/README.md).

## Licencja
GPL-2.0-or-later dla własnego kodu. Części pochodzące z LinuxCNC/QtDragon: GPL-2.0. Całość jest rozpowszechniana
na GPL-2.0 (pełny tekst w [`LICENSE`](LICENSE), zależności w [`docs/LICENCJE.md`](docs/LICENCJE.md), pochodzenie
zasobów w [`docs/PROVENANCE.md`](docs/PROVENANCE.md)). Licencja z katalogu nadrzędnego (`PythonProjects/LICENSE`)
nie dotyczy tego projektu.
