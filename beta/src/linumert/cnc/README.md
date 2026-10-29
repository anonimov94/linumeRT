# linumert.cnc

Warstwa dostepu do LinuxCNC (linuxcnc.command/stat) z atrapa do testow bez LinuxCNC.

| Moduł | Zawartość |
|---|---|
| `model.py` | niezmienna migawka stanu maszyny (sesja 006) |
| `linuxcnc_reader.py` | czytnik `linuxcnc.stat` (moduł wstrzykiwany, działa bez LinuxCNC w testach) |
| `fake.py` | atrapa z wirtualnym zegarem do testów |

Opis: `docs/RDZEN.md`.
