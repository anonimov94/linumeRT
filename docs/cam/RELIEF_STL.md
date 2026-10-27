# Płaskorzeźba z STL — backend frezu kulistego v1

Model-Author: Codex · 2026-10-27. Zakres 041/043/051, polecenie właściciela.

Backend generuje trójosiową ścieżkę wykańczającą górną obwiednię STL. Wymaga
przygotówki po obróbce zgrubnej: nie dobiera głębokości skrawania w pełnym materiale.
Nie obsługuje podcięć, oprawki, chwytu frezu ani kolizji maszyny. LinuxCNC pozostaje
interpreterem i planerem ruchu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Uruchomienie

Po instalacji `pip install -e .`:

```bash
linumert-relief model.stl -o relief.ngc \
  --tool-diameter 3 --sample-step 0.1 --stepover 0.5 \
  --safe-z 15 --feed 500 --plunge 100 --tool 1 --rpm 10000
```

Alternatywnie: `python -m linumert.generators.relief` z tymi samymi argumentami.
STL nie określa jednostek: domyślnie współrzędne są w mm; `--scale 25.4` importuje
geometrię zapisaną w calach. Położenie STL staje się położeniem w G54; nie wykonujemy
automatycznego centrowania, obracania ani ustalania zera detalu.

Plik wynikowy jest zapisywany atomowo dopiero po poprawnym przeliczeniu całej ścieżki.
Błąd importu/parametrów pozostawia poprzedni wynik nietknięty. CLI nie łączy się z CNC.
Przed wykonaniem programu należy sprawdzić G54 i pozostałe przesunięcia, tabelę narzędzi
(T i H o tym samym numerze), wrzeciono M3, przygotówkę, mocowanie i limity maszyny.

## API i geometria

```python
from linumert.generators.relief import ReliefSettings, relief_from_stl

path = relief_from_stl("model.stl", ReliefSettings(tool_diameter=3, safe_z=15))
rows_xyz = path.rows
ngc = path.gcode()
```

`plan_relief(mesh, settings)` przyjmuje też `Mesh` ze wspólnego czytnika STL.
`ball_tip_height(triangles, x, y, radius)` liczy statyczny kontakt kuli z wnętrzami
trójkątów, krawędziami i wierzchołkami; pionowe ściany nie są pomijane. Wielowarstwowy
model daje górną obwiednię, a otwory bez kontaktu schodzą do minimalnej Z modelu.

Raster obejmuje prostokąt XY modelu, naprzemiennie wzdłuż X. Pomiędzy wierszami
narzędzie wraca do bezpiecznej Z. Bezpieczna Z musi przewyższać maksimum STL oraz
zachowawczy naddatek próbkowania. Program ma G21/G90/G17/G94/G40/G80/G54/G61,
T/M6/G43, G97/M3 i kończy się wycofaniem, M5 i M2.

Samo wyznaczenie wysokości w punktach może przeoczyć wąski szczyt między próbkami.
Dlatego sfera używana do kontaktu ma promień powiększony o największy rzeczywisty
odcinek X (`delta`); jej środek odnosimy do rzeczywistego promienia frezu. Każdy koniec
odcinka jest wtedy wystarczająco wysoko dla całego odcinka. Obie wysokości oraz ich
interpolacja liniowa pozostają ponad modelem w obszarze kulistego ostrza. Z zaokrąglamy
w górę do 0,0001 mm; XY jest zaokrąglane przed obliczeniem kontaktu. G61 zachowuje
wyliczoną łamaną.

**To zachowawczy naddatek, nie gwarancja tolerancji wykończenia.** Na poziomej
płaszczyźnie pozostaje `delta` (plus do 0,0001 mm zaokrąglenia); na stromych powierzchniach
może zostać więcej. Mniejszy `sample-step` zmniejsza ten efekt. Odstęp wierszy
`stepover` wpływa osobno na grzebienie po frezie. Pierwsza wersja nie oblicza
chropowatości ani nie zapewnia zadanej tolerancji całej powierzchni.

## Granice i odbiór

Czytnik ASCII/binary i przekroje pochodzą z backendowej części PR #184, bez Qt.
Limity: plik 8 MiB, 100000 trójkątów; raster 50000 punktów oraz 50000000 potencjalnych
porównań punkt–trójkąt. Po przekroczeniu następuje jawna odmowa przed eksportem.
Zwiększenie kroku lub uproszczenie STL ogranicza koszt. Planowanie jest synchronicznym
API poza RT; klient powinien uruchamiać je w osobnym zadaniu/procesie, poza pętlą UI.

Testy obejmują analityczne płaszczyzny, krawędź i pionową ścianę, niezależne gęste
próbkowanie trójkątów, szczyt między próbkami, skalę STL, kolejność wierszy,
niepoprawne parametry, limit pracy i zachowanie poprzedniego pliku. Osobny test
`linuxcnc` sprawdza cały program przez `rs274`. Test eksportowanego G-code
w Z-map z kulistym ostrzem potwierdza usunięcie naddatku na płaszczyźnie pochyłej,
brak ubytku na przejazdach szybkich i brak zejścia poniżej powierzchni docelowej.

Pozostaje rozszerzony odbiór złożonych płaskorzeźb w symulacji, strategia zgrubna,
kontrola trzpienia/oprawki oraz integracja funkcji w nowym kliencie web.
