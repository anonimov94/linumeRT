# M1 — first_motion: dowody diagnostyczne i wpływ rampy

Model-Author: Codex · 2026-10-25. **Krok diagnostyczny ukończony; LEGACY-RUNTIME/G1 nadal otwarte.**
Autokontrola, bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Pytanie i granice wyniku

Historyczna próba 8 na `d643a97` ukończyła program, lecz próbka błędu X wyniosła
0,3 mm przy wymaganiu ≤0,2 mm. W setup wystąpił też `joint 3 following error`.
Log nie zachował przebiegu w chwili skoku X, więc nie dowodzi jego przyczyny.
Późniejsza kolizja procesów z testem Claude nie wyjaśnia tego wcześniejszego wyniku.
Nowe próby nie odtworzyły 0,3 mm. Nie deklarujemy naprawy ani 10 kolejnych PASS.

Właściciel doprecyzował: bezwładność i uchyb fizycznego modelu są pożądane;
sterowanie powinno im przeciwdziałać, np. przez rampę rozpędzania/hamowania.
**Cel: największe użyteczne przyspieszenia i hamowanie dla G0 i bardzo szybkich G1
przy kontrolowanym uchybie, z oceną przeregulowania i drogi zatrzymania.** Sam uchyb
fizyczny nie jest błędem systemowym. Przekroczenie tolerancji testu i błąd implementacji
to oddzielne oceny. Zmniejszenie przyspieszenia jest punktem porównawczym,
nie docelowym rozwiązaniem ani wynikiem optymalizacji.
LinuxCNC pozostaje jedynym planerem. Nie usuwamy bezwładności, nie dodajemy drugiego
planera i nie podnosimy progu testu. Próba niżej zmienia wyłącznie limit rampy w
tymczasowej konfiguracji LinuxCNC; repozytoryjne INI i machine.yaml pozostają bez zmian.

## Pomiar

Kod `99c4cb9eabf13097a0a2801041bd51c7d1f7b11b`, Debian 12/WSL2, Python 3.11.2,
LinuxCNC RIP `a33293f46575c809e082e0806e79ab996f982513`, Xvfb, Plant lockstep,
4 podkroki, seed 5. Program `plant/scenarios/programs/first_motion.ngc`, próg X 0,2 mm.
W obu wariantach te same masy, napędy, regulatory i program; tylko XY
`MAX_ACCELERATION` w sekcjach AXIS/JOINT: 1000 → 500 mm/s². Z pozostaje 500 mm/s².

| Limit XY [mm/s²] | Próbka maksimum X [mm] | Y [mm] | Z [mm] | Kryteria |
|---:|---:|---:|---:|---|
| 1000 (obecna konfiguracja) | 0,11118 | 0,05607 | 0,04911 | 5/5 PASS |
| 500 (eksperyment) | 0,07621 | 0,04845 | 0,04681 | 5/5 PASS |

X: spadek o około 31%. W obu próbach maksimum X przy linii 6 (G0 powrotny),
prędkość jointa w próbce odpowiednio około −98,5 i −70 mm/s. Łagodniejsza rampa
zmniejszyła także szczytową prędkość na krótkim ruchu. To jedna para obserwacji,
nie izolowany pomiar samej bezwładności ani uzasadnienie zmiany konfiguracji docelowej.
Wstępny przebieg z wcześniejszą wersją diagnostyki (`9ee302e`) dał X 0,11256 mm, 5/5 PASS.

W chwili próbek maksimum `reply-age=1`, `connected=true`, Plant `lost=late=0`;
raporty końcowe: brak watchdoga i błędu modelu. Oddzielne odczyty pinu uchybu
napędu dały około −0,00885 / −0,00427 mm. **NML i HAL odczytywane są kolejno,
nie atomowo**: nie wolno odejmować tych wartości jako zsynchronizowanych próbek.
Ruch 100 mm/s daje około 0,1 mm różnicy na każdy cykl 1 ms opóźnienia sprzężenia;
to wyjaśnia skalę wymagającą rozdzielenia od uchybu regulatora, ale nie dowodzi
przyczyny historycznych 0,3 mm. Diagnostyka działa poza RT; jej koszt może zmieniać
odstępy próbkowania (sleep 10 ms + odczyty HAL i logowanie).

W wariancie 500 i we wstępnym przebiegu wystąpił błąd nadążania Z podczas bazowania.
Istniejący runner ponowił bazowanie; dopiero potem rozpoczął program. PASS 5/5
dotyczy kryteriów programu i nie oznacza bezbłędnego pierwszego bazowania.

## Zachowanie i odtworzenie dowodów

`LINUMERT_SCENARIO_DIAGNOSTICS` zachowuje unikalny katalog także przy wyjątku:
INI/HAL, driver, plan, log drivera (PEAK/RESULT), log Plant, raport i telemetrię.
Tryb diagnostyczny uruchamia LinuxCNC z `-r`, aby jego stdout/stderr trafiły do
`linuxcnc.log`, zamiast do domyślnych plików w HOME. Domyślna ścieżka bez diagnostyki
nadal usuwa katalog tymczasowy. Testy sprawdzają zachowanie po wyjątku i opcję `-r`.

Zwięzły dowód, surowe RESULT, logi LinuxCNC oraz SHA-256 pełnych lokalnych artefaktów:
[M1_FIRST_MOTION_2026-10-25.json](M1_FIRST_MOTION_2026-10-25.json).
Pełne artefakty: `/home/codex/linumert-m1-diagnostics-20261025/build/ramp-{1000,500}/lrt_scen_*`.
Polecenie bazowe (wyłącznie pod wspólną blokadą):

```sh
LINUMERT_SCENARIO_DIAGNOSTICS=build/scenario-evidence \
  xvfb-run -a python tools/run_scenario.py first_motion --master linuxcnc --out build/report
```

Eksperyment używa tego samego `run_linuxcnc(load_scenario(...), port=47822)`;
w wyniku `_prepare` zastępuje wyłącznie `MAX_ACCELERATION = 1000.0` przez
`MAX_ACCELERATION = 500.0`, przed startem LinuxCNC. Obie konfiguracje mają hashe w JSON.
W czasie prób zajęto obie zastane lokalizacje blokady:
`/home/codex/linumert-test/locks` oraz `/home/codex/.cache/linumert-preview-locks`;
zwolniono obie. Nie przerwano cudzych procesów ani nie zmieniono checkoutu Claude.

## Następny krok

Odtworzyć błąd Z podczas bazowania z zachowanymi logami, a przy skoku X zebrać
zsynchronizowany ślad zadanego ruchu, sprzężenia i wieku odpowiedzi. Następnie dobrać
rampy/nastawy do masy i napędu na podstawie pomiaru: szukać największego użytecznego
przyspieszania i hamowania przy kontrolowanym uchybie, osobno dla G0 i bardzo szybkiego
G1; uwzględniać prędkość, obciążenie, nasycenie momentu, przeregulowanie i drogę
zatrzymania. Obecna para prób nie wybiera algorytmu ani maksimum przyspieszenia.
Historyczny FAIL, seria 10 PASS, pulpit,
GUI/heartbeat, VirtualBox, RT i sprzęt pozostają otwarte zgodnie z plan.json.
