# linumeRT HMI — architektura ekranów workflow (projekt v0.1)

Status: własne widoki operatora na QtVCP / LinuxCNC 2.9. Kontrakt obsługi i dalszych zmian:
[`OBSLUGA_OPERATORA.md`](../OBSLUGA_OPERATORA.md), D36/D37. Sprzęt fizyczny niezweryfikowany.

## Stan realizacji

Dostępne: Start, Maszyna, Bazowanie, Zero detalu 3D, Narzędzia, Program (wybór i podgląd),
Symulacja, Produkcja i Diagnostyka. Bazowy QtDragon jest osobną stroną zaplecza.
Na samej górze: trzy alarmy i Reset; niżej stan maszyny i tryb JOG/MDI/AUTO.
Maszyna i Symulacja współdzielą panel JOG/MDI, M3/M4/M5 i potwierdzanej wymiany M6.
Specjalista umożliwia wolne wycofanie; fizyczne safety i limity LinuxCNC pozostają nadrzędne.
Wirtualny bliźniak jest jawnie oznaczony `VIRTUAL_MODE=1`; ma reset materiału i HOME.

## Cel
Stan po integracji PR #45/#46 (2026-10-19): własne widoki Bazowanie (stawy i czujniki),
Program (wybór, podgląd i jawne wczytanie), Symulacja i Narzędzia. Własne Zero detalu oferuje
maszynę 3D, cztery przygotówki, profil odlewu i G54–G59 ([instrukcja](../ZERO_DETALU.md)).
Edycja i sprawdzanie G-code w widoku Program pozostają kolejnymi krokami.

Rozdzielić monolityczny QtDragon na dedykowane widoki operatora bez przepisywania sterowania LinuxCNC. Nawigacja nie może wykonywać komend ruchu ani zmieniać trybu pracy automatycznie.

## Globalny shell (widoczny na każdej zakładce)
- Najwyższy pasek: trzy ostatnie alarmy i Reset (pojedynczy/podwójny, D37).
- Pasek stanu: tryb AUTO/MDI/MANUAL, MACHINE ON, homed, interpreter, połączenie LRT-NET, aktywny program.
- Stałe DRO X/Y/Z (G54 i przełączalnie G53), F/S override, alarmy, status wrzeciona i narzędzia.
- Wyraźny stan sprzętowego E-STOP; GUI nie zastępuje toru bezpieczeństwa.
- Nawigacja główna: Start, Przygotowanie, Program, Produkcja, Ręczne, Diagnostyka; druga warstwa podstron.
- Ostrzeżenia modalne tylko dla operacji nieodwracalnych; alarmy i potwierdzenia dostępne stale.

## Ekrany według kolejności pracy
| Faza | Widok | Funkcje | Warunki |
|---|---|---|---|
| 0 | Start | checklist gotowości, ostatnie alarmy, stan osi i napędów | odczyt zawsze |
| 1 | Bazowanie | home all/axis, czujniki NC, sekwencja, status homed | komendy wyłącznie w dopuszczonym trybie LinuxCNC |
| 2 | Zero detalu | G54–G59, sonda, touch-off, offsets, potwierdzenie układu | blokada przy aktywnym programie |
| 3 | Narzędzia | tabela, pomiar długości/średnicy, ATC, narzędzie aktywne | interlock wrzeciona, osłony i pozycji wymiany |
| 4 | Wybór programu | lista plików, podgląd G-code, metadane, wybór | brak uruchomienia przez sam wybór |
| 5 | Edytor programu | edycja, zapis, walidacja i historia zmian | ostrzeżenie przy edycji aktywnego pliku |
| 6 | Symulacja | trajektoria, soft limits, strefy zakazane, dry-run | symulacja wyraźnie oddzielona od ruchu rzeczywistego |
| 7 | Produkcja | Cycle Start, Hold, Stop, restart, postęp, override | stan i blokady LinuxCNC |
| 8 | Ręczne / MDI | JOG, MPG, inkrement, MDI, bezpieczna prędkość | deadman/enable zgodnie z konfiguracją sprzętową |
| 9 | Diagnostyka | software: HAL, logi, LinuxCNC; hardware: CiA402, LRT-NET, I/O, E-STOP, krańcówki | diagnostyka nie omija interlocków |
| 10 | Ustawienia | profil maszyny, motyw, uprawnienia, kalibracja | kontrola uprawnień |

## Implementacja przy zachowaniu upstream
1. Nie zmieniać `linumert_upstream_handler.py`. Logikę linumeRT umieszczać w `linumert_handler.py` i osobnych modułach.
2. Zachować nazwy istniejących widgetów QtDragon wymagane przez handler i połączenia HAL. Najpierw zrobić inwentaryzację `linumert.ui`: widgety, akcje, signal-slot i zależności.
3. Zbudować `QStackedWidget`/zagnieżdżone zakładki jako warstwę nawigacji; przenosić istniejące widgety, nie duplikować instancji podłączonych do HAL.
4. Centralny router widoków ma sterować wyłącznie prezentacją. Akcje maszyny nadal przez ACTION/STATUS QtVCP.
5. Stan UI (ostatnia zakładka) przywracać tylko dla widoków bezpiecznych; po restarcie domyślnie Start.
6. Układ skalowalny dla 1280×768; duże cele dotykowe, klawiatura i czytelność alarmów.

## Etapy realizacji i odbiór
- HMI-01: mapa widgetów i kontrakt sygnałów QtDragon; screenshot bazowy.
- HMI-02: shell + nawigacja + Start/Bazowanie/Ręczne, bez regresji istniejących akcji.
- HMI-03: Zero detalu/Narzędzia z potwierdzeniami i interlockami.
- HMI-04: Programy/Edytor/Symulacja/Produkcja.
- HMI-05: Diagnostyka software/hardware + scenariusze alarmów.
- HMI-06: testy QtVCP pod Xvfb i LinuxCNC RIP, zrzuty wszystkich widoków, testy 1280×768 i obsługi klawiaturą.

Kryteria: brak ruchu przy zmianie zakładki; alarm/E-STOP widoczny zawsze; brak osieroconych widgetów i utraconych sygnałów; wszystkie bazowe funkcje QtDragon dostępne; przejście Start → Bazowanie → Zero → Narzędzia → Program → Symulacja → Produkcja bez powrotu do monolitycznego ekranu.

**Bezpieczeństwo:** projekt UI nie jest walidacją funkcji bezpieczeństwa CNC; testy na sprzęcie wymagane przed eksploatacją.
