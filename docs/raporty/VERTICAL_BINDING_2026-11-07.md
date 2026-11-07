# Powiązanie zadania z obserwacją LinuxCNC

Model-Author: Codex · 2026-11-07. VERTICAL-RUN, sesje028/029/049/053/061.

Baza pełnego projektu: maincd8ed66 po scaleniach #227 (63254c9, formalny verified,
konfiguracja zamrożona) i #228 (cd8ed66, prywatny rozruch). Wymagane końcowe Python CI
i LinuxCNC obu dokładnych headów success. Końcowy211160e:2134 lokalne testy PASS,
wheel/REQ22/22, rzeczywisty rozruch i kliknięte GUI PASS. Poziom2 odebrany offline
w opisanym zakresie diagnostycznym; nie jest zgodą na ruch.

Pierwszy checkpoint wiązania porównuje obserwację z tego samego poll NML co migawka:
INI instancji, ścieżkę programu, tabelę narzędzi w RAM (wszystkie przesunięcia, średnicę,
kąty/orientację), jednostki maszyny, ON/AUTO/IDLE/bazowanie/bezruch, początek nosa,
T0/zerową korekcję, G5x, G92 i obrót XY. Nie wysyła poleceń ani nie opróżnia ponownie
kanału błędów. Brak danych ma wynik unavailable. WebHMI pokazuje poszczególne wyniki.
Obliczenia zachowują1e-6mm; pozycja rzeczywista musi być ściśle poniżej0,001mm błędu,
bez zaokrąglania do prezentowanych4 miejsc.62 testy zakresu PASS; syntax JS PASS.

To jeszcze checkpoint, nie pełna bramka Start. Pozostałe wymagane elementy:
ponowna integralność statycznych plików/programu, gotowość HAL/napędów, świeża kontrola
przy poleceniu Start, odrębne warunki wznowienia, zapis przebiegu i rzeczywisty odbiór
Start/pauza/wznowienie/Stop/awarie oraz telemetria i raport. Aktualnie Start/wznowienie
pozostają zamknięte. Testy rzeczywistego NML i kliknięty odbiór tej porcji wymagane.
Nie zmieniono zasad E-STOP/STO/watchdog. NIEZWERYFIKOWANE NA SPRZĘCIE.
