<!-- Generowane przez python3 tools/roadmap.py; edytuj docs/roadmap/plan.json. -->
# Ukończone zakresy — widok rejestru

Pierwotny plan: **84 sesje M0–M6**, commit `796c6a2`. Stan na 2026-10-25: planowane: 15; w toku: 0; częściowe: 30; do odbioru: 0; ukończone: 39; zablokowane: 0.

Zakończenie części implementacji nie oznacza odbioru całej funkcji ani sprzętu.

To wynik generatora, nie lista do ręcznego dopisywania. Wybór pracy i statusy są w [plan.json](../docs/roadmap/plan.json); częściowe zakresy w [PLAN.md](../docs/roadmap/PLAN.md).

Ukończone pierwotne sesje: **39 z 84**.

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
027 | 2026-10-24 | Rozliczenie promptu 027: tokens.yaml źródłem prawdy; QSS powłoki generowany z tokenów (linumert_shell_model.shell_qss, test kolorów/44 px) + tools/gen_qss.py do zrzutu; fonty IBM Plex Sans i JetBrains Mono (OFL) w screens/linumert/fonts, rejestrowane przy starcie ekranu i podglądu skórek; 31 ikon z wpisami PROVENANCE (test_ip_guard); skórki korzystają z kontraktu palet (linumert_skin_contract); Claude
032 | 2026-10-18 | Baza narzędzi (rdzeń): 10 typów z walidacją, SQLite z migracjami i historią, tool.tbl bez strat (sprawdzone w rs274 LinuxCNC 2.9), CSV; ekran w sesji ekranu; PR #16; Claude
036 | 2026-10-24 | Role operator/technolog/serwis, PIN scrypt w SQLite (nigdy jawnie), blokada po błędach, audyt, CLI; przycisk roli i logowanie PIN w HMI; blokada edycji narzędzi/offsetów (technolog) i Konfiguracji/pełnego QtDragon (serwis). Opcjonalny klucz pulpitu: API Session.set_key, pin HAL do podłączenia z pulpitem; Claude
039 | 2026-10-18 | Format .lnx (Pydantic + lnx_schema.json), ;@STOCK, BaseMacroGenerator, deterministyczny kompilator .lnx → .ngc (golden, rs274), alarmy P-5011…P-5015; PR #14; Claude
040 | 2026-10-20 | Generatory header/program_end/tool_change/face_mill (#47) + walidacja kroków z bazą narzędzi (typ, średnica, skok, długość ostrza, obroty, kierunek; P-5207…P-5211, compile_program(tools=…)); Claude
041 | 2026-10-21 | Kieszenie v2: pionowo/rampa/helisa, naroża, obrót, CW/CCW, naddatki i wykańczanie; v1 niezmienne; golden, materiał bez wysp, rs274 i wykonanie na LinuxCNC + Plant; 882 + 94 LinuxCNC PASS; PR #58; Codex
043 | 2026-10-24 | contours.py: slot_linear, slot_arc, stud_rect, stud_circle, contour (G41.1/G42.1, dojazd/odjazd styczny, P-5010 z numerem segmentu), preview_2d, w menu Cykli; golden 5 programów, weryfikacja materiałem StockMap, test rs274 w CI; Claude
044 | 2026-10-18 | Lekser G-code LinuxCNC (P-5101…P-5111, linia/kolumna, słowa O), kontrola w rs274; 44 próbki zgodne z LinuxCNC 2.9; przycisk Sprawdź w sesji ekranu; PR #15; Claude
048 | 2026-10-20 | Podprogramy o<lrt_face_mill>, o<lrt_drill_grid>, o<lrt_drill_circle> (NgcGui), eksport do user_macros, PODPROGRAMY.md; ruch zgodny z generatorami w rs274 (część: kieszenie/rowki później); Claude
049 | Wybrane cykle na LinuxCNC + Plant (#58/#60); tools/suite_cycles.py: 10 przypadków generatorów (planowanie, wiercenie G81/G83, kieszenie, rowki, czopy, kontur) × router_gantry_steppers i mill_servo_table, warianty A (G0 z machine.yaml) i B (G0 ≤ 3000 mm/min): 40/40 PASS po poprawce Plant (interpolacja celu CSP w podkrokach, PLANT-SUBSTEPS). Wcześniejsze zgubione kroki routera i E-4201 frezarki przy G0 były artefaktem modelu, nie generatorów.
051 | simulation/linumert_sim/path.py: MoveList (start/end float32, line/tool int32, kind int8, feed float32), łuki G17/G18/G19 z linią śrubową na cięciwach z błędem ≤ 0,01 mm, PathCanon dla gcode.parse oraz zapasowy interpreter podzbioru (G0–G3, IJK/R, G20/21, G90/91, G90.1/91.1, T/M6, G81/82/83/73 z G98/G99) z notatkami zamiast zgadywania. 10 programów golden z M3; z LinuxCNC 2.9 (RIP) 9 programów bez korekcji zgodnych z rs274 co do linii, końców i długości. Naprawiony brak canon.parameter_file (TypeError w gcode.parse, także w core load_ngc).
052 | Symulacja live (osobny proces, nice 10) z wcześniejszych sesji, a teraz także offline: simulation/linumert_sim/offline.py (ścieżka 051 → SimEngine: materiał, K-3xx, czas G0/G1, objętość usunięta) i worker.py — proces potomny spawn z nice ≥ 10, kolejka zadań, anulowanie zadania bieżącego i oczekującego, cache wyników po SHA-256 wejścia (pamięć + pliki JSON), wątek pomocniczy z callbackiem; most sygnałów Qt screens/linumert/linumert_sim_worker.py. MoveList z obrotami wrzeciona (S, M3/M4/M5; rs274 przez LineCode.spindle/speed).
054 | 2026-10-20 | Przygotówka: ;@STOCK, dialog Symulacja, K-321 (wcześniej) + cel sondy Plant z przygotówki (tools/stock_probe.py); Claude

## Ukończone rozszerzenia (nie zamykają automatycznie sesji)

D38-A | PR #62: external offsets, zachowanie modalności i testy sim/Plant PASS. PR #102: poprawka zależności QtVCP i test pełnego HMI (pauza, podgląd, raport, rzeczywiste wycofanie Z 2 mm/powrót/wznowienie), Debian PASS.
PLAN-21-22 | Rampa/helisa, geometria i wykańczanie; #58, odbiór automatyczny PASS.
PLAN-23 | PR #59: odbiór automatyczny wskazanego kroku PASS.
PLAN-24 | PR #60: odbiór podglądu PASS; wykonanie pozostaje w D38-B.
PLAN-25 | PR #60: pomiary i testy ETA PASS.
PLAN-26 | PR #60: odbiór raportu PASS.
SKIN-01 | PR #87: prototyp i testy GPU/Mesa PASS; odbiór docelowego HMI należy do SKIN-06.
SKIN-PREVIEW | PR #89: podgląd i odbiór 64 wariantów GL.
SKIN-GALLERY | PR #90: nowe zrzuty i README.
SKIN-OFFLINE | PR #91: launcher --skin i 128 wariantów GL; bez integracji sterowania.
KONKURS-01 | PR #93 scalony: bramka profilu i ograniczony audyt HAL.
KONKURS-02 | PR #94 scalony: procedura i dowody; odbiór A3 FAIL OD-01, T1–T7 otwarte.
KONKURS-03 | PR #95 scalony: odrzucanie NaN/inf; real mapping i geometria ATC nadal otwarte.
KONKURS-04 | PR #96 scalony: odczyt NML; nie kończy SKIN-02/04…06.
ISO-INTEGRATION | PR #97: bramka sim/Plant i monitor; PR #101 (iso/fix-live-login) dodaje konto linumert, user-setup/sudo i jawny autologin. Debian 12: rzeczywiste tworzenie konta, hasło, UID i idempotencja PASS; budowa końcowego ISO w kontrolach PR #101.
OD-01 | Przyczyna: losowy start (seed 1) w router_atc_rack lądował wewnątrz magazynu. Start omija bryły kolizyjne (emulacja xorshift rdzenia C, zmiana tylko przy kolizji), a matrix_smoke wymaga braku CRASH i COVER_CRASH; macierz 5/5 po 4 kryteria, 1116 testów PASS.
EDITOR-VALIDATION | PR #98: walidacja niezapisanej treści, lista błędów z przejściem do linii i wyszukiwanie/zamiana z Undo; Qt w Debianie: 60 testów zakresu PASS, zrzut rzeczywistego dialogu. Końcowe CI i SHA w PR.
ROADMAP-UNIFICATION | PR #99: jeden rejestr, generowane widoki, kontrola CI, instrukcje i migracja historii; lokalne testy i odbiór DOM PASS. Wynik CI i SHA w PR.
PLANT-SUBSTEPS | Cel CSP z cyklu mastera interpolowany liniowo w podkrokach rdzenia C (lrt_machine_step_cycle, jak 60C2h/stepgen); domyślnie 4 podkroki. Atrapa: frezarka i router PASS dla n = 2–16 (wcześniej E-4201 i ~1560 zgubionych kroków przy n ≥ 2–4). Raport docs/raporty/plant_substeps.md.

## Korekty historycznego rejestru

007 i 048 były wpisane jako wykonane mimo odłożonego zakresu; teraz są częściowe. Dawne wpisy zachowano w polu `historical_completion` rejestru i historii Git. Numery 085–088 i oznaczenia konkursowe są aliasami rozszerzeń, nie nowymi sesjami pierwotnego planu.
