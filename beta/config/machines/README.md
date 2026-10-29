# config/machines

Przykladowe machine.yaml - jedno zrodlo prawdy dla Plant i LinuxCNC.

Pola dodane w sesji 014 (Plant, REQ-VM-02…05):
- `kinematics.chain[].branch`: `tool` (domyślnie) albo `workpiece` — gałąź łańcucha; człon o `id` równym
  literze osi jest napędzany tą osią, dziecko musi być w gałęzi rodzica.
- `axes[].hardstops.drive_fault`: `true` — wjazd w twardy zderzak daje też awarię napędu (E-4207).
  Sztywność i tłumienie zderzaków min i max muszą być równe (model osi ma jedną parę).
  Dla osi obrotowych `stiffness_n_mm`/`damping_ns_mm` oznaczają N·m/° i N·m·s/°.
- `io.estop.action`: `sto` (domyślnie) albo `quick_stop` — reakcja Plant na otwarcie pętli E-STOP.
- `probe`: sonda we wrzecionie — `input`, `contact` (domyślnie NO), `tip_length` [mm],
  `target: {type: box|plate, min, max}` w układzie detalu; płytka: kontakt poniżej `max.z` w obrysie XY.
- Numery `io.inputs`/`io.outputs` 0…31 (32 bity LRT-NET); pozycja startowa osi w Plant = środek soft limits.
