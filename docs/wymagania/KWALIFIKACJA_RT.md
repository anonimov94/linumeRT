# Wymagania: kwalifikacja czasu rzeczywistego i kryteria wydania

Wersja 1.0 · 2026-10-17 · status: obowiązująca

## 1. Zasada
Testy RT wykonuje się na dokładnie opisanej konfiguracji sprzętu i oprogramowania. Liczą się maksima,
histogram, powtarzalność i zachowanie pod obciążeniem, nie średnia. Wynik w maszynie wirtualnej nie
świadczy o sprzęcie.

## 2. Kryteria robocze (do potwierdzenia dla konkretnej maszyny)
- cykl nominalny 1000 µs; czas pracy RT w scenariuszu ≤ 800 µs;
- odchylenie fazy cyklu ≤ 50 µs (cel projektowy);
- zero niewyjaśnionych przekroczeń terminu, utrat PDO/WKC i błędów synchronizacji;
- przetestowane reakcje na utratę komunikacji, błąd napędu i przekroczenie czasu cyklu.

## 3. Plan testów
| Test | Zakres |
|---|---|
| T1 | latencja systemu bez i z obciążeniem (CPU, GPU, dysk, USB, sieć) |
| T2 | cykl LinuxCNC 1 ms: czas wykonania i odchylenie fazy pod obciążeniem UI |
| T3 | EtherCAT bez ruchu: PDO, WKC, stan OP, watchdog, DC, stany CiA 402 |
| T4 | jedna oś, potem wszystkie: skalowanie, kierunki, limity, bazowanie, reakcje na błędy |
| T5 | obciążenie i awarie: UI, symulacja, logowanie razem; odłączenie sieci, utrata magistrali, błąd napędu, pełny dysk |
| T6 | test długi 24–72 h: anomalie, temperatury, throttling |
| T7 | renderer 30 FPS przy 100 000 segmentów równolegle z pomiarem RT |

## 4. Raport testu
Identyfikator, data, osoba, commit; CPU, płyta, BIOS, RAM, karta sieciowa i sterownik; jądro i PREEMPT_RT,
wersje LinuxCNC, IgH, bibliotek; ustawienia BIOS, przypisania CPU, zasilanie; warunki obciążenia i czas;
histogram i maksima; błędy magistrali i napędów; liczba przekroczeń terminu; PASS/FAIL z uzasadnieniem.
PASS tylko przy kryteriach ustalonych przed testem.

Procedura wykonawcza T1–T7, warunki przerwania, oddzielny odbiór sim/Plant i pulpitu:
[Odbiór stanowiska](../raporty/ODBIOR_STANOWISKA.md).
Każdy przebieg zapisuj według [szablonu](../raporty/SZABLON_ODBIORU.md),
z surowymi pomiarami. Brak stanowiska lub zatwierdzonych progów = BLOCKED;
testy CI nie zastępują kwalifikacji fizycznej konfiguracji.

## 5. Kryteria wersji 1.0
- osie CSP działają na opisanej konfiguracji sprzętowej, cykl 1 ms zakwalifikowany;
- brak niewyjaśnionych przekroczeń terminu w przebiegu kwalifikacyjnym;
- EtherCAT, PDO, synchronizacja i reakcje na błędy udokumentowane;
- ekran, rdzeń, SQLite, renderer i symulacja nie blokują RT;
- utrata telemetrii wykrywana i oznaczana;
- instalacja, aktualizacja i rollback powtarzalne;
- funkcje bezpieczeństwa nie zależą od ekranu ani zwykłego procesu;
- dokumentacja, manifest wersji, raporty testów i audyt licencji dołączone.
