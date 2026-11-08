# Badania przed integracją sterowania

2026-11-08 · Model-Author: Codex.

Zakres: PR #211 (sonda), #212 (STOP/E-STOP i śledzenie narzędzi),
#213 (oznaczenia operacji) oraz #231 (raport przebiegu). Polecenie właściciela:
zbadać dokumentację i fora CNC, następnie stosować ustalenia podczas domykania main.
To notatka źródłowa i kryteria przeglądu, nie drugi rejestr statusów.

## Sondowanie: punkt styku i punkt zatrzymania

[Dokumentacja LinuxCNC 2.9, G38.x](https://linuxcnc.org/docs/2.9/html/gcode/g-code.html#gcode:g38)
rozróżnia zatrzaśnięty wynik pomiaru i zatrzymanie ograniczone dynamiką maszyny.
Parametry 5061–5069 opisują punkt zadziałania w układzie używanym podczas pomiaru;
nie należy zastępować go późniejszą pozycją zatrzymania. Nieudane G38.2 zgłasza błąd.
G10 L20 ustawia układ na podstawie aktualnej pozycji, więc użycie go po odjeździe
wymaga jawnego uwzględnienia różnicy względem zatrzaśniętego styku.

[Wątek LinuxCNC o kalibracji płytki](https://forum.linuxcnc.org/38-general-linuxcnc-questions/50132-trouble-with-z-axis-touch-plate-calibration)
oraz [dyskusja CNC Arena o pomiarze i kalibracji](https://en.cncarena.com/siemens/forum/thread/103325-2-kreistaschen-antasten-mittelwert-als-nullpunkt/)
są wskazówkami praktycznych problemów prędkości, kierunku i korekcji sondy.
Odczyt pełnych stron nie powiódł się; dostępne były fragmenty indeksu. Nie traktujemy
ich jako dowodu poprawności konkretnej poprawki. Podstawą implementacji jest API
LinuxCNC i własny test sim/Plant, nie przenoszenie makr producenta.

Wniosek do #211: sprawdzić aktywny układ, jednostki, kierunki XYZ, chybienie,
sondę już zwartą, zatrzymanie oraz to, że po błędzie zero nie zostaje zmienione.
Odbiór pojedynczego styku nie zastępuje kalibracji i powtarzalności sprzętu.

## Wznowienie, narzędzia i numery operacji

[LinuxCNC: O codes](https://linuxcnc.org/docs/2.9/html/gcode/o-code.html)
wymaga spójnych, unikalnych oznaczeń bloków. Numer O oznacza sterowanie przepływem,
nie jest sam w sobie punktem bezpiecznego wznowienia.
[Zgłoszenie użytkownika LinuxCNC 2.7.15](https://forum.linuxcnc.org/38-general-linuxcnc-questions/40228-issues-with-remapped-m6-subroutine-and-o-sub-routines-when-running-from-line)
opisuje wykonanie wcześniejszych remapów M6 i zewnętrznych podprogramów przy starcie
od linii. To historyczna obserwacja, nie potwierdzenie błędu wersji 2.9.

[Siemens: opis wariantów block search](https://sieportal.siemens.com/de-bg/products-services/10508579)
rozróżnia wyszukiwanie z obliczeniem stanu i bez niego. To użyteczny punkt porównania
funkcjonalnego: odnalezienie numeru bloku nie dowodzi przywrócenia narzędzia, offsetów
i innych stanów programu. Nie przenosimy zachowania tego sterowania do LinuxCNC.

Wnioski do #212/#213: śledzić rzeczywiście wykonane instrukcje T/M6/M61, testować
pominięte warunki, pętle i podprogramy. Komentarze umieszczać poza linią O.
Sprawdzić odrębnie pełne wykonanie i start od linii na LinuxCNC 2.9, szczególnie
remap M6 i stan modalny. Etykiety operacji nie zamykają D38-B.

## Raport i znaczenie pomiaru

[LinuxCNC Python API](https://linuxcnc.org/docs/2.9/html/config/python-interface.html)
udostępnia oddzielne pola pozycji, stanów osi/przegubów i `joint.ferror_current`.
Różnica pozycji kartezjańskich odczytanych przez NML i błąd pojedynczego przegubu
muszą mieć oddzielne nazwy. Portal z dwiema osiami napędowymi Y wymaga obu przegubów.

[Relacja użytkownika LinuxCNC z diagnostyki skoku błędu](https://forum.linuxcnc.org/10-advanced-configuration/33263-cannot-explain-ferror-cnc-hobbing-machine)
wskazuje na potrzebę zachowania komendy i sprzężenia razem, zamiast oceniania samej
liczby błędu. [Dokumentacja rejestracji Siemens TRCDATA](https://support.industry.siemens.com/cs/attachments/109815659/TRCDATA_fct_man_en-US.pdf)
oddziela okres próbkowania sygnału i okres danych wyjściowego bufora.
Porównanie funkcjonalne prowadzi do jawnego raportowania próbkowania, redukcji
wykresu oraz brakujących danych. Nie wynika z niego gwarancja śladu RT w NML.

[Forum Siemens Industry: pomiar G120C](https://support.industry.siemens.com/forum/WW/en/post/1009473/)
zawiera praktyczną uwagę o porównaniu odczytu z pomiarem w konkretnej instalacji.
Strona przekierowuje do aplikacji SiePortal wymagającej JavaScript; tekst dostępny
w indeksie nie stanowi kwalifikacji naszej maszyny ani dokładności napędów.

Wnioski do #231: podawać max/RMS próbek, lukę czasową, jednostki, mapowanie przegubów,
oddzielać końcowe ustalenie od błędów w ruchu. Wyświetlać ograniczenia również po
ponownym otwarciu offline. Suma kontrolna zapewnia spójność pliku, nie autentyczność
źródła. Odrzucać sprzeczne statystyki i mapowanie; oryginalne archiwa zachować.

## Zastosowanie i granice

Pierwszy przegląd wykrył nieaktualny opis raportu: deklarował brak surowego FERR,
choć nowy kanał już go zawiera. Poprawiono opis. Dodano kontrolę nieujemnego RMS,
relacji RMS do maksimum i kompletnego mapowania przegubów dostępnego kanału,
z regresjami uszkodzonych raportów. Dalsze wyniki odbioru trafiają do dziennika i
wspólnego `docs/roadmap/plan.json`; otwarcie PR nie oznacza zakończonej integracji.

Materiały służą analizie ogólnych funkcji. Nie kopiujemy kodu, ekranów, makr ani
zasobów producentów. NIEZWERYFIKOWANE NA SPRZĘCIE.
