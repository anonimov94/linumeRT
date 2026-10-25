# M1 — gotowość napędów przed bazowaniem

Model-Author: Codex · 2026-10-25. Autokontrola; odbiór poprawki na LinuxCNC w CI PASS.
NIEZWERYFIKOWANE NA SPRZĘCIE. Zakres Claude 033 (G54–G59.3 i sonda Z/narożnika)
pozostaje odrębny.

## Ustalenie z kodu i śladu

Ślad z #141 na `23caa5f` pokazuje rozpoczęcie zadania Z przy statusword 512
i drive-enabled=0, następnie błąd nadążania 0,51 mm > 0,5 mm.
Statusword 512 = `0x0200`: `lrt_drive_statusword` dodaje bit REMOTE do stanu
NOT_READY (maska `0x4f` daje 0). `lrt_cia402.decode_state` rozpoznaje go poprawnie
jako NOT_READY i nie wystawia enabled. Plant odmierza `boot_time_s` w czasie modelu;
szablon serwa Z ustawia 1 s. Nie ma podstaw do wyłączania tego opóźnienia.

Runner czekał na `linuxcnc.STATE_ON`, po czym wywoływał `home(-1)`. Stan zadania ON
uruchamia żądanie enable do CiA402, ale nie potwierdza zakończenia rozruchu napędu.
To brak warunku gotowości w orkiestracji testu, odrębny od poprawnej fizycznej
odpowiedzi napędu podczas rozpędzania i hamowania. Nie wyjaśnia historycznego X 0,3 mm.

Źródła: `hal/lrt_cia402.comp`, `plant/core/drive.c`, szablon `servo_750w.yaml`,
`config/plant/linumert_plant_xyz/linumert_plant.hal`, embedded DRIVER w
`plant/server/linumert_plant/scenario_linuxcnc.py`.

## Poprawka runnera

Po ON runner czeka maksymalnie 5 s na piny `lrt-cia402.0…3.enabled` wszystkich
czterech napędów tej konfiguracji. Dopiero potem zaczyna home. Brak gotowości
kończy driver jawnym błędem przed bazowaniem; to samo obowiązuje istniejący retry.
Diagnostyka zachowuje DRIVES_READY z wynikiem i monotonicznym czasem odbioru.
Bez zmian Plant, masy, czasu rozruchu, regulatorów, ramp, progów, liczby retry
ani konfiguracji operatora. Nie jest to nowe zabezpieczenie sprzętowe ani
ogólny interlock ruchu w HMI — dotyczy wyłącznie tego runnera scenariuszy.

## Weryfikacja i incydent

- 24 testy bez LinuxCNC PASS (readiness, diagnostics, trace), ruff PASS w Debianie.
- Cztery przypadki opóźnionej gotowości sprawdzają każdy napęd osobno. Task ON
  pojawia się od razu, a driver czeka na ostatni napęd. Trwały brak gotowości
  kończy rzeczywiste instrukcje startowe drivera błędem przed wywołaniem home.
- Pierwsze polecenie testowe błędnie nie zawierało `-m "not linuxcnc"` i wybrało
  również test live samplera, mimo aktywnej blokady Claude „033”. Guard leftovers
  trafił w przerwę między jego procesami; test wystartował bez wspólnej blokady.
  To błąd Codexa, zgłoszony natychmiast w Dla Claude. Driver zapisał DRIVES_READY
  true (0,58485 s), następnie KeyboardInterrupt podczas home. **Ta próba jest
  nieważnym odbiorem**, nie PASS ani dowód przyczyny przerwania. Mogła zakłócić
  przebieg Claude. Nie przejmowano ani nie zwalniano jego blokady.
- Dowody incydentu: `/tmp/pytest-of-codex/pytest-123/test_servo_trace_with_real_sam0/evidence/`.
  Wynik pierwszego polecenia: 24 unit PASS / 1 live FAIL. Kolejne polecenie z
  `-m "not linuxcnc"`: 24 PASS / 1 deselected w 0,24 s. Nie uruchamiano następnej instancji.

Przed scaleniem wymagane CI dla właściwego SHA i odbiór w odrębnym środowisku CI
lub celowany first_motion ze śladem dopiero po uzyskaniu wspólnej blokady.
Oczekiwany dowód: gotowość wszystkich napędów poprzedza pierwsze zadanie Z,
pierwsze bazowanie bez retry, program przechodzi istniejące kryteria.
G1, dziesięć kolejnych PASS, RT, pulpit i sprzęt pozostają otwarte.

Dodany test `test_first_home_after_drive_readiness` ma marker linuxcnc i wymaga
pierwszego bazowania bez retry oraz pustego setup_errors. Nie uruchamiano go
lokalnie. Ostatni zestaw jednostkowy kodu `f85bcd7`: 24 PASS / 2 live deselected,
lint/roadmap i pokrycie 22/22 REQ PASS. To nadal nie zastępuje wyniku testu live.

## Końcowy odbiór w CI — d223909

Po opisanym wyżej nieważnym przebiegu lokalnym wykonano niezależny przebieg
w środowisku CI dla `d223909716b5aa51c7d152d1ae30f8a26754e77f`.
[LinuxCNC job 121128248228](https://github.com/anonimov94/linumeRT/actions/runs/40179788254/job/121128248228)
zakończył się SUCCESS; zestaw live: **147 PASS**, bez pominięcia nowych testów.
`test_first_home_after_drive_readiness` PASS (09:31:08 UTC) oraz
`test_servo_trace_with_real_sampler` PASS (09:31:21 UTC).

Test pierwszego bazowania wymaga jednocześnie ukończenia programu, wszystkich
kryteriów scenariusza, pustego setup_errors, gotowości wszystkich napędów oraz
dokładnie jednego wywołania machine_on — pierwszego bazowania bez retry.
To dowód usunięcia wykazanego braku oczekiwania na gotowość w tym runnerze;
nie odbiór ogólnego interlocka HMI, historycznego uchybu X ani całej bramki G1.
Model, czas rozruchu Z, rampy, progi i liczba dostępnych retry pozostały bez zmian.
Incydent lokalny pozostaje nieważnym wynikiem i nie jest zastępowany deklaracją PASS.

Kontrole python i plant-matrix dla tego samego HEAD również SUCCESS.
Po scaleniu zależności #141 (`890c399`) PR #142 skierowano na main i scalono jako
`c0281596a54a6911b344edf8709edabed8748090`; zdalny main zweryfikowany.
Następne otwarte kryterium: historyczny uchyb X 0,3 mm, potem wymagana seria
10 kolejnych PASS; GUI/heartbeat, VirtualBox, RT i sprzęt nadal otwarte.
