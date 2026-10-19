# Wymagania: typy narzędzi, przygotówka i reguły kolizji

Wersja 1.0 · 2026-10-17 · status: obowiązująca (zastępuje wcześniejsze dokumenty źródłowe)

## 1. Typy narzędzi (baza narzędzi i symulacja)

| Typ (`id`) | Parametry wymagane | Profil w symulacji |
|---|---|---|
| Palcowy (`flat`) | D, L, długość ostrza | walec z płaskim czołem |
| Kulowy (`ball`) | D, L | walec + półkula R = D/2 |
| Torusowy (`bull`) | D, L, R naroża | walec z zaokrąglonym narożem |
| Teowy (`tslot`) | D tarczy, szerokość, Ø i długość szyjki | tarcza na szyjce |
| Lizak (`lollipop`) | D kuli, Ø i długość szyjki | kula na szyjce |
| Fazownik (`chamfer`) | D, kąt | stożek |
| Wiertło 118°/120° (`drill_118`) | D, L | walec + stożek |
| Wiertło z kątem (`drill_angle`) | D, kąt ≤ 180° | walec + stożek (180° = płaskie) |
| Głowica frezarska (`face_mill`) | D, H | walec D × H |
| Gwintownik (`tap`) | D, L, skok | walec; skrawa tylko z obrotami w kierunku narzędzia |
| Specjalne (`special_stl`) | plik STL (oś Z, czoło w 0) | z pliku; w symulacji 2.5D obwiednia + ostrzeżenie |

Wspólne pola: maks. obroty, kierunek skrawania (prawy M3 / lewy M4), korekcja średnicy ±1 mm, oprawka (Ø, długość), numer T, miejsce P, opis, oprawka (typ lub STL), długość ostrza (część tnąca), szyjka i
oprawka (część nietnąca), trwałość. Brak typu → model zastępczy walca D × L i ostrzeżenie K-320.

## 2. Przygotówka
Zapis w `.lnx` i w nagłówku `.ngc`:
`;@STOCK BOX X120 Y80 Z30 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 TOP=1.0 MAT="aluminium"` lub
`;@STOCK CYL D60 H40 ORIGIN=TOP_CENTER OFFSET=G54`. Brak przygotówki → K-321 i okno definicji przed symulacją.
Ta sama przygotówka może trafić do Plant (sonda trafia w ten sam materiał).

## 3. Reguły kolizji i błędów symulacji

| Kod | Klasa | Warunek |
|---|---|---|
| K-301 | kolizja | ruch roboczy (G1/G2/G3) usuwa materiał, gdy wrzeciono stoi (brak M3/M4 lub S poniżej progu, domyślnie 10 obr/min) |
| K-302 | kolizja | ruch szybki G0 usuwa materiał |
| K-303 | kolizja | część nietnąca (szyjka, oprawka, wrzeciono) w materiale |
| K-304 | kolizja | narzędzie lub oprawka z mocowaniem (później) |
| K-305 | kolizja | element ruchomy z modelem maszyny (później) |
| K-310 | ostrzeżenie | przekroczenie limitów programowych osi |
| K-311 | ostrzeżenie | bliski kontakt poniżej progu (domyślnie 2,0 mm) |
| K-320 | dane | narzędzie bez geometrii |
| K-321 | dane | brak definicji przygotówki |

Zdarzenie zawiera kod, numer linii, narzędzie, pozycję, opis i parę elementów. Domyślnie symulacja trwa
dalej po zdarzeniu; dostępna opcja „zatrzymaj przy pierwszej kolizji”. Kolizje symulacji nie są funkcją
bezpieczeństwa.

## 4. Renderer
Widok 3D maksymalnie 30 FPS, bez cieni i efektów, renderowanie tylko przy zmianie; geometria ścieżki
w jednym buforze; zmiana kamery nie przelicza G-code ani kolizji. Test referencyjny: 100 000 segmentów.
