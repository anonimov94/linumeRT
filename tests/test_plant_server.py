"""Serwer LRT-NET Plant: pętla zwrotna UDP, watchdog, odporność i determinizm (sesja 016).

Model-Author: Claude

Testy z rdzeniem C wymagają kompilatora (Linux/WSL), inaczej są pomijane. Testy CLI z błędną
konfiguracją działają bez rdzenia (Plant nie startuje przed zbudowaniem modelu).
NIEZWERYFIKOWANE z LinuxCNC (komponent lrt_net w sesji 017) i na sprzęcie.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import yaml
from linumert_plant.__main__ import main as plant_main
from linumert_plant.lrtnet import FLAG_FAULT
from linumert_plant.server import PlantConfig, PlantConfigError, PlantServer, load_plant_config
from linumert_plant.test_master import Master, drive_state
from linumert_plant.trace import TraceWriter

ROOT = Path(__file__).resolve().parents[1]
MACHINE = ROOT / "config" / "machines" / "mill_servo_table.yaml"
WATCHDOG_CODE = 0x8130  # 603Fh awarii COMM_WATCHDOG (E-4003)


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")
    return core_binding


def _server(core, seed: int = 1, **cfg) -> PlantServer:
    from linumert_plant.build_machine import build_machine

    machine = core.PlantMachine(build_machine(MACHINE, seed=seed))
    return PlantServer(machine, PlantConfig(seed=seed, **cfg))


def _local(server: PlantServer) -> Master:
    return Master(len(server.drives), transport=server.handle)


def _scripted_run(server: PlantServer) -> Master:
    master = _local(server)
    master.enable()
    master.move(0, 40_000, 200_000.0, 2_000_000.0)
    master.move(3, -20_000, 100_000.0, 1_000_000.0)
    for _ in range(100):
        master.exchange()
    return master


# ---- pętla zwrotna UDP -----------------------------------------------------------------------

def test_lockstep_10000_frames_udp_without_loss(core) -> None:
    server = _server(core)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    thread = threading.Thread(target=server.serve, args=(sock, 10_000), daemon=True)
    thread.start()
    master = Master(len(server.drives), port=port, timeout=2.0)
    try:
        sent = master.enable()
        start = master.axes[0].target_pos
        sent += master.move(0, 50_000, 200_000.0, 2_000_000.0)
        while master.seq <= 10_000:
            master.exchange()
    finally:
        master.close()
        thread.join(timeout=10)
        sock.close()
    assert not thread.is_alive()
    s = server.stats
    assert (s.received, s.rejected, s.lost, s.late, master.timeouts) == (10_000, 0, 0, 0, 0)
    assert s.steps == 10_000
    rep = master.last
    assert rep.frames_lost == 0 and rep.frames_late == 0 and rep.jitter_us == 0
    assert all(drive_state(a.statusword) == "OPERATION_ENABLED" for a in rep.axes)
    assert rep.axes[0].actual_pos == pytest.approx(start + 50_000, abs=20)
    assert abs(rep.axes[0].following_error) < 20


def test_lost_and_late_frames_are_counted(core) -> None:
    server = _server(core)
    master = _local(server)
    master.enable()
    t0 = server.machine.time
    master.seq += 4  # luka: 4 ramki utracone
    master.exchange()
    assert server.stats.lost == 4 and master.last.frames_lost == 4
    master.seq -= 1  # powtórzona ramka: bez kroku modelu
    master.time_ns -= master.cycle_ns
    t1 = server.machine.time
    master.exchange()
    assert server.stats.late == 1 and server.machine.time == t1 > t0


def test_reset_stats_flag(core) -> None:
    server = _server(core)
    master = _local(server)
    master.exchange()
    master.seq += 2
    master.exchange()
    assert server.stats.lost == 2
    master.exchange(flags=1)
    assert server.stats.lost == 0 and master.last.frames_lost == 0


def test_outputs_and_inputs_pass_through(core) -> None:
    server = _server(core)
    master = _local(server)
    master.digital_out = 0b101
    master.exchange()
    assert server.machine.outputs == 0b101
    # estop_b (kanał B E-STOP) = kopia kanału A; reszta bitów jak w modelu C
    b = server.machine.model.inputs.get("estop_b")
    expected = server.machine.inputs
    if b is not None:
        expected |= (server.machine.inputs >> server.machine.model.inputs["estop"] & 1) << b
    assert master.last.digital_in == expected


def test_mode_zero_and_unsupported_mode_do_not_stop_plant(core) -> None:  # REQ-QA-03
    """Pierwszy cykl mastera HAL może nieść 6060h = 0; tryb spoza modelu jest odrzucany."""
    server = _server(core)
    master = _local(server)
    for axis in master.axes:
        axis.mode = 0
    master.exchange()
    master.axes[0].mode = 3  # profil prędkości: nieobsługiwany przez model napędu
    master.exchange()
    assert not server.model_failed
    assert server.mode_rejects >= 1
    for axis in master.axes:
        axis.mode = 8
    master.enable()
    assert master.states() == ["OPERATION_ENABLED"] * len(server.drives)


# ---- watchdog (docs/PLANT.md §3 reguła 4) ----------------------------------------------------

def test_watchdog_lockstep_faults_all_drives_until_reset(core) -> None:  # REQ-QA-03
    server = _server(core, watchdog_ms=50)
    master = _local(server)
    master.digital_out = 0b11
    master.enable()
    for _ in range(50):
        master.exchange()
    master.exchange(advance_ns=60_000_000)  # następna ramka po 61 ms
    master.exchange()
    rep = master.last
    assert server.watchdog_tripped
    assert all(drive_state(a.statusword) == "FAULT" for a in rep.axes)
    assert all(a.error_code == WATCHDOG_CODE for a in rep.axes)
    assert rep.flags & FLAG_FAULT and server.machine.outputs == 0
    assert any("E-4003" in m for m in server.messages)
    for _ in range(100):  # wznowienie ramek nie kasuje faultu
        master.exchange()
    assert all(drive_state(a.statusword) == "FAULT" for a in master.last.axes)
    assert server.machine.outputs == 0
    master.enable()  # fault reset + włączenie
    master.exchange()
    assert not server.watchdog_tripped and server.machine.outputs == 0b11
    assert not master.last.flags & FLAG_FAULT


def test_watchdog_realtime_without_frames(core) -> None:  # REQ-QA-03
    server = _server(core, mode="realtime", watchdog_ms=50)
    now = [1_000_000_000]

    def handle(frame: bytes) -> bytes | None:
        now[0] += 1_000_000
        return server.handle(frame, now[0])

    master = Master(len(server.drives), transport=handle)
    master.enable()
    assert not server.check_watchdog(now[0] + 40_000_000)
    assert server.check_watchdog(now[0] + 51_000_000)
    master.exchange()
    assert all(a.error_code == WATCHDOG_CODE for a in master.last.axes)


# ---- odporność (REQ-QA-03) -------------------------------------------------------------------

def test_corrupt_frames_rejected_process_keeps_running(core) -> None:  # REQ-QA-03
    server = _server(core)
    master = _local(server)
    master.enable()
    for junk in (b"", b"\x4c\x52garbage", bytes(56), bytes(range(200))):
        assert server.handle(junk) is None
    wrong_axes = Master(2, transport=server.handle)
    with pytest.raises(Exception, match="odrzucona"):
        wrong_axes.exchange()
    assert server.stats.rejected == 5
    master.exchange()
    assert all(drive_state(a.statusword) == "OPERATION_ENABLED" for a in master.last.axes)


def test_corrupt_frames_over_udp(core) -> None:  # REQ-QA-03
    server = _server(core)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve, args=(sock,), daemon=True)
    thread.start()
    master = Master(len(server.drives), port=sock.getsockname()[1], timeout=2.0)
    try:
        for _ in range(20):
            master.sock.sendto(b"\xff" * 40, master.addr)
        master.enable()
    finally:
        master.close()
        server.stop()
        thread.join(timeout=5)
        sock.close()
    assert server.stats.rejected == 20 and server.stats.lost == 0


def test_model_exception_gives_safe_state(core, monkeypatch) -> None:  # REQ-QA-03
    server = _server(core)
    master = _local(server)
    master.digital_out = 0b1
    master.enable()
    real_step = server.machine.step

    def broken(dt, n=1):
        raise RuntimeError("symulowany błąd modelu")

    monkeypatch.setattr(server.machine, "step_cycle", broken)
    master.exchange()
    rep = master.last
    assert server.model_failed and rep.flags & FLAG_FAULT
    assert all(a.statusword & 0x0008 and a.error_code == 0xFF00 for a in rep.axes)
    assert server.machine.outputs == 0
    assert any("E-4200" in m for m in server.messages)
    for _ in range(10):  # serwer nadal odpowiada
        master.exchange()
    real_step(1e-3)  # napędy naprawdę wyłączone (disable voltage)
    assert all(server.machine.drive_state(d) == "SWITCH_ON_DISABLED" for d in server.drives)


def _write_machine(tmp_path: Path, template: str) -> Path:
    data = yaml.safe_load(MACHINE.read_text(encoding="utf-8"))
    data["drives"][0]["template"] = template
    path = tmp_path / "machine.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_missing_template_refuses_start(tmp_path, capsys) -> None:  # REQ-QA-03
    machine = _write_machine(tmp_path, "brak_takiego_szablonu")
    assert plant_main(["serve", str(machine), "--lockstep", "--frames", "1"]) == 1
    err = capsys.readouterr().err
    assert "Plant nie wystartował" in err and "brak_takiego_szablonu" in err
    assert "Traceback" not in err


@pytest.mark.parametrize("text, field", [
    ("mode: turbo\n", "mode"),
    ("timing: {watchdog_ms: 0}\n", "timing.watchdog_ms"),
    ("timing: {cycle_ns: 5}\n", "timing.cycle_ns"),
    ("network: {port: 70000}\n", "network.port"),
    ("network: [1, 2]\n", "network"),
    ("timing: {substeps: abc}\n", "typ"),
    (": : :\n", "YAML"),
])
def test_bad_plant_yaml(tmp_path, text, field, capsys) -> None:  # REQ-QA-03
    path = tmp_path / "plant.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(PlantConfigError, match=field):
        load_plant_config(path)
    assert plant_main(["serve", str(MACHINE), "--plant", str(path)]) == 1
    assert "Plant nie wystartował" in capsys.readouterr().err


def test_plant_yaml_paths_relative(tmp_path) -> None:
    path = tmp_path / "plant.yaml"
    path.write_text("machine: m.yaml\nmode: realtime\ntiming: {watchdog_ms: 20, substeps: 4}\n"
                    "trace: {path: tr/a.jsonl, format: jsonl}\nseed: 9\n", encoding="utf-8")
    cfg = load_plant_config(path)
    assert cfg.machine == tmp_path / "m.yaml" and cfg.trace_path == tmp_path / "tr" / "a.jsonl"
    assert (cfg.mode, cfg.watchdog_ms, cfg.substeps, cfg.seed) == ("realtime", 20.0, 4, 9)


# ---- determinizm (REQ-QA-04) -----------------------------------------------------------------

def test_determinism(core) -> None:  # REQ-QA-04
    a = _server(core, seed=5)
    b = _server(core, seed=5)
    c = _server(core, seed=6)
    for server in (a, b, c):
        _scripted_run(server)
    assert a.digest == b.digest
    assert a.digest != c.digest  # inne ziarno = inny start losowy osi


def test_substeps_change_nothing_in_protocol(core) -> None:
    server = _server(core, substeps=4)
    master = _scripted_run(server)
    assert master.last.axes[0].actual_pos != 0
    assert server.stats.steps == server.stats.received


# ---- ślad w osobnym wątku --------------------------------------------------------------------

@pytest.mark.parametrize("fmt", ["csv", "jsonl"])
def test_trace_written_in_thread(core, tmp_path, fmt) -> None:
    server = _server(core)
    path = tmp_path / f"trace.{fmt}"
    server.trace = TraceWriter(path, server.drives, fmt)
    master = _local(server)
    for _ in range(300):
        master.exchange()
    server.trace.close()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert server.trace.dropped == 0 and server.trace.written == 300
    if fmt == "csv":
        assert lines[0].startswith("seq,time_ns,drv_x.statusword") and len(lines) == 301
        assert lines[-1].split(",")[0] == "300"
    else:
        assert len(lines) == 300 and '"drv_z"' in lines[0]


def test_trace_rejects_unknown_format(tmp_path) -> None:
    with pytest.raises(ValueError, match="format"):
        TraceWriter(tmp_path / "x", ["a"], "npz")


# ---- proces serwera z wiersza poleceń --------------------------------------------------------

def test_serve_cli_process(core, tmp_path) -> None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    trace = tmp_path / "t.csv"
    env_path = f"{ROOT / 'core'}:{ROOT / 'plant' / 'server'}"
    proc = subprocess.Popen(
        [sys.executable, "-m", "linumert_plant", "serve", str(MACHINE), "--lockstep",
         "--port", str(port), "--frames", "2000", "--trace", str(trace)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={"PYTHONPATH": env_path, "PATH": "/usr/bin:/bin"})
    try:
        line = proc.stdout.readline()
        assert "lockstep" in line, line + proc.stderr.read()
        master = Master(4, port=port, timeout=5.0)
        master.enable()
        while master.seq <= 2000:
            master.exchange()
        master.close()
        out, err = proc.communicate(timeout=20)
    finally:
        proc.kill()
    assert proc.returncode == 0, err
    assert "ramki 2000, odrzucone 0, utracone 0" in out and "SHA-256" in out
    assert len(trace.read_text(encoding="utf-8").splitlines()) == 2001


def test_example_plant_yaml_loads() -> None:
    cfg = load_plant_config(ROOT / "config" / "plant" / "plant.example.yaml")
    assert cfg.machine.resolve() == MACHINE.resolve() and cfg.mode == "lockstep"
    assert cfg.trace_format == "csv" and cfg.port == 47700
