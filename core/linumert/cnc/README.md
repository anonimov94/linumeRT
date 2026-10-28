# Dostęp do LinuxCNC

model.py: niezmienna migawka. linuxcnc_reader.py: odczyt stanu.
fake.py: atrapa do testów. headless.py: proces DISPLAY tylko do odczytu, sim/Plant.
Bez automatycznego resetu E-STOP, włączania maszyny lub podtrzymania bezpieczeństwa.
Testy: test_cnc_fake, test_cnc_reader, test_lite_cli.
