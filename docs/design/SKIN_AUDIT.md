# SKIN-00 — audyt i kolejność wdrożenia

Model-Author: Codex · 2026-10-23. Gałąź robocza, bez scalania na polecenie właściciela.
Źródło: `SKIN_SYSTEM_ROADMAP.md` z gałęzi design, commit 32e8691.

## Granice obecnej prezentacji

- `screens/linumert/linumert_handler.py`: integracja QtVCP, ACTION/STATUS i piny HAL.
  Pozostaje właścicielem komend oraz heartbeat; pakiet skórki nie tworzy pinów.
- `linumert_shell.py`: QObject, montaż QStackedWidget, nawigacja, odświeżanie statusu.
  Obecny układ nie jest implementacją Classic Digital.
- `linumert_shell_model.py`: stan powłoki, tokeny i QSS. Zachować zgodność istniejących
  widoków; nowy kontrakt prezentacji powstaje w osobnym module bez importu QtVCP.
- `linumert_*_page.py`: istniejące funkcje operatora. Nie przenosić widgetów HAL
  do kilku instancji nowych widoków i nie wiązać nawigacji z komendami maszyny.
- `linumert_workpiece_view.py`: QPainter, sortowanie trójkątów średnią głębokością,
  cieniowanie przez bezwzględną składową normalnej. Ta metoda nie rozwiązuje ogólnie
  wzajemnego zasłaniania przecinających się trójkątów; zgłoszenie GPU pozostaje
  do reprodukcji. `simulation/linumert_sim/stl.py` oblicza normalne eksportu osobno.

## Kolejność od łatwych do trudnych

1. Walidowany, niezależny od Qt kontrakt preferencji: skórka, motyw i język osobno.
   Rejestr rodzin oznacza koncepcje, nie cztery gotowe aplikacje.
2. Semantyczne palety i katalog tłumaczeń; kompletność i kontrast przed integracją.
3. Manifesty, model tylko do odczytu, kontrola świeżości statusu przed przełączeniem.
   Brak telemetrii lub zatrzymania potwierdzonego przez sterownik oznacza odmowę.
4. Niezależna scena testowa renderera: głębokość, winding, normalne, degeneracje,
   kilka kamer. Zrzuty i próba GPU/Mesa na Debianie i EndeavourOS przed wyborem.
5. Osobny launcher prototypu Qt/PyQt5, pierwsza kompozycja Classic Digital,
   następnie Industrial Pro, Cyberdeck i Organic Vector; bez automatycznego
   przełączenia aktualnego ekranu operatora.
6. Odbiór pełnej macierzy 4 × 4 × 2, obu rozdzielczości i wejścia dotykowego.

## Decyzje i odbiór

Zachowujemy zamrożony stos QtVCP/PyQt5 i limit 30 FPS. Zastąpienie kompozycji
oraz rozszerzenie tokenów pozostają propozycją architektoniczną do przeglądu;
prototyp nie zmienia kontraktu produkcyjnego. SKIN-01 jest bramką przed wdrożeniem
nowego renderera, nawet jeśli prostsze kontrakty SKIN-02/03 powstaną wcześniej.
STOP, Hold, alarmy i stan E-STOP muszą pozostać dostępne przy każdym układzie.
Nie ma jeszcze odbioru nowych skórek ani renderera na docelowym komputerze.

## Kontrakt manifestu i przełączenia — prototyp, 2026-10-23

`screens/linumert/linumert_skin_runtime.py` przyjmuje manifest JSON z dokładnie
polami `skin`, `version` (major.minor.patch), `api` (1), `views`, `global_controls`
oraz `resolutions`. Wymagane widoki: dro, gcode, tools, toolpath, machine,
workpiece, alarms, cycle, manual, diagnostics. Stałe kontrolki: alarms,
estop_status, stop, feed_hold, mode. Deklaracja obejmuje 1280×800 i 1920×1080.
Manifest opisuje zdolności pakietu; sam wpis nie potwierdza wdrożenia widoku.
Nie ma jeszcze ładowania kodu wtyczek ani uruchamiania deklarowanych komponentów.

Model `SwitchSnapshot` jest niezmienny i nie ma dostępu do ACTION/HAL.
Adapter musi jawnie potwierdzić połączenie, zatrzymanie osi **i wrzeciona**,
bezczynność interpretera, pustą kolejkę oraz brak bazowania i oczekującej komendy.
Pauza programu nie jest bezczynnością. Znaczniki czasu korzystają z tego samego
lokalnego zegara monotonicznego; próbka starsza niż 0,5 s lub z przyszłości
powoduje odmowę, tak samo jak brak danych i niepoprawne typy.

Reguła `switch_gate` zwraca wynik i stabilny kod przyczyny, bez zatrzymywania,
resetowania czy zmiany trybu maszyny. Nie jest jeszcze podłączona do powłoki.
Przyszły host musi ponowić odczyt tuż przed wymianą widoku, obsłużyć awarię
montażu i zachować globalne kontrolki przez całą operację. Sama zgoda z modelu
nie eliminuje zmiany statusu między odczytem a montażem.

## Pierwszy podgląd kompozycji Qt — historyczny stan przed PR #89

Uruchom z katalogu repozytorium w środowisku z PyQt5:

```sh
python3 tools/dev/skin-preview.py
```

Okno jest studium układu offline: cztery różne kompozycje, cztery palety i EN/PL.
Przełączanie zmienia tylko lokalną prezentację; nie korzysta z adaptera statusu,
LinuxCNC ani HAL. STOP/Hold są nieaktywne, a stan maszyny jest niedostępny.
Wartości DRO/narzędzia to kreski; G-code jest podpisanym przykładem, nie programem
wczytanym do sterowania. Panele 3D jawnie informują o braku renderera.
To początek prac nad kompozycjami, bez docelowych kontrolek/animacji rodzin skórek.

Test Qt sprawdza 64 warianty (4 × 4 × 2 przy dwóch rozdzielczościach), brak
nakładania komórek, widoczność paneli i cele kontrolek co najmniej 44 px.
Lokalny podgląd sprawdzono w Qt offscreen na Windows, nie na docelowym GPU/Mesa.
W tym trybie Windows nie wylicza fontów: do zrzutów/testu zarejestrowano font
systemowy bez kopiowania go do repo. Normalny launcher korzysta z fontów platformy.


## Podgląd według obrazów właściciela — PR #89, 2026-10-23

Model-Author: Codex. Wzorce: `referencje-skin/README.md` i cztery WEBP otrzymane
z https://megawrzuta.pl/hdimgnec. Nie wykorzystujemy bitmap jako fasady aplikacji:
obudowy, wskaźniki i układ są rysowane kodem Qt. Rodziny różnią się położeniem
paneli, metalowymi/ściętymi/obłymi ramkami oraz geometrią wskaźników.

`python3 tools/dev/skin-preview.py` uruchamia trzy niezależne, interaktywne
widoki OpenGL: maszyna bramowa, detal z kieszenią i czterema otworami, kontury
ścieżki. To modele poglądowe offline w mm, nie telemetria ani wynik wykonania CNC.
DRO i wskaźniki pokazują brak danych; Start/Hold/Stop są jawnie nieaktywne.
Opcja `--layout-only` pozwala oglądać układy bez pyqtgraph/PyOpenGL.
Przyciski ↗/↙ powiększają i przywracają każdy panel 3D, zachowując status,
selektory i kontrolki cyklu. Zmiana skórki usuwa także ukryte poprzednie karty.

Launcher współdzieli konteksty OpenGL między widgetami Qt. Bez
`AA_ShareOpenGLContexts` wielokrotna wymiana kart dawała puste panele w złożonym
obrazie okna, mimo prawidłowego indywidualnego `grabFramebuffer`.
`tools/dev/skin-check.py --output build/skin-preview` sprawdza 64 warianty,
24-bitowy depth, niepuste obrazy GL, rozmiary 1280×800 / 1920×1080, powiększenie
oraz złożone zrzuty czterech skórek w obu rozmiarach. Ten odbiór jest także w CI
Debian/Mesa; zwykłe testy Qt offscreen pozostają niezależne od OpenGL.

To ukończony krok podglądu, **nie ukończone SKIN-02…06 ani wierna realizacja
całych makiet**. Otwarte: szczegółowe kontrolki/ikony/typografia, modele maszyny
zamiast schematu, pełne strony oraz bezpieczny adapter stanu/poleceń QtVCP.
Aktualny ekran operatora pozostaje osobną aplikacją. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Osobne ekrany i kształty kontrolek — PR #91, 2026-10-23

Model-Author: Codex. Właściciel zlecił osobne ekrany z układami i przyciskami
maksymalnie odpowiadającymi pierwotnym obrazom. Cztery niezależne klasy w modułach
linumert_skin_classic/industrial/cyberdeck/organic.py mają własne układy i konsole.
Wspólna baza dostarcza komponenty, nie jeden układ przemalowywany przez QSS.

Classic: pięć odczytów, duża ścieżka, metalowe prostokątne klawisze i przełączniki.
Industrial: duża maszyna po lewej, środkowe DRO, prawa ścieżka/program, obrotowy
selektor i osobna konsola. Cyberdeck: ścięte obrysy, moduły asymetryczne,
podświetlane przyciski i dolny pokład JOG/wskaźników. Organic: asymetryczne krzywe
obudów, okrągłe klawisze, obłe wyspy, status na dole. Typografia należy do rodziny.

`--skin <id>` uruchamia osobny ekran bez stałego paska selektorów. Ustawienia
zmieniają lokalną prezentację po Zastosuj; Anuluj zachowuje ekran. Nagłówki mają
działającą lokalną nawigację i diagnostykę renderera. Kontrolki CNC są nieaktywne,
grzyby E-STOP są nieinteraktywne i pokazują stan nieznany; bez ACTION/STATUS/HAL.
Nie jest to jeszcze produkcyjny host CNC ani odbiór wszystkich szczegółów wizji.

Testy sprawdzają cztery różne klasy/moduły, nawigację, brak emisji kliknięć
nieaktywnych kontrolek, anulowanie/atomowe ustawienia oraz usuwanie starych paneli.
Odbiór GL rozszerzony do 128 wariantów browser/standalone; wykrył przekroczenie
800 px o 15 px w Industrial, usunięte bez zmniejszania celów 44 px.
Aktualne obrazy: `docs/raporty/hmi_sym/README.md`, kod ekranów ea2fc39.
