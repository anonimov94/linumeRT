# M1 — HAL na końcu wątku serwo: pierwszy błąd Z

Model-Author: Codex · 2026-10-25. Autokontrola, NIEZWERYFIKOWANE NA SPRZĘCIE.
LEGACY-RUNTIME/G1 pozostają otwarte.

## Narzędzie i odbiór

Kod `23caa5f94e29aec5bddc6f6711b695f0edc969c6`, Debian/WSL, LinuxCNC RIP
`a33293f46575c809e082e0806e79ab996f982513`. Opt-in standardowy sampler/halsampler:
21 kanałów X/Z i łącza na końcu servo-thread; bez zmian modelu, ramp, progów i retry.
Przy pierwszym przygotowaniu kod `0124318` przekroczył limit 21 kanałów samplera;
LinuxCNC odmówił startu przed ruchem. Ograniczono zestaw 25 → 21, dodano kontrolę
limitu. Zachowano command/feedback, uchyb i próg, flagę błędu, drive-enabled,
statusword i uchyb napędu dla X/Z oraz liczniki łącza.

Celowany first_motion na poprawionym kodzie: **70 697 próbek, 0 luk, 0 overruns,
FIFO opróżnione, kolektor zakończony kodem 0; valid=true**. Obie wspólne blokady
linuxcnc zajęte na czas próby i zwolnione po zakończeniu; cudzych procesów nie przerywano.
19 testów jednostkowych diagnostyki/trace PASS i ruff PASS. Ślad runtime zachowany.

## Zaobserwowana kolejność

| Próbka | Z pos-cmd [mm] | Z pos-fb [mm] | Z f-error [mm] | f-error-lim [mm] | f-errored | drive-enabled | statusword |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 811 (pierwsze niezerowe zadanie Z) | 0,0005 | 0 | 0 | 0,5 | 0 | 0 | 512 |
| 856 (zbocze błędu) | 0 | 0 | 0,51 | 0,5 | 1 | 0 | 512 |

W próbce 856 connected=1, reply-age=1, sent=857, received=856, missed=1.
Pierwszy odczyt drive-enabled=1 dla Z dopiero w próbce 60812, po retry bazowania.
Po retry program uzyskał 5/5 PASS, maksimum X około 0,11211 mm.
To nie jest bezbłędne pierwsze bazowanie ani odbiór 10 kolejnych PASS.

Ślad wskazuje kolejność wymagającą wyjaśnienia: **zadanie bazowania Z pojawia się
przed potwierdzeniem drive-enabled**, a następnie uchyb przekracza istniejący limit.
Nie dowodzi jeszcze, dlaczego napęd nie zgłosił gotowości. Następny krok to audyt
sekwencji enable/CiA402 oraz warunku rozpoczęcia homing w runnerze i konfiguracji.
Nie wyciągamy z tego wniosku o usunięciu fizyki ani podniesieniu progów.

## Semantyka i dowody

Próbka przedstawia wartości HAL na końcu cyklu. motion-controller oblicza f-error
przed aktualizacją LRT-NET; po błędzie może też wyzerować zadanie. Dlatego nie wolno
wyliczać f-error przez proste odjęcie pos-cmd − pos-fb z tej samej końcowej próbki.
Numer próbki nie jest zegarem ściennym; nominalny SERVO_PERIOD to 1 ms, WSL nie daje
gwarancji RT. Ślad nie wyrównuje fizycznych zegarów Plant i NML.

[JSON](M1_SERVO_TRACE_2026-10-25.json) zawiera metadane integralności, okno próbek
wokół zbocza błędu, kryteria i hashe pełnych plików.
Pełne dowody: `/home/codex/linumert-m1-servo-trace-20261025-v2/build/evidence/`.
Historyczny uchyb X 0,3 mm nadal niewyjaśniony; nie wykonano pełnej serii.
