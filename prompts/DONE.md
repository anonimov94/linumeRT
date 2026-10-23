# Wykonane sesje

Format linii: `NNN | RRRR-MM-DD | opis; PR; model`. Linie są posortowane według numeru sesji. Agent dopisuje
linię dopiero po spełnieniu kryteriów akceptacji sesji i wstawia ją we właściwe miejsce. Harmonogram bierze
najniższy numer, którego tu nie ma (teraz: **027**). Szczegóły każdej sesji: [`docs/DZIENNIK.md`](../docs/DZIENNIK.md),
stan scalania PR: [`docs/NASTEPNA_SESJA.md`](../docs/NASTEPNA_SESJA.md).

Wykonane: 33 z 84.

001 | 2026-10-17 | Szkielet monorepo: pyproject, katalogi z README, Makefile, CI, LICENSE (GPL-2), LICENCJE, PROVENANCE, testy licencji/IP/układu; Claude
002 | 2026-10-17 | Proces IP, słownik, rejestr pochodzenia (52 wpisy), lista przed wydaniem, rozszerzony strażnik IP; Claude
003 | 2026-10-18 | LinuxCNC 2.9 RIP (uspace) w środowisku agenta: budowa, testy, CI na Debianie 12 (debian:bookworm); PR #3 i #26; Codex, dokończenie Claude (D31)
004 | 2026-10-18 | Konfiguracja sim linumert_xyz (QtDragon, kontrakt sygnałów D05, bazowanie latch release), HAL_KONTRAKT, SIM_WSL; PR #24; Claude (D31)
005 | 2026-10-18 | Ekran screens/linumert: kopia QtDragon 2.9.10 (commit 86cdca7), handler-patch, UPSTREAM.md, DISPLAY = qtvcp linumert, zrzut G0; PR #25; Claude (D31)
006 | 2026-10-18 | Rdzeń cnc: niezmienna migawka stanu, czytnik linuxcnc.stat (wstrzykiwany moduł), atrapa z wirtualnym zegarem, 30 testów, docs/RDZEN.md; PR #5; Claude
007 | 2026-10-18 | Katalog alarmów (56 kodów PL/EN) z walidacją, AlarmManager, 23 testy; tłumaczenia Qt (.ts, i18n.sh) odłożone do sesji ekranu; PR #6; Claude
008 | 2026-10-18 | Bramka G0: sprzątanie po testach LinuxCNC (61/61 w jednym przebiegu), czytnik rdzenia na RIP (zaległość 006), docs/raporty/G0.md, architektura w README; PR #35; Claude
009 | 2026-10-18 | Specyfikacja Plant (docs/PLANT.md), protokół LRT-NET v1, macierz 22 REQ, testy spójności; PR #7; Claude
010 | 2026-10-18 | Schemat machine.yaml (Pydantic v2), 24 reguły spójności, 5 przykładowych maszyn, 42 testy; PR #8; Claude
011 | 2026-10-18 | Plant: rdzeń dynamiki osi w C (bezwładność, krzywa momentu, tarcie, grawitacja, luz, zderzaki), 23 testy C, make test-c w CI; PR #9; Claude
012 | 2026-10-18 | Plant: napęd CiA 402 (CSP, krokowiec otwarty/zamknięty, awarie E-42xx) w C, 49 testów; PR #10; Claude
013 | 2026-10-18 | Biblioteka napędów wirtualnych: 7 szablonów YAML + JSON Schema, instancje drives: w machine.yaml (id/template/overrides), CLI drive clone, parametry w locie; REQ-VD-01…05; PR #11; Claude
014 | 2026-10-18 | Plant: machine.c (osie i napędy, gantry z alarmem rozjazdu, łańcuch kinematyczny, zderzaki, krańcówki, indeks, E-STOP, sonda, I/O 32 bity), build_machine.py + ctypes; REQ-VM-02…05; PR #12; Claude
015 | 2026-10-18 | Bazowanie po rozruchu (REQ-VM-07): enkoder przyrostowy/absolutny z baterią (E-4211), tryb 6 w napędzie, start losowy, plik stanu, gantry, atrapa mastera, hal/lrt_hardstop_home.comp; PR #13; Claude
016 | 2026-10-18 | Plant: serwer LRT-NET (kodek v1, UDP lockstep/realtime, watchdog E-4003, stan bezpieczny, SHA-256 śladu, ślad CSV/JSONL, master testowy); 10 000 ramek bez strat; REQ-QA-03/04; PR #17; Claude
017 | 2026-10-18 | Komponenty HAL lrt_net + lrt_cia402 (LRT-NET v1 w C), test halrun + Plant; PR #27; Claude (D31)
018 | 2026-10-18 | config/plant/linumert_plant_xyz: LinuxCNC ↔ Plant, bazowanie na krańcówkach, test e2e, tools/dev/plant-gui.sh; PR #28; Claude (D31)
019 | 2026-10-18 | Wyrocznia Plant REQ-VM-06: soft limits i strefy zakazane, scenariusze softlimit/forbidden_zone z LinuxCNC; PR #29; Claude (D31)
020 | 2026-10-18 | Plant: magazyn narzędzi (regał/karuzela/parasol), zacisk, osłona, czujnik długości, kolizje CRASH; REQ-VM-08…10; PR #30; Claude (D31)
021 | 2026-10-18 | Plant: wrzeciono VFD — model, hy_vfd (pty), Modbus TCP, usterki; wariant LinuxCNC _vfd z prawdziwym hy_vfd (M3/M4/M5); PR #32; Claude (D31)
022 | 2026-10-18 | Plant: panel web (FastAPI/WS, uPlot) — telemetria 10 s, parametry live i presety, CSV, wirtualny pulpit MPG jako bity LRT-NET; PR #37; Claude (Opus 5.5)
023 | 2026-10-18 | Plant: edytor maszyny (drzewo, walidacja, wersje, przeładowanie bez restartu), widok 3D z modelu, zakładki Napędy i Awarie, scenariusz edit_reload; PR #39; Claude (Opus 5.5)
024 | 2026-10-18 | Plant: awarie (faults.py), scenariusze z atrapą mastera i z LinuxCNC, raport HTML/SVG, run_scenario, check_requirements w make test, job plant-matrix; PR #38; Claude (Opus 5.5)
025 | 2026-10-19 | Skrypty VM: create-vms.ps1 (VBoxManage, SHA-256, unattended VM-B), post-install ctl/plant (usługa linumert-plant, socat dla hy_vfd), docs/VM.md, lrtnet_probe; Plant przyjmuje nową sesję mastera; PR #41; Claude (Opus 5.5)
026 | 2026-10-20 | Odbiór automatyczny Plant P0/G1: pełne CI Debian 12/LinuxCNC, C+ASan/UBSan, scenariusze, raport P0 i checklista ręczna; PR #56; Codex
032 | 2026-10-18 | Baza narzędzi (rdzeń): 10 typów z walidacją, SQLite z migracjami i historią, tool.tbl bez strat (sprawdzone w rs274 LinuxCNC 2.9), CSV; ekran w sesji ekranu; PR #16; Claude
039 | 2026-10-18 | Format .lnx (Pydantic + lnx_schema.json), ;@STOCK, BaseMacroGenerator, deterministyczny kompilator .lnx → .ngc (golden, rs274), alarmy P-5011…P-5015; PR #14; Claude
040 | 2026-10-20 | Generatory header/program_end/tool_change/face_mill (#47) + walidacja kroków z bazą narzędzi (typ, średnica, skok, długość ostrza, obroty, kierunek; P-5207…P-5211, compile_program(tools=…)); Claude
041 | 2026-10-21 | Kieszenie v2: pionowo/rampa/helisa, naroża, obrót, CW/CCW, naddatki i wykańczanie; v1 niezmienne; golden, materiał bez wysp, rs274 i wykonanie na LinuxCNC + Plant; 882 + 94 LinuxCNC PASS; PR #58; Codex
044 | 2026-10-18 | Lekser G-code LinuxCNC (P-5101…P-5111, linia/kolumna, słowa O), kontrola w rs274; 44 próbki zgodne z LinuxCNC 2.9; przycisk Sprawdź w sesji ekranu; PR #15; Claude
048 | 2026-10-20 | Podprogramy o<lrt_face_mill>, o<lrt_drill_grid>, o<lrt_drill_circle> (NgcGui), eksport do user_macros, PODPROGRAMY.md; ruch zgodny z generatorami w rs274 (część: kieszenie/rowki później); Claude
054 | 2026-10-20 | Przygotówka: ;@STOCK, dialog Symulacja, K-321 (wcześniej) + cel sondy Plant z przygotówki (tools/stock_probe.py); Claude

085 | 2026-10-23 | SKIN-01: reprodukcja zasłaniania i windingu brył, podgląd OpenGL na Radeon/Mesa i Debian/LinuxCNC; PR #87; Codex
086 | 2026-10-23 | Podgląd skórek według czterech makiet właściciela, sceny 3D i powiększanie, odbiór GL 64 wariantów; nie kończy SKIN-02…06; PR #89; Codex
087 | 2026-10-23 | Nowe zrzuty skórek i rzeczywistej symulacji w README/raporcie hmi_sym, poprawka komentarza demo i potwierdzenie T11; PR #90; Codex
088 | 2026-10-23 | Cztery osobne ekrany offline, układy i kontrolki według wizji, launcher --skin, 128 wariantów GL, nowa galeria; nie kończy integracji CNC; PR #91; Codex
K04 | 2026-10-23 | Konkurs: typowany adapter read-only NML, cztery skórki, G53, timeout i reconnect LinuxCNC 2.9.10/Xvfb; PR #96 gotowy do oceny, bez scalania; raport raporty/04.md; Codex


KONKURS-03 | 2026-10-23 | Audyt trzech luk poza GUI, odmowa NaN/inf w machine.yaml; Debian 1104 PASS, 108 C/ASan PASS, REQ bez błędów; PR #95 do wspólnej oceny, bez scalenia; Model-Author: Codex
