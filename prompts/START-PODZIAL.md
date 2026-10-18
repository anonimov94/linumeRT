# Podział pracy na 4 sesje: 022, 024, 025 równolegle, potem 023

Model-Author: Claude · 2026-10-18 · polecenie właściciela (D33). Wspólne zasady dla `START-022.md`,
`START-024.md`, `START-025.md` i `START-023.md`. Sesja czyta ten plik i swój `START-NNN.md`.

| Sesja | Prompt | Kiedy | Własne pliki (tylko ta sesja je zmienia) |
|---|---|---|---|
| 022 Panel Plant i pulpit MPG | [START-022](START-022.md) | od razu | `plant/server/linumert_plant/panel/`, `plant/server/linumert_plant/server.py`, `serve.py`, `pyproject.toml`, `tests/test_panel*.py` |
| 024 Scenariusze, raport, check_requirements | [START-024](START-024.md) | od razu | `plant/scenarios/`, `plant/server/linumert_plant/faults.py`, `tools/run_scenario.py`, `tools/check_requirements.py`, `Makefile`, `.github/workflows/`, `docs/wymagania/MACIERZ.md`, `tests/test_scenario*.py`, `tests/test_requirements*.py` |
| 025 Maszyny wirtualne | [START-025](START-025.md) | od razu | `tools/vm/`, `docs/VM.md`, `tests/test_vm*.py` |
| 023 Edytor obrabiarki i awarie w panelu | [START-023](START-023.md) | po scaleniu 022 i 024 | panel (zakładki Maszyna, Napędy, Awarie), `plant/scenarios/edit_reload.yaml` |

Plik spoza swojej kolumny zmieniasz tylko wtedy, gdy bez tego nie da się zrobić zakresu: zmiana minimalna,
opisana w PR w sekcji „Pliki spoza zakresu”. Dokumenty wspólne (`docs/DZIENNIK.md`, `prompts/DONE.md`,
`docs/DECYZJE.md`, `docs/LICENCJE.md`, `docs/PROVENANCE.md`, `docs/PLANT.md`) zmieniasz tylko w końcowym
kroku sesji, dopisując własne wiersze.

## 1. Start
1. Lektura według `docs/PROMPT_NOWEJ_SESJI.md` §1, ale **bez** zajmowania `prompts/LOCK` i linii `Tura:`:
   przy pracy równoległej (D28, D33) nie ruszają ich sesje 022, 024 i 025. Stan bieżący prowadzisz w
   opisie swojego draft PR (sekcja „Stan zatrzymania”, jedna linia po każdym pushu).
2. Osobny checkout (worktree), nigdy wspólny katalog z inną sesją. W Git Bash, z
   `C:\Users\pc\Documents\PythonProjects\linumeRT\.collaboration\linumeRT`:
   ```bash
   git fetch -q origin
   git worktree add ../linumeRT-NNN -b wip/sesja-NNN origin/main   # gałąź już istnieje: bez -b, nazwa gałęzi
   ```
   Pracuj wyłącznie w `../linumeRT-NNN`. Jeśli istnieje `origin/wip/sesja-NNN`, kontynuuj ją
   (`git worktree add ../linumeRT-NNN wip/sesja-NNN`).
3. Draft PR do `main` po pierwszym kroku, tytuł `sesja NNN: ...`, opis z `Model-Author: Claude`.

## 2. Środowisko (Windows 11 + WSL)
- Narzędzia: Git Bash i PowerShell na Windows; testy w WSL `Ubuntu-24.04` (LinuxCNC 2.9 RIP w
  `~/.cache/linuxcnc-2.9`, Xvfb). Na Windows nie ma `make` ani `ruff`; nie instaluj Dockera.
- Testy zatwierdzonego HEAD (najpierw commit), z katalogu worktree:
  ```bash
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash tools/dev/wsl-test.sh             # lint, pytest, test-c
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash tools/dev/wsl-test.sh --linuxcnc # + testy -m linuxcnc
  ```
  Skrypt robi świeży klon w `~/linumert-test/<gałąź>` z własnym venv, więc sesje się nie mieszają.
  `--linuxcnc` zajmuje blokadę `linuxcnc` (jeden LinuxCNC w WSL naraz). Kod wyjścia 75 = blokada zajęta:
  nie czekaj w pętli, zrób inny krok i spróbuj później.
- Testy nie zajmują stałych portów: serwery w testach na porcie 0 albo na porcie z zakresu przypisanego
  sesji (022: 47810–47819, 024: 47820–47829, 025: 47830–47839). Port 8080 panelu tylko przy ręcznym starcie.
- Pliki zapisuj z końcami linii LF (repozytorium ma `.gitattributes`).

## 3. Praca
`docs/WSPOLPRACA_MODELI.md` §3: małe kroki, po każdym `wsl-test.sh` → commit → push → linia w PR.
Definition of Done z `CLAUDE.md` §11; wymagania REQ ze znacznikami `# REQ-XX-NN`; nowe zależności w
`docs/LICENCJE.md`, zasoby w `docs/PROVENANCE.md`. NIEZWERYFIKOWANE NA SPRZĘCIE tam, gdzie dotyczy.

## 4. Zamknięcie sesji
1. `git merge origin/main` w swoim worktree (scalone już sesje równoległe). Konflikty w dokumentach
   wspólnych rozwiąż, zostawiając wpisy obu stron (DONE według numeru, dziennik chronologicznie).
2. `wsl-test.sh` zielony (z `--linuxcnc`, jeśli sesja dotyka HAL, konfiguracji LinuxCNC albo serwera Plant).
3. Wpis w `docs/DZIENNIK.md` (wiersz w spisie i wpis na końcu), linia w `prompts/DONE.md` (licznik „Wykonane”),
   decyzje w `docs/DECYZJE.md`, stan w `prompts/README.md` (twoja sesja: zrobiona). Swój `START-NNN.md`
   przenieś do `prompts/archiwum/` i dopisz wiersz w `prompts/archiwum/README.md`.
4. PR gotowy, komentarz „autokontrola, bez niezależnego przeglądu” z SHA i wynikami testów, scalenie
   merge commitem po zielonym CI (`docs/WSPOLPRACA_MODELI.md` §5b). Usunięcie gałęzi może zablokować
   mechanizm uprawnień: zostaw ją.
5. `docs/NASTEPNA_SESJA.md` aktualizuje tylko sesja 023 (ostatnia z podziału). Sesje 022, 024 i 025
   wpisują w nim jedynie swój wiersz w §2 „Gałęzie i PR” przy scaleniu.
6. Usuń swój worktree: `git worktree remove ../linumeRT-NNN` (z głównego checkoutu).
7. Użytkownikowi: co powstało, link do PR, co sprawdzić ręcznie.
