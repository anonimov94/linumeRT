# Awaria HMI podczas pauzy i podglądu D38 — 2026-10-24

Model-Author: Codex. Zakres pierwotnego planu: 031, 045, 057.
Zgłoszenie właściciela po uruchomieniu symulatora z main b774ad1.

## Przyczyna i poprawka

Log operatora wskazał `ModuleNotFoundError: pydantic` w `_on_resume_preview`.
QtVCP uruchamia `/usr/bin/python3`; starter i proces symulacji korzystają z venv
`/opt/linumert`. Przejście przez exec LinuxCNC nie przekazywało katalogu zależności
venv do systemowego interpretera QtVCP. Dlatego testy uruchomione bezpośrednio
z Pythonem venv przechodziły, a rzeczywisty ekran nie widział pakietu.

`linumert.machine.launch` przekazuje purelib/platlib bieżącego venv w środowisku
procesu potomnego. Zachowuje istniejące ścieżki modułów i nie zmienia środowiska
rodzica ani zasad kontroli profilu/HAL. Dotyczy Debiana 12/Pythona 3.11 startera
oraz ISO; nie instaluje niczego w systemowym Pythonie gospodarza.

Preview2D wydzielono do samodzielnego modułu Qt: podgląd D38 nie ładuje już całego
kompilatora cykli, pydantic i modeli .lnx. Wygląd i geometria widżetu bez zmian.
Nie zmieniono progów, limitów, blokad ani sterowania retrakcją.

## Dowody

Przed poprawką dwa nowe testy regresji FAIL: brak zależności venv po exec do
systemowego Pythona oraz zależność podglądu od importu Cyklów. Po poprawce:
94 testy zakresu i 10 subtestów PASS w Debianie 12.

Nowy test `tests/test_hmi_runtime_linuxcnc.py` uruchamia pełny QtVCP przez tę samą
bramkę modułową co starter. Kopiuje wyłącznie profil sim, bez obejścia HMI E-STOP.
Sprawdza pydantic 2 i dostępność Cyklów wewnątrz rzeczywistego procesu GUI.
Samotest klika widoczne kontrolki; kontrolowany komunikat poprawnej geometrii
odtwarza callback powodujący awarię. Wyznaczanie geometrii ma odrębne testy
`test_resume_preview.py`; podgląd nie wykonuje ruchu.

Lokalny odbiór Debian 12/LinuxCNC 2.9.10 + Xvfb: PASS, 15 kroków, 42,72 s.
Raport zapisano przez rzeczywisty proces symulacji przy trwającej pauzie.
Rzeczywisty HAL: wycofanie `1.99999999945` mm, powrót `0.00000000094` mm;
program pozostawał w pauzie po powrocie, następnie zakończył się po wznowieniu.
Zrzuty i JSON: `build/pause-runtime/.../runtime/`; w CI: artefakt linuxcnc-evidence,
katalog test_launcher_runtime_in_actua*/runtime.

Odtworzenie w Debianie z LinuxCNC i venv zależności:

```sh
xvfb-run -a -s '-screen 0 1700x1100x24' .venv/bin/python -m pytest \
  -q -m linuxcnc tests/test_hmi_runtime_linuxcnc.py
```

Końcowe SHA i pełne wyniki CI: PR #102. Autokontrola, bez niezależnego przeglądu.
NIEZWERYFIKOWANE NA SPRZĘCIE. D38-B (wykonanie helisy po Abort/E-STOP) pozostaje otwarte.
