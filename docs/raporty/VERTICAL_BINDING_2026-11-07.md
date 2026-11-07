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

Drugi checkpoint dodaje porównanie niezmiennych plików przed Start/wznowieniem,
limity osi, gotowość napędów i HAL bez bypassu, świeży odczyt i nowe potwierdzenie
numeru polecenia LinuxCNC. Wymaga żywego połączenia WebHMI. Start dopuszcza tylko
pierwszą linię. Wznowienie porównuje ustalony kontekst pauzy (w tym aktualne narzędzie,
korekcje i pozycję), zamiast wymagać początkowego T0. Zapis manifestu i próbek zaczyna
się przed AUTO_RUN; osobne wyniki obejmują zakończenie obserwowane, Stop, E-STOP,
awarię, timeout i utratę klienta potwierdzoną następnym E-STOP.

110 testów Pythona i41JS PASS dla tej porcji. Start/wznowienie są warunkowe;
rzeczywisty dodatni przebieg i kliknięty odbiór pozostają wymagane przed scaleniem.
Próbki NML/tooldata/HAL nie są atomowe i nie zastępują rejestracji każdego cyklu serwa.
Pełna telemetria i raport poziomu4 pozostają otwarte. Nie zmieniono zasad E-STOP/STO/
watchdog. NIEZWERYFIKOWANE NA SPRZĘCIE.

Rzeczywisty checkpoint181f3af: test prywatnego LinuxCNC/Plant/HAL PASS. INI, jednostki,
RAM narzędzi, T0 i G5x zgodne; program niewczytany i E-STOP poprawnie dają niespełnione
warunki, Start409. Test zakończenia nie pozostawił procesów. Lokalny kod RIP potwierdza,
że stat.tool_table czyta tooldata po poll NML, więc nie jest to atomowa migawka całej
maszyny ani ślad RT. Tak samo trzeba opisywać późniejszą telemetrię.

Checkpoint d4be475 przeszedł rozszerzony test rzeczywistego rozruchu (1PASS):
limity zgodne, HAL poprawnie niespełnione w E-STOP. Próba dodatnia wykryła problem
ponownego użycia portu po zamknięciu HTTP (TIME_WAIT); kontrola portu z SO_REUSEADDR
nadal odrzuca aktywny listener. Zamykanie bramy kończy aktywny dziennik jako unavailable
i wysyła abort.48 testów związanej porcji PASS; dodatni Start nadal do odbioru.

Rzeczywisty b3b9692: Start i pauza programu z odebranego ZIP zadziałały. Wznowienie
zostało bezpiecznie odrzucone, bo stat.file zachował nazwę remapu M6 po jego powrocie.
Korekta dopuszcza przy wznowieniu wyłącznie zapamiętany plik G-code należący do
niezmiennych zasobów tej instancji; Start nadal wymaga głównego program.ngc.
Nieznany plik pozostaje odrzucony. Testy obejmują oba zaakceptowane konteksty i obcy plik.

Kolejna rzeczywista pauza wykazała, że LinuxCNC utrzymuje inpos=false przy pozostającej
kolejce ruchu mimo zerowej prędkości i ustalonego położenia. Wznowienie wymaga teraz
trzech kolejnych zgodnych kontekstów zadanych, zerowej prędkości i błędu każdej osi
ściśle poniżej0,001mm, zarówno actual-commanded, jak i following_error. Start i odbiór
zakończenia nadal wymagają inpos. Kontekst pauzy zapisuje się jako osobne zdarzenie.

Rzeczywisty4a29313: Start/pauza/wznowienie PASS; Stop zatrzymał ruch, ale stary
ogólny jog_stop generował błędy EMC_JOG_STOP podczas AUTO i dziennik poprawnie wskazał
fault. Backend pomija niedozwolony JOG_STOP w aktywnym AUTO; Stop nadal wysyła abort.
90 testów backendu/bramy/bramki PASS. Sterownik testowy zakończono po obserwacji fault;
nie jest to dodatni dowód Stop ani ukończenia programu.
