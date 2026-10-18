# Wykonane sesje

Format: `NNN | RRRR-MM-DD | opis`. Agent dopisuje linię po udanej sesji. Zaplanowane zadanie bierze najniższy numer, którego tu nie ma.

001 | 2026-10-17 | Szkielet monorepo: pyproject, katalogi z README, Makefile, CI, LICENSE (GPL-2), LICENCJE, PROVENANCE, testy licencji/IP/układu
002 | 2026-10-17 | Proces IP, słownik, rejestr pochodzenia (52 wpisy), lista przed wydaniem, rozszerzony strażnik IP
006 | 2026-10-18 | Rdzeń cnc: niezmienna migawka stanu, czytnik linuxcnc.stat (wstrzykiwany moduł), atrapa z wirtualnym zegarem, 30 testów, docs/RDZEN.md
007 | 2026-10-18 | Katalog alarmów (56 kodów PL/EN) z walidacją, AlarmManager, 23 testy; tłumaczenia Qt (.ts, i18n.sh) odłożone do sesji ekranu
009 | 2026-10-18 | Specyfikacja Plant (docs/PLANT.md), protokół LRT-NET v1, macierz 22 REQ, testy spójności
010 | 2026-10-18 | Schemat machine.yaml (Pydantic v2), 24 reguły spójności, 5 przykładowych maszyn, 42 testy
011 | 2026-10-18 | Plant: rdzeń dynamiki osi w C (bezwładność, krzywa momentu, tarcie, grawitacja, luz, zderzaki), 23 testy C, make test-c w CI; PR #9 czeka na przegląd Codexa; prompt kolejnej sesji: prompts/START-012.md
012 | 2026-10-18 | Plant: napęd CiA 402 (CSP, krokowiec otwarty/zamknięty, awarie E-42xx) w C, 49 testów; PR #10 czeka na przegląd Codexa (zależy od #9)
013 | 2026-10-18 | Biblioteka napędów wirtualnych: 7 szablonów YAML + JSON Schema, instancje drives: w machine.yaml (id/template/overrides), python -m plant drive clone, API live w axis.c i drive.c ze wspólnym dziennikiem; REQ-VD-01…05 z testami; PR do przeglądu Codexa
014 | 2026-10-18 | Plant: machine.c (osie i napędy, gantry z alarmem rozjazdu, łańcuch kinematyczny, zderzaki, krańcówki, indeks, E-STOP, sonda, I/O 32 bity), build_machine.py + ctypes, 5 przykładów działa w rdzeniu C; REQ-VM-02…05 z testami; PR do przeglądu Codexa
