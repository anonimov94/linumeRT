# Wytyczne dotyczące własności intelektualnej (wersja użytkownika 1.0, 17.10.2026)

Źródło: zastrzezeniaprawneopcje.txt od właściciela projektu. Tekst bez zmian poniżej.

```text
LICENCJA.TXT
Wytyczne dotyczące własności intelektualnej i projektowania interfejsu HMI sterowania CNC
Wersja: 1.0
Data: 17.10.2026

WAŻNE — CHARAKTER DOKUMENTU
Niniejszy dokument jest wewnętrzną listą kontrolną projektową, a nie opinią prawną, licencją udzielaną przez producenta sterowania ani gwarancją braku roszczeń. Nie zastępuje analizy prawnika/rzecznika patentowego dla konkretnego produktu, rynków sprzedaży i wersji interfejsu. Ocena zależy od rzeczywistych ekranów, kodu, materiałów źródłowych, oznaczeń, sposobu promocji oraz praw obowiązujących na danym rynku.

1. CEL I ZASADA OGÓLNA
Projektować niezależny interfejs CNC, który realizuje potrzebne funkcje przemysłowe, ale nie kopiuje chronionej formy wyrażenia, oznaczeń ani materiałów konkretnego producenta.
Podobieństwo wynikające z funkcji technicznej, bezpieczeństwa, ergonomii lub konwencji branżowej może być uzasadnione. Nie należy jednak zakładać, że każdy element interfejsu jest wolny od ochrony tylko dlatego, że występuje w innych sterowaniach.

2. CO ZASADNICZO MOŻNA ROZWAŻAĆ
- Własną implementację powszechnych funkcji CNC i ich logiki, o ile nie narusza ona patentu, tajemnicy przedsiębiorstwa, umowy ani innych praw.
- Używanie krótkich, opisowych i technicznych nazw funkcji, np. AUTO, JOG, EDIT, HOME, TOOL, OFFSET, ALARM, PROGRAM, jeśli w konkretnym kontekście nie narusza to cudzych praw do oznaczeń.
- Zastosowanie trybów pracy i koncepcji obsługi wymaganych przez proces technologiczny, normy, bezpieczeństwo lub przyjęte praktyki branżowe.
- Stworzenie własnych ikon, grafik, kolorystyki, typografii, kompozycji ekranów, komunikatów, dokumentacji i materiałów marketingowych.
- Niezależne napisanie kodu na podstawie wymagań funkcjonalnych, bez kopiowania kodu, zasobów ani materiałów chronionych.

Uwaga: „MDI” i „MDA” bywają używane w branży w różnych znaczeniach. Przed publikacją oznaczeń należy sprawdzić konkretne rejestry znaków towarowych dla odpowiednich klas, terytoriów i sposobu użycia. Nie należy zakładać automatycznie, że każdy skrót jest zawsze wolny w każdej jurysdykcji.

3. CZEGO NIE ROBIĆ — OBSZARY PODWYŻSZONEGO RYZYKA
A. Nie odtwarzać ekranów 1:1
- Nie kopiować zrzutów ekranu, ikon, grafik, ilustracji, animacji, układu paneli ani szczególnej kompozycji ekranu z Mazatrol, SINUMERIK, HEIDENHAIN, Hurco WinMax, FANUC, Mitsubishi, Fagor lub innego systemu.
- Nie traktować zmiany samego koloru, fontu lub kilku pikseli jako wystarczającej, jeśli całość nadal sprawia wrażenie kopii.
- Nie używać ekranów producenta jako gotowych zasobów produktu, instrukcji, materiałów handlowych ani demonstracyjnych bez odpowiedniej zgody/licencji.

B. Nie kopiować zasobów ani kodu
- Nie kopiować kodu źródłowego/obiektowego, plików konfiguracyjnych, bibliotek, czcionek, ikon, bitmap, dźwięków, tekstów pomocy ani dokumentacji producenta bez podstawy prawnej.
- Nie dekompilować, obchodzić zabezpieczeń ani analizować oprogramowania w sposób naruszający licencję, prawo lub umowę. Przed interoperacyjnością, testami lub inżynierią wsteczną sprawdzić zakres dozwolonych wyjątków i warunki licencji z prawnikiem.
- Nie używać nieautoryzowanych kopii podręczników, zdjęć ekranów, filmów szkoleniowych ani plików pobranych z niepewnych źródeł.

C. Nie sugerować powiązania z producentem
- Nie używać nazw, logo ani oznaczeń producentów w nazwie własnego sterowania, logo, ekranie startowym, obudowie, materiałach reklamowych lub domenie w sposób mogący sugerować pochodzenie, autoryzację, certyfikację albo współpracę.
- Nie nazywać produktu np. „Mazatrol Pro”, „SINUMERIK-like”, „Heidenhain Edition” ani podobnie bez uprzedniej analizy prawnej i, jeśli potrzeba, pisemnej zgody.
- Nie umieszczać logo producenta jako dekoracji lub elementu interfejsu.
- W razie potrzeby wskazania kompatybilności używać wyłącznie rzeczowego, proporcjonalnego opisu, np. „obsługuje import plików w formacie X”, po sprawdzeniu prawdziwości twierdzenia i ryzyka znakowego. Nie sugerować oficjalnej kompatybilności, jeśli nie została potwierdzona.

D. Nie kopiować „całego wrażenia” konkretnego sterowania
- Nie odtwarzać jednocześnie charakterystycznej kolorystyki, rozmieszczenia klawiszy ekranowych, ikon, hierarchii menu, nazewnictwa, komunikatów i ekranów diagnostycznych jednego producenta.
- Nie tworzyć materiałów, które mogą sprawiać wrażenie, że produkt jest zamiennikiem, wersją lub oficjalnym następcą produktu konkurenta, jeśli nie jest to prawdą.
- Nie używać w reklamie porównań typu „identyczny jak [marka]” bez analizy prawnej.

4. JAK OGRANICZAĆ RYZYKO W PRAKTYCE
1) Sporządzić własną specyfikację funkcjonalną: opisać, co operator ma wykonać i jakie informacje są potrzebne, bez kopiowania zrzutów ekranów konkurencji jako wzorca wykonawczego.
2) Oddzielić wymagania funkcjonalne od warstwy wizualnej. Dopuszczalne wymagania mogą opisywać tryby, sekwencje i dane, ale wygląd należy zaprojektować niezależnie.
3) Stworzyć własny system projektowy: paletę, fonty, siatkę, odstępy, kształty przycisków, ikony, styl komunikatów, animacje i hierarchię ekranów.
4) Prowadzić rejestr pochodzenia: autor, data, pliki źródłowe, licencje fontów/bibliotek/ikon, zgody i materiały wejściowe.
5) Zachować historię projektowania: wymagania, szkice, makiety, commity, decyzje projektowe i uzasadnienia funkcjonalne. Może to pomóc wykazać niezależny proces twórczy.
6) Korzystać z legalnie licencjonowanych bibliotek i zasobów; archiwizować tekst licencji oraz wersję zależności.
7) Sprawdzić nazwy produktu, logo, domenę i kluczowe oznaczenia w bazach znaków towarowych przed premierą. Analizę prowadzić dla krajów sprzedaży oraz właściwych klas towarów/usług.
8) Wykonać przegląd podobieństwa ekranów przez osobę nieuczestniczącą w projektowaniu. Porównać nie tylko pojedyncze przyciski, ale też ogólną kompozycję i wrażenie całości.
9) Przed komercjalizacją przeprowadzić przegląd prawny: prawa autorskie, znaki towarowe, wzory przemysłowe, patenty, tajemnice przedsiębiorstwa, umowy i licencje open source.
10) Jeżeli interfejs ma być celowo zbliżony do konkretnego sterowania, uzyskać pisemną zgodę/licencję albo przeprojektować go przed wydaniem.

5. WZORY PRZEMYSŁOWE, PATENTY I NIEUCZCIWA KONKURENCJA
Nie ograniczać analizy do praw autorskich. W zależności od faktów ochroną mogą być objęte zarejestrowane lub niezarejestrowane wzory przemysłowe, znaki towarowe, rozwiązania techniczne chronione patentem, tajemnice przedsiębiorstwa oraz elementy oceniane na gruncie przepisów o zwalczaniu nieuczciwej konkurencji.
Sama zmiana grafiki nie rozwiązuje problemu, jeżeli implementacja wykorzystuje cudze rozwiązanie techniczne objęte patentem, poufne informacje lub narusza umowę. Z drugiej strony samo podobieństwo funkcjonalne nie przesądza automatycznie o naruszeniu. Wymagana jest ocena konkretnych elementów i terytorium.

6. ZASADY DOTYCZĄCE NAZW FUNKCJI
- Preferować nazwy opisowe, krótkie i powszechne w technice, gdy rzeczywiście opisują funkcję.
- Nie wykorzystywać nazwy konkurencyjnego systemu jako nazwy funkcji, wariantu produktu lub oznaczenia kompatybilności.
- Dla nazw, które mają być kluczowym elementem marki lub wyróżnikiem produktu, wykonać wyszukiwanie znaków towarowych i ocenę prawną.
- Nie zakładać, że nazwa jest wolna tylko dlatego, że pojawia się w wielu interfejsach.
- W dokumentacji używać nazw producentów jedynie w koniecznym, rzeczowym kontekście porównawczym, bez sugerowania poparcia lub powiązania.

7. PROCEDURA PRZY WĄTPLIWOŚCI
Jeżeli zespół chce wykorzystać element zaczerpnięty z ekranu, instrukcji, filmu lub urządzenia konkurenta:
- wstrzymać wdrożenie danego elementu;
- zapisać źródło i dokładny zakres planowanego użycia;
- ustalić, czy element jest czysto funkcjonalny, czy zawiera charakterystyczną formę graficzną/tekstową;
- sprawdzić licencję, rejestry praw i warunki umowne;
- skonsultować element z prawnikiem specjalizującym się w IP/IT lub rzecznikiem patentowym;
- do czasu wyjaśnienia stworzyć niezależną alternatywę.

8. ŹRÓDŁA PRAWNE — PUNKT WYJŚCIA, NIE KOMPLETNA OPINIA
- TSUE, sprawa C-393/09, Bezpečnostní softwarová asociace, wyrok z 22.12.2010: interfejs graficzny nie jest sam w sobie formą wyrażenia programu chronioną jako program komputerowy na podstawie przepisów o programach; może jednak podlegać zwykłej ochronie prawnoautorskiej, jeśli stanowi własną twórczość intelektualną autora. W ocenie znaczenie ma m.in. konkretna konfiguracja elementów, przy czym elementy zdeterminowane wyłącznie funkcją techniczną nie spełniają kryterium oryginalności.
  https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62009CJ0393
- TSUE, sprawa C-406/10, SAS Institute, wyrok z 02.05.2012: idee i zasady leżące u podstaw elementów programu, w tym jego interfejsów, nie są jako takie chronione prawem autorskim dotyczącym programów; ochrona może dotyczyć konkretnej formy wyrażenia. Należy analizować pełne uzasadnienie i fakty konkretnego przypadku.
  https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:62010CJ0406
- Polska ustawa z 4 lutego 1994 r. o prawie autorskim i prawach pokrewnych — tekst i aktualne brzmienie należy sprawdzić w oficjalnym systemie aktów prawnych.
  https://isap.sejm.gov.pl/
- Urząd Patentowy RP — informacje i bazy dotyczące znaków towarowych, wzorów przemysłowych i patentów.
  https://uprp.gov.pl/
- EUIPO — bazy znaków towarowych i wzorów UE.
  https://www.euipo.europa.eu/
- WIPO Global Brand Database — pomocnicza wyszukiwarka oznaczeń międzynarodowych.
  https://branddb.wipo.int/

9. LISTA KONTROLNA PRZED WYDANIEM
[ ] Nie skopiowano kodu, grafik, ikon, tekstów, zrzutów ekranu ani dokumentacji bez licencji.
[ ] Nazwa produktu i logo zostały sprawdzone pod kątem kolizji z cudzymi znakami.
[ ] Wygląd i kompozycja ekranów powstały niezależnie.
[ ] Podobieństwa wynikające z funkcji technicznej są udokumentowane i ograniczone do niezbędnego zakresu.
[ ] Sprawdzono licencje bibliotek, fontów i pozostałych zasobów.
[ ] Sprawdzono, czy funkcje techniczne nie wchodzą w zakres cudzych patentów lub zobowiązań umownych.
[ ] Przeprowadzono przegląd prawny dla rynków docelowych.
[ ] Materiały marketingowe nie sugerują nieistniejącego powiązania z innym producentem.

10. ZASTRZEŻENIE KOŃCOWE
Ten dokument opisuje politykę ostrożności projektowej. Nie daje licencji na cudze prawa, nie przesądza, że określone nazwy są wolne, i nie gwarantuje, że produkt nie narusza praw osób trzecich. Przed sprzedażą sterowania, eksportem lub użyciem interfejsu wzorowanego na konkretnym systemie należy zlecić analizę prawną na podstawie rzeczywistych ekranów, nazw, kodu, dokumentacji i rynków docelowych.

```
