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

Checkpoint bcd10d5 na rzeczywistym LinuxCNC/Plant/WebHMI/HAL, bez bypassu:
Stop→aborted8,144927s/381próbek; pełne wykonanie→completed_observed112,531625s/
5288próbek; utrata żywego klienta→client_lost8,204209s/384próbki. Każdy przebieg
zawierał Start/pauzę/wznowienie; źródłem był ten sam faktycznie zweryfikowany ZIP227.
Własne procesy zakończone, moduły HAL przywrócone. Surowe manifesty/JSONL/wyniki w
vertical/run-*-20261107.tar.gz; hashe, ID, kontrole gotowości i ograniczenia w
vertical/runs-20261107.json. To próbki NML, nie dowód maksimum każdego cyklu serwa.

Oddzielny E-STOP ujawnił krótkie ESTOP_RESET przed potwierdzeniem HAL; pierwszy wynik
fault zachowano w lokalnym śladzie, bez deklarowania zaliczenia E-STOP. Poprawka
przerywa ruch po utracie ON i czeka do1s na potwierdzenie przyczyny; brak potwierdzenia
lub powrót ON kończy się fault, bez wznowienia.26 testów dziennika/bramki PASS.
Dodano trzy rzeczywiste testy regresji w test_job_run_linuxcnc.py; wymagają uruchomienia.

Pierwsza seria nowych regresji zakończyła się4FAIL: pierwszy przebieg miał poprawny
wynik, ale sterownik testowy czekał5s przy domyślnym10s close_timeout WebSocket;
wyjątek zamknięcia pomijał host.terminate i zaburzał następne próby. Zawężono timeout
testowego klienta do1s i zagwarantowano zamknięcie hosta również po błędzie klienta.
Rozruch czeka na stan własnej instancji zamiast pierwszej dostępnej odpowiedzi NML.
Nie jest to zielona regresja; ponowny przebieg wymagany.

Końcowy runtime293af3e: rzeczywiste4 regresje RIP PASS,58,34s (rozruch oraz
Start/pauza/wznowienie→Stop/E-STOP/utrata klienta). Izolacja i własne procesy sprawdzone.
Kliknięte WebHMI8796: RUN, PAUSE, RESUME, potem completed_observed148,279929s/
6895próbek/linia105. Czas obejmuje pauzę operatora. Przeglądarka była jedynym żywym
klientem HMI; testowe ustawienie maszyny wykonano jawnie przez REST przed RUN.
Źródło to ten sam faktycznie verified ZIP227. Zrzut run-paused-20261107.png,
surowy stan gui-terminal-20261107.json i archiwum run-gui-completed-20261107.tar.gz
wiążą wynik z ID zadania i przebiegu. Host zamknięty, własne procesy nie pozostały.

Porcja gotowości/sterowania i obserwacyjnego dziennika ma odbiór operatora.
Pełna regresja/końcowe CI i scalenie229 wymagane. Raport porównawczy poziomu4,
obsługa ponownego odczytu oraz ocena luk telemetrii pozostają do wykonania;
nie deklarujemy kwalifikacji sprzętu ani rejestracji wszystkich cykli serwa.

Analiza końcowych surowych próbek ujawniła, że inpos/RCS_DONE nie oznacza jeszcze
ustalonego sprzężenia zwrotnego: stare completed_observed kończyły zapis przy błędzie
Z0,030182mm (automat) i0,033386mm (GUI), a Stop przy X0,013973mm. To prawidłowe dowody
zakończenia interpretera/przerwania, ale NIE dodatni odbiór końcowego pozycjonowania.
Nowy stan settling zbiera dalej próbki do trzech zgodnych odczytów ze stabilną pozycją
zadaną i błędem actual-commanded oraz following_error każdej osi <0,001mm. Brak
ustalenia przez5s po opróżnieniu kolejki daje settle_timeout i abort.28 testów dziennika/
bramki PASS; odbiór rzeczywisty i GUI poprawki wymagane. Wcześniejsze archiwa zachowane.

## Końcowy odbiór ustalenia osi — runtime90e8100

4 rzeczywiste regresje RIP PASS59,77s. Faktyczny verified ZIP227: Stop→aborted9,017242s,
największy błąd w trzech końcowych odczytach X0,000607649mm. Kliknięte GUI8796
RUN/PAUSE/RESUME→completed_observed126,645824s/5898próbek/linia105; największy błąd
w trzech końcowych odczytach Z0,000655949mm. Wszystkie osie w obu przebiegach <0,001mm.
Są to obserwacje końcowego ustalenia w NML, bez kwalifikacji sprzętu i bez twierdzenia
o maksymalnym błędzie każdego cyklu serwa. Pole following_error to różnica zadana−
rzeczywista z modelu AxisSnapshot, nie surowe joint.ferror_current.

Oryginały: run-gui-settled-20261107.tar.gz, run-stop-settled-20261107.tar.gz,
gui-settled-terminal-20261107.json; ID/hashe i błędy w runs-20261107.json.
Zrzut bez retuszu run-settled-20261107.png. Hosty zamknięte, moduły przywrócone,
brak własnych procesów i lease zwolniony. Pełna lokalna regresja7d6238d:2181PASS,
15skip/245deselected,464,40s; REQ22/22. CI dokładnego90e8100: Python/C/wheel i macierz
Plant success (42378074935); końcowy LinuxCNC42378074910 w toku przed scaleniem229.

Końcowy wariant sim bez procesu Plant również PASS: ten sam job95bf2c0 i verification,
executionae0ba5bdfd4aa2c6b76be8b4fd66d6a3a5ed74e6528cfa306eeb4178c222dd3f;
Start/pauza/wznowienie/Stop→aborted8,155675s. Końcowe trzy odczyty wszystkich osi
spełniają <0,001mm; raw w run-sim-stop-settled-20261107.tar.gz. Host zakończony,
moduły przywrócone, lease zwolniony. Kod runtime identyczny z90e8100.

CI LinuxCNC42378074910 próba1:244PASS/1FAIL, jedynie stary D38 sim
test_retract_returns_to_compensated_path. Sterownik, rdzeń i panel D38 mają identyczne
bloby na maincd8ed66 i90e8100; wariant Plant oraz wszystkie4 nowe testy zadania PASS.
Odmowa dotyczyła request1,001001192mm przy nominalnym1,001mm i progu1e-6mm.
Ten sam D38 sim lokalnie PASS67,06s bez zmiany kodu/progów. Ponowiono wyłącznie
nieudany job (próba2,128518681208); wynik oczekiwany przed scaleniem. Beta API w próbie1
było pominięte wskutek tego błędu, więc nie zaliczamy go z pierwszej próby.
Lokalny pełny7eb41ab:2182PASS/1FAIL wyłącznie ścieżka provenance nowego zrzutu;
poprawkaf02698d:10IP PASS i REQ22/22. CI dokumentacjif02698d42380002073 success.
