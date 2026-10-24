# CLAUDE.md — kontrakt dla agentów linumeRT (wersja 2, 2026-10-17)

Ten plik czyta **każdy** agent na początku **każdej** sesji. Jeśli prompt sesji jest sprzeczny z tym plikiem,
wygrywa ten plik i `docs/DECYZJE.md`. Zmiana kontraktu = osobny commit z wpisem w `docs/DECYZJE.md`.

## 1. Czym jest projekt
linumeRT to otwarty ekran operatora i zestaw narzędzi dla **LinuxCNC**, przeznaczony dla hobbystycznych
maszyn DIY (frezarki 3/4/5 osi; silniki krokowe, serwa krokowe, serwa; ręczna zmiana narzędzia i ATC;
EtherCAT, step/dir, RS485 dla wrzeciona). Oferuje przemysłowy sposób pracy: tryby, programowanie
dialogowe, symulację, diagnostykę. Ma **własny** wygląd i własne nazewnictwo.

- **LinuxCNC** jest jedynym interpreterem G-code i planerem ruchu.
- **Ekran operatora powstaje na bazie QtDragon** (QtVCP, część LinuxCNC, GPL-2). Kopia bazowa:
  `screens/linumert/`, pochodzenie i commit upstream w `screens/linumert/UPSTREAM.md`.
- **Rdzeń `linumert`** (Python) nie zależy od UI: generatory cykli, format `.lnx`, baza narzędzi,
  symulacja, generator konfiguracji, wtyczki, katalog alarmów.
- **Wirtualna maszyna (Plant)** w `plant/` symuluje fizyczną maszynę (dynamika, napędy, I/O) w osobnej VM
  i służy do testowania prototypów.

## 2. Stos (zamrożony — patrz docs/DECYZJE.md)
| Warstwa | Wybór |
|---|---|
| OS docelowy | Debian 12 + PREEMPT_RT (obraz LinuxCNC 2.9) |
| CNC | LinuxCNC 2.9.x |
| Ekran | QtVCP (PyQt5 przez `qtpy`), baza QtDragon; Qt Designer `.ui`, QSS, handler-patch |
| EtherCAT | IgH EtherCAT Master + linuxcnc-ethercat (lcec) ≥ 1.15, ogólny CiA 402 |
| Wrzeciono RS485 | `hy_vfd` / `mb2hal` (Modbus RTU, poza RT) |
| Rdzeń | Python 3.11, numpy, pyyaml, SQLite (stdlib) |
| 3D symulacji | pyqtgraph.opengl (MIT), limit 30 FPS |
| Plant | rdzeń dynamiki w C (C11, bez zależności), orkiestrator Python, panel web (FastAPI + uPlot) |
| Testy | pytest, ruff, testy C (`make -C plant/core test`), testy ekranu pod Xvfb, gdy LinuxCNC dostępny |
| Licencja | własny kod: GPL-2.0-or-later; całość z kodem QtDragon/LinuxCNC rozpowszechniana na GPL-2.0 |

**Licencja z katalogu nadrzędnego (`PythonProjects/LICENSE`, „Paid Reuse Source-Available”) NIE dotyczy
tego projektu** i nie wolno jej tu stosować — jest niezgodna z GPL.

## 3. Struktura repozytorium
```
core/linumert/         # rdzeń: alarms/ tools/ programs/ generators/ machine/ plugins/ cnc/ diag/
simulation/            # ścieżka, czas, materiał, kolizje (proces osobny)
screens/linumert/      # ekran QtVCP (kopia QtDragon + nasze zmiany)
plant/core/            # C: dynamika osi, napęd CiA402, I/O, kinematyka, magazyn
plant/library/drives/  # szablony napędów wirtualnych (kopiowalne)
config/machines/       # przykładowe machine.yaml (wspólne dla Plant i LinuxCNC)
docs/wymagania/        # wymagania REQ i macierz pokrycia
plant/server/          # Python: serwer LRT-NET, scenariusze, panel web
hal/                   # komponenty HAL (lrt_net.comp itd.)
config/sim/ config/plant/ config/examples/
tools/ tools/vm/ tools/ci/
tests/ docs/ docs/prawne/ prompts/ community/
```

## 4. Praca bez sprzętu i testowanie
- Użytkownik nie ma maszyny. Do testów służy **Plant** (VM-B) połączona z **VM-A** (LinuxCNC + ekran).
- Rdzeń i Plant muszą mieć testy działające bez LinuxCNC (atrapy, pętla zwrotna UDP).
- Jeśli `tools/ci/build-linuxcnc.sh` działa w środowisku agenta (sesja 003), używaj go do testów
  integracyjnych (LinuxCNC sim + Plant na localhost, ekran pod Xvfb). Testy z LinuxCNC mają marker
  `@pytest.mark.linuxcnc`.
- Wszystko dotyczące prawdziwego sprzętu oznaczaj `NIEZWERYFIKOWANE NA SPRZĘCIE`.

## 5. Czas rzeczywisty
- UI, rdzeń, SQLite, symulacja i panel Plant działają poza RT. W RT tylko komponenty HAL (`hal/*.comp`):
  bez alokacji, bez blokującego I/O (UDP tylko nieblokująco, jak hm2_eth), bez logowania na dysk.
- Symulacja: osobny proces, `nice` ≥ 10. Widok 3D: maks. 30 FPS.

## 5a. Wymagania formalne
- Pliki `docs/wymagania/*.md` zawierają wymagania z identyfikatorami (REQ-VD, REQ-VM, REQ-QA). Są obowiązujące i mają pierwszeństwo przed promptem sesji.
- Każdy test realizujący wymaganie ma znacznik `# REQ-XX-NN` (Python/C) albo `requirements: [REQ-XX-NN]` (scenariusz YAML).
- `tools/check_requirements.py` (od sesji 024) musi przechodzić; sesja, która usuwa pokrycie wymagania, jest niezakończona.
- Wirtualny napęd to zawsze instancja szablonu z `plant/library/drives/`; wirtualna obrabiarka powstaje wyłącznie z `machine.yaml` (jedno źródło prawdy).

## 6. Bezpieczeństwo
- Ekran nie jest funkcją bezpieczeństwa. E-STOP i STO to obwód sprzętowy, podłączony fizycznie do HAL i
  nadrzędny wobec ekranu.
- Grzyb E-STOP w HMI to DODATKOWY, szeregowy element łańcucha E-STOP w HAL (D35): może tylko odebrać
  zezwolenie, nigdy go nadać; reset (potwierdzenie) E-STOP grzybem HMI albo podwójnym Resetem (D37),
  zawsze przez ten sam zatrzask HAL i bez zamykania otwartego fizycznego safety; ekran wysyła sygnał życia do `watchdog` w HAL (zawieszone HMI = E-STOP).
  Obejście (`[LINUMERT]HMI_ESTOP_BYPASS = 1`) wolno tylko w uruchomieniach bez ekranu (testy).
- Aktualizacja właściciela 2026-10-20: PC jest dodatkowym warunkiem zezwolenia na ruch fizycznej
  obrabiarki; utrata sygnału PC ma odebrać zgodę, bez obejścia obwodu sprzętowego.
  Nadzór całego PC wymaga niezależnego toru sprzętowego; sam watchdog HAL nie wystarcza.
- Symulacja materiału/kolizji jest diagnostyczna: nie wystawia E-STOP, STO ani resetu do LinuxCNC.
  To rozdzielenie zastępuje wcześniejsze zatrzymanie E-STOP z procesu symulacji w D35/D37.
  Zakres zmian emulacji Plant pozostaje do doprecyzowania; nie usuwać jego zabezpieczeń przy okazji.
  Kontrakt i audyt: `docs/bezpieczenstwo/README.md`. NIEZWERYFIKOWANE NA SPRZĘCIE.
- Wtyczki generują wyłącznie tekst G-code.
- Generator konfiguracji odmawia konfiguracji sprzętowej bez wejścia E-STOP.

## 6a. Nazwa i wygląd
- Nazwa zawsze **linumeRT** (dokładnie ta pisownia). W kodzie: pakiet i identyfikatory `linumert`, sygnały HAL `linumert.*`.
- Wygląd wyłącznie z `docs/design/tokens.yaml`, ikon `docs/design/ikony/` i znaku `docs/design/marka/`. Makiety docelowe: `docs/design/makiety/01–09` (08–09: panel Plant — napędy wirtualne i wirtualna obrabiarka) (kompozycja: lewa szyna obszarów, górny pasek trybu/stanu, dolny pasek dużych akcji). Nowe ekrany projektuj w tym samym systemie.

## 7. Własność intelektualna (obowiązkowe — pełny tekst: docs/prawne/WYTYCZNE_IP.md)
- Zakaz kopiowania kodu, ikon, grafik, tekstów, zrzutów, dokumentacji i plików konfiguracyjnych
  producentów sterowań.
- Nie odtwarzamy „całego wrażenia” żadnego producenta: własna paleta, fonty, ikony, kompozycja,
  komunikaty i hierarchia menu. Funkcje techniczne (tryby, G54…, cykle) mogą być wspólne.
- Nazwy producentów sterowań (lista: `docs/prawne/ZAKAZANE_NAZWY.txt`) nie
  pojawiają się w UI, kodzie, nazwach plików ani marketingu. Wyjątek: `docs/prawne/` i rzeczowe porównania
  w dokumentacji. Nigdy „X-like”, „zamiennik X”.
- Każdy nowy zasób (ikona, font, grafika, biblioteka, kod z innego projektu) → wpis w `docs/PROVENANCE.md`
  (autor, data, źródło, licencja, zakres użycia). Kod z LinuxCNC/QtDragon: GPL-2, zachowaj nagłówki i
  zaznacz zmiany.
- Wątpliwość → procedura z WYTYCZNE_IP.md §7: wstrzymaj element, opisz w DECYZJE jako PROPOZYCJA,
  zrób niezależną alternatywę.
- Słownik (`docs/SLOWNIK.md`): MDI, Układ detalu / Układ maszyny, Reset, parametry użytkownika.
- Alarmy: `W-xxxx`, `E-xxxx`, `K-3xx`, `P-xxxx`; jedyne źródło `core/linumert/alarms/catalog.yaml`.

## 8. G-code LinuxCNC
- Podprogramy `o<nazwa> call`, nie `M98`. Cykle `G81–G89`, `G73`, `G98/G99`.
- Komentarze `( )` lub `;`. Przygotówka: `;@STOCK ...`.

## 9. Ścieżki na maszynie
- Konfiguracje: `~/linuxcnc/configs/<maszyna>/`, programy: `~/linuxcnc/nc_files/`, makra:
  `~/linuxcnc/nc_files/user_macros/`. W kodzie zawsze z ustawień, nie na sztywno.

## 10. Jak pracuje agent w jednej sesji

Aktualizacja właściciela z 2026-10-17: projekt rozwijają naprzemiennie Claude i Codex.
Każdy agent czyta `docs/WSPOLPRACA_MODELI.md` oraz otwarte PR przed rozpoczęciem pracy.
Nowe zmiany trafiają przez pull request i przegląd drugiego modelu; poniższe historyczne
polecenia automatycznego scalania zastępuje ten proces (również w promptach sesji).
Autor oznacza commit i PR polem `Model-Author: Codex` albo `Model-Author: Claude`.
Nie deklaruj przeglądu drugiego modelu bez jego rzeczywistej oceny konkretnego commita.

1. Przeczytaj ten plik, `docs/DECYZJE.md`, ostatnie 3 wpisy `docs/DZIENNIK.md`, prompt sesji.
2. Wykonuj zakres sesji w krokach. **Po każdym ukończonym kroku commit i push na gałąź
   `wip/sesja-NNN`** — limit konta może przerwać sesję w każdej chwili, a kolejna sesja wznowi pracę.
3. Na końcu `make lint test` (i testy C/ekranu, jeśli dotyczy); gdy zielone — oznacz PR jako gotowy i scal
   do `main` według `docs/WSPOLPRACA_MODELI.md` §5 (przegląd drugiego modelu albo autokontrola z adnotacją, D25/D26/D29).
4. Wpis do `docs/DZIENNIK.md`, aktualizacja `docs/roadmap/plan.json` i `python3 tools/roadmap.py`;
   `prompts/DONE.md`, spis promptów i widoki roadmapy są generowane. Commit `sesja NNN: ...`.
5. Dylemat architektoniczny → wybierz rozwiązanie zgodne z ogólną praktyką inżynierską, zapisz w
   `docs/DECYZJE.md` jako PROPOZYCJA i idź dalej.

## 11. Definition of Done

**Kontrakt operatora D37:** [`docs/OBSLUGA_OPERATORA.md`](docs/OBSLUGA_OPERATORA.md) obowiązuje
wszystkie dalsze zmiany: alarmy, Reset, specjalista, pola liczbowe i sterowanie bliźniakiem.
**GUI od pierwszego kroku (D36, polecenie właściciela):** funkcja przeznaczona dla operatora
pojawia się od razu w nawigacji i ma minimalne użyteczne działanie. Backend rozwijamy iteracyjnie
za dostępnym widokiem. Każda porcja zwiększa działające możliwości. Wersję częściową opisujemy
uczciwie w GUI (co działa i co jeszcze powstaje); nie pokazujemy pozornie działających przycisków.
Odbiór obejmuje kliknięcie przez GUI i pokazanie efektu właścicielowi (zrzut lub podgląd),
oprócz testów logiki. Nie uznajemy samego backendu za ukończoną funkcję operatora.

Testy przechodzą · błędy obsłużone jawnie · brak blokowania RT · dokumentacja zaktualizowana ·
nowe zależności i zasoby w LICENCJE.md / PROVENANCE.md · wpis w DZIENNIK.md.

## 12. Współpraca modeli
Jedyne źródło zasad (tury, LOCK, małe kroki, oszczędność tokenów, etapy i scalanie, podział pracy):
`docs/WSPOLPRACA_MODELI.md`. Sprzeczne zapisy w innych plikach i promptach tracą moc.
