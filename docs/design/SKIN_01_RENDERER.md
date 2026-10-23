# SKIN-01 — renderer 3D poza ekranem operatora

Model-Author: Codex · 2026-10-23 · PR #87. Prototyp OpenGL nie jest jeszcze
integracją ze stroną Symulacja ani modelem produkcyjnym kolizji.

Uruchom w repozytorium z istniejącymi PyQt5, pyqtgraph i PyOpenGL:
`python3 tools/dev/renderer-preview.py`. Widoki `solids`, `crossing`, `winding`
używają XYZ w mm i lokalnych kamer iso/top/bottom. Wireframe, back-face culling
i oświetlenie z normalnych są narzędziami diagnozy. Poza edytowanym modelem GUI
nie czyta STATUS ani LinuxCNC i nie importuje STL z zewnętrznych źródeł.

Scena `crossing` reprodukuje ograniczenie sortowania średnią głębokością QPainter:
dwie otwarte, przecinające się powierzchnie zamieniają się miejscami wzdłuż
przecięcia. Bufor głębokości daje obraz niezależny od kolejności obiektów.
Stary generator `linumert_sim_page._revolve` wstawiał pełny pierścień zerowych
wierzchołków na osi dla każdego końca; przy 24 segmentach przygotówka `cylinder`
produkowała 48 zerowych ścian kapsli. Siatki `Workpiece` i zamknięty STL z mapy
wysokości zachowują dodatnią objętość i spójny winding w fixture'ach testowych.

Walidator wylicza płaską normalną ze windingu CCW, odrzuca NaN, niepoprawne
indeksy i wejście bez poprawnych ścian. Zerowe ściany pomija z jawnym licznikiem;
nie próbuje naprawiać normalnych otwartej siatki ani samoprzecięć. Opaque OpenGL
depth test/depth write jest włączony, winding CCW i opcjonalny culling jest jawny.
Odświeżenia z treści i interakcji są łączone przez timer 34 ms (maks. 30 żądań/s);
statyczny widok nie animuje się.

Odbiór obrazu: `python3 tools/dev/renderer-check.py --output build/skin01/host`
przechodzi na AMD Radeon 660M, Mesa radeonsi 26.2.5, pyqtgraph 0.14, Qt 5.15.
Debian 12/LinuxCNC 2.9.10 z pyqtgraph 0.13/Mesa llvmpipe 22.3.6 również PASS.
W obu środowiskach głębia to 24 bity, zamiana kolejności dała 0% różnicy,
a kamery, culling zamkniętych brył, culling orientacji ścian, wireframe, obrót,
licznik odświeżeń i bezczynność zostały sprawdzone; raport i PNG zapisuje probe.
Test ten jest w jobie `LinuxCNC RIP smoke`. Wyniki nie potwierdzają zachowania
konkretnego GPU właściciela, przezroczystości, importu STL ani kolizji produkcyjnych.

Model-Author: Codex. Autokontrola, bez niezależnego przeglądu. Sprzęt obrabiarki
nie był używany. Następny etap wymaga przeglądu algorytmu windingu/normalnych dla
wszystkich modeli Plant i przyłączenia do hosta testowego bez komend CNC.
