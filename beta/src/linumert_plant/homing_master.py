"""Atrapa mastera bazowania w stylu LinuxCNC dla testów i scenariuszy Plant (REQ-VM-07).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 015.

Master widzi maszynę tak jak LinuxCNC przez LRT-NET: wejścia cyfrowe, pozycję rzeczywistą
napędu w impulsach (6064h), moment (6077h), słowo stanu i licznik indeksu. Nie zna prawdziwego
położenia osi. Skala impulsy/jednostkę (`MachineModel.counts_per_unit`) odpowiada SCALE z INI.

Sekwencje (`homing.method` z machine.yaml):
  switch        szukanie czujnika z search_speed, potem strategia `homing.latch`:
                approach — zjazd z latch_speed, ponowny dojazd z latch_speed do zadziałania
                = baza (HOME_SEARCH_VEL i HOME_LATCH_VEL z tym samym znakiem);
                release — wolny zjazd z latch_speed, baza na zwolnieniu styku (dla NC:
                zbocze narastające, obwód znów zamknięty; HOME_LATCH_VEL ze znakiem przeciwnym);
  switch_index  jak switch, potem z latch_speed od czujnika (kierunek zjazdu) do impulsu
                indeksu (HOME_USE_INDEX). Po zadziałaniu czujnika master zawsze zawraca:
                jazda dalej za krańcówkę groziłaby uderzeniem w zderzak.
  hardstop      jak switch, ale „czujnik” to zderzak wykryty przez moment albo błąd nadążania
                (`HardstopDetector`, ta sama logika co hal/lrt_hardstop_home.comp) przy
                zredukowanym limicie momentu 6072h; po bazie limit wraca do wartości z napędu;
  absolute      bez ruchu: enkoder absolutny już zna pozycję (HOME_ABSOLUTE_ENCODER = 2);
                awaria E-4211 albo nieważna pozycja = błąd bazowania;
  drive         tryb 6 w napędzie (6098h z `cia402_method`), master czeka na bity 10 i 12.
Gantry z `gantry_square`: każdy napęd bazuje na swoim czujniku, więc belka się wyrównuje.
Baza: pozycja zatrzaśnięta staje się `homing.offset`; master pamięta przesunięcie w impulsach
(jak LinuxCNC w motor-offset), poza metodą drive, gdzie robi to napęd (607Ch).
NIEZWERYFIKOWANE z LinuxCNC: porównanie z prawdziwym homemod robi sesja 018.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from linumert.machine.schema import Axis

from .core_binding import (
    CW_ENABLE,
    CW_HOMING_START,
    MODE_CSP,
    MODE_HOMING,
    SW_HOMING_ATTAINED,
    SW_HOMING_ERROR,
    SW_TARGET_REACHED,
    PlantMachine,
)

MASTER_PERIOD = 1e-3     # okres wątku servo LinuxCNC [s]
STEPPER_DT = 1e-4        # krok Plant dla krokowców bez sprzężenia (drive.h)
SEARCH_RANGE = 1.5       # szukanie czujnika najwyżej na 1,5 długości przejazdu


class HomingError(RuntimeError):
    """Bazowanie nie powiodło się (komunikat po polsku z nazwą osi)."""


def _input_is_nc(axis: Axis, name: str) -> bool:
    """Styk NC na wejściu `name` (krańcówka albo czujnik osi; `<nazwa>_2` jak `<nazwa>`)."""
    base = name.removesuffix("_2")
    for sw in (axis.limits.min, axis.limits.max):
        if sw is not None and sw.input == base:
            return sw.contact == "NC"
    sensor = axis.home_sensor
    return sensor is not None and sensor.input == base and sensor.contact == "NC"


def _trapezoid(start: float, target: float, speed: float, accel: float) -> list[float]:
    """Pozycje co okres mastera dla profilu trapezowego (krokowiec nie zgubi kroków)."""
    distance = abs(target - start)
    sign = 1.0 if target >= start else -1.0
    v = min(speed, (distance * accel) ** 0.5)  # trójkąt, gdy droga krótka
    t_acc = v / accel if accel > 0 else 0.0
    d_acc = 0.5 * accel * t_acc * t_acc
    t_total = 2 * t_acc + ((distance - 2 * d_acc) / v if v > 0 else 0.0)
    out = []
    n = max(1, round(t_total / MASTER_PERIOD))
    for k in range(1, n + 1):
        t = t_total * k / n
        if t < t_acc:
            s = 0.5 * accel * t * t
        elif t > t_total - t_acc:
            r = t_total - t
            s = distance - 0.5 * accel * r * r
        else:
            s = d_acc + v * (t - t_acc)
        out.append(start + sign * s)
    return out


class HardstopDetector:
    """Zderzak jako czujnik: |wartość| >= próg nieprzerwanie przez czas `time_s`.

    Ta sama logika jest w hal/lrt_hardstop_home.comp (strona LinuxCNC).
    """

    def __init__(self, threshold: float, time_s: float):
        if threshold <= 0 or time_s < 0:
            raise ValueError("próg > 0 i czas >= 0")
        self.threshold = threshold
        self.time_s = time_s
        self.timer = 0.0

    def update(self, value: float, dt: float) -> bool:
        self.timer = self.timer + dt if abs(value) >= self.threshold else 0.0
        return self.timer >= self.time_s


@dataclass
class DriveHoming:
    """Wynik bazowania jednego napędu."""

    drive: str
    zero_counts: int = 0       # impulsy odpowiadające pozycji osi 0 (po bazie)
    latch_counts: int = 0      # pozycja raportowana w chwili zatrzaśnięcia
    homed: bool = False


@dataclass
class AxisHoming:
    letter: str
    method: str
    drives: dict[str, DriveHoming] = field(default_factory=dict)
    time: float = 0.0


class _Homer:
    """Maszyna stanów jednego napędu (metody switch, switch_index, hardstop)."""

    def __init__(self, master: HomingMaster, axis: Axis, drive: str):
        self.m = master.machine
        self.axis = axis
        self.drive = drive
        self.scale = self.m.model.counts_per_unit[drive]
        h = axis.homing
        self.dir = h.direction
        self.search = h.search_speed
        self.latch = h.latch_speed
        self.accel = axis.max_acceleration
        self.cmd = self.m.position_actual(drive) / self.scale  # [jedn. osi], ramka napędu
        self.vel = 0.0
        self.goal = 0.0
        self.phase = "search"
        self.travelled = 0.0
        self.limit = SEARCH_RANGE * abs(axis.travel[1] - axis.travel[0])
        self.result = DriveHoming(drive)
        self.index_seen = self.m.index_count(drive)
        self.detector: HardstopDetector | None = None
        self.input_name = self.m.model.drive_home_inputs.get(drive, "")
        self.nc = _input_is_nc(axis, self.input_name)
        if h.method == "hardstop":
            # Próg momentu w promilach znamionowego; błędu nadążania w jednostkach osi.
            self.detector = HardstopDetector(h.detect_threshold or 0.0,
                                             (h.detect_time_ms or 0.0) / 1000.0)
            self.saved_limit = self.m.od_read(drive, 0x6072)
            self.m.od_write(drive, 0x6072, round((h.reduced_torque_pct or 100.0) * 10.0))
        elif not self.input_name:
            raise HomingError(f"oś {axis.letter}, napęd {drive}: brak wejścia czujnika bazy "
                              "u mastera (gantry: dodaj wejście <nazwa>_2 w io.inputs)")
        self.sensor = self._sensor(MASTER_PERIOD)
        if self.sensor:
            self.phase, self.goal = "backoff", -self.dir * self.latch  # start na czujniku
        else:
            self.goal = self.dir * self.search

    def _sensor(self, dt: float) -> bool:
        if self.detector is None:
            return self.m.input(self.input_name) != self.nc  # NC: aktywny = obwód otwarty
        h = self.axis.homing
        if h.detect == "torque":
            value = self.m.torque_actual(self.drive)
        else:
            value = self.cmd - self.m.position_actual(self.drive) / self.scale
        return self.detector.update(value, dt)

    def _set_home(self) -> None:
        actual = self.m.position_actual(self.drive)
        self.result.latch_counts = actual
        self.result.zero_counts = actual - round(self.axis.homing.offset * self.scale)
        self.result.homed = True
        self.cmd = actual / self.scale  # zatrzymanie w miejscu zatrzaśnięcia
        self.vel = self.goal = 0.0
        if self.detector is not None:
            self.m.od_write(self.drive, 0x6072, self.saved_limit)
        self.phase = "done"

    def update(self, dt: float) -> None:
        if self.phase == "done":
            return
        sensor = self._sensor(dt)
        if self.phase == "search" and sensor:
            self.phase, self.goal = "backoff", -self.dir * self.latch
            if self.detector is not None:
                self.cmd = self.m.position_actual(self.drive) / self.scale  # bez docisku
                self.vel = 0.0
        elif self.phase == "backoff" and not sensor and self.vel * self.dir < 0:
            if self.axis.homing.latch == "approach":
                self.phase, self.goal = "latch", self.dir * self.latch
            elif self.axis.homing.method == "switch_index":
                self.phase = "index"  # dalej w kierunku zjazdu, od czujnika
                self.index_seen = self.m.index_count(self.drive)
            else:
                self._set_home()  # zwolnienie styku = baza
                return
        elif self.phase == "latch" and sensor:
            if self.axis.homing.method == "switch_index":
                self.phase, self.goal = "index", -self.dir * self.latch
                self.index_seen = self.m.index_count(self.drive)
            else:
                self._set_home()
                return
        elif self.phase == "index" and self.m.index_count(self.drive) != self.index_seen:
            self._set_home()
            return
        dv = self.accel * dt
        self.vel = min(self.vel + dv, self.goal) if self.vel < self.goal else \
            max(self.vel - dv, self.goal)
        self.cmd += self.vel * dt
        self.travelled += abs(self.vel) * dt
        if self.travelled > self.limit:
            raise HomingError(f"oś {self.axis.letter}, napęd {self.drive}: nie znaleziono "
                              f"czujnika bazy w fazie {self.phase}")
        self.m.set_target(self.drive, round(self.cmd * self.scale))


class HomingMaster:
    """Bazowanie osi wirtualnej maszyny tak, jak robi to LinuxCNC (atrapa mastera)."""

    def __init__(self, machine: PlantMachine, plant_dt: float | None = None):
        self.machine = machine
        steppers = any(e == 0 for e in machine.model.encoders.values())
        self.plant_dt = plant_dt or (STEPPER_DT if steppers else MASTER_PERIOD)
        self.substeps = max(1, round(MASTER_PERIOD / self.plant_dt))
        self.results: dict[str, AxisHoming] = {}

    def _axis(self, letter: str) -> Axis:
        cfg = self.machine.model.config
        assert cfg is not None
        return next(a for a in cfg.axes if a.letter == letter)

    def tick(self) -> None:
        """Jeden okres mastera (kilka kroków Plant)."""
        self.machine.step_cycle(self.plant_dt * self.substeps, self.substeps)

    def hold(self, letter: str) -> None:
        for drive in self.machine.model.joint_drives[letter]:
            self.machine.hold_position(drive)

    def home_axis(self, letter: str, timeout: float = 120.0) -> AxisHoming:
        """Bazuje oś `letter` (wszystkie jej napędy równolegle); HomingError przy błędzie."""
        axis = self._axis(letter)
        method = axis.homing.method
        result = AxisHoming(letter, method)
        start = self.machine.time
        drives = self.machine.model.joint_drives[letter]
        if not axis.homing.gantry_square and len(drives) > 1 and method != "absolute":
            drives_to_home = drives[:1]  # belka bez wyrównania: jedna strona prowadzi
        else:
            drives_to_home = drives
        if method == "absolute":
            for drive in drives:
                state = self.machine.absolute_state(drive)
                if self.machine.drive_state(drive) == "FAULT" or state is None or not state[1]:
                    raise HomingError(f"oś {letter}, napęd {drive}: pozycja enkodera "
                                      "absolutnego nieważna (E-4211) — wymagane ustawienie bazy")
                result.drives[drive] = DriveHoming(drive, zero_counts=0, homed=True,
                                                   latch_counts=self.machine.position_actual(drive))
        elif method == "drive":
            self._home_in_drives(letter, drives, result, timeout)
        else:
            homers = [_Homer(self, axis, d) for d in drives_to_home]
            followers = [d for d in drives if d not in drives_to_home]
            while any(h.phase != "done" for h in homers):
                for h in homers:
                    h.update(MASTER_PERIOD)
                for d in followers:  # druga strona belki jedzie za pierwszą
                    lead = homers[0]
                    self.machine.set_target(d, round(lead.cmd * self.machine.model.
                                                     counts_per_unit[d]))
                self.tick()
                if self.machine.time - start > timeout:
                    raise HomingError(f"oś {letter}: przekroczony czas bazowania")
            for h in homers:
                result.drives[h.drive] = h.result
            for d in followers:
                lead = homers[0].result
                result.drives[d] = DriveHoming(d, zero_counts=lead.zero_counts,
                                               latch_counts=lead.latch_counts, homed=True)
        result.time = self.machine.time - start
        self.results[letter] = result
        return result

    def _home_in_drives(self, letter: str, drives: list[str], result: AxisHoming,
                        timeout: float) -> None:
        m = self.machine
        for d in drives:
            m.set_mode(d, MODE_HOMING)
            m.set_controlword(d, CW_ENABLE)
        self.tick()
        for d in drives:
            m.set_controlword(d, CW_ENABLE | CW_HOMING_START)
        start = m.time
        done = set()
        while len(done) < len(drives):
            self.tick()
            for d in drives:
                word = m.statusword(d)
                if word & SW_HOMING_ERROR:
                    raise HomingError(f"oś {letter}, napęd {d}: błąd bazowania w napędzie "
                                      f"(metoda {m.od_read(d, 0x6098)}, E-4210)")
                if word & SW_HOMING_ATTAINED and word & SW_TARGET_REACHED:
                    done.add(d)
            if m.time - start > timeout:
                raise HomingError(f"oś {letter}: napęd nie zakończył bazowania w czasie")
        for d in drives:
            m.set_controlword(d, CW_ENABLE)
            m.set_mode(d, MODE_CSP)
            m.hold_position(d)
            result.drives[d] = DriveHoming(d, zero_counts=0, homed=True,
                                           latch_counts=m.position_actual(d))

    def set_absolute_home(self, letter: str) -> None:
        """Enkoder absolutny: bieżące położenie staje się `homing.offset` (uruchomienie maszyny
        albo po utracie baterii). Napęd robi to metodą 35 w trybie 6, licznik znów ważny."""
        axis = self._axis(letter)
        m = self.machine
        for d in m.model.joint_drives[letter]:
            m.od_write(d, 0x6098, 35)
            m.od_write(d, 0x607C, round(axis.homing.offset * m.model.counts_per_unit[d]))
        saved = axis.homing.method
        try:
            self._home_in_drives(letter, m.model.joint_drives[letter], AxisHoming(letter, saved),
                                 timeout=1.0)
        finally:
            self.results.pop(letter, None)

    def home_all(self, timeout: float = 300.0) -> dict[str, AxisHoming]:
        """Bazuje wszystkie osie według `homing.order` (jak HOME_SEQUENCE)."""
        cfg = self.machine.model.config
        assert cfg is not None
        for axis in sorted(cfg.axes, key=lambda a: a.homing.order):
            self.home_axis(axis.letter, timeout)
        return self.results

    # ---- po bazowaniu --------------------------------------------------------------------
    def position(self, letter: str) -> float:
        """Pozycja osi w układzie mastera po bazowaniu (średnia stron gantry)."""
        result = self.results[letter]
        values = [(self.machine.position_actual(d) - r.zero_counts) /
                  self.machine.model.counts_per_unit[d] for d, r in result.drives.items()]
        return sum(values) / len(values)

    def move(self, letter: str, target: float, speed: float) -> None:
        """Jazda osi zbazowanej do pozycji mastera (wszystkie napędy razem)."""
        result = self.results[letter]
        start = self.position(letter)
        for p in _trapezoid(start, target, speed, self._axis(letter).max_acceleration):
            for d, r in result.drives.items():
                scale = self.machine.model.counts_per_unit[d]
                self.machine.set_target(d, r.zero_counts + round(p * scale))
            self.tick()
        for _ in range(300):
            self.tick()
