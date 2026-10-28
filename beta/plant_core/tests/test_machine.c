/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - testy maszyny Plant (machine.c): kinematyka, gantry, zderzaki, krancowki, I/O.
 * Model-Author: Claude · sesja 014
 * Wymagania: REQ-VM-02 (kinematyka), REQ-VM-03 (osie, gantry), REQ-VM-04 (zderzaki),
 * REQ-VM-05 (krancowki), REQ-VM-07 (start i bazowanie, sesja 015). Testy z maszynami z machine.yaml: tests/test_build_machine.py.
 */
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "../machine.h"
#include "lrt_test.h"

#define DT 1e-3
#define PI 3.14159265358979323846

static lrt_machine M; /* duza struktura: poza stosem */

static void set(lrt_machine_cfg *c, const char *key, double v)
{
    int rc = lrt_machine_cfg_set(c, key, v);
    if (rc != LRT_MACHINE_OK) {
        printf("#   klucz %s: %s\n", key, lrt_machine_strerror(rc));
    }
    LRT_CHECK(rc == LRT_MACHINE_OK);
}

static void setf(lrt_machine_cfg *c, const char *fmt, int i, double v)
{
    char key[64];
    snprintf(key, sizeof(key), fmt, i);
    set(c, key, v);
}

/* Maszyna XYZ: trzy serwa, os N = naped N, lancuch narzedzia X -> Y -> Z. */
static void cfg_xyz(lrt_machine_cfg *c)
{
    int j;

    lrt_machine_cfg_init(c);
    for (j = 0; j < 3; j++) {
        setf(c, "drive.%d.type", j, 0);
        setf(c, "mech.%d.kind", j, 0);
        setf(c, "joint.%d.drive0", j, j);
        setf(c, "link.%d.joint", j, j);
        setf(c, "link.%d.parent", j, j - 1);
        setf(c, "link.%d.ax", j, j == 0);
        setf(c, "link.%d.ay", j, j == 1);
        setf(c, "link.%d.az", j, j == 2);
    }
}

static int init_ok(const lrt_machine_cfg *c)
{
    int rc = lrt_machine_init(&M, c);
    if (rc != LRT_MACHINE_OK) {
        printf("#   init: %s (element %d, kod %d)\n", lrt_machine_strerror(rc), M.err_index,
               M.err_detail);
    }
    return rc == LRT_MACHINE_OK;
}

static void step_n(int n)
{
    int i;
    for (i = 0; i < n; i++) {
        int rc = lrt_machine_step(&M, DT);
        LRT_CHECK(rc == LRT_MACHINE_OK);
        if (rc != LRT_MACHINE_OK) {
            return;
        }
    }
}

/* Wlacza wszystkie napedy (CiA 402: shutdown -> switch on -> enable operation). */
static void enable_all(void)
{
    int s;
    int i;

    for (s = 0; s < M.c.n_drives; s++) {
        lrt_machine_set_target(&M, s, lrt_drive_position_actual(&M.slots[s].drive));
        lrt_machine_set_controlword(&M, s, LRT_CW_CMD_SHUTDOWN);
    }
    for (i = 0; i < 3000; i++) {
        int ready = 1;
        step_n(1);
        for (s = 0; s < M.c.n_drives; s++) {
            ready &= lrt_drive_get_state(&M.slots[s].drive) == LRT_DRIVE_READY_TO_SWITCH_ON;
        }
        if (ready) {
            break;
        }
    }
    for (s = 0; s < M.c.n_drives; s++) {
        lrt_machine_set_target(&M, s, lrt_drive_position_actual(&M.slots[s].drive));
        lrt_machine_set_controlword(&M, s, LRT_CW_CMD_SWITCH_ON);
    }
    step_n(2);
    for (s = 0; s < M.c.n_drives; s++) {
        lrt_machine_set_controlword(&M, s, LRT_CW_CMD_ENABLE_OPERATION);
    }
    step_n(2);
    for (s = 0; s < M.c.n_drives; s++) {
        LRT_CHECK(lrt_drive_get_state(&M.slots[s].drive) == LRT_DRIVE_OPERATION_ENABLED);
    }
}

/* ---- konfiguracja -------------------------------------------------------------------- */

static void test_cfg_rejects_bad_keys_and_values(void)
{
    lrt_machine_cfg c;

    lrt_machine_cfg_init(&c);
    LRT_CHECK(lrt_machine_cfg_set(&c, "drive.0.nieznane", 1.0) == LRT_MACHINE_ERR_KEY);
    LRT_CHECK(lrt_machine_cfg_set(&c, "bez_kropki", 1.0) == LRT_MACHINE_ERR_KEY);
    LRT_CHECK(lrt_machine_cfg_set(&c, "drive.x.kv", 1.0) == LRT_MACHINE_ERR_KEY);
    LRT_CHECK(lrt_machine_cfg_set(&c, "drive.13.kv", 1.0) == LRT_MACHINE_ERR_INDEX);
    LRT_CHECK(lrt_machine_cfg_set(&c, "joint.6.kind", 0.0) == LRT_MACHINE_ERR_INDEX);
    LRT_CHECK(lrt_machine_cfg_set(&c, "drive.0.type", 3.0) == LRT_MACHINE_ERR_VALUE);
    LRT_CHECK(lrt_machine_cfg_set(&c, "drive.0.following_window_ms", 1.5) ==
              LRT_MACHINE_ERR_VALUE);
    LRT_CHECK(lrt_machine_cfg_set(&c, "switch.0.side", 0.0) == LRT_MACHINE_ERR_VALUE);
    LRT_CHECK(lrt_machine_cfg_set(&c, "switch.0.input", 32.0) == LRT_MACHINE_ERR_VALUE);
    LRT_CHECK(lrt_machine_cfg_set(&c, "joint.0.initial", NAN) == LRT_MACHINE_ERR_VALUE);
    LRT_CHECK(lrt_machine_cfg_set(&c, "drive.0.kv", 0.5) == LRT_MACHINE_OK);
    LRT_CHECK(c.drives[0].drive.kv == 0.5);
    LRT_CHECK(lrt_machine_cfg_set(NULL, "drive.0.kv", 0.5) == LRT_MACHINE_ERR_NULL);
}

static void test_init_rejects_inconsistent_machines(void)
{
    lrt_machine_cfg c;

    /* REQ-VM-03: naped nieprzypisany do osi */
    cfg_xyz(&c);
    set(&c, "drive.3.type", 0);
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_JOINT);
    LRT_CHECK(M.err_detail == 3);

    /* REQ-VM-03: gantry bez dopuszczalnego rozjazdu */
    cfg_xyz(&c);
    set(&c, "drive.3.type", 0);
    set(&c, "joint.1.drive1", 3);
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_JOINT);
    set(&c, "joint.1.max_skew", 0.0005);
    LRT_CHECK(init_ok(&c));

    /* naped uzyty przez dwie osie */
    cfg_xyz(&c);
    set(&c, "joint.2.drive0", 0);
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_JOINT);

    /* REQ-VM-02: rodzic po dziecku i os bez czlonu */
    cfg_xyz(&c);
    set(&c, "link.0.parent", 2);
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_LINK);
    cfg_xyz(&c);
    set(&c, "link.2.joint", -1);
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_LINK);
    cfg_xyz(&c);
    set(&c, "link.1.kind", 1); /* czlon obrotowy na osi liniowej */
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_LINK);

    /* REQ-VM-05: NC i NO na jednym wejsciu */
    cfg_xyz(&c);
    set(&c, "switch.0.joint", 0);
    set(&c, "switch.0.input", 1);
    set(&c, "switch.1.joint", 1);
    set(&c, "switch.1.input", 1);
    set(&c, "switch.1.nc", 0);
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_IO);
    LRT_CHECK(M.err_index == 1);

    /* REQ-VM-04: zderzaki odwrocone */
    cfg_xyz(&c);
    set(&c, "joint.0.use_stops", 1);
    set(&c, "joint.0.stop_min", 0.1);
    set(&c, "joint.0.stop_max", -0.1);
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_JOINT);

    /* bledne parametry napedu sa zglaszane z kodem lrt_drive */
    cfg_xyz(&c);
    set(&c, "drive.1.counts_per_rev", 0);
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_DRIVE);
    LRT_CHECK(M.err_index == 1 && M.err_detail == LRT_DRIVE_ERR_RESOLUTION);
}

/* ---- kinematyka (REQ-VM-02) ---------------------------------------------------------- */

static void test_kin_xyz_tool_tip_equals_joints(void) /* REQ-VM-02 */
{
    lrt_machine_cfg c;
    double tip[3];

    cfg_xyz(&c);
    set(&c, "probe.type", 2);
    set(&c, "probe.input", 5);
    set(&c, "probe.tip_length", 0.05);
    set(&c, "probe.min_x", -1);
    set(&c, "probe.max_x", 1);
    set(&c, "probe.min_y", -1);
    set(&c, "probe.max_y", 1);
    set(&c, "probe.max_z", -0.2);
    LRT_CHECK(init_ok(&c));
    lrt_machine_set_joint_position(&M, 0, 0.1);
    lrt_machine_set_joint_position(&M, 1, 0.2);
    lrt_machine_set_joint_position(&M, 2, -0.03);
    lrt_machine_tool_tip(&M, 0, tip);
    LRT_CHECK_ABS(tip[0], 0.1, 1e-12);
    LRT_CHECK_ABS(tip[1], 0.2, 1e-12);
    LRT_CHECK_ABS(tip[2], -0.08, 1e-12);
}

/* Stol obrotowy A wokol X na galezi detalu, srodek obrotu (0, 0.1, 0.05). */
static void test_kin_rotary_table_transforms_tool_into_workpiece(void) /* REQ-VM-02 */
{
    lrt_machine_cfg c;
    double q[4] = {0.0, 0.1, 0.15, PI / 2};
    double w[3];
    double mpos[3];

    cfg_xyz(&c);
    set(&c, "drive.3.type", 0);
    set(&c, "mech.3.kind", 1);
    set(&c, "joint.3.kind", 1);
    set(&c, "joint.3.drive0", 3);
    set(&c, "link.3.kind", 1);
    set(&c, "link.3.joint", 3);
    set(&c, "link.3.branch", 1);
    set(&c, "link.3.ax", 1);
    set(&c, "link.3.az", 0);
    set(&c, "link.3.oy", 0.1);
    set(&c, "link.3.oz", 0.05);
    LRT_CHECK(init_ok(&c));
    LRT_CHECK(lrt_machine_forward(&c, q, 0.0, 0, mpos) == LRT_MACHINE_OK);
    LRT_CHECK_ABS(mpos[1], 0.1, 1e-12);
    LRT_CHECK_ABS(mpos[2], 0.15, 1e-12);
    /* narzedzie 0.1 nad srodkiem obrotu; stol obrocony o +90 st. wokol X: w ukladzie detalu
     * punkt lezy na +Y: R^T * (0, 0, 0.1) = (0, 0.1, 0) */
    LRT_CHECK(lrt_machine_forward(&c, q, 0.0, 1, w) == LRT_MACHINE_OK);
    LRT_CHECK_ABS(w[0], 0.0, 1e-12);
    LRT_CHECK_ABS(w[1], 0.1, 1e-12);
    LRT_CHECK_ABS(w[2], 0.0, 1e-12);
    q[3] = -PI / 2;
    lrt_machine_forward(&c, q, 0.0, 1, w);
    LRT_CHECK_ABS(w[1], -0.1, 1e-12);
    LRT_CHECK_ABS(w[2], 0.0, 1e-12);
    /* dlugosc narzedzia skraca punkt wzdluz -Z narzedzia */
    q[3] = 0.0;
    lrt_machine_forward(&c, q, 0.02, 1, w);
    LRT_CHECK_ABS(w[2], 0.08, 1e-12);
}

/* ---- gantry (REQ-VM-03) -------------------------------------------------------------- */

static void test_gantry_skew_alarm(void) /* REQ-VM-03 */
{
    lrt_machine_cfg c;

    cfg_xyz(&c);
    set(&c, "drive.3.type", 0);
    set(&c, "joint.1.drive1", 3);
    set(&c, "joint.1.max_skew", 0.0005);
    LRT_CHECK(init_ok(&c));
    lrt_machine_set_joint_position(&M, 1, 0.3);
    lrt_machine_set_drive_position(&M, 3, 0.3004); /* 0.4 mm: w granicy */
    step_n(1);
    LRT_CHECK_ABS(lrt_machine_joint_position(&M, 1), 0.3002, 1e-6);
    LRT_CHECK_ABS(lrt_machine_joint_skew(&M, 1), -0.0004, 1e-6);
    LRT_CHECK(!(lrt_machine_events(&M) & LRT_MACHINE_EV_GANTRY_SKEW));
    lrt_machine_set_drive_position(&M, 3, 0.3006); /* 0.6 mm: alarm */
    LRT_CHECK(lrt_machine_joint_events(&M, 1) & LRT_MACHINE_EV_GANTRY_SKEW);
    LRT_CHECK(!(lrt_machine_joint_events(&M, 0) & LRT_MACHINE_EV_GANTRY_SKEW));
}

static void test_gantry_skew_from_one_side_stalled(void) /* REQ-VM-03 */
{
    lrt_machine_cfg c;
    int i;

    cfg_xyz(&c);
    set(&c, "drive.3.type", 0);
    set(&c, "joint.1.drive1", 3);
    set(&c, "joint.1.max_skew", 0.0005);
    LRT_CHECK(init_ok(&c));
    enable_all();
    /* awaria jednej strony gantry: druga jedzie dalej, rozjazd rosnie */
    lrt_drive_inject_fault(lrt_machine_drive(&M, 3), LRT_DRIVE_FAULT_OVERCURRENT, 1);
    for (i = 1; i <= 500; i++) {
        lrt_machine_set_joint_target(&M, 1, 0.01 * i / 500.0);
        step_n(1);
    }
    step_n(200);
    LRT_CHECK(fabs(lrt_machine_joint_skew(&M, 1)) > 0.005);
    LRT_CHECK(lrt_machine_joint_events(&M, 1) & LRT_MACHINE_EV_GANTRY_SKEW);
    LRT_CHECK(lrt_machine_events(&M) & LRT_MACHINE_EV_DRIVE_FAULT);
}

/* ---- zderzaki (REQ-VM-04) ------------------------------------------------------------ */

static void cfg_hardstop(lrt_machine_cfg *c, int fault)
{
    cfg_xyz(c);
    set(c, "joint.0.use_stops", 1);
    set(c, "joint.0.stop_min", -0.002);
    set(c, "joint.0.stop_max", 0.1);
    set(c, "joint.0.stop_k", 5e5);
    set(c, "joint.0.stop_c", 5e3);
    set(c, "joint.0.stop_fault", fault);
    set(c, "joint.0.initial", 0.095);
}

static void drive_x_to(double target, double seconds)
{
    int n = (int)(seconds / DT);
    double start = lrt_machine_joint_position(&M, 0);
    int i;

    for (i = 1; i <= n; i++) {
        lrt_machine_set_joint_target(&M, 0, start + (target - start) * i / n);
        step_n(1);
    }
}

static void test_hardstop_crash(void) /* REQ-VM-04 */
{
    lrt_machine_cfg c;
    double peak = 0.0;
    int i;

    cfg_hardstop(&c, 0);
    LRT_CHECK(init_ok(&c));
    enable_all();
    drive_x_to(0.099, 0.2); /* 20 mm/s, przed zderzakiem */
    LRT_CHECK(!(lrt_machine_events(&M) & LRT_MACHINE_EV_CRASH_HARDSTOP));
    for (i = 1; i <= 300; i++) {
        lrt_machine_set_joint_target(&M, 0, 0.099 + 0.006 * i / 300.0);
        step_n(1);
        if (lrt_machine_joint_position(&M, 0) > peak) {
            peak = lrt_machine_joint_position(&M, 0);
        }
    }
    LRT_CHECK(lrt_machine_joint_events(&M, 0) & LRT_MACHINE_EV_CRASH_HARDSTOP);
    LRT_CHECK(lrt_machine_impact_speed(&M, 0) > 0.005);
    LRT_CHECK(lrt_machine_impact_speed(&M, 0) < 0.05);
    /* zderzak sprezysty: penetracja nie wieksza niz F_max/k (F z momentu 1 N*m) */
    LRT_CHECK(peak > 0.1);
    LRT_CHECK(peak < 0.1 + 1.0 / M.slots[0].axis.p.ratio / 5e5 * 1.05);
    LRT_CHECK(lrt_drive_error_code(lrt_machine_drive(&M, 0)) !=
              lrt_drive_fault_error_code(LRT_DRIVE_FAULT_HW_LIMIT));
    LRT_CHECK(!(lrt_machine_joint_events(&M, 1) & LRT_MACHINE_EV_CRASH_HARDSTOP));
}

static void test_hardstop_crash_with_drive_fault(void) /* REQ-VM-04 */
{
    lrt_machine_cfg c;

    cfg_hardstop(&c, 1);
    LRT_CHECK(init_ok(&c));
    enable_all();
    drive_x_to(0.104, 0.45);
    step_n(20);
    LRT_CHECK(lrt_machine_events(&M) & LRT_MACHINE_EV_CRASH_HARDSTOP);
    LRT_CHECK(lrt_drive_get_state(lrt_machine_drive(&M, 0)) == LRT_DRIVE_FAULT);
    LRT_CHECK(lrt_drive_error_code(lrt_machine_drive(&M, 0)) ==
              lrt_drive_fault_error_code(LRT_DRIVE_FAULT_HW_LIMIT));
    LRT_CHECK(lrt_machine_events(&M) & LRT_MACHINE_EV_DRIVE_FAULT);
}

/* ---- krancowki (REQ-VM-05) ----------------------------------------------------------- */

static void cfg_limits(lrt_machine_cfg *c, int nc, int shared)
{
    cfg_xyz(c);
    set(c, "switch.0.joint", 0); /* X min */
    set(c, "switch.0.side", -1);
    set(c, "switch.0.position", 0.0005);
    set(c, "switch.0.hysteresis", 0.0002);
    set(c, "switch.0.nc", nc);
    set(c, "switch.0.input", 1);
    set(c, "switch.1.joint", 0); /* X max */
    set(c, "switch.1.side", 1);
    set(c, "switch.1.position", 0.5995);
    set(c, "switch.1.hysteresis", 0.0002);
    set(c, "switch.1.nc", nc);
    set(c, "switch.1.input", shared ? 1 : 2);
    set(c, "switch.2.joint", 1); /* Y min */
    set(c, "switch.2.side", -1);
    set(c, "switch.2.position", 0.0005);
    set(c, "switch.2.nc", nc);
    set(c, "switch.2.input", shared ? 1 : 3);
}

static int bit(int n)
{
    return (int)((lrt_machine_inputs(&M) >> n) & 1u);
}

static void test_limit_switch_trip(void) /* REQ-VM-05 */
{
    lrt_machine_cfg c;

    cfg_limits(&c, 1, 0);
    set(&c, "joint.0.initial", 0.3);
    set(&c, "joint.1.initial", 0.3);
    LRT_CHECK(init_ok(&c));
    LRT_CHECK(bit(1) == 1 && bit(2) == 1 && bit(3) == 1); /* NC: zamkniete, gdy nie wcisniete */
    lrt_machine_set_joint_position(&M, 0, 0.0006);
    LRT_CHECK(bit(1) == 1);
    lrt_machine_set_joint_position(&M, 0, 0.0005); /* punkt zadzialania */
    LRT_CHECK(bit(1) == 0);
    LRT_CHECK(lrt_machine_joint_events(&M, 0) & LRT_MACHINE_EV_LIMIT_TRIP);
    /* histereza 0.2 mm: zwolnienie dopiero powyzej 0.7 mm */
    lrt_machine_set_joint_position(&M, 0, 0.00065);
    LRT_CHECK(bit(1) == 0);
    lrt_machine_set_joint_position(&M, 0, 0.00071);
    LRT_CHECK(bit(1) == 1);
    lrt_machine_set_joint_position(&M, 0, 0.6);
    LRT_CHECK(bit(2) == 0 && bit(1) == 1);
    LRT_CHECK(!(lrt_machine_joint_events(&M, 1) & LRT_MACHINE_EV_LIMIT_TRIP));

    /* NO: otwarte w spoczynku, zamkniete po zadzialaniu */
    cfg_limits(&c, 0, 0);
    set(&c, "joint.0.initial", 0.3);
    set(&c, "joint.1.initial", 0.3);
    LRT_CHECK(init_ok(&c));
    LRT_CHECK(bit(1) == 0 && bit(2) == 0);
    lrt_machine_set_joint_position(&M, 0, 0.0);
    LRT_CHECK(bit(1) == 1);
}

static void test_limit_switch_trip_while_moving(void) /* REQ-VM-05 */
{
    lrt_machine_cfg c;

    cfg_limits(&c, 1, 0);
    set(&c, "joint.0.initial", 0.01);
    set(&c, "joint.1.initial", 0.3);
    LRT_CHECK(init_ok(&c));
    enable_all();
    lrt_machine_clear_events(&M);
    drive_x_to(0.0, 0.5);
    step_n(100);
    LRT_CHECK(lrt_machine_joint_events(&M, 0) & LRT_MACHINE_EV_LIMIT_TRIP);
    LRT_CHECK(bit(1) == 0);
}

static void test_shared_limit_input(void) /* REQ-VM-05 */
{
    lrt_machine_cfg c;

    /* NC szeregowo: dowolna krancowka z trzech otwiera wspolne wejscie */
    cfg_limits(&c, 1, 1);
    set(&c, "joint.0.initial", 0.3);
    set(&c, "joint.1.initial", 0.3);
    LRT_CHECK(init_ok(&c));
    LRT_CHECK(bit(1) == 1);
    lrt_machine_set_joint_position(&M, 0, 0.6);
    LRT_CHECK(bit(1) == 0);
    lrt_machine_set_joint_position(&M, 0, 0.3);
    LRT_CHECK(bit(1) == 1);
    lrt_machine_set_joint_position(&M, 1, 0.0);
    LRT_CHECK(bit(1) == 0);
    LRT_CHECK(lrt_machine_joint_events(&M, 1) & LRT_MACHINE_EV_LIMIT_TRIP);

    /* NO rownolegle: dowolna zamyka */
    cfg_limits(&c, 0, 1);
    set(&c, "joint.0.initial", 0.3);
    set(&c, "joint.1.initial", 0.3);
    LRT_CHECK(init_ok(&c));
    LRT_CHECK(bit(1) == 0);
    lrt_machine_set_joint_position(&M, 1, 0.0);
    LRT_CHECK(bit(1) == 1);
}

static void test_contact_bounce_is_seeded_and_settles(void) /* REQ-VM-05 */
{
    lrt_machine_cfg c;
    uint32_t trace[2][20];
    int run;
    int i;
    int toggles = 0;

    for (run = 0; run < 2; run++) {
        cfg_limits(&c, 1, 0);
        set(&c, "switch.0.bounce", 0.010); /* 10 ms drgan */
        set(&c, "machine.seed", 1234);
        set(&c, "joint.0.initial", 0.3);
        LRT_CHECK(init_ok(&c));
        lrt_machine_set_joint_position(&M, 0, 0.0);
        for (i = 0; i < 20; i++) {
            step_n(1);
            trace[run][i] = lrt_machine_inputs(&M) & 2u;
        }
    }
    for (i = 0; i < 20; i++) {
        LRT_CHECK(trace[0][i] == trace[1][i]); /* deterministyczne */
        if (i > 0 && i < 10 && trace[0][i] != trace[0][i - 1]) {
            toggles++;
        }
    }
    LRT_CHECK(toggles >= 2);       /* styk drga */
    LRT_CHECK(trace[0][15] == 0u); /* po 10 ms ustalony: NC otwarty */
    LRT_CHECK(trace[0][19] == 0u);
}

static void test_home_sensor_own_input(void) /* REQ-VM-05 */
{
    lrt_machine_cfg c;

    cfg_xyz(&c);
    set(&c, "switch.0.joint", 2);
    set(&c, "switch.0.role", 1);
    set(&c, "switch.0.side", 1);
    set(&c, "switch.0.position", -0.001);
    set(&c, "switch.0.nc", 0);
    set(&c, "switch.0.input", 7);
    set(&c, "joint.2.initial", -0.05);
    LRT_CHECK(init_ok(&c));
    LRT_CHECK(bit(7) == 0);
    lrt_machine_set_joint_position(&M, 2, 0.0);
    LRT_CHECK(bit(7) == 1);
    LRT_CHECK(lrt_machine_joint_events(&M, 2) & LRT_MACHINE_EV_HOME_SENSOR);
    LRT_CHECK(!(lrt_machine_events(&M) & LRT_MACHINE_EV_LIMIT_TRIP));
}

/* ---- indeks, E-STOP, sonda ----------------------------------------------------------- */

static void test_index_pulse_once_per_motor_revolution(void)
{
    lrt_machine_cfg c;
    double rev; /* przesuw osi na obrot silnika */
    int i;

    cfg_xyz(&c);
    set(&c, "drive.0.index_input", 9);
    LRT_CHECK(init_ok(&c));
    rev = M.slots[0].axis.p.ratio * 2.0 * PI;
    enable_all();
    for (i = 1; i <= 1000; i++) {
        lrt_machine_set_joint_target(&M, 0, 3.5 * rev * i / 1000.0);
        step_n(1);
    }
    step_n(200);
    LRT_CHECK(lrt_machine_index_count(&M, 0) == 3);
    LRT_CHECK_ABS(lrt_machine_index_latch(&M, 0), 3.0 * rev, 0.01 * rev);
}

static void test_estop_sto_and_quick_stop(void)
{
    lrt_machine_cfg c;
    int s;

    cfg_xyz(&c);
    set(&c, "estop.input", 0);
    LRT_CHECK(init_ok(&c));
    LRT_CHECK(bit(0) == 1); /* NC: petla zamknieta */
    enable_all();
    lrt_machine_set_estop(&M, 1);
    LRT_CHECK(bit(0) == 0);
    LRT_CHECK(lrt_machine_events(&M) & LRT_MACHINE_EV_ESTOP);
    step_n(5);
    for (s = 0; s < 3; s++) {
        LRT_CHECK(lrt_drive_get_state(lrt_machine_drive(&M, s)) == LRT_DRIVE_FAULT);
        LRT_CHECK(lrt_drive_error_code(lrt_machine_drive(&M, s)) ==
                  lrt_drive_fault_error_code(LRT_DRIVE_FAULT_STO));
    }
    /* reset awarii odrzucany, dopoki petla otwarta; po zamknieciu dziala */
    lrt_machine_set_controlword(&M, 0, LRT_CW_FAULT_RESET);
    step_n(2);
    LRT_CHECK(lrt_drive_get_state(lrt_machine_drive(&M, 0)) == LRT_DRIVE_FAULT);
    lrt_machine_set_controlword(&M, 0, 0);
    lrt_machine_set_estop(&M, 0);
    step_n(1);
    lrt_machine_set_controlword(&M, 0, LRT_CW_FAULT_RESET);
    step_n(2);
    LRT_CHECK(lrt_drive_get_state(lrt_machine_drive(&M, 0)) == LRT_DRIVE_SWITCH_ON_DISABLED);

    /* quick stop: naped hamuje i wychodzi z OPERATION_ENABLED bez awarii */
    cfg_xyz(&c);
    set(&c, "estop.input", 0);
    set(&c, "estop.action", 1);
    LRT_CHECK(init_ok(&c));
    enable_all();
    lrt_machine_set_estop(&M, 1);
    step_n(300);
    LRT_CHECK(lrt_drive_get_state(lrt_machine_drive(&M, 0)) != LRT_DRIVE_OPERATION_ENABLED);
    LRT_CHECK(lrt_drive_get_state(lrt_machine_drive(&M, 0)) != LRT_DRIVE_FAULT);
}

static void test_probe_box_and_plate(void)
{
    lrt_machine_cfg c;

    cfg_xyz(&c);
    set(&c, "probe.type", 1);
    set(&c, "probe.input", 4);
    set(&c, "probe.tip_length", 0.05);
    set(&c, "probe.min_x", 0.1);
    set(&c, "probe.max_x", 0.2);
    set(&c, "probe.min_y", 0.1);
    set(&c, "probe.max_y", 0.2);
    set(&c, "probe.min_z", -0.1);
    set(&c, "probe.max_z", -0.07);
    LRT_CHECK(init_ok(&c));
    lrt_machine_set_joint_position(&M, 0, 0.15);
    lrt_machine_set_joint_position(&M, 1, 0.15);
    lrt_machine_set_joint_position(&M, 2, -0.019); /* koniec -0.069 */
    LRT_CHECK(bit(4) == 0);
    lrt_machine_set_joint_position(&M, 2, -0.021); /* koniec -0.071: w przygotowce */
    LRT_CHECK(bit(4) == 1);
    LRT_CHECK(lrt_machine_events(&M) & LRT_MACHINE_EV_PROBE);
    lrt_machine_set_tool_length(&M, 0.04); /* krotsza koncowka: brak kontaktu */
    LRT_CHECK(bit(4) == 0);
    lrt_machine_set_tool_length(&M, 0.05);
    lrt_machine_set_joint_position(&M, 0, 0.25); /* obok przygotowki */
    LRT_CHECK(bit(4) == 0);

    /* plytka: kontakt ponizej gornej powierzchni bez dolnej granicy */
    set(&c, "probe.type", 2);
    LRT_CHECK(init_ok(&c));
    lrt_machine_set_joint_position(&M, 0, 0.15);
    lrt_machine_set_joint_position(&M, 1, 0.15);
    lrt_machine_set_joint_position(&M, 2, -0.5);
    LRT_CHECK(bit(4) == 1);
}

static void test_step_rejects_bad_dt_and_is_deterministic(void)
{
    lrt_machine_cfg c;
    static lrt_machine other;

    cfg_xyz(&c);
    LRT_CHECK(init_ok(&c));
    LRT_CHECK(lrt_machine_step(&M, 0.0) == LRT_MACHINE_ERR_DT);
    LRT_CHECK(lrt_machine_step(&M, 0.1) == LRT_MACHINE_ERR_DT);
    LRT_CHECK(lrt_machine_step(&M, NAN) == LRT_MACHINE_ERR_DT);
    LRT_CHECK(lrt_machine_step(NULL, DT) == LRT_MACHINE_ERR_NULL);
    enable_all();
    drive_x_to(0.05, 0.2);
    other = M;
    step_n(100);
    {
        lrt_machine tmp = M;
        M = other;
        step_n(100);
        LRT_CHECK(memcmp(&tmp.joint_pos, &M.joint_pos, sizeof(M.joint_pos)) == 0);
    }
    LRT_CHECK(lrt_machine_cfg_size() == sizeof(lrt_machine_cfg));
    LRT_CHECK(lrt_machine_size() == sizeof(lrt_machine));
}

/* ---- cykl mastera w podkrokach (sesja 049) ------------------------------------------- */

/* Ruch osi X z rampa predkosci do 0,1 m/s; cel ustawiany raz na cykl 1 ms, n podkrokow.
 * Zwraca najwiekszy blad nadazania [m] na granicach cykli. */
static double ramp_x_peak_error(int n)
{
    lrt_machine_cfg c;
    double pos;
    double peak = 0.0;
    int i;

    cfg_xyz(&c);
    LRT_CHECK(init_ok(&c));
    enable_all();
    pos = M.joint_pos[0];
    for (i = 0; i < 600; i++) {
        double v = 0.1 * (i < 200 ? i / 200.0 : 1.0);
        double err;

        pos += v * DT;
        lrt_machine_set_target(&M, 0, lrt_machine_counts_for(&M, 0, pos));
        LRT_CHECK(lrt_machine_step_cycle(&M, DT, n) == LRT_MACHINE_OK);
        LRT_CHECK(M.slots[0].applied == M.slots[0].target);
        err = fabs(pos - M.joint_pos[0]);
        peak = err > peak ? err : peak;
    }
    return peak;
}

static void test_step_cycle_interpolates_target(void)
{
    double e1 = ramp_x_peak_error(1);
    double e8 = ramp_x_peak_error(8);

    /* Bez interpolacji skok celu w pierwszym podkroku dawal n-krotny impuls FF predkosci:
     * przy n = 8 blad ok. 49 mm (E-4201 przy G0, sesja 049). Z interpolacja drobniejszy krok
     * nie pogarsza nadazania (n = 1: ok. 0,1 mm, n = 8: ok. 0,013 mm). */
    LRT_CHECK(e1 < 1e-3);
    LRT_CHECK(e8 <= e1);
    LRT_CHECK(lrt_machine_step_cycle(&M, DT, 0) == LRT_MACHINE_ERR_DT);
    LRT_CHECK(lrt_machine_step_cycle(&M, DT, LRT_MACHINE_MAX_SUBSTEPS + 1) == LRT_MACHINE_ERR_DT);
    LRT_CHECK(lrt_machine_step_cycle(&M, 0.1, 4) == LRT_MACHINE_ERR_DT); /* dt/n > max */
    LRT_CHECK(lrt_machine_step_cycle(NULL, DT, 4) == LRT_MACHINE_ERR_NULL);
}

/* ---- bazowanie po rozruchu (REQ-VM-07, sesja 015) ------------------------------------ */

static void test_random_start_is_seeded_and_in_range(void) /* REQ-VM-07 */
{
    lrt_machine_cfg c;
    double first;
    double other;

    cfg_xyz(&c);
    set(&c, "joint.0.initial_random", 1);
    set(&c, "joint.0.initial_min", 0.1);
    set(&c, "joint.0.initial_max", 0.5);
    set(&c, "machine.seed", 7);
    LRT_CHECK(init_ok(&c));
    first = lrt_machine_joint_position(&M, 0);
    LRT_CHECK(first >= 0.1 && first <= 0.5);
    LRT_CHECK(init_ok(&c));
    LRT_CHECK(lrt_machine_joint_position(&M, 0) == first); /* to samo ziarno = ten sam start */
    set(&c, "machine.seed", 8);
    LRT_CHECK(init_ok(&c));
    other = lrt_machine_joint_position(&M, 0);
    LRT_CHECK(other >= 0.1 && other <= 0.5 && other != first);
    LRT_CHECK_ABS(lrt_machine_joint_position(&M, 1), 0.0, 1e-12); /* bez losowania: initial */

    set(&c, "joint.0.initial_min", 0.6);
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_JOINT);
    cfg_xyz(&c);
    set(&c, "drive.0.din_home", 3); /* styk nie istnieje */
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_SWITCH);
    cfg_xyz(&c);
    set(&c, "switch.0.joint", 0);
    set(&c, "switch.0.drive", 1); /* naped innej osi */
    LRT_CHECK(lrt_machine_init(&M, &c) == LRT_MACHINE_ERR_SWITCH);
}

static void test_incremental_encoder_counts_for_follows_offset(void) /* REQ-VM-07 */
{
    lrt_machine_cfg c;
    int i;

    cfg_xyz(&c);
    set(&c, "drive.0.encoder", LRT_ENC_INCREMENTAL);
    set(&c, "joint.0.initial", 0.2);
    LRT_CHECK(init_ok(&c));
    enable_all();
    /* Po wlaczeniu naped raportuje 0, choc os stoi na 0,2 m. */
    LRT_CHECK(abs(lrt_drive_position_actual(lrt_machine_drive(&M, 0))) <= 2);
    LRT_CHECK(abs(lrt_machine_counts_for(&M, 0, 0.2)) <= 2); /* uwzglednia przesuniecie */
    for (i = 1; i <= 500; i++) {
        lrt_machine_set_joint_target(&M, 0, 0.2 + 0.01 * i / 500.0);
        step_n(1);
    }
    step_n(300);
    LRT_CHECK_ABS(lrt_machine_joint_position(&M, 0), 0.21, 2e-6);
}

static void test_gantry_square_with_drive_homing_on_two_sensors(void) /* REQ-VM-07 */
{
    lrt_machine_cfg c;
    int side[2] = {1, 3};
    int k;
    int i;
    int32_t reported_target = 2000;

    cfg_xyz(&c);
    set(&c, "drive.3.type", 0);
    set(&c, "joint.1.drive1", 3);
    set(&c, "joint.1.max_skew", 0.002);
    for (k = 0; k < 2; k++) {
        /* Czujnik bazowy kazdej strony, aktywny ponizej 10 mm (strona ujemna). */
        setf(&c, "switch.%d.joint", k, 1);
        setf(&c, "switch.%d.role", k, LRT_SWITCH_HOME);
        setf(&c, "switch.%d.side", k, -1);
        setf(&c, "switch.%d.position", k, 0.010);
        setf(&c, "switch.%d.hysteresis", k, 0.0001);
        setf(&c, "switch.%d.nc", k, 0);
        setf(&c, "switch.%d.drive", k, side[k]);
        setf(&c, "drive.%d.din_home", side[k], k);
        setf(&c, "drive.%d.homing_method", side[k], 21);
    }
    set(&c, "switch.0.input", 4);  /* strona 1: tez na wejsciu mastera */
    set(&c, "switch.1.input", -1); /* strona 2: tylko wejscie napedu */
    LRT_CHECK(init_ok(&c));
    lrt_machine_set_drive_position(&M, 1, 0.050);
    lrt_machine_set_drive_position(&M, 3, 0.0512); /* belka skrzywiona o 1,2 mm */
    LRT_CHECK_ABS(lrt_machine_joint_skew(&M, 1), -0.0012, 1e-9);
    for (k = 0; k < 2; k++) {
        LRT_CHECK(lrt_drive_od_write(lrt_machine_drive(&M, side[k]), 0x6060u, 0,
                                     LRT_MODE_HOMING) == LRT_DRIVE_OK);
    }
    enable_all();
    for (k = 0; k < 2; k++) {
        lrt_machine_set_controlword(&M, side[k],
                                    LRT_CW_CMD_ENABLE_OPERATION | LRT_CW_HOMING_START);
    }
    for (i = 0; i < 30000; i++) {
        step_n(1);
        if (lrt_drive_homing_state(lrt_machine_drive(&M, 1)) == LRT_HM_DONE &&
            lrt_drive_homing_state(lrt_machine_drive(&M, 3)) == LRT_HM_DONE) {
            break;
        }
    }
    for (k = 0; k < 2; k++) {
        lrt_drive *d = lrt_machine_drive(&M, side[k]);
        LRT_CHECK(lrt_drive_homing_state(d) == LRT_HM_DONE);
        LRT_CHECK((lrt_drive_statusword(d) & LRT_SW_HOMING_ATTAINED) != 0u);
        /* Master: CSP i jazda obu stron do tej samej pozycji raportowanej. */
        LRT_CHECK(lrt_drive_od_write(d, 0x6060u, 0, LRT_MODE_CSP) == LRT_DRIVE_OK);
        lrt_machine_set_target(&M, side[k], lrt_drive_position_actual(d));
    }
    step_n(200);
    for (k = 0; k < 2; k++) {
        lrt_machine_set_target(&M, side[k], reported_target);
    }
    step_n(1000);
    /* Obie strony w tej samej odleglosci od swoich czujnikow: belka wyrownana. */
    LRT_CHECK(fabs(lrt_machine_joint_skew(&M, 1)) < 2e-5);
    LRT_CHECK(lrt_drive_get_state(lrt_machine_drive(&M, 1)) == LRT_DRIVE_OPERATION_ENABLED);
    LRT_CHECK(lrt_drive_get_state(lrt_machine_drive(&M, 3)) == LRT_DRIVE_OPERATION_ENABLED);
}

int main(void)
{
    LRT_RUN(test_cfg_rejects_bad_keys_and_values);
    LRT_RUN(test_init_rejects_inconsistent_machines);
    LRT_RUN(test_kin_xyz_tool_tip_equals_joints);
    LRT_RUN(test_kin_rotary_table_transforms_tool_into_workpiece);
    LRT_RUN(test_gantry_skew_alarm);
    LRT_RUN(test_gantry_skew_from_one_side_stalled);
    LRT_RUN(test_hardstop_crash);
    LRT_RUN(test_hardstop_crash_with_drive_fault);
    LRT_RUN(test_limit_switch_trip);
    LRT_RUN(test_limit_switch_trip_while_moving);
    LRT_RUN(test_shared_limit_input);
    LRT_RUN(test_contact_bounce_is_seeded_and_settles);
    LRT_RUN(test_home_sensor_own_input);
    LRT_RUN(test_index_pulse_once_per_motor_revolution);
    LRT_RUN(test_estop_sto_and_quick_stop);
    LRT_RUN(test_probe_box_and_plate);
    LRT_RUN(test_step_rejects_bad_dt_and_is_deterministic);
    LRT_RUN(test_step_cycle_interpolates_target);
    LRT_RUN(test_random_start_is_seeded_and_in_range);
    LRT_RUN(test_incremental_encoder_counts_for_follows_offset);
    LRT_RUN(test_gantry_square_with_drive_homing_on_two_sensors);
    return lrt_summary();
}
