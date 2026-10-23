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

Trwa odświeżanie zrzutów z oddzielnej instancji LinuxCNC, `linumert_demo.ngc`
i diagnostycznego programu `linumert_kolizja.ngc`. Obrazy poniżej zostaną zastąpione
po zakończeniu przebiegu; szczegółowy wynik zapisuje `build/sim-e2e/wynik.json`.

![Demo podczas obróbki](demo_w_trakcie.png)
![Demo po obróbce](demo_po_obrobce.png)
![Diagnostyka K-302](kolizja_k302.png)
