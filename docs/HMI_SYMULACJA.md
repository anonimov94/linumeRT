# HMI w trybie symulacji — uruchomienie i funkcje

Model-Author: Claude · 2026-10-19. Wszystko to symulacja: NIEZWERYFIKOWANE NA SPRZĘCIE.

## Uruchomienie (EndeavourOS / Arch, podman)

```bash
~/Projekty/linumeRT-claude/tools/linumert-start.sh --no-update --dir ~/Projekty/linumeRT-claude
# albo z GitHuba (main):  bash <(curl -fsSL https://raw.githubusercontent.com/anonimov94/linumeRT/main/tools/linumert-start.sh)
```

Pierwsze uruchomienie buduje obraz `linumert-app:bookworm-2` (Debian 12, LinuxCNC 2.9, pyqtgraph) — kilka
minut. Starter ustawia G54 symulatora (X100 Y100 Z-150 = lewy przedni róg wierzchu przygotówki na stole), gdy
`linumert.var` nie istnieje albo ma zerowe G54.

## Kolejność pracy

1. **Grzyb E-STOP** w dolnym pasku (F1 = wciśnięcie). Zwolnienie grzyba = potwierdzenie E-STOP (D35);
   tylko tak resetuje się E-STOP, także po kolizji w symulacji.
2. **Maszyna WŁ.**, potem **Bazuj** — bazowanie na krańcówkach (symulowane styki w HAL).
3. **Program** → wczytaj, np. `linumert_demo.ngc` (planowanie, kieszeń, rowek kulowy, fazowanie,
   wiercenie, frez lewy M4) albo `linumert_kolizja.ngc` (G0 w materiał → K-302 i E-STOP).
   Linia `;@STOCK …` w nagłówku programu ustawia przygotówkę automatycznie.
4. **Symulacja** (szyna po lewej): widok 3D przygotówki, narzędzia (bryła z profilu), stołu, docisków
   i śladu ruchu (bursztynowy = G0, morski = posuw). Materiał ubywa tam, gdzie przejeżdża część tnąca
   wirującego narzędzia.
   - **Przygotówka**: BOX/CYL, wymiary, punkt zera (ORIGIN), układ (G54…), naddatek TOP, materiał →
     „Ustaw przygotówkę”; „Odnów materiał” przywraca pełny blok.
   - **Model maszyny**: „Wczytaj model maszyny…” (`machine.yaml`: bryły kolizyjne, napędy). Domyślnie
     `config/sim/linumert_xyz/machine.yaml`.
   - **Obciążenie napędów**: moment wrzeciona wobec krzywej napędu, siły osi wobec granic napędów.
   - **Zdarzenia symulacji**: K-3xx z pozycją; każda kolizja i przeciążenie = E-STOP.
5. **Narzędzia**: tabela z bazy narzędzi; edycja typu (palcowy, kulowy, torusowy, teowy, lizak, fazownik,
   wiertła, głowica, gwintownik, specjalne), D, korekcji D ±1 mm, długości Z, ostrzy, maks. obrotów,
   kierunku skrawania (prawe M3 / lewe M4), oprawki. „Zapisz” = baza + `tool.tbl` + ponowne wczytanie
   w LinuxCNC i w symulacji.

## Reguły symulacji (`simulation/linumert_sim/engine.py`)

| Kod | Warunek |
|---|---|
| K-301 | narzędzie w materiale bez obrotów |
| K-302 | ruch szybki G0 usuwa materiał |
| K-303 | szyjka, oprawka albo wrzeciono w materiale |
| K-304 | narzędzie/oprawka/wrzeciono z dociskiem (mocowaniem) — z obrotami i bez |
| K-305 | element ruchomy z bryłą maszyny (stół itd.) — z obrotami i bez |
| K-306 | przeciążenie wrzeciona: moment skrawania (kc · objętość/s ÷ ω) > krzywa napędu |
| K-307 | przeciążenie napędu osi: siła posuwu > moment szczytowy / przełożenie |
| K-308 | skrawanie przy obrotach w złym kierunku (narzędzie prawe przy M4 itd.) |
| K-309 | obroty powyżej maksimum narzędzia |
| K-320 / K-322 | ostrzeżenia: narzędzie bez geometrii; podcięcie (teowy, lizak) poza modelem 2.5D |

Ograniczenia: materiał 2.5D (mapa wysokości, bez podcięć); siły szacowane z oporu właściwego kc materiału;
bryły głowicy typu `box` jadące z wrzecionem są pomijane (tylko walce). Kolizje symulacji nie są funkcją
bezpieczeństwa.

## Test bez operatora

`tools/dev/sim-e2e.sh` — Xvfb w obrazie startera: bazowanie, program demo, program kolizji; zrzuty
i `events.jsonl` w `build/sim-e2e/`. Dziennik zdarzeń symulacji przy zwykłym uruchomieniu:
`LINUMERT_SIM_LOG=/ścieżka/plik.jsonl`.
