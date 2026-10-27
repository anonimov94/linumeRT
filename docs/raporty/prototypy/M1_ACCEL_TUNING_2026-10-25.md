# M1 — dobór przyspieszeń z budżetu uchybu (Plant)

Model-Author: Claude · 2026-10-25. Wykonanie decyzji właściciela „Plant — cel strojenia dynamiki”:
uchyb z bezwładności jest odpowiedzią modelu, a nie błędem; szukamy największego użytecznego
przyspieszenia w jawnym budżecie. Narzędzie: `tools/tune_accel.py` (`linumert_plant.accel_tuning`).
Atrapa mastera (lockstep, `substeps` = 4), test = bazowanie i szybki przejazd tam i z powrotem po
150 mm (lub 0,6 zakresu), kryteria: bez alarmu napędu, bez zgubionych kroków, uchyb osi ≤ 0,2 mm.
Wartości dotyczą **modelu Plant**, nie fizycznej maszyny. Do `machine.yaml` wpisano je na polecenie właściciela, z korektą opisaną w „Weryfikacji” poniżej.

## Wnioski
- Frezarka serwo: na atrapie mastera budżet 0,2 mm dopuszczał X i Y ok. 17 100, Z ok. 5 400 mm/s²
  (z zapasem 10%), ale odbiór z prawdziwym LinuxCNC (niżej) obniżył to do **2 000 / 2 000 / 2 500**.
- Przekroczenie nie jest łagodne: X 20 000 → uchyb 0,26 mm, od 24 000 napęd wpada w E-4201 (uchyb
  28 mm, nasycenie momentu).
- Router krokowy: uchyb nie istnieje (silniki bez sprzężenia), granicą jest utrata kroków:
  X i Y ok. 3 800, Z ok. 9 400 mm/s². Wynik Z jest niemonotoniczny (przechodzi 16 000, nie przechodzi
  14 400 i niżej): pasma rezonansu. Narzędzie wykrywa to i wymaga, by zalecana wartość i jej niższy sąsiad
  (−10%) przeszły oba pomiary. Nie wykryje dziury, w którą żaden pomiar nie trafi.
- Ograniczenie: test bada jedną oś naraz i ruch G0; „bardzo szybkie G1” przy obciążeniu skrawaniem
  wymaga osobnego pomiaru. Ograniczenie zrywu i filtr drgań to dalsze kroki.

Model-Author: Claude. Wynik dla **modelu Plant** (atrapa mastera, lockstep); uchyb to
odpowiedź bezwładności modelu, nie błąd. NIEZWERYFIKOWANE NA SPRZĘCIE.

| Oś | Budżet uchybu [mm] | Obecne [mm/s²] | Największe przechodzące | Pierwsze niespełniające | Zalecane (zapas) | Uchyb przy zalecanym [mm] | Uwagi |
|---|---:|---:|---:|---:|---:|---:|---|
| X | 0.2 | 1000 | 19000 | 19500 | **17100** | 0.1683 | — |
| Y | 0.2 | 1000 | 19000 | 19500 | **17100** | 0.1685 | — |
| Z | 0.2 | 500 | 6000 | 6250 | **5400** | 0.1736 | — |

## Weryfikacja na programach generatorów (korekta Z routera)
Po wpisaniu wartości test `test_suite_cycles` (generatory cykli na routerze) zgłosił zgubione kroki osi Z
(−8 kroków, `stud_circle`) przy zalecanych 9 440 mm/s². Krótki przejazd testowy narzędzia przechodził,
a dłuższy program z wieloma zmianami kierunku nie: to skutek niemonotonicznej odpowiedzi krokowca
(rezonans), którą narzędzie sygnalizuje w kolumnie „Uwagi”, ale sam pomiar jednego wzorca ruchu jej nie
wyczerpuje. Przyspieszenie Z routera ustawiono na **4 000 mm/s²** (przechodziło w pomiarze i w serii
cykli: 61 testów PASS). Wniosek na przyszłość: wartości z `tune_accel` dla krokowców trzeba sprawdzać
na programach z generatorów, a nie tylko na pomiarze jednego przejazdu.

## Odbiór z prawdziwym LinuxCNC (korekta frezarki)
Scenariusz `first_motion` z LinuxCNC (próg uchybu X 0,2 mm) wykazał, że atrapa mastera **zaniża uchyb ok. 1,5×**
(LinuxCNC dokłada opóźnienie jednego cyklu serwo): przy 17 100 mm/s² atrapa dawała 0,168 mm, LinuxCNC 0,23–0,25 mm.
Zmierzone w LinuxCNC (X): 1 000 → ok. 0,11; 3 000 → 0,208; 5 000 → 0,217; 17 100 → 0,25 mm. Frezarka ma więc
X/Y **2 000**, Z **2 500** mm/s² (pomiar X/Y 2 000: trzy testy `first_motion` PASS; pozostałe testy LinuxCNC —
pause_retract, Plant, generator, układy G54–G59.3, sondowanie — PASS przy 3 000/2 500). Progu nie zmieniano.
Narzędzie dostało `--lag-factor` (zalecane ok. 1,5), by budżet pomiaru uwzględniał to opóźnienie.

## Pomiary (atrapa mastera, przed korektą)

| Oś | Przyspieszenie | Wynik | Uchyb [mm] | Powód |
|---|---:|---|---:|---|
| X | 1000 | PASS | 0.0761 | — |
| X | 2000 | PASS | 0.0986 | — |
| X | 4000 | PASS | 0.1316 | — |
| X | 8000 | PASS | 0.1489 | — |
| X | 16000 | PASS | 0.1570 | — |
| X | 32000 | FAIL | 29.9445 | program ukończony: przerwany; brak alarmów: E-4201; uchyb 29.9445 mm > budżet 0.2 mm |
| X | 24000 | FAIL | 28.3928 | program ukończony: przerwany; brak alarmów: E-4201; uchyb 28.3928 mm > budżet 0.2 mm |
| X | 20000 | FAIL | 0.2568 | uchyb 0.2568 mm > budżet 0.2 mm |
| X | 18000 | PASS | 0.1600 | — |
| X | 19000 | PASS | 0.1914 | — |
| X | 19500 | FAIL | 0.2177 | uchyb 0.2177 mm > budżet 0.2 mm |
| X | 17100 | PASS | 0.1683 | — |
| X | 15390 | PASS | 0.1493 | — |
| Y | 1000 | PASS | 0.0759 | — |
| Y | 2000 | PASS | 0.0982 | — |
| Y | 4000 | PASS | 0.1308 | — |
| Y | 8000 | PASS | 0.1519 | — |
| Y | 16000 | PASS | 0.1534 | — |
| Y | 32000 | FAIL | 29.7766 | program ukończony: przerwany; brak alarmów: E-4201; uchyb 29.7766 mm > budżet 0.2 mm |
| Y | 24000 | FAIL | 28.3935 | program ukończony: przerwany; brak alarmów: E-4201; uchyb 28.3935 mm > budżet 0.2 mm |
| Y | 20000 | FAIL | 0.2406 | uchyb 0.2406 mm > budżet 0.2 mm |
| Y | 18000 | PASS | 0.1600 | — |
| Y | 19000 | PASS | 0.1913 | — |
| Y | 19500 | FAIL | 0.2177 | uchyb 0.2177 mm > budżet 0.2 mm |
| Y | 17100 | PASS | 0.1685 | — |
| Y | 15390 | PASS | 0.1493 | — |
| Z | 500 | PASS | 0.0445 | — |
| Z | 1000 | PASS | 0.0660 | — |
| Z | 2000 | PASS | 0.1118 | — |
| Z | 4000 | PASS | 0.1422 | — |
| Z | 8000 | FAIL | 0.2541 | uchyb 0.2541 mm > budżet 0.2 mm |
| Z | 6000 | PASS | 0.1955 | — |
| Z | 7000 | FAIL | 0.2271 | uchyb 0.2271 mm > budżet 0.2 mm |
| Z | 6500 | FAIL | 0.2072 | uchyb 0.2072 mm > budżet 0.2 mm |
| Z | 6250 | FAIL | 0.2025 | uchyb 0.2025 mm > budżet 0.2 mm |
| Z | 5400 | PASS | 0.1736 | — |
| Z | 4860 | PASS | 0.1583 | — |

Model-Author: Claude. Wynik dla **modelu Plant** (atrapa mastera, lockstep); uchyb to
odpowiedź bezwładności modelu, nie błąd. NIEZWERYFIKOWANE NA SPRZĘCIE.

| Oś | Budżet uchybu [mm] | Obecne [mm/s²] | Największe przechodzące | Pierwsze niespełniające | Zalecane (zapas) | Uchyb przy zalecanym [mm] | Uwagi |
|---|---:|---:|---:|---:|---:|---:|---|
| X | 0.2 | 1000 | 4250 | 4375 | **3820** | 0.0000 | — |
| Y | 0.2 | 1000 | 4250 | 4375 | **3820** | 0.0000 | — |
| Z | 0.2 | 500 | 16000 | brak do limitu | **9440** | 0.0000 | niemonotoniczne: porażki poniżej przechodzącego (rezonans, utrata kroków) — zalecane poniżej najniższej porażki |

## Pomiary

| Oś | Przyspieszenie | Wynik | Uchyb [mm] | Powód |
|---|---:|---|---:|---|
| X | 1000 | PASS | 0.0000 | — |
| X | 2000 | PASS | 0.0000 | — |
| X | 4000 | PASS | 0.0000 | — |
| X | 8000 | FAIL | 0.0000 | zgubione kroki X ≤ 0: 408 kroków |
| X | 6000 | FAIL | 0.0000 | zgubione kroki X ≤ 0: 940 kroków |
| X | 5000 | FAIL | 0.0000 | zgubione kroki X ≤ 0: 32 kroków |
| X | 4500 | FAIL | 0.0000 | zgubione kroki X ≤ 0: 308 kroków |
| X | 4250 | PASS | 0.0000 | — |
| X | 4375 | FAIL | 0.0000 | zgubione kroki X ≤ 0: -532 kroków |
| X | 3820 | PASS | 0.0000 | — |
| X | 3440 | PASS | 0.0000 | — |
| Y | 1000 | PASS | 0.0000 | — |
| Y | 2000 | PASS | 0.0000 | — |
| Y | 4000 | PASS | 0.0000 | — |
| Y | 8000 | FAIL | 0.0000 | zgubione kroki Y ≤ 0: 380 kroków |
| Y | 6000 | FAIL | 0.0000 | zgubione kroki Y ≤ 0: 316 kroków |
| Y | 5000 | FAIL | 0.0000 | zgubione kroki Y ≤ 0: 200 kroków |
| Y | 4500 | FAIL | 0.0000 | zgubione kroki Y ≤ 0: 780 kroków |
| Y | 4250 | PASS | 0.0000 | — |
| Y | 4375 | FAIL | 0.0000 | zgubione kroki Y ≤ 0: 288 kroków |
| Y | 3820 | PASS | 0.0000 | — |
| Y | 3440 | PASS | 0.0000 | — |
| Z | 500 | PASS | 0.0000 | — |
| Z | 1000 | PASS | 0.0000 | — |
| Z | 2000 | PASS | 0.0000 | — |
| Z | 4000 | PASS | 0.0000 | — |
| Z | 8000 | PASS | 0.0000 | — |
| Z | 16000 | PASS | 0.0000 | — |
| Z | 14400 | FAIL | 0.0000 | zgubione kroki Z ≤ 0: 8 kroków |
| Z | 12960 | FAIL | 0.0000 | zgubione kroki Z ≤ 0: -4 kroków |
| Z | 11660 | FAIL | 0.0000 | zgubione kroki Z ≤ 0: 4 kroków |
| Z | 10490 | FAIL | 0.0000 | zgubione kroki Z ≤ 0: -8 kroków |
| Z | 9440 | PASS | 0.0000 | — |
| Z | 8500 | PASS | 0.0000 | — |
