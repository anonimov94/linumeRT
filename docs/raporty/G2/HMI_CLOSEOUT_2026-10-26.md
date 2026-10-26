# HMI 028 — kontynuacja przekazania Claude

Model-Author: Codex · 2026-10-26. Autokontrola, bez niezależnego przeglądu.

Pierwsza porcja 9e2fec9: szyna w dwóch kolumnach na niskim ekranie, znak marki,
kody alarmów ze źródła i przygotówka bez poziomego przewijania. 9 testów Qt PASS.
Porcja f52c222: osadzone HMI korzysta z pasków QtVCP. 5 testów złożenia PASS:
cztery rodziny, 1280×768 → 1920×1080 → 1280×768, wszystkie karty widoczne.

Rzeczywisty LinuxCNC 2.9 w istniejącym kontenerze Debian 12, zwykły użytkownik
(`--userns keep-id`), `--init`, Xvfb 1280×768, programowe Mesa. Istniejący test
`test_shell_selftest_in_gui`: 1 PASS / 63,21 s, 45 kroków, strony tools/cycles=true.
Obie lease zwolnione. Próba uruchomienia kontenera jako root nie była odbiorem.

CI f52c222: python i plant-matrix PASS. Kontrola linuxcnc run40285964696:
start Plant/QtVCP oraz samotest numeryczny PASS; seria zbiorcza zawiera FAILED
home_and_move i została anulowana po przekroczeniu budżetu 35 min przy około 70%.
Nie jest to zielona kontrola; nie uznajemy tego za odbiór całego LinuxCNC.
Lokalne make lint PASS. Pełne make test w środowisku z zainstalowanym gcode
zakończyło się SIGSEGV w istniejącym simulation/linumert_sim/path.py:307,
przez test_sim_worker.py:47; test_sim_path także zgłosił FAIL. Zmiany HMI nie
dotykają tych modułów. Pełna seria offline w CI (bez gcode) jest zielona.
Surowe logi lokalne: build/hmi-closeout/{step1-checks,live-check}.log.

Odbiór pulpitu właściciela i sprzętu pozostaje odrębny.
NIEZWERYFIKOWANE NA SPRZĘCIE.
