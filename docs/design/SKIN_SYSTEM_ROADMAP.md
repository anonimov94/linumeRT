# linumeRT — roadmap nowego systemu skórek GUI

Status: **nowy cel rozwojowy / wytyczne projektowe**, nie implementacja.
Model-Author: ChatGPT · 2026-10-22. Koncepcja na polecenie właściciela.

## Decyzja kierunkowa właściciela

Nowy interfejs operatora ma być zaprojektowany **od nowa**. Aktualny układ QtDragon/linumeRT nie jest skórką docelową ani skórką „classic”. Nie przenosić automatycznie jego kompozycji do nowego projektu. Zachować logikę sterowania LinuxCNC, HAL, funkcje safety i niezbędne API; zastąpić warstwę prezentacji po weryfikacji nowego rozwiązania. Zmiana zamrożonego stosu z `CLAUDE.md` wymaga osobnej decyzji architektonicznej i aktualizacji kontraktu, **nie jest zatwierdzona tym dokumentem**.

**Skórka = osobna aplikacja/moduł prezentacji z własną kompozycją**, rozmieszczeniem DRO, paneli G-code, maszyną 3D, detalem i symulacją ścieżki, nawigacją, typami kontrolek, animacjami i geometrią okien. Nie jest samą paletą QSS.

**Motyw kolorystyczny = niezależny parametr** aplikowany do każdej skórki. Cztery warianty:
1. Classic Turquoise — grafit/czerń i turkus, wyraziste cyfrowe odczyty.
2. Graphite Gray — grafit/stal, `#404040` i `#606060`, jasne napisy.
3. Reactor Green — ciemna szarość i techniczna zieleń.
4. Ion Blue — ciemna stal i niebieski.

**Język = trzecia niezależna oś**: English (docelowo domyślny) / Polski, komplet tłumaczeń GUI i stanów. Identyczna semantyka alarmów niezależnie od języka i skórek.

## Cztery AUTORSKIE rodziny skórek — referencje koncepcyjne

| Rodzina | Charakter / inspiracja gatunkiem | Rozmieszczenie i nawigacja | Kontrolki |
| --- | --- | --- | --- |
| **Classic Digital** | retro-cyfrowy, stary odtwarzacz multimedialny / wyświetlacze LED, BEZ kopiowania cudzej skóry | duże DRO po lewej, największy środkowy widok ścieżki, alternatywny widok maszyny po prawej, paski G-code i status na dole | prostokątne przyciski, cyfrowe odczyty, gałki override |
| **Industrial Pro** | profesjonalne CNC i przemysłowe pulpity, własny projekt | maszynę 3D i detal można zestawiać obok ścieżki, gęste tabele i statusy, dolny blok akcji | duże fizycznie wyglądające przyciski, przełączniki dźwigniowe i lampki |
| **Cyberdeck** | futurystyczny panel techniczny, sci-fi i terminal | asymetryczny układ modułowy: ścieżka 3D u góry/prawej, maszyna 3D na dole/lewej, G-code i DRO w odrębnych sekcjach | ostrokątne obrysy, podświetlane przełączniki jak w statku kosmicznym, czytelne wskaźniki |
| **Organic Vector** | organiczny sci-fi, płynne i ostrzejsze formy jednocześnie | obłe ramy i wyspy interakcji, duże niezależne okna maszyny i ścieżki, adaptacyjne położenie sekcji | okrągłe wskaźniki, obłe obudowy, selektywnie spiczaste przyciski i akcenty |

Nazwy skór nie nawiązują do produktów konkretnych producentów; inspiracja jest wyłącznie ogólnym gatunkiem estetycznym. Każda rodzina obsługuje wszystkie cztery palety, czyli minimum **16 kombinacji** plus dwa języki.

## Funkcjonalne wymagania Skin Engine

- Wtyczkowe pakiety: manifest (id, wersja, API, komponenty, obsługiwane widoki, rozdzielczości), niezależny kod widoku, assets, konfiguracja rozmieszczenia.
- Stabilny read-only model stanu maszyny oraz osobny, walidowany kanał poleceń przez istniejące API LinuxCNC/QtVCP; UI nie może omijać interlocków.
- Jednolity kontrakt widoków: DRO X/Y/Z/pozostałe osie, G-code, narzędzia, symulacja ścieżki, model maszyny 3D, model detalu i materiału, alarmy, cykl, JOG/MDI/AUTO, diagnostyka.
- Konfigurowalne umieszczenie widoków 3D: machine/toolpath/workpiece, maksymalizacja, układ 1/2/3 paneli, zapis profilu operatora; bez zgubienia alarmów/stanu.
- Per-skórka zmiany układu, typografii, ramek, wyświetlaczy, ikon i kontrolek; per-motyw wyłącznie stylistyka kolorystyczna. Skórka/motyw/język przechowywane osobno.
- Zmiana skórki tylko w bezpiecznym stanie maszyny (bez ruchu i aktywnego programu) po sprawdzeniu statusu; przełączenie nie wysyła komend ruchu.
- Sygnały alarmowe, stan E-STOP, STOP, Feed Hold i tryb pracy zawsze dostępne, z redundancją informacji kolor + tekst/ikona. **Graficzny E-STOP nie zastępuje hardware E-STOP**.
- Wymagane rozdzielczości testowe co najmniej 1280×800, 1920×1080 oraz ekran dotykowy; minimalny cel dotykowy 44 px, duże DRO, kontrast i opcjonalne skalowanie fontów.

## Nowy silnik wizualizacji 3D — warunek wdrożenia

Właściciel zgłosił na EndeavourOS wadliwe wyświetlanie trójkątów, błędną kolejność ścian / odwrócone powierzchnie i prymitywne modele. To jest **zgłoszenie użytkownika do reprodukcji**, nie potwierdzona diagnoza wszystkich backendów.

- Wyizolować współdzielony moduł renderingu niezależny od skórek. Zweryfikować obecne ścieżki `QPainter` (sortowanie trójkątów średnią głębokością), pyqtgraph.opengl i eksport STL.
- Prototyp porównawczy na docelowym GPU/Mesa: bufor głębokości, poprawny winding, normalne, culling, test brył otwartych/zamkniętych, wireframe do debugowania.
- Renderować maszyny, przygotówkę, narzędzie, materiał po obróbce i trajektorię w spójnych jednostkach i przestrzeniach współrzędnych.
- Testy geometrii (normalne, winding, zdegenerowane trójkąty, widoczność), screenshot regresyjny z kilku kątów oraz test interaktywny na EndeavourOS i Debian 12.
- Maksimum 30 FPS zgodnie z obecnym kontraktem do czasu osobnej decyzji. Symulacja / GUI nie blokują RT. Zero udawania precyzyjnej symulacji dla modeli poglądowych.

## Etapy roadmapy (do oszacowania, po istniejących zobowiązaniach)

- **SKIN-00** — audyt kontraktów, wpis PROPOZYCJA w `docs/DECYZJE.md`, rozstrzygnięcie konfliktu z zamrożonym QtDragon i wspólnymi tokenami w `CLAUDE.md`.
- **SKIN-01** — niezależny prototyp renderera 3D; reprodukcja i regresje artefaktów z EndeavourOS.
- **SKIN-02** — interfejs Skin API, launcher, manifesty, model stanu i komend, przełączanie przy zatrzymanej maszynie.
- **SKIN-03** — 4 palety, system tłumaczeń English/Polski, preferencje operatorów.
- **SKIN-04** — pierwsze dwie kompletne skórki: Classic Digital i Industrial Pro.
- **SKIN-05** — Cyberdeck i Organic Vector, układy adaptacyjne 3D.
- **SKIN-06** — odbiór HMI na 16 kombinacjach, 2 językach, różnych rozdzielczościach i LinuxCNC/Plant, testy safety i stabilności, dokumentacja.

## Kryterium akceptacji

Cztery faktycznie odrębne aplikacje GUI, po cztery palety, dwujęzyczne, z możliwością niezależnego rozmieszczania wizualizacji ścieżki, maszyny i detalu. Poprawny rendering trójkątów zweryfikowany na sprzęcie testowym. Bez regresji sterowania i bez przyznawania GUI roli certyfikowanej funkcji bezpieczeństwa. **NIEZWERYFIKOWANE NA SPRZĘCIE.**

## Makiety poglądowe

W rozmowie z właścicielem wygenerowano cztery obrazy: Industrial Pro, Classic Digital, Cyberdeck, Organic Vector. **Grafiki nie są jeszcze załączone do repozytorium**; niniejszy opis zachowuje ich układ i wytyczne. Przed dodaniem plików graficznych: ustalić prawa i pochodzenie, wpisać je do `docs/PROVENANCE.md`, zweryfikować bezpieczeństwo oraz kontrakt IP. Nie kopiować ani nie brandować ekranów innych produktów.
