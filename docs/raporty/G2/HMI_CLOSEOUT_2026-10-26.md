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


## Domknięcie zleconych trzech grup

1. Układ 1280×768: szyna, przygotówka, dolne karty HMI, znak i kody alarmów.
   Cztery rodziny mieszczą karty bez przewijania całej strony; treści formularzy
   nadal przewijają się we własnym panelu.
2. Cyberdeck: dwa prostokątne podglądy pod nakładką. Detal z narzędziem i
   poglądowy model XYZ korzystają ze wspólnej sceny Neon. To renderer QPainter,
   nie deklaracja modelu kolizji Plant ani nowego renderera pyqtgraph.
3. Monitor: źródło rzeczywistego programu i aktywna linia, rzeczywisty posuw toru,
   zadane obroty, T/D/offset Z tabeli; brak danych i utrata statusu jawne.

Wyniki z LinuxCNC (kod monitora ee722b6, host/samotest 6b82b95):
- AUTO zakończone; pauza: linia 59 = 59, DTG 3,230968241 mm = 3,230968241 mm,
  DRO zgodne z NML. T1, D6 mm, L0 mm, zadane S12000; źródło programu widoczne.
- Trzy presety: detal 2,95 / 3,66 / 4,31 ms; maszyna 2,96 / 3,06 / 3,55 ms.
- Osadzony Cyberdeck 1280×768: 45 kroków PASS w 61,22 s. Pierwsza próba ujawniła
  założenie samotestu o aktywnym Start; po jawnym kliknięciu Start scenariusz PASS.
  Nie zmieniano interlocków.
- Qt/IP: 218 PASS, 101 subtestów PASS, 1 SKIP, 6 testów live poza tym wywołaniem.
  GL Mesa: 160 kombinacji rozmiarów/rodzin/motywów/języków PASS.
- Fixture Plant: 1 live PASS w 133,88 s; endpoint ustalony po 1,053 s,
  [100.0000, 199.9977, -20.0000] mm, peak f-error 0,19263 mm, errors_motion puste.
  Zainstalowany LinuxCNC, istniejące helpery RIP uruchomione przez adapter ścieżek
  wskazujący rzeczywiste binaria/moduły systemowe; nie nazywamy tego budową RIP.
  Ciągła tolerancja 5 µm przez 0,2 s; bez zmiany modelu, ramp, tolerancji lub limitu 60 s.

Dowody: [start](HMI_CLOSEOUT_2026-10-26/01-start.png),
[środek](HMI_CLOSEOUT_2026-10-26/02-srodek.png),
[koniec](HMI_CLOSEOUT_2026-10-26/03-koniec.png),
[wyniki i hashe](HMI_CLOSEOUT_2026-10-26/results.json).
Próba monitora zapisała ostrzeżenie QProcess przy wyjściu; skrypt odbioru teraz
zamyka monitor przed LinuxCNC. Nie wpływało to na porównanie NML ani ukończenie programu.
Wymagane kontrole CI dla e9ed723 zakończone SUCCESS; PR #169 scalony jako 3c20817.
Nie zamykamy całego 028/SKIN-02…06 ani odbioru pulpitu właściciela.


## Końcowy wynik CI

[LinuxCNC run40293747003](https://github.com/anonimov94/linumeRT/actions/runs/40293747003):
1542 PASS, 184 subtesty PASS (11 SKIP, 154 deselected), następnie 154 testy live PASS.
Osobne wczesne kroki: start prawdziwego QtVCP/Plant 2 PASS i samotest numeryczny 1 PASS.
`test_cyberdeck_host_selftest_in_gui` i `test_plant_linuxcnc_home_and_move` PASS.
Cała kontrola trwała 50 min 6 s, w tym live 38 min 14 s.
[Python i macierz Plant run40293746655](https://github.com/anonimov94/linumeRT/actions/runs/40293746655):
1407 PASS, 114 SKIP, REQ 22/22, testy C oraz plant-matrix SUCCESS.
Autokontrola, bez niezależnego przeglądu; odbiór pulpitu i sprzętu pozostaje odrębny.
