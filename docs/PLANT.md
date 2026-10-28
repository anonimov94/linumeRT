# Plant lite

Plant emuluje napędy i fizykę maszyny opisanej przez machine.yaml oraz wspólne szablony
w core/linumert/machine/drives/templates. Współpracuje z masterem przez LRT-NET UDP.
Nie zawiera HTTP ani GUI. Python wymaga kompilacji biblioteki plant/core/build/libplant_core.so.

Budowanie: make -C plant/core shared. Regresja C: make -C plant/core test.
CLI: linumert-plant machine build MACHINE.yaml --run oraz linumert-plant serve MACHINE.yaml.
Tryb lockstep: czas z ramek. Realtime: zegar hosta, bez kwalifikacji hard RT.
Scenariusze: python tools/run_scenario.py first_motion --no-report.
Macierz zachowanych pięciu konfiguracji: make plant-matrix.

Fizyka C oraz obsługa E-STOP/watchdog, bazowania i kolizji nie zostały uproszczone.
Obsługa istniejących magazynów i osi obrotowych służy regresji; nie oznacza obsługi
sprzętu ani generatora makr ATC w lite. NIEZWERYFIKOWANE NA SPRZĘCIE.

Moduły Python: server (UDP), core_binding (ctypes), build_machine (parametry C),
scenario (wykonanie testów), homing_master, faults, atc, collisions, trace.
Telemetria i desk są headless modelami danych. Editor jest backendem walidowanych
zmian konfiguracji używanym przez scenariusze; nie udostępnia serwera ani widoków.
