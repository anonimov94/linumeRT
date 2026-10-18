/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - testy modulu napedu (plant/core/drive.c) w petli z osia (axis.c).
 * Model-Author: Claude
 *
 * Oczekiwania pochodza z rozwiazan analitycznych (blad ustalony P, kat obciazenia krokowca,
 * czas przeciazenia I2t, droga hamowania rampa), nie z dopasowania do wyniku.
 * Znaczniki REQ-VD-nn wskazuja wymagania z docs/wymagania/WIRTUALNA_OBRABIARKA.md.
 * NIEZWERYFIKOWANE NA SPRZECIE: zgodnosc z prawdziwymi napedami nie jest sprawdzana.
 */
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "../axis.h"
#include "../drive.h"
#include "lrt_test.h"

#define PI 3.14159265358979323846

/* ------------------------------------------------------------------------- */
/* Stanowisko: naped + os w jednej petli                                      */
/* ------------------------------------------------------------------------- */

typedef struct {
    lrt_axis ax;
    lrt_drive dr;
    lrt_drive_feedback fb;
    double dt;
    double tau;     /* ostatni moment zadany [N*m] */
    double t;       /* czas symulacji [s] */
    double tau_max; /* najwiekszy |moment| od rig_init() */
} rig;

static void rig_feedback(rig *r)
{
    r->fb.theta_m = r->ax.th_m;
    r->fb.omega_m = r->ax.w_m;
    r->fb.torque_avail = lrt_axis_torque_limit(&r->ax, fabs(r->ax.w_m));
    r->fb.j_total = lrt_axis_j_total(&r->ax);
}

static void rig_init(rig *r, const lrt_axis_params *ap, const lrt_drive_params *dp, double dt)
{
    int rc;

    memset(r, 0, sizeof(*r));
    rc = lrt_axis_init(&r->ax, ap);
    LRT_CHECK(rc == LRT_AXIS_OK);
    rc = lrt_drive_init(&r->dr, dp);
    LRT_CHECK(rc == LRT_DRIVE_OK);
    r->dt = dt;
    rig_feedback(r);
}

static void rig_step(rig *r)
{
    int rc = lrt_drive_step(&r->dr, &r->fb, r->dt, &r->tau);

    LRT_CHECK(rc == LRT_DRIVE_OK);
    rc = lrt_axis_step(&r->ax, r->tau, r->dt);
    LRT_CHECK(rc == LRT_AXIS_OK);
    rig_feedback(r);
    r->t += r->dt;
    if (fabs(r->tau) > r->tau_max) {
        r->tau_max = fabs(r->tau);
    }
}

static void rig_run(rig *r, double seconds)
{
    long n = (long)floor(seconds / r->dt + 0.5);
    long i;

    for (i = 0; i < n; i++) {
        rig_step(r);
    }
}

static int32_t rig_rotor_counts(const rig *r)
{
    return (int32_t)floor(r->ax.th_m * r->dr.counts_per_rad + 0.5);
}

static void rig_cw(rig *r, uint16_t cw)
{
    lrt_drive_set_controlword(&r->dr, cw);
    rig_step(r);
}

static lrt_drive_state rig_state(const rig *r)
{
    return lrt_drive_get_state(&r->dr);
}

/* Sekwencja mastera: NOT_READY -> SWITCH_ON_DISABLED -> READY -> SWITCHED_ON -> OP. */
static void rig_enable(rig *r)
{
    lrt_drive_set_target_position(&r->dr, rig_rotor_counts(r));
    rig_step(r);
    rig_cw(r, LRT_CW_CMD_SHUTDOWN);
    rig_cw(r, LRT_CW_CMD_SWITCH_ON);
    rig_cw(r, LRT_CW_CMD_ENABLE_OPERATION);
    LRT_CHECK(rig_state(r) == LRT_DRIVE_OPERATION_ENABLED);
}

/* Maski stanow wg ogolnego opisu profilu. */
static unsigned sw_state_41(const rig *r)
{
    return lrt_drive_statusword(&r->dr) & 0x004Fu;
}

static unsigned sw_state_6f(const rig *r)
{
    return lrt_drive_statusword(&r->dr) & 0x006Fu;
}

/* ------------------------------------------------------------------------- */
/* Zestawy parametrow                                                         */
/* ------------------------------------------------------------------------- */

#define SERVO_J 3.0e-5

static lrt_axis_params servo_axis(void)
{
    lrt_axis_params a;

    lrt_axis_params_default(&a);
    a.kind = LRT_AXIS_ROTARY;
    a.j_motor = SERVO_J;
    a.j_screw = 0.0;
    a.load = 0.0;
    a.ratio = 1.0;
    lrt_axis_set_flat_curve(&a, 3.8, 600.0);
    return a;
}

static lrt_drive_params servo_drive(double dt)
{
    lrt_drive_params p;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    lrt_drive_tune_servo(&p, SERVO_J, 1000.0, dt);
    p.following_window = 0xFFFFFFFFu; /* wylaczone, gdy test go nie sprawdza */
    return p;
}

#define STEP_J 1.0e-4
#define STEP_TORQUE 3.0

static lrt_axis_params stepper_axis(void)
{
    lrt_axis_params a;

    lrt_axis_params_default(&a);
    a.kind = LRT_AXIS_ROTARY;
    a.j_motor = STEP_J;
    a.j_screw = 0.0;
    a.load = 0.0;
    a.ratio = 1.0;
    lrt_axis_set_flat_curve(&a, STEP_TORQUE, 300.0);
    return a;
}

static lrt_drive_params stepper_drive(void)
{
    lrt_drive_params p;

    lrt_drive_params_default(&p, LRT_DRIVE_STEPPER_OPEN);
    return p;
}

/* Profil trapezowy: przyspieszenie a, predkosc v, czas jazdy ze stala predkoscia t_cruise. */
static double trap_pos(double t, double a, double v, double t_cruise)
{
    double t_acc = v / a;
    double d_acc = 0.5 * a * t_acc * t_acc;
    double td;

    if (t < 0.0) {
        return 0.0;
    }
    if (t < t_acc) {
        return 0.5 * a * t * t;
    }
    if (t < t_acc + t_cruise) {
        return d_acc + v * (t - t_acc);
    }
    td = t - t_acc - t_cruise;
    if (td < t_acc) {
        return d_acc + v * t_cruise + v * td - 0.5 * a * td * td;
    }
    return 2.0 * d_acc + v * t_cruise;
}

/* Jedzie profilem trapezowym (pozycja zadana w impulsach), potem czeka settle sekund. */
static void rig_run_trap(rig *r, double a, double v, double t_cruise, double settle)
{
    double t_total = 2.0 * v / a + t_cruise;
    double t0 = r->t;

    while (r->t - t0 < t_total + settle) {
        double th = trap_pos(r->t - t0, a, v, t_cruise);

        lrt_drive_set_target_position(&r->dr, (int32_t)floor(th * r->dr.counts_per_rad + 0.5));
        rig_step(r);
    }
}

/* ------------------------------------------------------------------------- */
/* Parametry, inicjalizacja, kody bledow                                      */
/* ------------------------------------------------------------------------- */

static void test_params_default_valid_for_all_types(void) /* REQ-VD-01 */
{
    lrt_drive_params p;
    int t;

    for (t = 0; t <= 2; t++) {
        lrt_drive_params_default(&p, (lrt_drive_type)t);
        LRT_CHECK(p.type == (lrt_drive_type)t);
        LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_OK);
    }
    lrt_drive_params_default(&p, (lrt_drive_type)42); /* nieznany typ => serwo */
    LRT_CHECK(p.type == LRT_DRIVE_SERVO_CSP);
}

static void test_params_check_rejects_invalid(void)
{
    lrt_drive_params p;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    LRT_CHECK(lrt_drive_params_check(NULL) == LRT_DRIVE_ERR_NULL);

    p.type = (lrt_drive_type)7;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_TYPE);
    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.counts_per_rev = 0.0;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_RESOLUTION);
    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.enc_noise_counts = -1.0;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_RESOLUTION);
    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.rated_torque = 0.0;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_TORQUE);
    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.torque_limit_permille = (uint16_t)(p.torque_limit_permille + 10u); /* ponad szczyt */
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_TORQUE);
    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.kp_pos = -1.0;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_GAINS);
    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.kff_vel = 3.0;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_GAINS);
    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.vel_filter_hz = 0.0;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_GAINS);
    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.quick_stop_decel = 0u;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_LIMITS);
    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.fault_reaction_option = 1;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_LIMITS);
    lrt_drive_params_default(&p, LRT_DRIVE_STEPPER_OPEN);
    p.full_steps_per_rev = 6;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_STEPPER);
    lrt_drive_params_default(&p, LRT_DRIVE_STEPPER_OPEN);
    p.stepper_damping_ratio = 3.0;
    LRT_CHECK(lrt_drive_params_check(&p) == LRT_DRIVE_ERR_STEPPER);
}

static void test_init_and_strerror(void)
{
    lrt_drive d;
    lrt_drive_params p;
    int code;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    LRT_CHECK(lrt_drive_init(NULL, &p) == LRT_DRIVE_ERR_NULL);
    LRT_CHECK(lrt_drive_init(&d, NULL) == LRT_DRIVE_ERR_NULL);
    p.counts_per_rev = -5.0;
    LRT_CHECK(lrt_drive_init(&d, &p) == LRT_DRIVE_ERR_RESOLUTION);
    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    LRT_CHECK(lrt_drive_init(&d, &p) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_get_state(&d) == LRT_DRIVE_NOT_READY);
    LRT_CHECK(lrt_drive_statusword(&d) == LRT_SW_REMOTE); /* NOT_READY: tylko bit "remote" */

    for (code = LRT_DRIVE_ERR_UNSUPPORTED; code <= LRT_DRIVE_OK; code++) {
        const char *s = lrt_drive_strerror(code);

        LRT_CHECK(s != NULL && s[0] != '\0');
        LRT_CHECK(strcmp(s, "nieznany kod bledu") != 0);
    }
    LRT_CHECK(strcmp(lrt_drive_strerror(-99), "nieznany kod bledu") == 0);
}

static void test_fault_table_complete(void) /* REQ-VD-01 */
{
    int f;
    int g;

    for (f = LRT_DRIVE_FAULT_GENERIC; f < LRT_DRIVE_FAULT_COUNT; f++) {
        const char *alarm = lrt_drive_fault_alarm(f);

        LRT_CHECK(alarm != NULL);
        /* E-42xx: awarie napedu; E-4003: watchdog magistrali (sesja 016) */
        LRT_CHECK(alarm != NULL && strlen(alarm) == 6 &&
                  (strncmp(alarm, "E-42", 4) == 0 || strcmp(alarm, "E-4003") == 0));
        LRT_CHECK(lrt_drive_fault_error_code(f) != 0);
        for (g = f + 1; g < LRT_DRIVE_FAULT_COUNT; g++) {
            LRT_CHECK(strcmp(alarm, lrt_drive_fault_alarm(g)) != 0);
            LRT_CHECK(lrt_drive_fault_error_code(f) != lrt_drive_fault_error_code(g));
        }
    }
    LRT_CHECK(lrt_drive_fault_alarm(LRT_DRIVE_FAULT_NONE) == NULL);
    LRT_CHECK(lrt_drive_fault_alarm(LRT_DRIVE_FAULT_COUNT) == NULL);
    LRT_CHECK(lrt_drive_fault_error_code(LRT_DRIVE_FAULT_COUNT) == 0);
    LRT_CHECK(lrt_drive_fault_error_code(LRT_DRIVE_FAULT_FOLLOWING_ERROR) == 0x8611u);
    LRT_CHECK(strcmp(lrt_drive_fault_alarm(LRT_DRIVE_FAULT_COMM_WATCHDOG), "E-4003") == 0);
    LRT_CHECK(lrt_drive_fault_error_code(LRT_DRIVE_FAULT_COMM_WATCHDOG) == 0x8130u);
}

static void test_tune_servo_formulas_and_bandwidth_clamp(void)
{
    lrt_drive_params p;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    lrt_drive_tune_servo(&p, 2.0e-4, 400.0, 1.0e-4);
    LRT_CHECK_REL(p.kv, 2.0e-4 * 400.0, 1e-12);
    LRT_CHECK_REL(p.ti, 4.0 / 400.0, 1e-12);
    LRT_CHECK_REL(p.kp_pos, 80.0, 1e-12);
    LRT_CHECK_REL(p.inertia_est, 2.0e-4, 1e-12);
    lrt_drive_tune_servo(&p, 2.0e-4, 1.0e6, 1.0e-3); /* ograniczone do 0.15/dt = 150 */
    LRT_CHECK_REL(p.kv, 2.0e-4 * 150.0, 1e-9);
    lrt_drive_tune_servo(&p, -1.0, 400.0, 1.0e-3); /* niepoprawne wejscie: bez zmian */
    LRT_CHECK_REL(p.kv, 2.0e-4 * 150.0, 1e-9);
    lrt_drive_tune_servo(NULL, 1.0, 1.0, 1.0); /* nie wywala sie */
}

/* ------------------------------------------------------------------------- */
/* Maszyna stanow CiA 402                                                     */
/* ------------------------------------------------------------------------- */

static void test_boot_delay_and_statusword_masks(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    long steps = 0;

    dp.boot_time_s = 0.05;
    rig_init(&r, &ap, &dp, 1e-4);
    LRT_CHECK(sw_state_41(&r) == 0x0000u);
    while (rig_state(&r) == LRT_DRIVE_NOT_READY && steps < 10000) {
        rig_step(&r);
        steps++;
    }
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    LRT_CHECK(labs(steps - 500) <= 2);
    LRT_CHECK(sw_state_41(&r) == 0x0040u);
    LRT_CHECK(r.tau == 0.0);
}

static void test_nominal_sequence_and_statuswords(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);

    rig_init(&r, &ap, &dp, 1e-4);
    rig_step(&r);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    LRT_CHECK(sw_state_41(&r) == 0x0040u);
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_READY_TO_SWITCH_ON);
    LRT_CHECK(sw_state_6f(&r) == 0x0021u);
    rig_cw(&r, LRT_CW_CMD_SWITCH_ON);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCHED_ON);
    LRT_CHECK(sw_state_6f(&r) == 0x0023u);
    rig_cw(&r, LRT_CW_CMD_ENABLE_OPERATION);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    LRT_CHECK(sw_state_6f(&r) == 0x0027u);
    LRT_CHECK((lrt_drive_statusword(&r.dr) & LRT_SW_FOLLOWS_COMMAND) != 0u);
    LRT_CHECK((lrt_drive_statusword(&r.dr) & LRT_SW_FAULT) == 0u);
}

static void test_illegal_commands_are_ignored(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);

    rig_init(&r, &ap, &dp, 1e-4);
    rig_step(&r);
    rig_cw(&r, LRT_CW_CMD_SWITCH_ON); /* z SWITCH_ON_DISABLED trzeba najpierw shutdown */
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    rig_cw(&r, LRT_CW_CMD_ENABLE_OPERATION);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    rig_cw(&r, (uint16_t)(LRT_CW_CMD_SHUTDOWN | LRT_CW_FAULT_RESET)); /* bit 7 psuje komende */
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_READY_TO_SWITCH_ON);
    rig_cw(&r, 0x0000u); /* disable voltage */
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
}

static void test_disable_voltage_from_every_state(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);

    /* z READY */
    rig_init(&r, &ap, &dp, 1e-4);
    rig_step(&r);
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    rig_cw(&r, LRT_CW_CMD_DISABLE_VOLTAGE);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    /* z SWITCHED_ON */
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    rig_cw(&r, LRT_CW_CMD_SWITCH_ON);
    rig_cw(&r, LRT_CW_CMD_DISABLE_VOLTAGE);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    /* z OPERATION_ENABLED: moment zero */
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    rig_cw(&r, LRT_CW_CMD_SWITCH_ON);
    rig_cw(&r, LRT_CW_CMD_ENABLE_OPERATION);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    rig_cw(&r, LRT_CW_CMD_DISABLE_VOLTAGE);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    LRT_CHECK(r.tau == 0.0);
    /* quick stop z READY i SWITCHED_ON prowadzi do SWITCH_ON_DISABLED */
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    rig_cw(&r, LRT_CW_CMD_QUICK_STOP);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    rig_cw(&r, LRT_CW_CMD_SWITCH_ON);
    rig_cw(&r, LRT_CW_CMD_QUICK_STOP);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
}

static void test_shutdown_and_disable_operation_from_operation(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);

    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    lrt_drive_set_target_position(&r.dr, rig_rotor_counts(&r) + 500);
    rig_run(&r, 0.001);
    LRT_CHECK(fabs(r.tau) > 0.0);
    rig_cw(&r, LRT_CW_CMD_SWITCH_ON); /* disable operation */
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCHED_ON);
    LRT_CHECK(r.tau == 0.0);
    rig_cw(&r, LRT_CW_CMD_ENABLE_OPERATION);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_READY_TO_SWITCH_ON);
    LRT_CHECK(r.tau == 0.0);
}

/* Rozpedza os do predkosci v [rad/s] profilem pozycji zadanej (FF predkosci wlaczone). */
static void servo_spin_up(rig *r, double v, double seconds)
{
    double t0 = r->t;
    double cnt0 = (double)rig_rotor_counts(r);

    while (r->t - t0 < seconds) {
        double cnt = cnt0 + v * (r->t - t0) * r->dr.counts_per_rad;

        lrt_drive_set_target_position(&r->dr, (int32_t)floor(cnt + 0.5));
        rig_step(r);
    }
}

/* Rozpedza os trapezem przyspieszenia a do predkosci v i jedzie dalej ze stala predkoscia
 * przez lacznie 'seconds' (bez skoku predkosci: krokowiec nie traci krokow na starcie). */
static void rig_spin_up_smooth(rig *r, double a, double v, double seconds)
{
    double t0 = r->t;
    double cnt0 = (double)rig_rotor_counts(r);

    while (r->t - t0 < seconds) {
        double th = trap_pos(r->t - t0, a, v, 1.0e9);

        lrt_drive_set_target_position(&r->dr,
                                      (int32_t)floor(cnt0 + th * r->dr.counts_per_rad + 0.5));
        rig_step(r);
    }
}

static void test_quick_stop_ramp_servo(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    double v0 = 20.0;
    double decel = 400.0; /* rad/s^2 => czas hamowania 0.05 s */
    double t_start;
    long guard = 0;

    dp.quick_stop_decel = (uint32_t)(decel / (2.0 * PI / dp.counts_per_rev));
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    servo_spin_up(&r, v0, 0.3);
    LRT_CHECK_REL(r.ax.w_m, v0, 0.02);
    lrt_drive_set_controlword(&r.dr, LRT_CW_CMD_QUICK_STOP);
    t_start = r.t;
    rig_step(&r);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_QUICK_STOP_ACTIVE);
    LRT_CHECK(sw_state_6f(&r) == 0x0007u);
    while (rig_state(&r) == LRT_DRIVE_QUICK_STOP_ACTIVE && guard < 100000) {
        rig_step(&r);
        guard++;
    }
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    LRT_CHECK(r.t - t_start >= v0 / decel - 0.002);
    LRT_CHECK(r.t - t_start <= v0 / decel + 0.03);
    LRT_CHECK(fabs(r.ax.w_m) < 0.5);
    LRT_CHECK(r.tau == 0.0);
}

static void test_quick_stop_option_1_disables_immediately(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);

    dp.quick_stop_option = 1;
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_cw(&r, LRT_CW_CMD_QUICK_STOP);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_QUICK_STOP_ACTIVE);
    LRT_CHECK(r.tau == 0.0);
    rig_step(&r);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
}

static void test_fault_injection_reaction_and_reset(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);

    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    LRT_CHECK(lrt_drive_inject_fault(&r.dr, LRT_DRIVE_FAULT_OVERTEMP, 0) == LRT_DRIVE_OK);
    rig_step(&r);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT_REACTION_ACTIVE);
    LRT_CHECK(sw_state_41(&r) == 0x000Fu);
    LRT_CHECK(r.tau == 0.0);
    LRT_CHECK(lrt_drive_error_code(&r.dr) == 0x4310u);
    rig_step(&r);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);
    LRT_CHECK(sw_state_41(&r) == 0x0008u);
    LRT_CHECK(r.dr.fault == LRT_DRIVE_FAULT_OVERTEMP);

    /* komendy poza resetem nie wyprowadzaja z FAULT */
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);
    rig_cw(&r, 0x0000u);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);

    rig_cw(&r, LRT_CW_FAULT_RESET); /* zbocze narastajace */
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    LRT_CHECK(lrt_drive_error_code(&r.dr) == 0u);
    LRT_CHECK(r.dr.fault == LRT_DRIVE_FAULT_NONE);
}

static void test_fault_reset_needs_edge_and_cleared_cause(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);

    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    LRT_CHECK(lrt_drive_inject_fault(&r.dr, LRT_DRIVE_FAULT_ENCODER_LOST, 1) == LRT_DRIVE_OK);
    rig_run(&r, 0.001);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);
    LRT_CHECK(lrt_drive_error_code(&r.dr) == 0x7305u);

    rig_cw(&r, LRT_CW_FAULT_RESET); /* przyczyna trwa: reset odrzucony */
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);
    lrt_drive_clear_fault_cause(&r.dr, LRT_DRIVE_FAULT_ENCODER_LOST);
    rig_run(&r, 0.001); /* bit 7 nadal 1: brak nowego zbocza => dalej FAULT */
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);
    rig_cw(&r, 0x0000u);
    rig_cw(&r, LRT_CW_FAULT_RESET);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    /* z bitem 7 trzymanym wysoko naped nie rusza dalej, dopoki bit nie opadnie */
    rig_cw(&r, (uint16_t)(LRT_CW_CMD_SHUTDOWN | LRT_CW_FAULT_RESET));
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_READY_TO_SWITCH_ON);
}

static void test_injected_fault_from_disabled_state_and_invalid_code(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);

    rig_init(&r, &ap, &dp, 1e-4);
    rig_step(&r);
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    LRT_CHECK(lrt_drive_inject_fault(&r.dr, LRT_DRIVE_FAULT_STO, 0) == LRT_DRIVE_OK);
    rig_step(&r);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT_REACTION_ACTIVE);
    rig_step(&r);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);
    LRT_CHECK(lrt_drive_error_code(&r.dr) == 0xFF02u);
    LRT_CHECK(lrt_drive_inject_fault(&r.dr, 0, 0) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_inject_fault(&r.dr, LRT_DRIVE_FAULT_COUNT, 0) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_inject_fault(NULL, 1, 0) == LRT_DRIVE_ERR_NULL);
}

static void test_fault_reaction_option_2_ramps_down(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    double v0 = 20.0;
    double decel = 400.0;
    long guard = 0;

    dp.fault_reaction_option = 2;
    dp.quick_stop_decel = (uint32_t)(decel / (2.0 * PI / dp.counts_per_rev));
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    servo_spin_up(&r, v0, 0.3);
    lrt_drive_inject_fault(&r.dr, LRT_DRIVE_FAULT_GENERIC, 0);
    rig_step(&r);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT_REACTION_ACTIVE);
    LRT_CHECK(fabs(r.tau) > 0.0); /* hamuje momentem, nie wybiega swobodnie */
    while (rig_state(&r) == LRT_DRIVE_FAULT_REACTION_ACTIVE && guard < 100000) {
        rig_step(&r);
        guard++;
    }
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);
    LRT_CHECK(fabs(r.ax.w_m) < 0.5);
    LRT_CHECK((double)guard * r.dt >= v0 / decel - 0.003);
    LRT_CHECK((double)guard * r.dt <= v0 / decel + 0.03);
}

/* ------------------------------------------------------------------------- */
/* Okno bledu nadazania (6065h/6066h)                                         */
/* ------------------------------------------------------------------------- */

static void test_following_error_fault_after_window_time(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    double t_step;
    long guard = 0;

    dp.following_window = 100u;
    dp.following_window_ms = 10u;
    dp.torque_limit_permille = 1u; /* os prawie nie rusza sie: blad rosnie */
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    t_step = r.t;
    lrt_drive_set_target_position(&r.dr, rig_rotor_counts(&r) + 1000);
    while (rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED && guard < 10000) {
        rig_step(&r);
        guard++;
    }
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT_REACTION_ACTIVE);
    LRT_CHECK(r.dr.fault == LRT_DRIVE_FAULT_FOLLOWING_ERROR);
    LRT_CHECK(lrt_drive_error_code(&r.dr) == 0x8611u);
    LRT_CHECK(r.t - t_step >= 0.0098);
    LRT_CHECK(r.t - t_step <= 0.0106);
    LRT_CHECK(r.tau == 0.0);
}

static void test_following_error_short_excursion_is_tolerated(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    int saw_bit13 = 0;
    long i;

    dp.following_window = 100u;
    dp.following_window_ms = 20u;
    dp.torque_limit_permille = 1u;
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    lrt_drive_set_target_position(&r.dr, rig_rotor_counts(&r) + 1000);
    for (i = 0; i < 100; i++) { /* 10 ms przekroczenia < 20 ms */
        rig_step(&r);
        if ((lrt_drive_statusword(&r.dr) & LRT_SW_FOLLOWING_ERROR) != 0u) {
            saw_bit13 = 1;
        }
    }
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    LRT_CHECK(saw_bit13);
    lrt_drive_set_target_position(&r.dr, rig_rotor_counts(&r)); /* wraca do okna */
    rig_run(&r, 0.1);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    LRT_CHECK((lrt_drive_statusword(&r.dr) & LRT_SW_FOLLOWING_ERROR) == 0u);
}

static void test_following_window_object_write_takes_effect(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);

    dp.torque_limit_permille = 1u;
    rig_init(&r, &ap, &dp, 1e-4);
    LRT_CHECK(lrt_drive_od_write(&r.dr, 0x6065u, 0, 50) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&r.dr, 0x6066u, 0, 0) == LRT_DRIVE_OK); /* natychmiast */
    rig_enable(&r);
    lrt_drive_set_target_position(&r.dr, rig_rotor_counts(&r) + 500);
    rig_step(&r); /* okno czasu = 0: awaria od razu w pierwszym kroku z bledem > 50 */
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT_REACTION_ACTIVE);
    LRT_CHECK(r.dr.fault == LRT_DRIVE_FAULT_FOLLOWING_ERROR);
    rig_step(&r);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);
}

/* ------------------------------------------------------------------------- */
/* Tryb CSP: regulatory, FF, limit momentu                                    */
/* ------------------------------------------------------------------------- */

static void test_csp_step_response_settles_without_big_overshoot(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    int32_t base;
    int32_t target;
    double peak = 0.0;
    long i;

    dp.kff_vel = 0.0;
    dp.kff_acc = 0.0;
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    base = rig_rotor_counts(&r);
    target = base + 2000;
    lrt_drive_set_target_position(&r.dr, target);
    for (i = 0; i < 3000; i++) { /* 0.3 s */
        double pos;

        rig_step(&r);
        pos = (double)(rig_rotor_counts(&r) - base);
        if (pos > peak) {
            peak = pos;
        }
    }
    LRT_CHECK(labs((long)(rig_rotor_counts(&r) - target)) <= 1);
    LRT_CHECK((peak - 2000.0) / 2000.0 < 0.15); /* przeregulowanie < 15 % */
    LRT_CHECK(r.tau_max < 3.8); /* nie weszlo w limit: rozsadny skok */
}

static void test_csp_ramp_error_without_ff_matches_v_over_kp(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    double v = 20.0;
    double rpc;
    double err_counts;
    double expected;

    dp.kff_vel = 0.0;
    dp.kff_acc = 0.0;
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    servo_spin_up(&r, v, 0.6);
    rpc = r.dr.rad_per_count;
    err_counts = (double)(r.dr.target_counts - rig_rotor_counts(&r));
    expected = v / dp.kp_pos / rpc; /* e = v / kp */
    LRT_CHECK_REL(err_counts, expected, 0.03);
}

static void test_csp_velocity_ff_removes_ramp_error(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    double v = 20.0;
    double rpc = 2.0 * PI / dp.counts_per_rev;
    double no_ff_err = v / dp.kp_pos / rpc;
    double expected_lag = -v * 1e-4 / rpc; /* pomiar sprzezenia opozniony o jeden krok */
    double err_counts;

    dp.kff_vel = 1.0;
    dp.kff_acc = 1.0;
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    servo_spin_up(&r, v, 0.6);
    err_counts = (double)(r.dr.target_counts - rig_rotor_counts(&r));
    /* regulator zeruje blad widziany w pomiarze; prawdziwa pozycja wyprzedza go o v*dt */
    LRT_CHECK_ABS(err_counts, expected_lag, 4.0);
    LRT_CHECK(fabs(err_counts) < 0.03 * no_ff_err);
}

static void test_csp_load_torque_error_without_and_with_integral(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    double load = 0.5; /* N*m */
    double expected;

    ap.gravity_force = -load;
    dp.kff_vel = 0.0;
    dp.kff_acc = 0.0;

    /* bez calki: e = M / (kv * kp) */
    dp.ti = 0.0;
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_run(&r, 1.0);
    expected = load / (dp.kv * dp.kp_pos) / r.dr.rad_per_count;
    LRT_CHECK_REL((double)(r.dr.target_counts - rig_rotor_counts(&r)), expected, 0.02);

    /* z calka: blad ustalony znika */
    lrt_drive_params_default(&dp, LRT_DRIVE_SERVO_CSP);
    lrt_drive_tune_servo(&dp, SERVO_J, 1000.0, 1e-4);
    dp.following_window = 0xFFFFFFFFu;
    dp.kff_vel = 0.0;
    dp.kff_acc = 0.0;
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_run(&r, 1.0);
    LRT_CHECK(labs((long)(r.dr.target_counts - rig_rotor_counts(&r))) <= 2);
}

static void test_csp_torque_limit_object_6072(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    double limit;
    int saw_limit_bit = 0;
    long i;

    rig_init(&r, &ap, &dp, 1e-4);
    LRT_CHECK(lrt_drive_od_write(&r.dr, 0x6072u, 0, 500) == LRT_DRIVE_OK);
    limit = 0.5 * dp.rated_torque;
    rig_enable(&r);
    lrt_drive_set_target_position(&r.dr, rig_rotor_counts(&r) + 65536); /* pol obrotu */
    for (i = 0; i < 2000; i++) {
        rig_step(&r);
        if ((lrt_drive_statusword(&r.dr) & LRT_SW_INTERNAL_LIMIT) != 0u) {
            saw_limit_bit = 1;
        }
        LRT_CHECK(fabs(r.tau) <= limit + 1e-12);
    }
    LRT_CHECK(r.tau_max > 0.99 * limit); /* faktycznie dochodzi do limitu */
    LRT_CHECK(saw_limit_bit);
    LRT_CHECK(lrt_drive_torque_actual(&r.dr) <= 500);
}

static void test_encoder_quantization_and_report(void) /* REQ-VD-01 */
{
    lrt_drive d;
    lrt_drive_params p;
    lrt_drive_feedback fb;
    double tau;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.counts_per_rev = 4096.0;
    LRT_CHECK(lrt_drive_init(&d, &p) == LRT_DRIVE_OK);
    fb.theta_m = 1.0;
    fb.omega_m = 0.0;
    fb.torque_avail = 3.8;
    fb.j_total = 3e-5;
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-3, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_position_actual(&d) == 652); /* 4096/(2*pi) = 651.9 */
    fb.theta_m = -1.0;
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-3, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_position_actual(&d) == -652);
    fb.theta_m = 1.0e7; /* 6.5e9 impulsow: poza zakresem int32, nasycenie zamiast UB */
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-3, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_position_actual(&d) == INT32_MAX);
}

static void test_encoder_noise_is_reproducible_and_scaled(void) /* REQ-VD-01 */
{
    lrt_drive a;
    lrt_drive b;
    lrt_drive c;
    lrt_drive_params p;
    lrt_drive_feedback fb;
    double tau;
    double sum = 0.0;
    double sum2 = 0.0;
    int differ = 0;
    int n = 5000;
    int i;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.counts_per_rev = 4096.0;
    p.enc_noise_counts = 2.0;
    p.enc_noise_seed = 12345u;
    LRT_CHECK(lrt_drive_init(&a, &p) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_init(&b, &p) == LRT_DRIVE_OK);
    p.enc_noise_seed = 777u;
    LRT_CHECK(lrt_drive_init(&c, &p) == LRT_DRIVE_OK);
    fb.theta_m = 0.0;
    fb.omega_m = 0.0;
    fb.torque_avail = 3.8;
    fb.j_total = 3e-5;
    for (i = 0; i < n; i++) {
        double x;

        LRT_CHECK(lrt_drive_step(&a, &fb, 1e-3, &tau) == LRT_DRIVE_OK);
        LRT_CHECK(lrt_drive_step(&b, &fb, 1e-3, &tau) == LRT_DRIVE_OK);
        LRT_CHECK(lrt_drive_step(&c, &fb, 1e-3, &tau) == LRT_DRIVE_OK);
        LRT_CHECK(lrt_drive_position_actual(&a) == lrt_drive_position_actual(&b));
        if (lrt_drive_position_actual(&a) != lrt_drive_position_actual(&c)) {
            differ = 1;
        }
        x = (double)lrt_drive_position_actual(&a);
        sum += x;
        sum2 += x * x;
    }
    LRT_CHECK(differ);
    LRT_CHECK(fabs(sum / n) < 0.2);
    /* odch. std. ~ szum (2.0) + kwantyzacja (~0.29) */
    LRT_CHECK_REL(sqrt(sum2 / n - (sum / n) * (sum / n)), 2.02, 0.1);
}

/* ------------------------------------------------------------------------- */
/* Przeciazenie I2t                                                           */
/* ------------------------------------------------------------------------- */

static void test_overload_trips_after_i2t_time_and_needs_cooldown(void) /* REQ-VD-01 */
{
    lrt_drive d;
    lrt_drive_params p;
    lrt_drive_feedback fb;
    double tau = 0.0;
    double dt = 1e-3;
    double t = 0.0;
    double limit_torque;
    double expected;
    int warned = 0;
    long guard = 0;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    p.following_window = 0xFFFFFFFFu;
    LRT_CHECK(lrt_drive_init(&d, &p) == LRT_DRIVE_OK);
    fb.theta_m = 0.0;
    fb.omega_m = 0.0;
    fb.torque_avail = 3.8;
    fb.j_total = 3e-5;
    /* sekwencja wlaczenia przy zerowym bledzie */
    LRT_CHECK(lrt_drive_step(&d, &fb, dt, &tau) == LRT_DRIVE_OK);
    lrt_drive_set_controlword(&d, LRT_CW_CMD_SHUTDOWN);
    LRT_CHECK(lrt_drive_step(&d, &fb, dt, &tau) == LRT_DRIVE_OK);
    lrt_drive_set_controlword(&d, LRT_CW_CMD_SWITCH_ON);
    LRT_CHECK(lrt_drive_step(&d, &fb, dt, &tau) == LRT_DRIVE_OK);
    lrt_drive_set_controlword(&d, LRT_CW_CMD_ENABLE_OPERATION);
    LRT_CHECK(lrt_drive_step(&d, &fb, dt, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_get_state(&d) == LRT_DRIVE_OPERATION_ENABLED);

    lrt_drive_set_target_position(&d, 1000000); /* ogromny blad: moment w limicie */
    limit_torque = (double)d.torque_limit_permille * 0.001 * p.rated_torque;
    expected = (p.peak_torque * p.peak_torque - p.rated_torque * p.rated_torque) *
               p.peak_time_s / (limit_torque * limit_torque - p.rated_torque * p.rated_torque);
    while (lrt_drive_get_state(&d) == LRT_DRIVE_OPERATION_ENABLED && guard < 5000) {
        LRT_CHECK(lrt_drive_step(&d, &fb, dt, &tau) == LRT_DRIVE_OK);
        t += dt;
        guard++;
        if ((lrt_drive_statusword(&d) & LRT_SW_WARNING) != 0u) {
            warned = 1;
        }
    }
    LRT_CHECK(warned);
    LRT_CHECK(d.fault == LRT_DRIVE_FAULT_OVERLOAD);
    LRT_CHECK(lrt_drive_error_code(&d) == 0x2350u);
    LRT_CHECK_REL(t, expected, 0.02);

    /* zaraz po awarii naped jest goracy: reset odrzucony */
    fb.torque_avail = 3.8;
    lrt_drive_set_target_position(&d, 0);
    guard = 0;
    while (lrt_drive_get_state(&d) != LRT_DRIVE_FAULT && guard < 10) {
        LRT_CHECK(lrt_drive_step(&d, &fb, dt, &tau) == LRT_DRIVE_OK);
        guard++;
    }
    lrt_drive_set_controlword(&d, LRT_CW_FAULT_RESET);
    LRT_CHECK(lrt_drive_step(&d, &fb, dt, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_get_state(&d) == LRT_DRIVE_FAULT);

    /* po ostygnieciu (I2t < 50 %) reset dziala; chlodzenie: dI2t/dt = -M_zn^2 */
    lrt_drive_set_controlword(&d, 0x0000u);
    for (guard = 0; guard < 4500; guard++) {
        LRT_CHECK(lrt_drive_step(&d, &fb, dt, &tau) == LRT_DRIVE_OK);
    }
    lrt_drive_set_controlword(&d, LRT_CW_FAULT_RESET);
    LRT_CHECK(lrt_drive_step(&d, &fb, dt, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_get_state(&d) == LRT_DRIVE_SWITCH_ON_DISABLED);
    LRT_CHECK((lrt_drive_statusword(&d) & LRT_SW_WARNING) == 0u);
}

/* ------------------------------------------------------------------------- */
/* Slownik obiektow (SDO)                                                     */
/* ------------------------------------------------------------------------- */

static void test_od_read_write_ranges_and_access(void) /* REQ-VD-01 */
{
    lrt_drive d;
    lrt_drive_params p;
    int64_t v = 0;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    LRT_CHECK(lrt_drive_init(&d, &p) == LRT_DRIVE_OK);

    LRT_CHECK(lrt_drive_od_read(&d, 0x6065u, 0, &v) == LRT_DRIVE_OK && v == p.following_window);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6065u, 0, 12345) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6065u, 0, &v) == LRT_DRIVE_OK && v == 12345);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6065u, 0, -1) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6065u, 0, 0x100000000LL) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6065u, 0, &v) == LRT_DRIVE_OK && v == 12345); /* bez zmian */

    LRT_CHECK(lrt_drive_od_write(&d, 0x6066u, 0, 65535) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6066u, 0, 65536) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x607Au, 0, -100000) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_read(&d, 0x607Au, 0, &v) == LRT_DRIVE_OK && v == -100000);
    LRT_CHECK(lrt_drive_od_write(&d, 0x607Au, 0, 0x80000000LL) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6040u, 0, 0x10000) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6040u, 0, 0x0006) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6040u, 0, &v) == LRT_DRIVE_OK && v == 6);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6085u, 0, 0) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6085u, 0, 5000) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x60B2u, 0, -300) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x60B2u, 0, 40000) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x60B1u, 0, 1000) == LRT_DRIVE_OK);

    /* tylko do odczytu */
    LRT_CHECK(lrt_drive_od_write(&d, 0x6041u, 0, 1) == LRT_DRIVE_ERR_READ_ONLY);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6064u, 0, 1) == LRT_DRIVE_ERR_READ_ONLY);
    LRT_CHECK(lrt_drive_od_write(&d, 0x603Fu, 0, 1) == LRT_DRIVE_ERR_READ_ONLY);
    LRT_CHECK(lrt_drive_od_write(&d, 0x606Cu, 0, 1) == LRT_DRIVE_ERR_READ_ONLY);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6077u, 0, 1) == LRT_DRIVE_ERR_READ_ONLY);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6061u, 0, 8) == LRT_DRIVE_ERR_READ_ONLY);
    /* nieistniejace */
    LRT_CHECK(lrt_drive_od_read(&d, 0x1234u, 0, &v) == LRT_DRIVE_ERR_NO_OBJECT);
    LRT_CHECK(lrt_drive_od_write(&d, 0x1234u, 0, 1) == LRT_DRIVE_ERR_NO_OBJECT);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6065u, 1, &v) == LRT_DRIVE_ERR_NO_OBJECT);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6065u, 3, 1) == LRT_DRIVE_ERR_NO_OBJECT);
    LRT_CHECK(lrt_drive_od_read(NULL, 0x6065u, 0, &v) == LRT_DRIVE_ERR_NULL);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6065u, 0, NULL) == LRT_DRIVE_ERR_NULL);
    LRT_CHECK(lrt_drive_od_write(NULL, 0x6065u, 0, 1) == LRT_DRIVE_ERR_NULL);
}

static void test_od_6072_bounds_follow_peak_torque(void) /* REQ-VD-01 */
{
    lrt_drive d;
    lrt_drive_params p;
    int64_t v = 0;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP); /* szczyt 3.8 / 1.27 => 2992 */
    LRT_CHECK(lrt_drive_init(&d, &p) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6072u, 0, 2992) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6072u, 0, 2993) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6072u, 0, -1) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6072u, 0, 0) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6072u, 0, &v) == LRT_DRIVE_OK && v == 0);

    lrt_drive_params_default(&p, LRT_DRIVE_STEPPER_OPEN); /* szczyt = znamionowy => 1000 */
    LRT_CHECK(lrt_drive_init(&d, &p) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6072u, 0, 1000) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6072u, 0, 1001) == LRT_DRIVE_ERR_RANGE);
}

static void test_od_homing_objects_roundtrip(void) /* REQ-VD-01 */
{
    lrt_drive d;
    lrt_drive_params p;
    int64_t v = 0;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    LRT_CHECK(lrt_drive_init(&d, &p) == LRT_DRIVE_OK);

    LRT_CHECK(lrt_drive_od_read(&d, 0x6099u, 0, &v) == LRT_DRIVE_OK && v == 2);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6099u, 0, 2) == LRT_DRIVE_ERR_READ_ONLY);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6099u, 1, 500000) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6099u, 2, 50000) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6099u, 1, &v) == LRT_DRIVE_OK && v == 500000);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6099u, 2, &v) == LRT_DRIVE_OK && v == 50000);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6099u, 3, &v) == LRT_DRIVE_ERR_NO_OBJECT);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6099u, 3, 1) == LRT_DRIVE_ERR_NO_OBJECT);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6099u, 1, 0) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6099u, 1, 0x100000000LL) == LRT_DRIVE_ERR_RANGE);

    LRT_CHECK(lrt_drive_od_write(&d, 0x609Au, 0, 123456) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_read(&d, 0x609Au, 0, &v) == LRT_DRIVE_OK && v == 123456);
    LRT_CHECK(lrt_drive_od_write(&d, 0x609Au, 0, 0) == LRT_DRIVE_ERR_RANGE);

    LRT_CHECK(lrt_drive_od_read(&d, 0x6098u, 0, &v) == LRT_DRIVE_OK && v == 35);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6098u, 0, 1) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6098u, 0, 37) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6098u, 0, -1) == LRT_DRIVE_OK); /* zderzak */
    LRT_CHECK(lrt_drive_od_write(&d, 0x6098u, 0, -2) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6098u, 0, &v) == LRT_DRIVE_OK && v == -2);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6098u, 0, 0) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6098u, 0, 15) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6098u, 0, 36) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6098u, 0, 38) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6098u, 0, -129) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6098u, 0, &v) == LRT_DRIVE_OK && v == -2); /* bez zmian */
}

static void test_od_mode_and_options(void)
{
    lrt_drive d;
    lrt_drive_params p;
    int64_t v = 0;

    lrt_drive_params_default(&p, LRT_DRIVE_SERVO_CSP);
    LRT_CHECK(lrt_drive_init(&d, &p) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6060u, 0, 8) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6060u, 0, 6) == LRT_DRIVE_OK); /* bazowanie, sesja 015 */
    LRT_CHECK(lrt_drive_od_read(&d, 0x6061u, 0, &v) == LRT_DRIVE_OK && v == 6);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6060u, 0, 8) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6060u, 0, 7) == LRT_DRIVE_ERR_UNSUPPORTED);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6060u, 0, 300) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6061u, 0, &v) == LRT_DRIVE_OK && v == 8);
    LRT_CHECK(lrt_drive_od_read(&d, 0x6060u, 0, &v) == LRT_DRIVE_OK && v == 8);

    LRT_CHECK(lrt_drive_od_write(&d, 0x605Au, 0, 1) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x605Au, 0, 5) == LRT_DRIVE_ERR_UNSUPPORTED);
    LRT_CHECK(lrt_drive_od_write(&d, 0x605Au, 0, 40000) == LRT_DRIVE_ERR_RANGE);
    LRT_CHECK(lrt_drive_od_read(&d, 0x605Au, 0, &v) == LRT_DRIVE_OK && v == 1);
    LRT_CHECK(lrt_drive_od_write(&d, 0x605Eu, 0, 2) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x605Eu, 0, 1) == LRT_DRIVE_ERR_UNSUPPORTED);
    LRT_CHECK(lrt_drive_od_read(&d, 0x605Eu, 0, &v) == LRT_DRIVE_OK && v == 2);
}

static void test_od_status_and_actual_values_follow_drive(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    int64_t v = 0;

    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    servo_spin_up(&r, 10.0, 0.3);
    LRT_CHECK(lrt_drive_od_read(&r.dr, 0x6041u, 0, &v) == LRT_DRIVE_OK);
    LRT_CHECK(v == (int64_t)lrt_drive_statusword(&r.dr));
    LRT_CHECK(lrt_drive_od_read(&r.dr, 0x6064u, 0, &v) == LRT_DRIVE_OK);
    /* pomiar jest sprzed ostatniego kroku osi: roznica <= v*dt = 21 impulsow */
    LRT_CHECK(llabs(v - (int64_t)rig_rotor_counts(&r)) <= 25);
    LRT_CHECK(lrt_drive_od_read(&r.dr, 0x606Cu, 0, &v) == LRT_DRIVE_OK);
    LRT_CHECK_REL((double)v, 10.0 * r.dr.counts_per_rad, 0.03);
    LRT_CHECK(lrt_drive_od_read(&r.dr, 0x6077u, 0, &v) == LRT_DRIVE_OK);
    LRT_CHECK(v == lrt_drive_torque_actual(&r.dr));
    LRT_CHECK(lrt_drive_od_read(&r.dr, 0x603Fu, 0, &v) == LRT_DRIVE_OK && v == 0);
}

/* ------------------------------------------------------------------------- */
/* Testy samego napedu (sprzezenie zadawane recznie)                          */
/* ------------------------------------------------------------------------- */

/* Przeprowadza swiezo zainicjowany naped do OPERATION_ENABLED przy stalym sprzezeniu. */
static void dr_enable(lrt_drive *d, const lrt_drive_params *p, const lrt_drive_feedback *fb,
                      double dt)
{
    double tau;

    LRT_CHECK(lrt_drive_init(d, p) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_step(d, fb, dt, &tau) == LRT_DRIVE_OK);
    lrt_drive_set_controlword(d, LRT_CW_CMD_SHUTDOWN);
    LRT_CHECK(lrt_drive_step(d, fb, dt, &tau) == LRT_DRIVE_OK);
    lrt_drive_set_controlword(d, LRT_CW_CMD_SWITCH_ON);
    LRT_CHECK(lrt_drive_step(d, fb, dt, &tau) == LRT_DRIVE_OK);
    lrt_drive_set_controlword(d, LRT_CW_CMD_ENABLE_OPERATION);
    LRT_CHECK(lrt_drive_step(d, fb, dt, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_get_state(d) == LRT_DRIVE_OPERATION_ENABLED);
}

static void test_csp_integrator_does_not_wind_up_in_saturation(void) /* REQ-VD-01 */
{
    lrt_drive d;
    lrt_drive_params p = servo_drive(1e-4);
    lrt_drive_feedback fb = {0.0, 0.0, 3.8, SERVO_J};
    double tau = 0.0;
    double limit;
    int i;

    p.kff_vel = 0.0;
    p.kff_acc = 0.0;
    dr_enable(&d, &p, &fb, 1e-4);
    LRT_CHECK(lrt_drive_od_write(&d, 0x6072u, 0, 1000) == LRT_DRIVE_OK); /* = moment znamionowy */
    limit = p.rated_torque;
    lrt_drive_set_target_position(&d, 100000); /* os zablokowana: 0.5 s w nasyceniu */
    for (i = 0; i < 5000; i++) {
        LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
    }
    LRT_CHECK_ABS(tau, limit, 1e-9);
    LRT_CHECK((lrt_drive_statusword(&d) & LRT_SW_INTERNAL_LIMIT) != 0u);
    /* po zwolnieniu (blad = 0) calka nie moze trzymac momentu: brak "windup" */
    lrt_drive_set_target_position(&d, 0);
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(fabs(tau) < 0.05 * limit);
    LRT_CHECK((lrt_drive_statusword(&d) & LRT_SW_INTERNAL_LIMIT) == 0u);
}

static void test_csp_acceleration_feedforward_provides_inertia_torque(void) /* REQ-VD-01 */
{
    lrt_drive_params p = servo_drive(1e-4);
    double a = 2000.0; /* rad/s^2 */
    int variant;

    p.ff_filter_hz = p.vel_filter_hz; /* rowne filtry: v_zad i v_mierzona nie rozjezdzaja sie */
    p.kff_vel = 1.0;
    for (variant = 0; variant < 2; variant++) {
        lrt_drive d;
        lrt_drive_feedback fb = {0.0, 0.0, 3.8, SERVO_J};
        double tau = 0.0;
        double t = 0.0;
        int i;

        p.kff_acc = variant == 1 ? 1.0 : 0.0;
        dr_enable(&d, &p, &fb, 1e-4);
        for (i = 0; i < 2000; i++) {
            int32_t cnt = (int32_t)floor(0.5 * a * t * t * d.counts_per_rad + 0.5);

            lrt_drive_set_target_position(&d, cnt);
            fb.theta_m = (double)cnt * d.rad_per_count; /* idealne sledzenie */
            fb.omega_m = a * t;
            LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
            t += 1e-4;
        }
        if (variant == 1) {
            LRT_CHECK_REL(tau, p.inertia_est * a, 0.03); /* M = J * a */
        } else {
            LRT_CHECK(fabs(tau) < 0.03 * p.inertia_est * a);
        }
    }
}

static void test_csp_velocity_and_torque_offsets_feed_forward(void) /* REQ-VD-01 */
{
    lrt_drive d;
    lrt_drive_params p = servo_drive(1e-4);
    lrt_drive_feedback fb = {0.0, 0.0, 3.8, SERVO_J};
    double tau = 0.0;

    p.kff_vel = 0.0;
    p.kff_acc = 0.0;
    p.ti = 0.0;
    dr_enable(&d, &p, &fb, 1e-4);
    LRT_CHECK(lrt_drive_od_write(&d, 0x60B2u, 0, 200) == LRT_DRIVE_OK); /* 20 % znamionowego */
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
    LRT_CHECK_REL(tau, 0.2 * p.rated_torque, 1e-9);
    LRT_CHECK(lrt_drive_od_write(&d, 0x60B2u, 0, -300) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
    LRT_CHECK_REL(tau, -0.3 * p.rated_torque, 1e-9);
    LRT_CHECK(lrt_drive_od_write(&d, 0x60B2u, 0, 0) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_write(&d, 0x60B1u, 0, 100000) == LRT_DRIVE_OK); /* impulsy/s */
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
    LRT_CHECK_REL(tau, p.kv * 100000.0 * d.rad_per_count, 1e-9); /* kv * v_zad */
    LRT_CHECK(lrt_drive_od_write(&d, 0x60B1u, 0, -100000) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
    LRT_CHECK_REL(tau, -p.kv * 100000.0 * d.rad_per_count, 1e-9);
}

static void test_stepper_slip_counter_has_hysteresis(void) /* REQ-VD-01 */
{
    lrt_drive d;
    lrt_drive_params p = stepper_drive();
    lrt_drive_feedback fb = {0.0, 0.0, STEP_TORQUE, STEP_J};
    double period = 2.0 * PI / (double)(p.full_steps_per_rev / 4);
    /* wirnik 'za' polem o p okresow elektrycznych; pole w pozycji 0 */
    static const double seq1[] = {0.45, 0.58, 0.5, 0.59}; /* |p - 0| <= 0.6: bez zmian */
    static const double seq2[] = {0.42, 0.55, 0.45};      /* |p - 1| <= 0.6: bez zmian */
    double tau = 0.0;
    size_t i;

    dr_enable(&d, &p, &fb, 1e-4);
    for (i = 0; i < sizeof(seq1) / sizeof(seq1[0]); i++) {
        fb.theta_m = -seq1[i] * period;
        LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
        LRT_CHECK(lrt_drive_lost_steps(&d) == 0);
        LRT_CHECK(lrt_drive_slip_events(&d) == 0);
    }
    fb.theta_m = -0.65 * period; /* przekroczony prog histerezy */
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_lost_steps(&d) == 4);
    LRT_CHECK(lrt_drive_slip_events(&d) == 1);
    for (i = 0; i < sizeof(seq2) / sizeof(seq2[0]); i++) {
        fb.theta_m = -seq2[i] * period;
        LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
        LRT_CHECK(lrt_drive_lost_steps(&d) == 4); /* brak migotania licznika */
        LRT_CHECK(lrt_drive_slip_events(&d) == 1);
    }
    fb.theta_m = -1.7 * period;
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_lost_steps(&d) == 8);
    LRT_CHECK(lrt_drive_slip_events(&d) == 2);
    fb.theta_m = 0.8 * period; /* wirnik przed polem: ujemne okresy; zmiana o 3 okresy */
    LRT_CHECK(lrt_drive_step(&d, &fb, 1e-4, &tau) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_lost_steps(&d) == -4);
    LRT_CHECK(lrt_drive_slip_events(&d) == 5);
}

/* ------------------------------------------------------------------------- */
/* Krokowiec bez sprzezenia                                                   */
/* ------------------------------------------------------------------------- */

static void test_stepper_follows_reasonable_acceleration_without_loss(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = stepper_axis();
    lrt_drive_params dp = stepper_drive();
    double a_max = STEP_TORQUE / STEP_J; /* 3e4 rad/s^2: J*a = moment dostepny */

    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_run_trap(&r, 0.3 * a_max, 60.0, 0.1, 0.3);
    LRT_CHECK(lrt_drive_lost_steps(&r.dr) == 0);
    LRT_CHECK(lrt_drive_slip_events(&r.dr) == 0);
    LRT_CHECK(fabs(r.ax.th_m - (double)r.dr.target_counts * r.dr.rad_per_count) < 1e-4);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    LRT_CHECK(sw_state_6f(&r) == 0x0027u);
}

static void test_stepper_loses_steps_when_acceleration_exceeds_torque(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = stepper_axis();
    lrt_drive_params dp = stepper_drive();
    double a_max = STEP_TORQUE / STEP_J;
    double theta_f;
    double x;
    int lost;

    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    /* Bariera potencjalna: 2*A/Ne = 0.12 J. Po skoku predkosci pola do 100 rad/s w ~0.3 ms wirnik
     * zdazy nabrac najwyzej a_max*t, wiec energia wzgledna ~0.4 J > bariera => poslizg.
     * Mierzymy po ponownej synchronizacji, w jezdzie ze stala predkoscia (wynik po ostrym
     * hamowaniu pola bylby chaotyczny). */
    rig_spin_up_smooth(&r, 10.0 * a_max, 100.0, 0.15);
    lost = lrt_drive_lost_steps(&r.dr);
    theta_f = (double)r.dr.target_counts * r.dr.rad_per_count;
    LRT_CHECK(lost > 0); /* pole wyprzedza wirnik */
    LRT_CHECK(lost % 4 == 0); /* okres elektryczny = 4 pelne kroki */
    LRT_CHECK(lrt_drive_slip_events(&r.dr) >= lost / 4);
    /* niezalezny odczyt z fizyki: pole wyprzedza wirnik o 'lost/4' okresow elektrycznych */
    x = r.dr.pole_pairs * (theta_f - r.ax.th_m) / (2.0 * PI);
    LRT_CHECK_ABS(x, (double)lost / 4.0, 0.08);
    LRT_CHECK(theta_f - r.ax.th_m > 0.3); /* realnie stracona droga */
    LRT_CHECK_ABS(r.ax.w_m, 100.0, 2.0);  /* wirnik zsynchronizowany z polem */
    /* master nie widzi niczego: brak awarii, pozycja raportowana = pozycja pola */
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    LRT_CHECK((lrt_drive_statusword(&r.dr) & LRT_SW_FAULT) == 0u);
    LRT_CHECK(lrt_drive_position_actual(&r.dr) == r.dr.target_counts);
}

static void test_stepper_cannot_follow_speed_above_pullout_curve(void) /* REQ-VD-01 */
{
    rig slow;
    rig fast;
    lrt_axis_params ap = stepper_axis();
    lrt_drive_params dp = stepper_drive();
    double a_max = STEP_TORQUE / STEP_J;

    /* krzywa pull-out: 3 N*m w spoczynku, 2 N*m przy 50 rad/s, 0 przy 100 rad/s */
    ap.n_curve = 3;
    ap.curve[0].omega = 0.0;
    ap.curve[0].torque = 3.0;
    ap.curve[1].omega = 50.0;
    ap.curve[1].torque = 2.0;
    ap.curve[2].omega = 100.0;
    ap.curve[2].torque = 0.0;

    rig_init(&slow, &ap, &dp, 1e-4);
    rig_enable(&slow);
    rig_run_trap(&slow, 0.2 * a_max, 40.0, 0.2, 0.3);
    LRT_CHECK(lrt_drive_lost_steps(&slow.dr) == 0);

    rig_init(&fast, &ap, &dp, 1e-4);
    rig_enable(&fast);
    rig_run_trap(&fast, 0.2 * a_max, 150.0, 0.2, 0.6);
    LRT_CHECK(lrt_drive_lost_steps(&fast.dr) != 0);
    LRT_CHECK(lrt_drive_lost_steps(&fast.dr) % 4 == 0);
    LRT_CHECK(rig_state(&fast) == LRT_DRIVE_OPERATION_ENABLED);
}

static void test_stepper_holding_angle_under_load(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = stepper_axis();
    lrt_drive_params dp = stepper_drive();
    double load = 1.5;
    double expected;

    ap.gravity_force = -load; /* sila ciagnie w strone ujemna */
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_run(&r, 0.5);
    /* rownowaga: A*sin(delta) = M  =>  kat elektryczny delta = asin(M/A), kat mech. /50 */
    expected = asin(load / STEP_TORQUE) / r.dr.pole_pairs;
    LRT_CHECK_REL(-r.ax.th_m, expected, 0.02);
    LRT_CHECK(lrt_drive_lost_steps(&r.dr) == 0);
}

static void test_stepper_load_above_holding_torque_slips(void)
{
    rig r;
    lrt_axis_params ap = stepper_axis();
    lrt_drive_params dp = stepper_drive();

    ap.gravity_force = -4.0; /* ponad moment trzymania 3 N*m */
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_run(&r, 0.3);
    LRT_CHECK(r.ax.th_m < -1.0); /* wirnik ucieka */
    LRT_CHECK(lrt_drive_slip_events(&r.dr) > 0);
    LRT_CHECK(lrt_drive_lost_steps(&r.dr) > 0); /* pole - wirnik > 0: wirnik uciekl w minus */
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED); /* bez alarmu */
}

static void test_stepper_torque_limit_scales_holding_torque(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = stepper_axis();
    lrt_drive_params dp = stepper_drive();
    double load = 0.75;
    double amp;
    double expected;

    ap.gravity_force = -load;
    rig_init(&r, &ap, &dp, 1e-4);
    LRT_CHECK(lrt_drive_od_write(&r.dr, 0x6072u, 0, 500) == LRT_DRIVE_OK); /* A = 1.5 N*m */
    amp = 0.5 * STEP_TORQUE;
    rig_enable(&r);
    rig_run(&r, 0.5);
    expected = asin(load / amp) / r.dr.pole_pairs;
    LRT_CHECK_REL(-r.ax.th_m, expected, 0.02);
    LRT_CHECK(r.tau_max <= amp + 1e-9);
}

static void test_stepper_enable_snaps_to_nearest_equilibrium_without_counting_loss(void)
{
    rig r;
    lrt_axis_params ap = stepper_axis();
    lrt_drive_params dp = stepper_drive();
    double period;

    rig_init(&r, &ap, &dp, 1e-4);
    period = 2.0 * PI / (double)(dp.full_steps_per_rev / 4);
    lrt_axis_reset(&r.ax, 0.0);
    r.ax.th_m = 1.3 * period; /* wirnik przesuniety recznie o 1.3 okresu */
    r.ax.th_l = r.ax.th_m;
    r.ax.pos = r.ax.th_m;
    rig_feedback(&r);
    lrt_drive_set_target_position(&r.dr, 0);
    rig_step(&r);
    rig_cw(&r, LRT_CW_CMD_SHUTDOWN);
    rig_cw(&r, LRT_CW_CMD_SWITCH_ON);
    rig_cw(&r, LRT_CW_CMD_ENABLE_OPERATION);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    rig_run(&r, 0.3);
    LRT_CHECK_ABS(r.ax.th_m, 1.0 * period, 1e-3); /* najblizsza rownowaga */
    LRT_CHECK(lrt_drive_lost_steps(&r.dr) == 0);
    LRT_CHECK(lrt_drive_slip_events(&r.dr) == 0);
}

static void test_stepper_quick_stop_ramps_field_without_loss(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = stepper_axis();
    lrt_drive_params dp = stepper_drive();
    double v0 = 60.0;
    double decel = 6000.0; /* 0.2 * a_max: bez poslizgu */
    long guard = 0;

    dp.quick_stop_decel = (uint32_t)(decel / (2.0 * PI / dp.counts_per_rev));
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_spin_up_smooth(&r, 0.2 * STEP_TORQUE / STEP_J, v0, 0.3);
    LRT_CHECK_REL(r.ax.w_m, v0, 0.05);
    LRT_CHECK(lrt_drive_lost_steps(&r.dr) == 0);
    rig_cw(&r, LRT_CW_CMD_QUICK_STOP);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_QUICK_STOP_ACTIVE);
    while (rig_state(&r) == LRT_DRIVE_QUICK_STOP_ACTIVE && guard < 100000) {
        rig_step(&r);
        guard++;
    }
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    LRT_CHECK((double)guard * r.dt >= v0 / decel - 0.003);
    LRT_CHECK((double)guard * r.dt <= v0 / decel + 0.03);
    LRT_CHECK(lrt_drive_lost_steps(&r.dr) == 0);
    /* wirnik zatrzymany blisko ostatniego polozenia pola */
    LRT_CHECK(fabs(r.ax.w_m) < 0.5);
    LRT_CHECK(fabs(r.ax.th_m - (double)lrt_drive_position_actual(&r.dr) * r.dr.rad_per_count) <
              0.5 * 2.0 * PI / (double)(dp.full_steps_per_rev / 4));
    LRT_CHECK(lrt_drive_velocity_actual(&r.dr) == 0);
}

/* ------------------------------------------------------------------------- */
/* Serwo krokowe (petla zamknieta)                                            */
/* ------------------------------------------------------------------------- */

static lrt_axis_params closed_stepper_axis(void)
{
    lrt_axis_params a;

    lrt_axis_params_default(&a);
    a.kind = LRT_AXIS_ROTARY;
    a.j_motor = 2.0e-4;
    a.j_screw = 0.0;
    a.load = 0.0;
    a.ratio = 1.0;
    lrt_axis_set_flat_curve(&a, 2.2, 300.0);
    return a;
}

static lrt_drive_params closed_stepper_drive(double dt)
{
    lrt_drive_params p;

    lrt_drive_params_default(&p, LRT_DRIVE_STEPPER_CLOSED);
    lrt_drive_tune_servo(&p, 2.0e-4, 400.0, dt);
    return p;
}

static void test_closed_stepper_follows_without_fault(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = closed_stepper_axis();
    lrt_drive_params dp = closed_stepper_drive(1e-4);
    double a_max = 2.2 / 2.0e-4;
    double theta_end;

    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_run_trap(&r, 0.3 * a_max, 30.0, 0.1, 0.3);
    theta_end = (double)r.dr.target_counts * r.dr.rad_per_count;
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    LRT_CHECK(fabs(theta_end - r.ax.th_m) < 3.0 * r.dr.rad_per_count);
    LRT_CHECK(lrt_drive_lost_steps(&r.dr) == 0); /* dla petli zamknietej zawsze 0 */
}

static void test_closed_stepper_alarms_when_error_exceeds_threshold(void) /* REQ-VD-01 */
{
    rig r;
    lrt_axis_params ap = closed_stepper_axis();
    lrt_drive_params dp = closed_stepper_drive(1e-4);
    long guard = 0;

    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    lrt_drive_set_target_position(&r.dr, rig_rotor_counts(&r) + 4000); /* skok o 1 obrot */
    while (rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED && guard < 20000) {
        rig_step(&r);
        guard++;
    }
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT_REACTION_ACTIVE);
    LRT_CHECK(r.dr.fault == LRT_DRIVE_FAULT_FOLLOWING_ERROR);
    LRT_CHECK(lrt_drive_error_code(&r.dr) == 0x8611u);
    {
        const char *alarm = lrt_drive_fault_alarm(r.dr.fault);

        LRT_CHECK(alarm != NULL && strcmp(alarm, "E-4201") == 0);
    }
    LRT_CHECK(r.tau_max <= 2.2 + 1e-9); /* moment ograniczony krzywa */
}

/* ------------------------------------------------------------------------- */
/* Odpornosc: bledy wejscia, determinizm                                      */
/* ------------------------------------------------------------------------- */

static void test_step_rejects_bad_input_and_keeps_state(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    lrt_drive before;
    lrt_drive_feedback bad = {0.0, 0.0, 3.8, SERVO_J};
    double tau = 123.0;

    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_run(&r, 0.01);
    before = r.dr;

    LRT_CHECK(lrt_drive_step(NULL, &r.fb, 1e-4, &tau) == LRT_DRIVE_ERR_NULL);
    LRT_CHECK(lrt_drive_step(&r.dr, NULL, 1e-4, &tau) == LRT_DRIVE_ERR_NULL);
    LRT_CHECK(lrt_drive_step(&r.dr, &r.fb, 1e-4, NULL) == LRT_DRIVE_ERR_NULL);
    LRT_CHECK(lrt_drive_step(&r.dr, &r.fb, 0.0, &tau) == LRT_DRIVE_ERR_DT);
    LRT_CHECK(lrt_drive_step(&r.dr, &r.fb, -1e-4, &tau) == LRT_DRIVE_ERR_DT);
    LRT_CHECK(lrt_drive_step(&r.dr, &r.fb, 1.0, &tau) == LRT_DRIVE_ERR_DT);
    LRT_CHECK(lrt_drive_step(&r.dr, &r.fb, NAN, &tau) == LRT_DRIVE_ERR_DT);
    bad.theta_m = NAN;
    LRT_CHECK(lrt_drive_step(&r.dr, &bad, 1e-4, &tau) == LRT_DRIVE_ERR_NUMERIC);
    bad.theta_m = 0.0;
    bad.omega_m = INFINITY;
    LRT_CHECK(lrt_drive_step(&r.dr, &bad, 1e-4, &tau) == LRT_DRIVE_ERR_NUMERIC);
    bad.omega_m = 0.0;
    bad.torque_avail = -1.0;
    LRT_CHECK(lrt_drive_step(&r.dr, &bad, 1e-4, &tau) == LRT_DRIVE_ERR_NUMERIC);
    bad.torque_avail = 3.8;
    bad.j_total = 0.0;
    LRT_CHECK(lrt_drive_step(&r.dr, &bad, 1e-4, &tau) == LRT_DRIVE_ERR_NUMERIC);
    LRT_CHECK(tau == 123.0);                          /* wyjscie nietkniete */
    LRT_CHECK(memcmp(&before, &r.dr, sizeof(before)) == 0); /* stan nietkniety */
}

static void test_simulation_is_deterministic(void)
{
    rig a;
    rig b;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);

    dp.enc_noise_counts = 1.0;
    dp.enc_noise_seed = 99u;
    rig_init(&a, &ap, &dp, 1e-4);
    rig_init(&b, &ap, &dp, 1e-4);
    rig_enable(&a);
    rig_enable(&b);
    servo_spin_up(&a, 15.0, 0.2);
    servo_spin_up(&b, 15.0, 0.2);
    LRT_CHECK(a.ax.th_m == b.ax.th_m);
    LRT_CHECK(a.tau == b.tau);
    LRT_CHECK(lrt_drive_position_actual(&a.dr) == lrt_drive_position_actual(&b.dr));
}

static void test_accessors_tolerate_null(void)
{
    LRT_CHECK(lrt_drive_statusword(NULL) == 0u);
    LRT_CHECK(lrt_drive_position_actual(NULL) == 0);
    LRT_CHECK(lrt_drive_velocity_actual(NULL) == 0);
    LRT_CHECK(lrt_drive_torque_actual(NULL) == 0);
    LRT_CHECK(lrt_drive_error_code(NULL) == 0u);
    LRT_CHECK(lrt_drive_get_state(NULL) == LRT_DRIVE_NOT_READY);
    LRT_CHECK(lrt_drive_lost_steps(NULL) == 0);
    LRT_CHECK(lrt_drive_slip_events(NULL) == 0L);
    lrt_drive_set_controlword(NULL, 1u);
    lrt_drive_set_target_position(NULL, 1);
    lrt_drive_clear_fault_cause(NULL, 1);
}

/* ------------------------------------------------------------------------- */
/* Parametry live napedu (REQ-VD-04, sesja 013)                               */
/* ------------------------------------------------------------------------- */

/* REQ-VD-04: limit momentu w locie dziala od nastepnego kroku i trafia do dziennika z czasem;
 * bledne zmiany sa odrzucane bez zmiany stanu i bez wpisu. */
static void test_drive_live_torque_limit_logged_with_time(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    lrt_live_log log;
    lrt_live_entry e;
    int64_t od = 0;
    double v = 0.0;
    double limit = 0.4 * dp.rated_torque;
    const double bad[] = {NAN, INFINITY, -1.0, 400.5, 1.0e9};
    unsigned i;

    lrt_live_log_init(&log);
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_run(&r, 0.01);
    LRT_CHECK_ABS(r.dr.time, r.t, 1e-12);
    LRT_CHECK(lrt_drive_set_live(&r.dr, LRT_LIVE_TORQUE_LIMIT, 400.0, &log) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_od_read(&r.dr, 0x6072u, 0, &od) == LRT_DRIVE_OK && od == 400);
    LRT_CHECK(lrt_drive_get_live(&r.dr, LRT_LIVE_TORQUE_LIMIT, &v) == LRT_DRIVE_OK);
    LRT_CHECK_ABS(v, 400.0, 0.0);
    LRT_CHECK(lrt_live_log_size(&log) == 1u && lrt_live_log_get(&log, 0u, &e) == 0);
    LRT_CHECK(e.param == LRT_LIVE_TORQUE_LIMIT);
    LRT_CHECK_ABS(e.t, r.t, 1e-12);
    LRT_CHECK_ABS(e.old_value, (double)dp.torque_limit_permille, 0.0);
    LRT_CHECK_ABS(e.new_value, 400.0, 0.0);

    lrt_drive_set_target_position(&r.dr, rig_rotor_counts(&r) + 65536);
    r.tau_max = 0.0;
    for (i = 0; i < 2000u; i++) {
        rig_step(&r);
        LRT_CHECK(fabs(r.tau) <= limit + 1e-12);
    }
    LRT_CHECK(r.tau_max > 0.99 * limit);

    for (i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) {
        LRT_CHECK(lrt_drive_set_live(&r.dr, LRT_LIVE_TORQUE_LIMIT, bad[i], &log) ==
                  LRT_DRIVE_ERR_LIVE);
    }
    LRT_CHECK(lrt_drive_set_live(&r.dr, LRT_LIVE_INERTIA_EST, -1.0, &log) == LRT_DRIVE_ERR_LIVE);
    LRT_CHECK(lrt_drive_set_live(&r.dr, LRT_LIVE_LOAD, 1.0, &log) == LRT_DRIVE_ERR_LIVE);
    LRT_CHECK(lrt_drive_set_live(&r.dr, LRT_LIVE_COUNT, 1.0, &log) == LRT_DRIVE_ERR_LIVE);
    LRT_CHECK(lrt_drive_set_live(&r.dr, -1, 1.0, &log) == LRT_DRIVE_ERR_LIVE);
    LRT_CHECK(lrt_drive_set_live(NULL, LRT_LIVE_TORQUE_LIMIT, 1.0, &log) == LRT_DRIVE_ERR_NULL);
    LRT_CHECK(lrt_drive_get_live(&r.dr, LRT_LIVE_TORQUE_LIMIT, NULL) == LRT_DRIVE_ERR_NULL);
    LRT_CHECK(lrt_drive_od_read(&r.dr, 0x6072u, 0, &od) == LRT_DRIVE_OK && od == 400);
    LRT_CHECK(lrt_live_log_size(&log) == 1u);
    LRT_CHECK(lrt_drive_set_live(&r.dr, LRT_LIVE_INERTIA_EST, 2.0e-5, NULL) == LRT_DRIVE_OK);
    LRT_CHECK_ABS(r.dr.p.inertia_est, 2.0e-5, 0.0);
    LRT_CHECK(lrt_axis_set_live(&r.ax, LRT_LIVE_TORQUE_LIMIT, 1.0, &log) == LRT_AXIS_ERR_LIVE_ID);
    LRT_CHECK(strcmp(lrt_live_param_name(LRT_LIVE_TORQUE_LIMIT), "torque_limit") == 0);
    LRT_CHECK(strcmp(lrt_live_param_name(LRT_LIVE_INERTIA_EST), "inertia_est") == 0);
    LRT_CHECK(strcmp(lrt_drive_strerror(LRT_DRIVE_ERR_LIVE), "nieznany kod bledu") != 0);
}

/* Ruch z nasyconym momentem: zwraca najwieksze przyspieszenie walu [rad/s^2] w oknie `window`. */
static double saturated_move_max_accel(rig *r, double window)
{
    long n = (long)floor(window / r->dt + 0.5);
    double a_max = 0.0;
    double w_prev = r->ax.w_m;
    long i;

    lrt_drive_set_target_position(&r->dr, rig_rotor_counts(r) + 50 * 131072);
    for (i = 0; i < n; i++) {
        rig_step(r);
        if (fabs(r->ax.w_m - w_prev) / r->dt > a_max) {
            a_max = fabs(r->ax.w_m - w_prev) / r->dt;
        }
        w_prev = r->ax.w_m;
    }
    lrt_drive_set_target_position(&r->dr, rig_rotor_counts(r)); /* stop */
    rig_run(r, 0.5);
    return a_max;
}

/* REQ-VD-04 + test fizyczny: wieksza bezwladnosc ustawiona w locie => mniejsze maks.
 * przyspieszenie, a = T_lim / J (T_lim z 6072h); wspolny dziennik osi i napedu z czasem. */
static void test_drive_live_heavier_load_lowers_max_acceleration(void)
{
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = servo_drive(1e-4);
    lrt_live_log log;
    lrt_live_entry e[3];
    double t_lim = 0.5 * dp.rated_torque;
    double j1 = SERVO_J;
    double j2 = 4.0 * SERVO_J;
    double a1;
    double a2;
    unsigned i;

    lrt_live_log_init(&log);
    rig_init(&r, &ap, &dp, 1e-4);
    rig_enable(&r);
    rig_run(&r, 0.01);
    LRT_CHECK(lrt_drive_set_live(&r.dr, LRT_LIVE_TORQUE_LIMIT, 500.0, &log) == LRT_DRIVE_OK);
    a1 = saturated_move_max_accel(&r, 0.004);
    LRT_CHECK(fabs(r.ax.w_m) < 1.0);

    LRT_CHECK(lrt_axis_set_live(&r.ax, LRT_LIVE_LOAD, j2 - j1, &log) == LRT_AXIS_OK);
    LRT_CHECK(lrt_drive_set_live(&r.dr, LRT_LIVE_INERTIA_EST, j2, &log) == LRT_DRIVE_OK);
    rig_feedback(&r);
    a2 = saturated_move_max_accel(&r, 0.004);

    LRT_CHECK_REL(a1, t_lim / j1, 0.01);
    LRT_CHECK_REL(a2, t_lim / j2, 0.01);
    LRT_CHECK(a2 < a1);
    LRT_CHECK_REL(a1 / a2, j2 / j1, 0.02);

    LRT_CHECK(lrt_live_log_size(&log) == 3u);
    for (i = 0; i < 3u; i++) {
        LRT_CHECK(lrt_live_log_get(&log, i, &e[i]) == 0);
    }
    LRT_CHECK(e[0].param == LRT_LIVE_TORQUE_LIMIT && e[1].param == LRT_LIVE_LOAD &&
              e[2].param == LRT_LIVE_INERTIA_EST);
    LRT_CHECK(e[0].t < e[1].t);
    LRT_CHECK_ABS(e[1].t, e[2].t, 1e-12); /* os i naped licza ten sam czas modelu */
    LRT_CHECK_ABS(e[1].old_value, 0.0, 0.0);
    LRT_CHECK_ABS(e[2].new_value, j2, 0.0);
}

/* ------------------------------------------------------------------------- */
/* Przetwornik i bazowanie w napedzie (sesja 015)                             */
/* ------------------------------------------------------------------------- */

/* Otoczenie walu: krancowki, czujnik bazowy (aktywny powyzej home_at) i impuls indeksu raz
 * na obrot (zbocze przy przejsciu przez wielokrotnosc 2*pi). Katy walu [rad]. */
typedef struct {
    int use_neg, use_pos, use_home;
    double neg_at, pos_at, home_at;
    int home_below; /* 1: czujnik aktywny ponizej home_at (szukanie w kierunku ujemnym) */
    long rev;
} hm_env;

static unsigned hm_inputs(hm_env *e, const rig *r)
{
    double th = r->ax.th_m;
    long rev = (long)floor(th / (2.0 * PI));
    unsigned in = 0u;

    if (e->use_neg && th <= e->neg_at) {
        in |= LRT_DIN_NEG_LIMIT;
    }
    if (e->use_pos && th >= e->pos_at) {
        in |= LRT_DIN_POS_LIMIT;
    }
    if (e->use_home && (e->home_below ? th <= e->home_at : th >= e->home_at)) {
        in |= LRT_DIN_HOME;
    }
    if (rev != e->rev) {
        in |= LRT_DIN_INDEX;
        e->rev = rev;
    }
    return in;
}

static void hm_step(rig *r, hm_env *e)
{
    lrt_drive_set_inputs(&r->dr, hm_inputs(e, r));
    rig_step(r);
}

/* Wlaczenie w trybie 6 od biezacej pozycji raportowanej (enkoder dowolnego rodzaju). */
static void hm_enable(rig *r, hm_env *e)
{
    e->rev = (long)floor(r->ax.th_m / (2.0 * PI));
    LRT_CHECK(lrt_drive_od_write(&r->dr, 0x6060u, 0, LRT_MODE_HOMING) == LRT_DRIVE_OK);
    hm_step(r, e);
    lrt_drive_set_target_position(&r->dr, lrt_drive_position_actual(&r->dr));
    lrt_drive_set_controlword(&r->dr, LRT_CW_CMD_SHUTDOWN);
    hm_step(r, e);
    lrt_drive_set_controlword(&r->dr, LRT_CW_CMD_SWITCH_ON);
    hm_step(r, e);
    lrt_drive_set_controlword(&r->dr, LRT_CW_CMD_ENABLE_OPERATION);
    hm_step(r, e);
}

/* Start bazowania (bit 4) i praca do konca; zwraca faze koncowa. */
static int hm_run(rig *r, hm_env *e, double tmax)
{
    long n = (long)(tmax / r->dt);
    long i;
    int ph = LRT_HM_IDLE;

    lrt_drive_set_controlword(&r->dr, LRT_CW_CMD_ENABLE_OPERATION | LRT_CW_HOMING_START);
    for (i = 0; i < n; i++) {
        hm_step(r, e);
        ph = lrt_drive_homing_state(&r->dr);
        if (ph == LRT_HM_DONE || ph == LRT_HM_ERROR) {
            break;
        }
    }
    return ph;
}

/* Pozycja raportowana, ktora odpowiadalaby katowi walu th (po bazowaniu). */
static double hm_reported_at(const rig *r, double th)
{
    return th * r->dr.counts_per_rad - (double)lrt_drive_position_offset(&r->dr);
}

static lrt_drive_params hm_servo(double dt)
{
    lrt_drive_params p = servo_drive(dt);

    p.following_window = 20000u; /* ok. 1 rad: kontrola nadazania wlaczona */
    p.following_window_ms = 10u;
    return p;
}

static void test_encoder_incremental_starts_at_zero_absolute_keeps_offset(void)
{
    /* REQ-VM-07: po wlaczeniu polozenie nieznane (przyrostowy), absolutny pamieta pozycje */
    rig r;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = hm_servo(1e-4);
    int32_t off = 0;
    int valid = 0;

    dp.encoder = LRT_ENC_INCREMENTAL;
    rig_init(&r, &ap, &dp, 1e-4);
    lrt_axis_reset(&r.ax, 5.3);
    rig_feedback(&r);
    rig_step(&r);
    LRT_CHECK(lrt_drive_position_actual(&r.dr) == 0);
    LRT_CHECK_ABS(lrt_drive_position_offset(&r.dr), 5.3 * r.dr.counts_per_rad, 1.0);
    LRT_CHECK(lrt_drive_set_absolute(&r.dr, 0, 1) == LRT_DRIVE_ERR_UNSUPPORTED);

    dp.encoder = LRT_ENC_ABSOLUTE;
    rig_init(&r, &ap, &dp, 1e-4);
    lrt_axis_reset(&r.ax, 5.3);
    rig_feedback(&r);
    LRT_CHECK(lrt_drive_set_absolute(&r.dr, 12345, 1) == LRT_DRIVE_OK);
    rig_step(&r);
    LRT_CHECK_ABS(lrt_drive_position_actual(&r.dr), 5.3 * r.dr.counts_per_rad - 12345.0, 1.0);
    LRT_CHECK(lrt_drive_get_absolute(&r.dr, &off, &valid) == LRT_DRIVE_OK);
    LRT_CHECK(off == 12345 && valid == 1);
    LRT_CHECK(lrt_drive_set_absolute(&r.dr, 0, 1) == LRT_DRIVE_ERR_UNSUPPORTED); /* po pomiarze */
    LRT_CHECK(lrt_drive_set_battery(&r.dr, 0) == LRT_DRIVE_OK);
    LRT_CHECK(lrt_drive_get_absolute(&r.dr, &off, &valid) == LRT_DRIVE_OK && valid == 0);
    /* Bateria nie zmienia pozycji w czasie pracy (enkoder zasilany z napedu). */
    LRT_CHECK_ABS(lrt_drive_position_actual(&r.dr), 5.3 * r.dr.counts_per_rad - 12345.0, 1.0);

    dp.type = LRT_DRIVE_STEPPER_OPEN; /* krokowiec bez sprzezenia nie ma enkodera */
    LRT_CHECK(lrt_drive_params_check(&dp) == LRT_DRIVE_ERR_RESOLUTION);
    dp = hm_servo(1e-4);
    dp.encoder = 3;
    LRT_CHECK(lrt_drive_params_check(&dp) == LRT_DRIVE_ERR_RESOLUTION);
    dp.encoder = LRT_ENC_IDEAL;
    dp.hardstop_time_s = -1.0;
    LRT_CHECK(lrt_drive_params_check(&dp) == LRT_DRIVE_ERR_LIMITS);
}

static void test_encoder_battery_loss_keeps_single_turn_and_needs_homing(void)
{
    /* REQ-VM-07 (d): awaria baterii = utrata licznika obrotow, E-4211, nowa baza */
    rig r;
    hm_env e;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = hm_servo(1e-4);
    double th0 = 3.7 * 2.0 * PI;
    double cpr = 131072.0;
    int32_t off = 0;
    int valid = 1;
    int32_t pos;

    memset(&e, 0, sizeof(e));
    dp.encoder = LRT_ENC_ABSOLUTE;
    dp.homing_method = 35;
    rig_init(&r, &ap, &dp, 1e-4);
    lrt_axis_reset(&r.ax, th0);
    rig_feedback(&r);
    LRT_CHECK(lrt_drive_set_absolute(&r.dr, 777, 0) == LRT_DRIVE_OK);
    hm_enable(&r, &e);
    pos = lrt_drive_position_actual(&r.dr);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);
    LRT_CHECK(pos >= 0 && pos < (int32_t)cpr);          /* zostal jeden obrot */
    LRT_CHECK_ABS(pos, 0.7 * cpr, 2.0);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_FAULT);        /* awaria przy pierwszym wlaczeniu */
    LRT_CHECK(lrt_drive_error_code(&r.dr) == 0xFF03u);
    LRT_CHECK(strcmp(lrt_drive_fault_alarm(LRT_DRIVE_FAULT_ENCODER_BATTERY), "E-4211") == 0);
    LRT_CHECK(lrt_drive_get_absolute(&r.dr, &off, &valid) == LRT_DRIVE_OK && valid == 0);

    /* Reset awarii jest mozliwy (jednorazowa), ale pozycja dalej niewazna do bazowania. */
    lrt_drive_set_controlword(&r.dr, LRT_CW_FAULT_RESET);
    hm_step(&r, &e);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_SWITCH_ON_DISABLED);
    hm_enable(&r, &e);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    LRT_CHECK(lrt_drive_od_write(&r.dr, 0x607Cu, 0, 5000) == LRT_DRIVE_OK);
    LRT_CHECK(hm_run(&r, &e, 0.01) == LRT_HM_DONE);
    LRT_CHECK((lrt_drive_statusword(&r.dr) & LRT_SW_HOMING_ATTAINED) != 0u);
    LRT_CHECK_ABS(lrt_drive_position_actual(&r.dr), 5000.0, 3.0);
    LRT_CHECK(lrt_drive_get_absolute(&r.dr, &off, &valid) == LRT_DRIVE_OK && valid == 1);
    LRT_CHECK_ABS((double)off, th0 * r.dr.counts_per_rad - 5000.0, 3.0);
}

/* Bazowanie metoda `method` od kata th0; zwraca faze koncowa. */
static int hm_home_from(rig *r, hm_env *e, lrt_drive_params dp, int method, double th0)
{
    lrt_axis_params ap = servo_axis();

    dp.homing_method = (int8_t)method;
    rig_init(r, &ap, &dp, 1e-4);
    lrt_axis_reset(&r->ax, th0);
    rig_feedback(r);
    hm_enable(r, e);
    LRT_CHECK(rig_state(r) == LRT_DRIVE_OPERATION_ENABLED);
    return hm_run(r, e, 10.0);
}

static void test_homing_limit_switch_method_17_is_repeatable(void)
{
    /* REQ-VM-07 (a): krancowka ujemna, zjazd do zbocza; baza = zbocze niezaleznie od startu */
    static const double starts[3] = {3.0, 9.5, -1.0};
    rig r;
    hm_env e;
    lrt_drive_params dp = hm_servo(1e-4);
    int i;

    dp.home_offset = 1000;
    for (i = 0; i < 3; i++) {
        memset(&e, 0, sizeof(e));
        e.use_neg = 1;
        e.neg_at = -2.0;
        LRT_CHECK(hm_home_from(&r, &e, dp, 17, starts[i]) == LRT_HM_DONE);
        LRT_CHECK((lrt_drive_statusword(&r.dr) &
                   (LRT_SW_HOMING_ATTAINED | LRT_SW_TARGET_REACHED | LRT_SW_HOMING_ERROR)) ==
                  (LRT_SW_HOMING_ATTAINED | LRT_SW_TARGET_REACHED));
        /* Zbocze krancowki (wal -2 rad) ma pozycje 607Ch = 1000; tolerancja: droga 1 kroku
         * z predkoscia 6099h:2 (ok. 3 impulsy) i kwantyzacja. */
        LRT_CHECK_ABS(hm_reported_at(&r, -2.0), 1000.0, 8.0);
        LRT_CHECK(r.ax.th_m > -2.0); /* zatrzymanie poza krancowka */
        LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);
    }
}

static void test_homing_limit_and_index_method_1(void)
{
    /* REQ-VM-07 (b): krancowka + impuls indeksu: baza na pierwszym indeksie za zboczem */
    rig r;
    hm_env e;
    lrt_drive_params dp = hm_servo(1e-4);

    memset(&e, 0, sizeof(e));
    e.use_neg = 1;
    e.neg_at = -2.0;
    LRT_CHECK(hm_home_from(&r, &e, dp, 1, 4.0) == LRT_HM_DONE);
    /* Pierwszy indeks w kierunku dodatnim od -2 rad to kat 0. */
    LRT_CHECK_ABS(hm_reported_at(&r, 0.0), 0.0, 8.0);
    LRT_CHECK(r.ax.th_m > 0.0);
}

static void test_homing_home_switch_and_index_only_methods(void)
{
    /* REQ-VM-07 (a, b): czujnik bazowy (21, 5) i sam indeks (34) */
    rig r;
    hm_env e;
    lrt_drive_params dp = hm_servo(1e-4);

    memset(&e, 0, sizeof(e));
    e.use_home = 1;
    e.home_at = 1.0;
    e.home_below = 1; /* czujnik po stronie ujemnej: aktywny ponizej 1 rad */
    LRT_CHECK(hm_home_from(&r, &e, dp, 21, 4.0) == LRT_HM_DONE); /* szukanie w dol od 4 rad */
    LRT_CHECK_ABS(hm_reported_at(&r, 1.0), 0.0, 8.0);

    memset(&e, 0, sizeof(e));
    e.use_home = 1;
    e.home_at = 1.0;
    e.home_below = 1;
    LRT_CHECK(hm_home_from(&r, &e, dp, 5, 4.0) == LRT_HM_DONE); /* zbocze 1 rad, indeks 2*pi */
    LRT_CHECK_ABS(hm_reported_at(&r, 2.0 * PI), 0.0, 8.0);

    memset(&e, 0, sizeof(e));
    e.use_home = 1;
    e.home_at = 1.0; /* czujnik po stronie dodatniej, szukanie w gore od -3 rad */
    LRT_CHECK(hm_home_from(&r, &e, dp, 19, -3.0) == LRT_HM_DONE);
    LRT_CHECK_ABS(hm_reported_at(&r, 1.0), 0.0, 8.0);
    LRT_CHECK(r.ax.th_m < 1.0);

    memset(&e, 0, sizeof(e));
    LRT_CHECK(hm_home_from(&r, &e, dp, 34, 0.5) == LRT_HM_DONE); /* indeks w gore: 2*pi */
    LRT_CHECK_ABS(hm_reported_at(&r, 2.0 * PI), 0.0, 8.0);
}

static void test_homing_errors_unsupported_limit_first_and_abort(void)
{
    /* REQ-VM-07 (e): blad bazowania jako bit 13, bez awarii napedu */
    rig r;
    hm_env e;
    lrt_drive_params dp = hm_servo(1e-4);
    long i;

    memset(&e, 0, sizeof(e));
    LRT_CHECK(hm_home_from(&r, &e, dp, 7, 0.0) == LRT_HM_ERROR); /* nieobslugiwana */
    LRT_CHECK((lrt_drive_statusword(&r.dr) & LRT_SW_HOMING_ERROR) != 0u);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED);

    memset(&e, 0, sizeof(e));
    e.use_home = 1;
    e.home_at = 20.0; /* czujnik za krancowka */
    e.use_pos = 1;
    e.pos_at = 6.0;
    LRT_CHECK(hm_home_from(&r, &e, dp, 19, 0.0) == LRT_HM_ERROR);
    for (i = 0; i < 2000; i++) {
        hm_step(&r, &e);
    }
    LRT_CHECK(fabs(r.ax.w_m) < 0.05); /* blad = zatrzymanie */

    /* Przerwanie: zdjecie bitu 4 w czasie szukania. */
    memset(&e, 0, sizeof(e));
    e.use_neg = 1;
    e.neg_at = -50.0;
    dp.homing_method = 17;
    {
        lrt_axis_params ap = servo_axis();
        rig_init(&r, &ap, &dp, 1e-4);
    }
    hm_enable(&r, &e);
    lrt_drive_set_controlword(&r.dr, LRT_CW_CMD_ENABLE_OPERATION | LRT_CW_HOMING_START);
    for (i = 0; i < 1000; i++) {
        hm_step(&r, &e);
    }
    LRT_CHECK(lrt_drive_homing_state(&r.dr) == LRT_HM_SEARCH);
    lrt_drive_set_controlword(&r.dr, LRT_CW_CMD_ENABLE_OPERATION);
    hm_step(&r, &e);
    LRT_CHECK(lrt_drive_homing_state(&r.dr) == LRT_HM_ERROR);
    LRT_CHECK((lrt_drive_statusword(&r.dr) & LRT_SW_HOMING_ATTAINED) == 0u);
}

static void test_homing_hardstop_in_drive_with_reduced_torque(void)
{
    /* REQ-VM-07 (c, e): zderzak bez czujnika, limit 6072h, baza w miejscu styku */
    rig r;
    hm_env e;
    lrt_axis_params ap = servo_axis();
    lrt_drive_params dp = hm_servo(1e-4);
    long i;

    memset(&e, 0, sizeof(e));
    ap.use_stops = 1;
    ap.stop_min = -2.0;
    ap.stop_max = 100.0;
    ap.stop_stiffness = 2000.0; /* N*m/rad */
    ap.stop_damping_ratio = 0.5;
    dp.homing_method = -1;
    dp.torque_limit_permille = 300u;   /* zredukowany moment: 0,38 N*m */
    dp.hardstop_time_s = 0.05;
    rig_init(&r, &ap, &dp, 1e-4);
    lrt_axis_reset(&r.ax, 1.0);
    rig_feedback(&r);
    hm_enable(&r, &e);
    LRT_CHECK(hm_run(&r, &e, 10.0) == LRT_HM_DONE);
    LRT_CHECK(rig_state(&r) == LRT_DRIVE_OPERATION_ENABLED); /* bez awarii nadazania */
    /* Wgniecenie zderzaka przy 0,38 N*m i 2000 N*m/rad: ok. 0,2 mrad. */
    LRT_CHECK_ABS(hm_reported_at(&r, -2.0), 0.0, 0.002 * r.dr.counts_per_rad);
    for (i = 0; i < 2000; i++) {
        hm_step(&r, &e);
    }
    LRT_CHECK(fabs(r.tau) < 0.2); /* po bazie bez docisku do zderzaka */

    /* Krokowiec bez sprzezenia nie wykryje zderzaka: blad bazowania. */
    ap = stepper_axis();
    dp = stepper_drive();
    dp.homing_method = -1;
    rig_init(&r, &ap, &dp, 1e-4);
    memset(&e, 0, sizeof(e));
    hm_enable(&r, &e);
    LRT_CHECK(hm_run(&r, &e, 0.01) == LRT_HM_ERROR);
}

static void test_homing_stepper_open_on_limit_switch_and_back_to_csp(void)
{
    /* REQ-VM-07 (a, e): krokowiec bazuje na krancowce; potem CSP od pozycji raportowanej */
    rig r;
    hm_env e;
    lrt_axis_params ap = stepper_axis();
    lrt_drive_params dp = stepper_drive();
    int32_t p0;
    long i;

    memset(&e, 0, sizeof(e));
    e.use_neg = 1;
    e.neg_at = -1.0;
    dp.homing_method = 17;
    rig_init(&r, &ap, &dp, 1e-4);
    lrt_axis_reset(&r.ax, 2.0);
    rig_feedback(&r);
    hm_enable(&r, &e);
    LRT_CHECK(hm_run(&r, &e, 10.0) == LRT_HM_DONE);
    LRT_CHECK(lrt_drive_lost_steps(&r.dr) == 0);
    /* Pozycja raportowana przy wale -1 rad = 0 (krok 1,96 mrad przy 3200 imp/obr). */
    LRT_CHECK_ABS(hm_reported_at(&r, -1.0), 0.0, 4.0);
    LRT_CHECK_ABS(r.ax.th_m * r.dr.counts_per_rad - (double)lrt_drive_position_offset(&r.dr),
                  (double)lrt_drive_position_actual(&r.dr), 4.0);

    /* Master przechodzi do CSP i jedzie o +1600 impulsow (pol obrotu). */
    LRT_CHECK(lrt_drive_od_write(&r.dr, 0x6060u, 0, LRT_MODE_CSP) == LRT_DRIVE_OK);
    p0 = lrt_drive_position_actual(&r.dr);
    lrt_drive_set_controlword(&r.dr, LRT_CW_CMD_ENABLE_OPERATION);
    for (i = 0; i <= 5000; i++) {
        lrt_drive_set_target_position(&r.dr, p0 + (int32_t)(1600 * i / 5000));
        hm_step(&r, &e);
    }
    for (i = 0; i < 3000; i++) {
        hm_step(&r, &e);
    }
    LRT_CHECK_ABS(r.ax.th_m, -1.0 + (double)(p0 + 1600) / r.dr.counts_per_rad, 0.01);
    LRT_CHECK(lrt_drive_lost_steps(&r.dr) == 0);
}

int main(void)
{
    LRT_RUN(test_params_default_valid_for_all_types);
    LRT_RUN(test_params_check_rejects_invalid);
    LRT_RUN(test_init_and_strerror);
    LRT_RUN(test_fault_table_complete);
    LRT_RUN(test_tune_servo_formulas_and_bandwidth_clamp);
    LRT_RUN(test_boot_delay_and_statusword_masks);
    LRT_RUN(test_nominal_sequence_and_statuswords);
    LRT_RUN(test_illegal_commands_are_ignored);
    LRT_RUN(test_disable_voltage_from_every_state);
    LRT_RUN(test_shutdown_and_disable_operation_from_operation);
    LRT_RUN(test_quick_stop_ramp_servo);
    LRT_RUN(test_quick_stop_option_1_disables_immediately);
    LRT_RUN(test_fault_injection_reaction_and_reset);
    LRT_RUN(test_fault_reset_needs_edge_and_cleared_cause);
    LRT_RUN(test_injected_fault_from_disabled_state_and_invalid_code);
    LRT_RUN(test_fault_reaction_option_2_ramps_down);
    LRT_RUN(test_following_error_fault_after_window_time);
    LRT_RUN(test_following_error_short_excursion_is_tolerated);
    LRT_RUN(test_following_window_object_write_takes_effect);
    LRT_RUN(test_csp_step_response_settles_without_big_overshoot);
    LRT_RUN(test_csp_ramp_error_without_ff_matches_v_over_kp);
    LRT_RUN(test_csp_velocity_ff_removes_ramp_error);
    LRT_RUN(test_csp_load_torque_error_without_and_with_integral);
    LRT_RUN(test_csp_torque_limit_object_6072);
    LRT_RUN(test_csp_integrator_does_not_wind_up_in_saturation);
    LRT_RUN(test_csp_acceleration_feedforward_provides_inertia_torque);
    LRT_RUN(test_csp_velocity_and_torque_offsets_feed_forward);
    LRT_RUN(test_encoder_quantization_and_report);
    LRT_RUN(test_encoder_noise_is_reproducible_and_scaled);
    LRT_RUN(test_overload_trips_after_i2t_time_and_needs_cooldown);
    LRT_RUN(test_od_read_write_ranges_and_access);
    LRT_RUN(test_od_6072_bounds_follow_peak_torque);
    LRT_RUN(test_od_homing_objects_roundtrip);
    LRT_RUN(test_od_mode_and_options);
    LRT_RUN(test_od_status_and_actual_values_follow_drive);
    LRT_RUN(test_stepper_follows_reasonable_acceleration_without_loss);
    LRT_RUN(test_stepper_loses_steps_when_acceleration_exceeds_torque);
    LRT_RUN(test_stepper_cannot_follow_speed_above_pullout_curve);
    LRT_RUN(test_stepper_holding_angle_under_load);
    LRT_RUN(test_stepper_load_above_holding_torque_slips);
    LRT_RUN(test_stepper_torque_limit_scales_holding_torque);
    LRT_RUN(test_stepper_enable_snaps_to_nearest_equilibrium_without_counting_loss);
    LRT_RUN(test_stepper_slip_counter_has_hysteresis);
    LRT_RUN(test_stepper_quick_stop_ramps_field_without_loss);
    LRT_RUN(test_closed_stepper_follows_without_fault);
    LRT_RUN(test_closed_stepper_alarms_when_error_exceeds_threshold);
    LRT_RUN(test_step_rejects_bad_input_and_keeps_state);
    LRT_RUN(test_simulation_is_deterministic);
    LRT_RUN(test_accessors_tolerate_null);
    LRT_RUN(test_drive_live_torque_limit_logged_with_time);
    LRT_RUN(test_drive_live_heavier_load_lowers_max_acceleration);
    LRT_RUN(test_encoder_incremental_starts_at_zero_absolute_keeps_offset);
    LRT_RUN(test_encoder_battery_loss_keeps_single_turn_and_needs_homing);
    LRT_RUN(test_homing_limit_switch_method_17_is_repeatable);
    LRT_RUN(test_homing_limit_and_index_method_1);
    LRT_RUN(test_homing_home_switch_and_index_only_methods);
    LRT_RUN(test_homing_errors_unsupported_limit_first_and_abort);
    LRT_RUN(test_homing_hardstop_in_drive_with_reduced_torque);
    LRT_RUN(test_homing_stepper_open_on_limit_switch_and_back_to_csp);
    return lrt_summary();
}
