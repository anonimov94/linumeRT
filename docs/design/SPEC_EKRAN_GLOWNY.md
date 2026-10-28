# Ekran główny linumeRT — specyfikacja funkcjonalna sesji 028

Model-Author: Codex · 2026-10-25. Wymagania docelowe, nie deklaracja odbioru.
Źródła: [prompt 028](../../prompts/sesja-028.md), [przebieg pracy](HMI_WORKFLOW.md),
[kontrakt istniejących widgetów](HMI_BASELINE.md), [tokeny](tokens.yaml).

## Potrzeby operatora i hierarchia

Operator musi rozpoznać stan maszyny przed zleceniem działania. Stała warstwa
obejmuje E-STOP, zezwolenie maszyny, tryb, bazowanie, połączenie, aktywny program,
układ detalu, narzędzie oraz komunikat. Otwieranie widoku nie zmienia tych stanów.
Priorytet prezentacji: odebrane zezwolenie i alarm → wykonywany ruch/program →
świadoma akcja operatora → informacje pomocnicze. Brak świeżych danych musi być
widoczny; stare wskazania nie mogą udawać potwierdzonego połączenia.

| Obszar | Dane i czynności | Zasada |
|---|---|---|
| Pasek górny | znak linumeRT, JOG/MDI/AUTO, nazwa programu, połączenie, rola, zegar | stan niezależny od wybranej podstrony |
| Komunikat | bieżący alarm, odmowa lub potwierdzenie czynności | czytelna przyczyna odmowy, bez cichego zignorowania |
| Nawigacja | Maszyna, Program, Narzędzia, Symulacja, Diagnostyka, Konfiguracja; kroki pracy z HMI_WORKFLOW | klik zmienia wyłącznie prezentację |
| Pozycja | DRO X/Y/Z, aktywny układ detalu i możliwość rozpoznania układu maszyny | nie mieszać współrzędnych i jednostek |
| Narzędzie | numer, opis, korekcja długości, stan wymiany | zmiana narzędzia osobną świadomą akcją |
| Ruch i wrzeciono | zadany/rzeczywisty posuw i obroty, korekcje, stan wrzeciona | odczyt oddzielony od zadania polecenia |
| Program | bieżące bloki, aktywna linia, podgląd ścieżki i edytor | wybór pliku lub karty nie uruchamia programu |
| Dolny pasek | E-STOP i dostępne akcje Start, Wstrzymaj, Wznów, Stop | zawsze widoczny, dostępność zgodna ze stanem LinuxCNC |

## Kontrakt działań

LinuxCNC pozostaje interpreterem i planerem. Polecenia przechodzą przez istniejące
ACTION/STATUS QtVCP oraz sprawdzenia handlera; router widoków nie wysyła ruchu.
Nie duplikujemy widgetów podłączonych do HAL. Nazwy wymagane przez handler upstream
zostają zachowane, a przeniesienie widgetu ma zachować jego sygnały i cykl życia.
Warstwa linumeRT nie modyfikuje handlera upstream w celu nawigacji.

Bazowanie wymaga świadomej akcji. AUTO wymaga odpowiedniego trybu, programu,
bazowania i spełnionych blokad. Zmiana zakładki, motywu lub rozmiaru okna nie może
wywołać Start, home, MDI, JOG ani Reset. Po ponownym uruchomieniu domyślny widok
Start pokazuje gotowość; nie odtwarza ruchu. Powrót z diagnostyki zachowuje stan
programu zgodny z LinuxCNC, a nie z pamięcią widoku.

Ekran nie jest funkcją bezpieczeństwa. E-STOP/STO sprzętowe pozostają nadrzędne.
HMI może odebrać zezwolenie, nigdy obejść otwartego toru sprzętowego. Stan oraz
akcja E-STOP muszą być widoczne również w edytorze i diagnostyce.
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Układ i obsługa

Układ odnosi się do własnej makiety 01_maszyna i tokens.yaml; nie do ekranów
producentów sterowań. Docelowe minimum to 1280×768. Bez nakładania przycisków,
uciętego DRO lub schowania E-STOP poza oknem. Wielkość celów dotykowych, fontów,
odstępy, kolory i ikony pochodzą z systemu projektowego. Długi komunikat zawija
się lub ma dostępny pełny tekst, nie przesuwa podstawowych akcji poza ekran.

Kolejność Tab ma prowadzić przez dostępne akcje aktualnej strony; ukryte widoki
nie przechwytują skrótów. Wejście tekstowe w MDI/edytorze nie uruchamia JOG.
Sprawdzenie klawiatury, dotyku i rozdzielczości wymaga osobnych dowodów GUI.

## Odbiór 028 i dowody

| Kryterium | Istniejący punkt weryfikacji | Dowód wymagany do odbioru |
|---|---|---|
| Spójna mapa widgetów/akcji | tools/hmi_inventory.py, tests/test_hmi_inventory.py, tests/test_hmi_assembly.py | aktualna inwentaryzacja i wynik testów |
| Stan, tryby, dostępność akcji | tests/test_hmi_shell_model.py, tests/test_hmi_workflow_widgets.py | wynik offline; sam nie potwierdza GUI |
| Start bez wyjątku i działająca nawigacja | tests/test_hmi_shell_gui.py | rzeczywisty wynik LinuxCNC/QtVCP, log i zrzuty z przypiętej bazy |
| Układ 1280×768 i stałe akcje | makieta, HMI_BASELINE, widoki Start/Program/Diagnostyka | zrzuty całego okna i kontrola ucięć na tej rozdzielczości |
| Brak ruchu od samej nawigacji | test GUI i obserwacja stanu przed/po | wykonany scenariusz, bez domniemania z nazwy testu |
| Własna kompozycja i zasoby | tests/test_ip_guard.py, PROVENANCE.md | wynik testu i notatka funkcje wspólne/elementy własne |

Wspólne funkcje techniczne: DRO, tryby, posuw, obroty, alarmy i obsługa programu.
Własne elementy: znaki, tokeny, ikony, nazwy obszarów oraz kompozycja i kolejność
pracy z dokumentacji linumeRT. Jest to notatka pochodzenia projektu; nie zastępuje
oceny rzeczywistych zrzutów. Skórki offline i ich odbiór produkcyjny są oddzielnymi
rozszerzeniami w plan.json. Zaliczenie jednego testu nie zamyka ich automatycznie.

## Scenariusz ręcznego odbioru 1280×768

Model-Author: Codex · 2026-10-28. Procedura do wykonania, bez deklaracji PASS.
Odbiór dotyczy sesji 028; wymaga działającego LinuxCNC sim i pełnych stron
Narzędzia/Cykle, nie ich widoków zastępczych. Przed uruchomieniem zajmij zasób
LinuxCNC zgodnie z WSPOLPRACA_MODELI.md. Używaj wyłącznie konfiguracji sim,
bez podłączonej maszyny. Nie wykonuj tego scenariusza podczas innego testu ruchu.

Zapisz SHA, konfigurację INI, wersje LinuxCNC/Qt, skórkę, język, skalowanie pulpitu
oraz rzeczywisty rozmiar obszaru klienta okna. Obszar klienta ustaw na 1280×768;
rozdzielczość pulpitu z dekoracjami okna nie jest równoważnym pomiarem.
Zachowaj log startu oraz zrzuty całego okna, bez kadrowania problematycznych miejsc.

| Krok | Czynność | Oczekiwany wynik i dowód |
|---|---|---|
| 1 | Uruchom HMI w sim i otwórz Start. | Brak wyjątków handlera i widoków zastępczych; log, zrzut Start. DRO i dolne akcje mieszczą się w oknie. |
| 2 | Otwórz kolejno Program, Narzędzia, Symulacja, Diagnostyka i Konfiguracja. | Zrzut każdej strony: czytelne pola, brak nakładania, ucięcia prawej krawędzi i poziomego przewijania potrzebnego do podstawowych akcji. E-STOP stale dostępny. |
| 3 | Wróć z każdej strony na Start. | Układ wraca do rozmiaru okna; szerokość ukrytej strony nie wymusza przewijania. Zapisz stan trybu, programu i pozycji przed/po nawigacji. Nawigacja nie wydaje poleceń ruchu ani resetu. |
| 4 | Przejdź Tab i Shift+Tab przez dostępne kontrolki każdej strony. | Fokus jest widoczny, kolejność logiczna, ukryte strony nie otrzymują fokusu; wszystkie podstawowe akcje są osiągalne. Nie aktywuj poleceń ruchu. Zapisz kolejność i ewentualną pułapkę fokusu. |
| 5 | Ustaw fokus w polu MDI, następnie w edytorze Programu; użyj strzałek do przesuwania kursora. | Kursor porusza się w tekście, brak JOG i zmiany pozycji osi. Nie wysyłaj MDI ani nie uruchamiaj programu; zapisz obserwację stanu i log. |
| 6 | Pokaż długą nazwę pliku oraz pełny komunikat odmowy dostępny w sim. | Tekst zawija się lub można odczytać jego całość; DRO i dolne akcje pozostają widoczne. Zrzut z użytym tekstem. |
| 7 | Powiększ okno, po czym wróć do 1280×768 na Start i Narzędziach. | Układ ponownie mieści się w oknie; pola i fokus pozostają dostępne. Zrzuty po zmniejszeniu. |

Dla każdej obsługiwanej skórki i języka wykonaj osobny przebieg. Obsługę dotykową
sprawdź osobno na stanowisku z dotykiem; wynik klawiatury jej nie zastępuje.
Przy nieoczekiwanym ruchu przerwij przebieg i zachowaj log; nie powtarzaj czynności
przed diagnozą. Po zakończeniu zamknij własną instancję sim i zwolnij blokadę.

Raport umieść w `docs/raporty/G2/`: metadane środowiska powyżej oraz tabela
`krok | PASS/FAIL/NIEWYKONANY | obserwacja | plik dowodu`. Brak środowiska lub
niedostępna strona oznacza NIEWYKONANY, nie PASS. FAIL zawiera kroki odtworzenia.
Pełny odbiór wymaga dowodów wszystkich kroków; ta procedura sama nie zamyka 028.
