# Bieżące zrzuty HMI i podglądu skórek

Model-Author: Codex · 2026-10-23. Kod ekranu: main `8483b81` (PR #89).
Obrazy są zrzutami uruchomionych aplikacji, bez montażu grafik koncepcyjnych.

## Cztery skórki — osobny podgląd offline

Świeże zrzuty 1920×1080, English, Classic Turquoise; każda skórka obsługuje także
Graphite Gray, Reactor Green i Ion Blue oraz język polski. Własne sceny OpenGL
pokazują poglądową maszynę bramową, detal z kieszenią i otworami oraz ścieżkę.
Odczyty bez danych i nieaktywne Start/Hold/Stop: ten launcher nie łączy się z CNC.
Pełna zgodność z [wzorcami właściciela](../../design/referencje-skin/README.md)
i ukończone skórki operatora pozostają dalszym zakresem.

| Classic Digital | Industrial Pro |
|:--|:--|
| ![Classic Digital](skin_classic-digital.png) | ![Industrial Pro](skin_industrial-pro.png) |
| Cyberdeck | Organic Vector |
| ![Cyberdeck](skin_cyberdeck.png) | ![Organic Vector](skin_organic-vector.png) |

Odtworzenie (PyQt5, pyqtgraph, PyOpenGL; X11/Xwayland):

```sh
python3 tools/dev/skin-check.py --output build/skin-docs
```

Do galerii skopiowano pliki `*-1920.png`. Odbiór 64 wariantów przy obu rozmiarach
przeszedł na Radeon/Mesa i Debian/llvmpipe. Pełne CI PR #89: 1019 pytest,
166 subtestów oraz 109 prób LinuxCNC PASS; autokontrola autora.

## Symulacja obróbki — aktualny ekran operatora

Nowe ujęcia z 2026-10-23, Debian 12/LinuxCNC 2.9.10, osobny kontener i Xvfb,
okno 1920×1080. UI z main `8483b81`; program demonstracyjny po poprawce komentarza
`8675777`. Bez montażu, retuszu lub zastępowania widoku bitmapą wzorcową.

| Przebieg | Zrzut |
|:--|:--|
| Obróbka w toku | ![Demo podczas obróbki](demo_w_trakcie.png) |
| Po całym programie, łącznie z ostatnim narzędziem T11 | ![Demo po obróbce](demo_po_obrobce.png) |
| Diagnostyka K-302, bez odebrania stanu ON przez symulację | ![Diagnostyka K-302](kolizja_k302.png) |

[Wynik przebiegu w JSON](wynik-2026-10-23.json) potwierdza bazowanie, działanie
procesu symulacji, ukończenie demo bez kolizji, ubytek materiału i oczekiwane K-302.
Końcowe narzędzie T11 oraz bezczynny interpreter są warunkiem zaliczenia demo.
Podczas odświeżania wykryto zagnieżdżony komentarz przy operacji M4: poprzedni
skrypt błędnie zaliczał przedwcześnie przerwany program. Poprawiono komentarz,
wzmocniono kontrolę ukończenia i dodano test leksera dla obu dostarczonych programów.

Odtworzenie:

```sh
tools/dev/sim-e2e.sh
```

Wyniki i kolejne klatki: `build/sim-e2e/`. Do galerii wybrano ujęcie podczas
programu, `02_po_demo.png` i `03_kolizja.png`; okno rozciągnięto do 1920×1080.
Konfiguracja testowa jest kopiowana do `/tmp` wewnątrz kontenera i używa
`HMI_ESTOP_BYPASS=1` wyłącznie dla automatycznej próby bez operatora; konfiguracja
operatora pozostaje bez zmian. Test nie korzysta z fizycznej obrabiarki.

NIEZWERYFIKOWANE NA SPRZĘCIE. Autokontrola, bez niezależnego przeglądu.
