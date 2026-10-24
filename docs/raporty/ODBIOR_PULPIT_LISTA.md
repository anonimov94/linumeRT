# Lista do przeklikania na pulpicie właściciela (028–035, bramki G2–G4)

Model-Author: Claude · 2026-10-24 · GPL-2.0-or-later.

Te punkty wymagają człowieka przy ekranie. Agent nie ma pulpitu z LinuxCNC ani oceny „na oko”.
Pozostała praca w kodzie jest w PR. Wynik każdego punktu to **PASS / FAIL / BLOCKED**
z krótką notatką i zrzutem, jak w [szablonie](SZABLON_ODBIORU.md). Procedura pełnego stanowiska:
[ODBIOR_STANOWISKA](ODBIOR_STANOWISKA.md). Wszystko na sim/Plant, bez fizycznego I/O.
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Przygotowanie (raz, ok. 10 min)

1. WSL Debian 12 `linumeRT-Debian12`, katalog repozytorium na aktualnym `main`.
2. Ekran na symulatorze: `linuxcnc config/sim/linumert_xyz/linumert_xyz.ini` ([SIM_WSL](../SIM_WSL.md)).
3. Ekran z Plant: według [PLANT_START](../PLANT_START.md) (`config/plant/linumert_plant_xyz/`).
   Plant liczy domyślnie 4 podkroki (PR #116). Gdy panel Plant pokazuje opóźnienia, zapisz obciążenie CPU.
4. Na koniec dnia: `docs/raporty/<data>-pulpit/` ze zrzutami i wypełnioną tą listą.

## M2 — ekran (sesje 028–035, bramka G2)

| # | Sesja | Co kliknąć | Oczekiwane |
|---|---|---|---|
| 1 | 028 kompozycja | Przejdź wszystkie obszary lewej szyny; zmień skórkę (Classic, Classic × Neon, pozostałe) | Układ: szyna z lewej, pasek trybu/stanu u góry, duże akcje u dołu; nic nie ucięte przy 1280×800 i 1920×1080 |
| 2 | 029 tryby/JOG | Tryb Ręczny: JOG ciągły i krokowy (0,001/0,01/0,1/1 mm), wpisanie własnego kroku; przełącz tryby | Oś jedzie o zadany krok; zmiana trybu w trakcie ruchu niemożliwa albo zatrzymuje ruch |
| 3 | 029 MPG | Jeśli masz pokrętło/emulację: wybór osi i mnożnika | Ruch zgodny z mnożnikiem; bez MPG zostaje BLOCKED |
| 4 | 030 MDI | `G0 X10 Y10`, `G1 Z-1 F100` przez klawiaturę ekranową i fizyczną; historia MDI | Ruch wykonany, historia zapamiętana, błędna linia daje czytelny komunikat |
| 5 | 031 AUTO | `linumert_demo.ngc`: start, pauza, wycofanie/powrót (D38-A), stop; ETA na pasku | Pauza bez kolizji, powrót na tor, ETA maleje sensownie |
| 6 | 031 od linii | Uruchom od linii ze środka programu (po M6, z łukiem) | Ekran pyta o stan (narzędzie, wrzeciono, Z bezpieczne); jeśli tego brakuje, wpisz FAIL (dług D38-B) |
| 7 | 033 zero detalu | Ustaw G54 i G55 z pozycji, kreator zera na przygotówce; sprawdź G59.3 | Wartości w tabeli układów i w DRO zgodne; G59.1–G59.3 dostępne |
| 8 | 033 sonda | Sondowanie Z i narożnika na Plant (sonda wirtualna) | Wynik zgodny z położeniem przygotówki w Plant ±0,05 mm |
| 9 | 034 M6 | Program z `T2 M6`: dialog zmiany, potwierdzenie, anulowanie (W-2130) | Po potwierdzeniu G43 aktywne (długość T2); anulowanie zatrzymuje program z W-2130 |
| 10 | 035 alarmy | Wywołaj E-STOP, krańcówkę (najazd JOG), alarm napędu w panelu Plant | Kody W/E/K/P z katalogu, historia, filtr i eksport CSV |
| 11 | 036 role | Ustaw PIN technologa/serwisu, zaloguj się i wyloguj, spróbuj edycji tabeli narzędzi jako operator | Blokada edycji dla operatora, wpis w audycie |
| 12 | 007/037 język | `LINUMERT_LANG=en` i bez zmiennej | Podpowiedź Resetu PL/EN; brakujące tłumaczenia zanotuj (dług 037) |
| 13 | G2 podobieństwo | Przegląd świeżym okiem według `docs/prawne/` (ZAKAZANE_NAZWY, WYTYCZNE_IP §7) | Brak nazw producentów i „całego wrażenia” cudzego ekranu |

**Bramka G2:** punkty 1–2, 4–5, 7, 9–10 i 13 PASS (MPG i sonda mogą być BLOCKED z uzasadnieniem).

## M3 — programowanie dialogowe (bramka G3)

| # | Co zrobić | Oczekiwane |
|---|---|---|
| 14 | Na stronie Cykle złóż program z 5 kroków: planowanie, wiercenie G81, kieszeń prostokątna, rowek łukowy, kontur z korekcją | Podgląd 2D każdego kroku, zapis `.lnx` i `.ngc` |
| 15 | Wykonaj ten `.ngc` na Plant (AUTO) | Bez alarmów; czasy i błędy nadążania z panelu Plant do raportu |
| 16 | Porównaj z [suite_cycles](suite_cycles.md) (40/40 PASS w atrapie) | Te same generatory nie dają alarmu także z prawdziwym LinuxCNC |

**Bramka G3:** punkty 14–15 PASS.

## M4 — symulacja (bramka G4)

| # | Co zrobić | Oczekiwane |
|---|---|---|
| 17 | Dla 3 programów (`linumert_demo.ngc`, `linumert_rowek.ngc`, program z punktu 14) zapisz czas z symulacji i czas wykonania na Plant | Różnica ≤ 10 % (dziś czas offline nie uwzględnia przyspieszeń — sesja 053; spodziewany wynik: symulacja krótsza) |
| 18 | `linumert_kolizja.ngc` na stronie Symulacja | K-302 (G0 w materiał) wykryte i pokazane |
| 19 | Program z wejściem w materiał przy M5 | K-301 wykryte |

**Bramka G4:** 17–19 PASS. Jeśli 17 da FAIL przez brak przyspieszeń, wpisz FAIL i wskaż 053; nie zmieniaj progu.

## Po przeklikaniu

Wyniki wpisz do `docs/raporty/<data>-pulpit/README.md` (lub przekaż agentowi: zrzuty i notatki).
Na tej podstawie zmienimy statusy 028–035 i bramek w `docs/roadmap/plan.json`.
