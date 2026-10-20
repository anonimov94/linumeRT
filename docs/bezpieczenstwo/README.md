# Bezpieczeństwo: audyt i rozdział odpowiedzialności

Model-Author: Codex · 2026-10-20 · analiza main 7ad631379106144ae46e1212a29f6cc9a8f9d48b.
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Założenia właściciela

PC jest dodatkowym warunkiem zezwolenia na ruch fizycznej obrabiarki.
Brak sygnału życia PC/HMI ma odbierać zezwolenie. Sam stan wysoki wyjścia nie dowodzi,
że PC działa: potrzebny jest niezależny od PC sprzętowy nadzór zmian sygnału.
PC nie może obejść otwartego obwodu sprzętowego ani resetować sprzętowego urządzenia safety.
Powrót sygnału życia i reset nie mogą samoczynnie uruchamiać ruchu.

Symulacja materiału i kolizji jest diagnostyką, poza torem zezwolenia na ruch.
Jej proces odczytuje stan LinuxCNC i raportuje zdarzenia; nie wysyła E-STOP, resetu,
STO ani innych komend ruchu. Odrębne przyciski operatora sterujące LinuxCNC zachowują
swoją rolę. Zakres usunięcia emulacji safety w Plant wymaga doprecyzowania właściciela;
do tego czasu nie zmieniamy jego watchdogów, protokołu ani testów usterek.

## Ocena audytu Groka według aktualnego kodu

| Punkt | Ustalenie Codexa | Działanie |
|---|---|---|
| U1 profile | VIRTUAL_MODE istnieje, ale flaga nie dowodzi braku fizycznych wyjść; brak zweryfikowanego profilu sprzętowego | Rozdzielić konfiguracje i odmówić eksportu sprzętowego bez jawnego kontraktu I/O |
| U2 reset GUI | D35 ma już zatrzask HAL i watchdog; D37 dopuszcza podwójny Reset | Rozdzielić potwierdzenie software od fizycznego resetu safety; HMI nie resetuje przekaźnika safety |
| U3 walidacja | schema.IO.estop jest obowiązkowe; validate.r_estop_present odrzuca niezadeklarowane wejście | Nie dublować pola safety.estop_input; istniejąca walidacja nie potwierdza fizycznego okablowania |
| U4 STO | Emulacja Plant istnieje, brak odbioru sprzętowego | Udokumentować różnicę między STO, zatrzymaniem, odcięciem energii i resetem |
| U5 komunikacja | Plant ma watchdog i connected w łańcuchu HAL | Nie przedstawiać tego jako sprzętowej funkcji safety; EtherCAT wymaga osobnego projektu |
| U6 limity | LinuxCNC ma hard/soft limits, Plant modeluje krańcówki | Nie wymagać bez analizy ryzyka włączania każdej krańcówki do E-STOP |
| U7 dokumentacja | Brakuje jednoznacznego rozdziału od symulacji | Ten dokument i kontrakt HAL jako punkt wejścia |
| U8 sieć | Wymaga osobnego sprawdzenia startera, nasłuchu i wdrożenia | Osobny etap; nie deklarować potwierdzonej ekspozycji bez odczytu konfiguracji |

## Tor fizycznej maszyny

Schemat funkcjonalny, nie schemat elektryczny do wykonania:

```text
Fizyczne urządzenia ochronne + reset fizyczny
                  |
     niezależny układ bezpieczeństwa ----> funkcje napędów / wrzeciona
                  |
            monitor stanu ----------------> LinuxCNC (zezwolenie)
                  ^
PC/HMI -> sygnał życia -> zewnętrzny nadzór -> dodatkowe odebranie zezwolenia
```

Dobór interfejsu nadzoru PC i jego miejsca w torze należy do projektu maszyny.
Zwykły PC, HAL, UDP, standardowy przekaźnik i programowy watchdog nie uzyskują
przez ten schemat kategorii ani PL/SIL. Nie przypisujemy z góry kategorii 2/3
ani PL d/e: wymagany poziom wynika z oceny ryzyka i walidacji konkretnej maszyny.
Zawieszenie GUI i awaria systemu/PC to różne uszkodzenia; watchdog w HAL nie dowodzi
wykrycia awarii całego PC.

STO uniemożliwia wytwarzanie momentu przez napęd, ale nie jest izolacją elektryczną,
hamulcem podtrzymującym oś pionową ani gwarancją natychmiastowego zatrzymania.
Feed hold, M5, quick stop CiA 402 i amp disable są funkcjami sterowania,
nie automatycznie funkcjami bezpieczeństwa. Kategorie zatrzymania 0/1 i dobór
STO/hamowania/styczników wymagają analizy maszyny; nie narzucamy odcinania zasilania VFD
na podstawie samego alarmu programu. Reset fizycznego safety i potwierdzenie LinuxCNC
są oddzielnymi czynnościami; żadne nie stanowi polecenia rozpoczęcia ruchu.

## Wdrożenie i odbiór

1. Usunąć komendy safety z procesu symulacji i zmienić komunikaty zdarzeń na diagnostyczne.
2. Po doprecyzowaniu zakresu Plant oddzielić testowy model awarii od normalnej symulacji.
3. Dodać jawny profil sprzętowy i walidację eksportu bez zgadywania pinów z nazw.
   Samo szukanie tekstu pętli w HAL nie wykrywa połączeń pośrednich, aliasów i skryptów.
4. Zaprojektować kontrakt nadzoru PC: zanik zasilania, stałe 0/1, zawieszenie GUI,
   zawieszenie OS, restart i utrata I/O odbierają zgodę; powrót nie wznawia ruchu.
5. Przed sprzętem: niezależny projekt, dobór elementów i pomiary reakcji całego toru.
   Nie zastępujemy tego testem Qt, deklaracją YAML ani testem Plant.

Brak odbioru sprzętowego oznacza brak deklaracji gotowości do użycia na maszynie.

## Etap 2 — deklaracja profilu i toru I/O

Narzędzie inżynierskie (nie uruchamia CNC):

```bash
PYTHONPATH=core python -m linumert.machine.deployment ścieżka/do/maszyna.ini
```

Wymaga jawnego `[LINUMERT] MACHINE_PROFILE = sim|plant|hardware`.
Dla hardware odrzuca VIRTUAL_MODE=1, HMI_ESTOP_BYPASS=1 i brak deklaracji:

- `ESTOP_MONITOR_PIN`: fizyczne wejście stanu niezależnego obwodu;
- `PC_HEARTBEAT_OUTPUT_PIN`: fizyczne wyjście sygnału życia PC;
- `PC_WATCHDOG_MONITOR_PIN`: osobne wejście sprzężenia z zewnętrznego nadzoru PC;
- `EXTERNAL_PC_WATCHDOG=1`, `PHYSICAL_RESET=1`, `AUTOMATIC_RESTART=0` w sekcji SAFETY.

Piny muszą mieć różne nazwy; znane sygnały software (iocontrol, halui, HMI, watchdog HAL,
LRT-NET) nie są akceptowane jako deklaracje fizycznego I/O. To kontrola deklaracji,
nie dowód rodzaju, kierunku czy okablowania pinu. Nie analizuje grafu HAL.
Nie potwierdza wykonania fizycznego resetu ani obecności urządzenia nadzoru.
Przykład do uzupełnienia: `config/hardware/safety-contract.ini.example`.
Nie zawiera HAL ani konfiguracji napędów; puste piny celowo powodują odmowę.

Wynik JSON zawsze ma `hardware_verified=false`; kod 2 oznacza błędną/niekompletną
 deklarację, kod 0 jedynie jej kompletność. Nie jest jeszcze podłączony do startu HMI
ani do generatora/eksportu (sesje 061/062/070). Kolejny krok: integracja kontroli na granicy
uruchomienia profilu hardware, kontrola rzeczywistych pinów/grafu HAL i testy odmowy startu.
Nie zmieniamy automatycznie istniejących konfiguracji sim/Plant.
