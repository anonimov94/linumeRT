# Raport zapisanego przebiegu — checkpoint

Model-Author: Codex · 2026-11-07. VERTICAL-REPORT, sesje024/049/052/053/068.

Praca w toku na codex/job-run-report-20261107, nad dowodami etapu wykonania.
Jeden backend offline wiąże niezmienną konfigurację z manifestem, próbkami i wynikiem.
CLI run-report i uwierzytelnione API używają tej samej funkcji; WebHMI ma przycisk
raportu, maksima/RMS błędu osi, czas, pauzę, dolną granicę modelu i pobranie JSON.
Odczyt plików odbywa się poza blokadą obiegu HMI i nie wysyła poleceń sterowania.

Raport zachowuje jednostki i czasy monotoniczne, hashe odczytanych bajtów oraz jawne
braki/luki. Tor jest ograniczony do maksymalnie2001 zachowanych punktów bez interpolacji.
Maksima i RMS dotyczą próbek, a following_error to różnica zadana−rzeczywista
współrzędnych maszyny, nie surowe joint.ferror_current. Stary wynik zakończenia bez
potwierdzonego ustalenia, brak końcowego wyniku, uszkodzenie lub luka nie daje PASS
końcowej pozycji. Nie wystawiamy globalnego PASS maszyny ani kwalifikacji sprzętu.

9 testów raportu/CLI/API PASS;46 regresji bramy/klienta/architektury PASS i4skip;
ruff i składnia JS PASS. To checkpoint, bez klikniętego odbioru raportu ani końcowego
porównania CLI/API/GUI na rzeczywistych danych. Pełna regresja, przypadki wymuszeń,
ponowny odczyt raportu w WebHMI bez kontrolera i domknięcie VERTICAL-REPORT pozostają
otwarte. Właściciel polecił zakończyć bieżący etap wykonania; dalszy rozwój raportu
zapisano do osobnego draft PR.

## Kontynuacja poziomu4 — 2026-11-08

Model-Author: Codex. Po zamknięciu RUN wznowiono pełny cel. Wstępny odczyt7 oryginalnych
archiwów i zamrożonych konfiguracji działa; trzy odebrane końcowe ustalenia wyróżnione,
starsze zakończenia nie otrzymują PASS pozycji. Pełne GUI126,645824s obejmuje14,911371s
obserwowanej pauzy; dolna granica modelu107,958839s nie jest terminem zakończenia.
Uzupełniono piki błędu i alarmy o czas/linię, kontrolę zgodności błędu z pozycjami,
luki początku/końca oraz porównanie czasu wyłącznie dla zakończonego programu.
15 testów PASS; ponowny odczyt bez kontrolera, wykres i odbiór GUI nadal wymagane.
