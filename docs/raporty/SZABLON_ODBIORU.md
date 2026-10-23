# Raport odbioru — DO UZUPEŁNIENIA

Model-Author: Codex · szablon 2026-10-23 · GPL-2.0-or-later.
Wypełniać według [procedury](ODBIOR_STANOWISKA.md); po skopiowaniu popraw ten link.
**Wynik początkowy: BLOCKED. NIEZWERYFIKOWANE NA SPRZĘCIE.**
Nie usuwaj tego oznaczenia bez podpisanego odbioru rzeczywistej konfiguracji.

## Metryka i dowody wspólne

| Pole | Wartość / ścieżka do załącznika |
|---|---|
| ID raportu, początek/koniec UTC, wykonawca, zatwierdzający | DO UZUPEŁNIENIA |
| Zakres: sim / Plant / desktop / hardware, cel: prototyp / 1.0 | DO UZUPEŁNIENIA |
| SHA repo, gałąź, PR, diff i użyte pliki nieśledzone | DO UZUPEŁNIENIA |
| SHA-256 archiwum INI/HAL/machine.yaml/tool.tbl/parametrów | DO UZUPEŁNIENIA |
| OS, jądro/PREEMPT_RT, LinuxCNC/Qt, Python/pakiety, RIP SHA | DO UZUPEŁNIENIA |
| Obraz kontenera + ID/digest, wersja Podman/Docker (jeśli użyto) | DO UZUPEŁNIENIA |
| CPU, płyta/BIOS, RAM, zasilanie, chłodzenie | DO UZUPEŁNIENIA |
| GPU/sterownik, monitor, rozdzielczość i skala desktopu | DO UZUPEŁNIENIA |
| NIC/driver/firmware, topologia, IgH/lcec, napędy/firmware, mapa PDO | DO UZUPEŁNIENIA |
| BIOS, affinity CPU/IRQ, governor, izolacja CPU, okres servo | DO UZUPEŁNIENIA |
| Ocena ryzyka, schemat elektryczny/rewizja, protokół toru fizycznego | DO UZUPEŁNIENIA |
| Przyrządy, numery/kalibracja, dokładność, plan kanałów i polecenia pomiaru | DO UZUPEŁNIENIA |
| Czasy, powtórki, obciążenia, progi latencji/DC/temperatury/płynności/ruchu | DO UZUPEŁNIENIA — zatwierdzić przed startem |
| Lokalizacja trwałego archiwum, manifest plików z SHA-256 | DO UZUPEŁNIENIA |

## Rejestr kart

Każdy ID poniżej ma własną kartę według następnej sekcji. Nie oznaczaj całej grupy
PASS na podstawie samego kodu wyjścia, jeśli część wymaganego zakresu pominięto.

| ID / zakres | Wynik | Przyczyna / odsyłacz do karty |
|---|---|---|
| A1 lint, pytest, wymagania | BLOCKED | niewykonane |
| A2 C i sanitizery | BLOCKED | niewykonane |
| A3 scenariusze i macierz Plant | BLOCKED | niewykonane |
| A4 rzeczywisty LinuxCNC + QtVCP (wirtualna maszyna) | BLOCKED | niewykonane |
| B1 trzy launchery i zamknięcie | BLOCKED | niewykonane |
| B2 bazowanie, JOG, MDI | BLOCKED | niewykonane |
| B3 liczby, wrzeciono, wymiana | BLOCKED | niewykonane |
| B4 program, pauza, wznowienie i finał | BLOCKED | niewykonane |
| B5 .lnx, edycja i raport | BLOCKED | niewykonane |
| B6 grzyb HMI i reset w Plant | BLOCKED | niewykonane |
| C1 awarie z atrapą | BLOCKED | niewykonane |
| T1 latencja hosta | BLOCKED | niewykonane |
| T2 cykl LinuxCNC | BLOCKED | niewykonane |
| T3 EtherCAT bez ruchu | BLOCKED | niewykonane |
| T4 osie i limity | BLOCKED | niewykonane |
| T5 awarie stanowiska | BLOCKED | niewykonane |
| T6 próba długa | BLOCKED | niewykonane |
| T7 renderer i RT równolegle | BLOCKED | niewykonane |
| E1 instalacja, aktualizacja i rollback | BLOCKED | niewykonane |
| E2 komplet dowodów i audyt wydania | BLOCKED | niewykonane |

## Karta pojedynczej próby — powiel dla każdego ID i powtórki

- ID / powtórka / poprzednia nieudana próba: DO UZUPEŁNIENIA.
- Warunki wstępne, wersje, potwierdzenie izolacji lub zgoda na próbę fizyczną: DO UZUPEŁNIENIA.
- Start/koniec UTC i monotoniczny, rzeczywisty czas i liczba próbek: DO UZUPEŁNIENIA.
- Dokładne polecenia / działania operatora i kody wyjścia: DO UZUPEŁNIENIA.
- Oczekiwanie, jednostki i progi zatwierdzone **przed** testem: DO UZUPEŁNIENIA.
- Rzeczywisty wynik, min/max, histogram, utracone próbki i liczniki błędów: DO UZUPEŁNIENIA.
- Pliki surowe/logi/zrzuty/CSV, SHA-256 i źródło czasu pomiaru: DO UZUPEŁNIENIA.
- Odchylenia, pominięcia, incydenty, zadziałanie reguły przerwania: DO UZUPEŁNIENIA.
- PASS/FAIL/BLOCKED i uzasadnienie; wykonawca i data: BLOCKED — niewykonane.
- Działanie naprawcze, właściciel i termin następnego kroku: DO UZUPEŁNIENIA.

## Decyzja o wydaniu 1.0

| Wymagany dowód z KWALIFIKACJA_RT §5 | Wynik / dowód |
|---|---|
| CSP, cykl 1 ms na opisanym sprzęcie, T1–T7 | BLOCKED — brak kampanii |
| EtherCAT/PDO/DC, reakcje napędów i brak niewyjaśnionych deadline miss | BLOCKED — brak pomiarów |
| UI/SQLite/renderer/symulacja bez blokowania RT | BLOCKED — brak równoległych pomiarów |
| Wykrywanie i oznaczanie utraty telemetrii | BLOCKED — brak odbioru T5 |
| Tor fizyczny niezależny od zwykłego procesu i odbiór pulpitu | BLOCKED — brak podpisanych protokołów |
| Powtarzalna instalacja, aktualizacja, rollback i dane po migracji | BLOCKED — brak protokołu |
| Manifest wersji, dokumentacja, raporty i audyt licencji | BLOCKED — brak kompletu |

Decyzja: **BLOCKED**. Stosuj agregację z procedury; każda niezgodność → FAIL.
Osoba zatwierdzająca / data / ograniczenia dopuszczonego użycia: DO UZUPEŁNIENIA.
