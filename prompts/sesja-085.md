# Sesja 085 · SKIN-01 · Renderer 3D offline

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Model-Author: Codex · 2026-10-23. Zakres według `docs/design/SKIN_AUDIT.md` i `SKIN_SYSTEM_ROADMAP.md`.

Cel: odtworzyć błędy ścian QPainter/OpenGL/STL, zbudować osobny podgląd renderera, sprawdzić lokalny GPU/Mesa i Debian/LinuxCNC. Nie integrować go jeszcze z aktualnym sterowaniem.

Akceptacja: niezależne sceny geometrii, jawny winding/normale/depth/culling/degeneracje, kamery i screenshoty; testy geometryczne oraz obrazowe na host GPU i Debian 12/LinuxCNC; ≤30 FPS; lint, pytest, C i wymagania zielone; dokumentacja, pochodzenie, dziennik i PR scalony po zielonym CI.

Wynik i granice: `docs/design/SKIN_01_RENDERER.md`, PR #87.
