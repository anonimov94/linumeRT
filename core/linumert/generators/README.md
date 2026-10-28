# CAM 2D

Czyste generatory G-code; żadnych poleceń do LinuxCNC ani importów UI/Plant.
Kontrakt: base.BaseMacroGenerator, Field, Issue. Rejestr: nazwa + wersja.
Stare wersje muszą pozostać odtwarzalne dla istniejących .lnx.
CLI buduje jawny rejestr w linumert.cli.registry(). Testy: test_gen_*.py.
