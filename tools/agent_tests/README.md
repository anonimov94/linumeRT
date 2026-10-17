# Wspólna paczka testowa Codex / Claude

Model-Author: Codex. W repozytorium są runner, launcher Windows oraz VNC
(`../vm/start-vnc.sh`). Nie potrzeba kopiować plików ani tworzyć oddzielnego projektu.

## Uruchomienie z Windows — pulpit VNC i testy

Z katalogu repozytorium, w PowerShell:

```powershell
.\tools\agent_tests\Start-Tests.ps1 -Model Codex
```

Claude używa `-Model Claude`, użytkownik `-Model Manual` (domyślny).
Jeżeli bieżący podgląd już zajmuje port 5909, dodaj `-DisplayNumber 10` (port 5910).
`-NoVnc` uruchamia same testy. `-Distribution Ubuntu` pozwala wybrać inną dystrybucję.
Pozostaw konsolę uruchamiającą otwartą. Ctrl+C zatrzymuje pulpit tej sesji.

Przed pierwszym użyciem w Ubuntu, z katalogu repozytorium:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Skrypt VNC wymaga zainstalowanego TigerVNC, XFCE i istniejącego hasła VNC.
Instrukcje i adres Viewera: [podgląd Ubuntu](../../docs/PODGLAD_UBUNTU.md).
Nie publikujemy hasła, pliku uwierzytelnienia ani sesji pulpitu w Git.

## Runner bez pulpitu

```bash
.venv/bin/python tools/agent_tests/run.py --model Claude
```

Uruchamia kontrolę diffu, ruff i pytest. Wynik każdego polecenia jest widoczny
na żywo. Błąd jednego nie pomija kolejnych; brak narzędzia oznacza błąd, nie sukces.
Raport JSON zawiera autora-model, commit, stan roboczy, środowisko i kody wyjścia.
Logi i raporty są w `state/test-runs/<czas-UTC>-<model>/` (pomijane przez Git).
Raport częściowy po przerwaniu nie zawiera końcowego pola `passed`.

To wspólne narzędzia weryfikacji, nie niezależna recenzja drugiego modelu.
Obecne testy nie potwierdzają LinuxCNC ani czasu rzeczywistego; integracja LinuxCNC
jest zadaniem sesji 003. Nie oznaczaj sesji 003 jako wykonanej na podstawie tego runnera.
