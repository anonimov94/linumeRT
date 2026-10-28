# Synteza prac Claude i Codex — 2026-10-26

Model-Author: Codex. Na polecenie właściciela: synteza prac i domknięcie otwartych gałęzi.
Materiały Claude: #182 (bramka licencyjna) i #183 (potwierdzony kierunek HTML/WebGL).
Materiały Codex: #180 (edycja kroków) i #184 (strategie, napisy, kształty, STL).
Przegląd dokumentu Claude #183: SHA `5cc1938`, komentarz Codex w PR.

## Wspólny wynik

1. Rdzeń `core/linumert` pozostaje źródłem modeli, walidacji, generatorów i `.lnx`.
   Nowe strategie, snapshoty konturów napisów i przekroje STL nie zależą od Qt.
   LinuxCNC nadal odpowiada za interpretację i planowanie ruchu; Plant i HAL bez zmian.
2. Działający ekran Qt oraz gotowa integracja CAM są zachowane jako punkt odniesienia.
   Po domknięciu #184 rozwój nowych stron/skórek Qt jest zamrożony. Poprawki działania
   i sterowania pozostają dozwolone. Nowe GUI przechodzi na HTML/CSS/WebGL zgodnie z #183.
3. Nowy klient korzysta z tych samych pól generatorów, `normalize/check/generate/preview_2d`
   i wersji kroków `.lnx`. Nie powstaje drugi zestaw algorytmów CAM ani druga baza narzędzi.
   Adapter czcionek Qt pozostaje w `screens/`; nowy klient wytwarza snapshot geometrii
   zgodny z tym samym backendem. Kompilacja zapisanego kroku nie wymaga Qt ani czcionki.
4. Czytnik STL i przekroje działają w rdzeniu Python/NumPy. Obecny zakres to model poglądowy
   i przekrój XY do grawerowania. Frezowanie powierzchni STL 3D pozostaje osobnym zakresem.
5. Brama web pozostaje poza RT i podlega istniejącym kontraktom LinuxCNC/HAL, D35 oraz
   wymaganiom odbioru. Sam nowy frontend nie zamyka odbioru E-STOP, JOG, MPG ani sprzętu.
6. Bramka licencyjna z #182 pozostaje otwarta przed dystrybucją binarną/obrazu.
   Synteza nie zmienia licencji ani nie publikuje wydania.

## Domknięcie i dalsza praca

#183 jest scalony jako `3ea8eb7`. #184 zamyka aktualną porcję CAM po kontroli końcowego SHA.
Znaleziono i poprawiono routing klawiatury wielowierszowego napisu: edycja nie trafia do JOG,
F1/F2/Esc i zwolnienie rozpoczętego JOG zachowują obsługę; 15 testów routera PASS.
Rdzeń/GUI CAM: 256 lokalnych testów PASS; końcowe kontrole Debian/LinuxCNC w #184.

Następny zakres jest zapisany jako `WEB-HMI-POC` w jedynym rejestrze roadmapy.
Obejmuje bramę, DRO i scenę WebGL na atrapie oraz odbiór na LinuxCNC sim/Plant.
Synteza nie deklaruje wykonania tego PoC ani zamknięcia całych M2/M3/M4.

Przegląd dokumentu Claude wykonano przez Codex. CAM pozostaje autokontrolą Codex,
dopóki nie ma rzeczywistego przeglądu Claude konkretnego SHA. Ręczny odbiór pulpitu,
kwalifikacja RT i sprzęt są odrębne. NIEZWERYFIKOWANE NA SPRZĘCIE.
