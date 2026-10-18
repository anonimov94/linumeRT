/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - testy rdzenia dynamiki osi (plant/core/axis.c).
 * Model-Author: Claude
 *
 * Kazdy test porownuje wynik z rozwiazaniem analitycznym (tolerancja <= 1 %).
 * NIEZWERYFIKOWANE NA SPRZECIE: zgodnosc z prawdziwa maszyna nie jest sprawdzana.
 */
#include <math.h>
#include <string.h>

#include "../axis.h"
#include "lrt_test.h"

#define PI 3.14159265358979323846

static lrt_axis_params base_params(void)
{
    lrt_axis_params p;

    lrt_axis_params_default(&p);
    return p;
}

static void init_ok(lrt_axis *a, const lrt_axis_params *p)
{
    int rc = lrt_axis_init(a, p);

    LRT_CHECK(rc == LRT_AXIS_OK);
}

static void run_steps(lrt_axis *a, double tau, double dt, int n)
{
    int i;

    for (i = 0; i < n; i++) {
        int rc = lrt_axis_step(a, tau, dt);

        if (rc != LRT_AXIS_OK) {
            LRT_CHECK(rc == LRT_AXIS_OK);
            return;
        }
    }
}

/* 1. Stały moment bez tarcia: omega = tau*t/J, theta = tau*t^2/(2J). */
static void test_const_torque_matches_analytic(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double j = p.j_motor + p.j_screw + p.load * p.ratio * p.ratio;
    double t = 0.01;

    init_ok(&a, &p);
    run_steps(&a, 0.5, 1e-3, 10);
    LRT_CHECK_REL(a.w_m, 0.5 / j * t, 0.01);
    LRT_CHECK_REL(a.th_m, 0.5 * (0.5 / j) * t * t, 0.01);
    LRT_CHECK_REL(a.pos, 0.5 * (0.5 / j) * t * t * p.ratio, 0.01);
    LRT_CHECK_REL(a.vel, a.w_m * p.ratio, 1e-12);
}

/* 2. Masa: przy zerowej bezwladnosci silnika a = F/m, F = tau/ratio. */
static void test_mass_gives_f_equals_ma(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double force;

    p.j_motor = 0.0;
    p.j_screw = 0.0;
    p.load = 20.0;
    init_ok(&a, &p);
    run_steps(&a, 0.5, 1e-4, 50); /* 5 ms: omega ~ 200 rad/s, jeszcze w zakresie krzywej */
    force = 0.5 / p.ratio;
    LRT_CHECK_REL(a.vel, force / p.load * 0.005, 0.01);
}

/* 3. Wplyw masy na przyspieszenie: a1/a2 = J2/J1. */
static void test_heavier_load_accelerates_slower(void)
{
    lrt_axis_params p1 = base_params();
    lrt_axis_params p2 = base_params();
    lrt_axis a1;
    lrt_axis a2;
    double j1;
    double j2;

    p1.load = 20.0;
    p2.load = 200.0;
    init_ok(&a1, &p1);
    init_ok(&a2, &p2);
    j1 = lrt_axis_j_total(&a1);
    j2 = lrt_axis_j_total(&a2);
    run_steps(&a1, 0.3, 1e-4, 50);
    run_steps(&a2, 0.3, 1e-4, 50);
    LRT_CHECK(j2 > j1);
    LRT_CHECK_REL(a1.w_m / a2.w_m, j2 / j1, 0.01);
}

/* 4. Bezwladnosc zastepcza: liniowa i obrotowa (przelozenie 1:90). */
static void test_reflected_inertia_linear_and_rotary(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;

    init_ok(&a, &p);
    LRT_CHECK_REL(lrt_axis_j_total(&a), p.j_motor + p.j_screw + p.load * p.ratio * p.ratio, 1e-12);

    p.kind = LRT_AXIS_ROTARY;
    p.ratio = 1.0 / 90.0;
    p.load = 0.05; /* kg*m^2 na stole */
    init_ok(&a, &p);
    LRT_CHECK_REL(lrt_axis_j_total(&a), p.j_motor + p.j_screw + 0.05 / 8100.0, 1e-12);
}

/* 5. Os obrotowa: kat stolu = kat silnika / 90, przyspieszenie z J_tot. */
static void test_rotary_axis_motion(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double j;

    p.kind = LRT_AXIS_ROTARY;
    p.ratio = 1.0 / 90.0;
    p.load = 0.05;
    init_ok(&a, &p);
    j = lrt_axis_j_total(&a);
    run_steps(&a, 0.5, 1e-3, 10);
    LRT_CHECK_REL(a.w_m, 0.5 / j * 0.01, 0.01);
    LRT_CHECK_REL(a.vel, a.w_m / 90.0, 1e-12);
    LRT_CHECK_REL(a.pos, a.th_m / 90.0, 1e-12);
}

/* 6. Krzywa moment-predkosc: interpolacja, symetria, zero powyzej konca. */
static void test_torque_curve_interpolation(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;

    p.curve[0].omega = 0.0;
    p.curve[0].torque = 2.0;
    p.curve[1].omega = 100.0;
    p.curve[1].torque = 2.0;
    p.curve[2].omega = 200.0;
    p.curve[2].torque = 1.0;
    p.curve[3].omega = 300.0;
    p.curve[3].torque = 0.2;
    p.n_curve = 4;
    init_ok(&a, &p);
    LRT_CHECK_REL(lrt_axis_torque_limit(&a, 0.0), 2.0, 1e-12);
    LRT_CHECK_REL(lrt_axis_torque_limit(&a, 50.0), 2.0, 1e-12);
    LRT_CHECK_REL(lrt_axis_torque_limit(&a, 150.0), 1.5, 1e-12);
    LRT_CHECK_REL(lrt_axis_torque_limit(&a, 250.0), 0.6, 1e-12);
    LRT_CHECK_REL(lrt_axis_torque_limit(&a, 300.0), 0.2, 1e-12);
    LRT_CHECK_REL(lrt_axis_torque_limit(&a, -250.0), 0.6, 1e-12);
    LRT_CHECK_ABS(lrt_axis_torque_limit(&a, 400.0), 0.0, 1e-12);
}

/* 7. Obciecie momentu krzywa: przyspieszenie z momentu dostepnego + zdarzenie. */
static void test_torque_clipped_by_curve(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double j;

    lrt_axis_set_flat_curve(&p, 1.0, 300.0);
    init_ok(&a, &p);
    j = lrt_axis_j_total(&a);
    run_steps(&a, 10.0, 1e-3, 5);
    LRT_CHECK_REL(a.torque_applied, 1.0, 1e-12);
    LRT_CHECK_REL(a.w_m, 1.0 / j * 0.005, 0.01);
    LRT_CHECK((lrt_axis_events(&a) & LRT_AXIS_EV_TORQUE_LIMITED) != 0);

    lrt_axis_reset(&a, 0.0);
    run_steps(&a, 0.5, 1e-3, 5);
    LRT_CHECK((lrt_axis_events(&a) & LRT_AXIS_EV_TORQUE_LIMITED) == 0);
    LRT_CHECK_REL(a.torque_applied, 0.5, 1e-12);
}

/* 8. Tarcie lepkie: omega(t) = omega_inf*(1 - exp(-b t / J)), omega_inf = tau/b. */
static void test_viscous_friction_exponential(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double j;
    double b = 0.002;
    double tau = 0.4;
    double w_inf = tau / b;

    p.friction_viscous = b;
    lrt_axis_set_flat_curve(&p, 1.0, 1000.0);
    init_ok(&a, &p);
    j = lrt_axis_j_total(&a);
    run_steps(&a, tau, 2e-4, 250); /* t = 0.05 s */
    LRT_CHECK_REL(a.w_m, w_inf * (1.0 - exp(-b * 0.05 / j)), 0.01);
    run_steps(&a, tau, 2e-4, 1250); /* t = 0.3 s */
    LRT_CHECK_REL(a.w_m, w_inf, 0.01);
}

/* 9. Tarcie Coulomba: a = (tau - tau_c)/J po oderwaniu. */
static void test_coulomb_friction_reduces_acceleration(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double j;

    p.friction_coulomb = 0.2;
    p.friction_static = 0.3;
    init_ok(&a, &p);
    j = lrt_axis_j_total(&a);
    run_steps(&a, 0.5, 1e-4, 100);
    LRT_CHECK_REL(a.w_m, (0.5 - 0.2) / j * 0.01, 0.01);
    LRT_CHECK(a.sticking == 0);
}

/* 10. Tarcie statyczne: ponizej momentu odrywania stoi, powyzej rusza (oba kierunki). */
static void test_static_friction_breakaway(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;

    p.friction_coulomb = 0.2;
    p.friction_static = 0.3;
    init_ok(&a, &p);

    run_steps(&a, 0.25, 1e-3, 100);
    LRT_CHECK_ABS(a.pos, 0.0, 1e-15);
    LRT_CHECK_ABS(a.w_m, 0.0, 1e-15);
    LRT_CHECK(a.sticking == 1);

    run_steps(&a, -0.29, 1e-3, 100);
    LRT_CHECK_ABS(a.pos, 0.0, 1e-15);
    LRT_CHECK(a.sticking == 1);

    run_steps(&a, 0.35, 1e-3, 20);
    LRT_CHECK(a.pos > 1e-6);
    LRT_CHECK(a.sticking == 0);

    lrt_axis_reset(&a, 0.0);
    run_steps(&a, -0.35, 1e-3, 20);
    LRT_CHECK(a.pos < -1e-6);
}

/* 11. Wybieg z tarciem Coulomba: czas do zatrzymania t = J*omega0/tau_c. */
static void test_coulomb_coast_stop_time(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double j;
    double w0;
    double t = 0.0;
    const double dt = 1e-5;
    int guard = 0;

    p.friction_coulomb = 0.2;
    p.friction_static = 0.2;
    init_ok(&a, &p);
    j = lrt_axis_j_total(&a);
    run_steps(&a, 0.5, 1e-4, 50);
    w0 = a.w_m;
    LRT_CHECK(w0 > 1.0);
    while (a.sticking == 0 && guard++ < 100000) {
        if (lrt_axis_step(&a, 0.0, dt) != LRT_AXIS_OK) {
            LRT_CHECK(0);
            break;
        }
        t += dt;
    }
    LRT_CHECK_REL(t, j * w0 / 0.2, 0.01);
    LRT_CHECK_ABS(a.w_m, 0.0, 1e-12);
}

/* 12. Grawitacja osi Z: swobodny spadek a = F*ratio^2/J, a przy zerowej J silnika a = g. */
static void test_gravity_free_fall_and_hold(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double j;

    p.j_motor = 0.0;
    p.j_screw = 0.0;
    p.load = 20.0;
    p.gravity_force = -20.0 * 9.81;
    init_ok(&a, &p);
    run_steps(&a, 0.0, 1e-3, 100); /* 0.1 s */
    LRT_CHECK_REL(a.pos, -0.5 * 9.81 * 0.1 * 0.1, 0.01);

    p.j_motor = 5e-5;
    p.j_screw = 2e-5;
    init_ok(&a, &p);
    j = lrt_axis_j_total(&a);
    run_steps(&a, 0.0, 1e-3, 100);
    LRT_CHECK_REL(a.pos, -0.5 * (p.gravity_force * p.ratio * p.ratio / j) * -1.0 * 0.01, 0.01);

    /* moment trzymajacy rowny sile grawitacji sprowadzonej na wal => brak ruchu */
    lrt_axis_reset(&a, 0.1);
    run_steps(&a, 20.0 * 9.81 * p.ratio, 1e-3, 200);
    LRT_CHECK_ABS(a.pos, 0.1, 1e-9);
    LRT_CHECK_ABS(a.vel, 0.0, 1e-9);
}

/* 13. Wybieg bez tarcia: predkosc stala (zachowanie pedu). */
static void test_coasting_conserves_velocity(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double w0;

    init_ok(&a, &p);
    run_steps(&a, 0.5, 1e-4, 50);
    w0 = a.w_m;
    run_steps(&a, 0.0, 1e-3, 1000);
    LRT_CHECK_REL(a.w_m, w0, 1e-9);
}

/* 14. Niezaleznosc od kroku czasu: dt=1 ms vs 4 x 0.25 ms, oba wg wzoru analitycznego. */
static void test_step_size_independence(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a1;
    lrt_axis a2;
    double j;
    double tau = 0.3;
    double w_inf;
    double expected;

    p.friction_coulomb = 0.1;
    p.friction_static = 0.15;
    p.friction_viscous = 0.001;
    lrt_axis_set_flat_curve(&p, 1.0, 1000.0);
    init_ok(&a1, &p);
    init_ok(&a2, &p);
    j = lrt_axis_j_total(&a1);
    w_inf = (tau - 0.1) / 0.001;
    expected = w_inf * (1.0 - exp(-0.001 * 0.2 / j));
    run_steps(&a1, tau, 1e-3, 200);
    run_steps(&a2, tau, 2.5e-4, 800);
    LRT_CHECK_REL(a1.w_m, expected, 0.01);
    LRT_CHECK_REL(a2.w_m, expected, 0.01);
    LRT_CHECK_REL(a1.w_m, a2.w_m, 0.01);
}

/* 15. Luz: silnik pokonuje calkowity luz zanim obciazenie ruszy (z tarciem trzymajacym). */
static void test_backlash_total_travel_on_reversal(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double gap_rad;
    double k;
    double th_pos_contact;
    double th_neg_contact;

    p.backlash = 0.5e-3; /* 0.5 mm */
    p.load = 20.0;
    /* obciazenie trzymane tarciem; wieksze od szczytu momentu uderzenia w luz (~10 N*m) */
    p.friction_coulomb = 50.0;
    p.friction_static = 50.0;
    init_ok(&a, &p);
    k = LRT_AXIS_DEFAULT_CONTACT_STIFFNESS;
    gap_rad = p.backlash / p.ratio;

    run_steps(&a, 1.0, 1e-4, 3000); /* 0.3 s: docisk po stronie dodatniej */
    th_pos_contact = a.th_m;
    LRT_CHECK_REL(th_pos_contact, 0.5 * gap_rad + 1.0 / k, 0.01);
    LRT_CHECK_ABS(a.pos, 0.0, 1e-15);

    run_steps(&a, -1.0, 1e-4, 3000);
    th_neg_contact = a.th_m;
    LRT_CHECK_REL(th_pos_contact - th_neg_contact, gap_rad + 2.0 / k, 0.01);
    LRT_CHECK_REL((th_pos_contact - th_neg_contact - 2.0 / k) * p.ratio, p.backlash, 0.01);
    LRT_CHECK_ABS(a.pos, 0.0, 1e-15); /* obciazenie nie drgnelo */
}

/* 16. Luz: obciazenie bez tarcia rusza dopiero po zamknieciu polowy luzu. */
static void test_backlash_load_moves_after_gap_closes(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    int i;
    double th_at_move = -1.0;

    p.backlash = 0.5e-3;
    init_ok(&a, &p);
    for (i = 0; i < 5000; i++) {
        run_steps(&a, 1.0, 1e-5, 1);
        if (fabs(a.pos) > 1e-9) {
            th_at_move = a.th_m;
            break;
        }
    }
    LRT_CHECK(th_at_move > 0.0);
    LRT_CHECK_REL(th_at_move * p.ratio, 0.5 * p.backlash, 0.02);
}

/* 17. Podatnosc bez luzu przy duzej sztywnosci zachowuje sie jak ciało sztywne. */
static void test_stiff_coupling_equals_rigid_body(void)
{
    lrt_axis_params rigid = base_params();
    lrt_axis_params stiff = base_params();
    lrt_axis a_r;
    lrt_axis a_s;

    stiff.stiffness = 5e4;
    init_ok(&a_r, &rigid);
    init_ok(&a_s, &stiff);
    LRT_CHECK(a_s.two_body == 1);
    run_steps(&a_r, 0.5, 1e-3, 10);
    run_steps(&a_s, 0.5, 1e-3, 10);
    LRT_CHECK_REL(a_s.pos, a_r.pos, 0.01);
    LRT_CHECK_REL(a_s.vel, a_r.vel, 0.01);
}

/* 18. Zderzak sztywny: zdarzenie, obciecie pozycji, predkosc uderzenia, zerowanie predkosci. */
static void test_rigid_hardstop_max_and_min(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double j;
    double acc;
    double v_expected;
    int i;

    p.use_stops = 1;
    p.stop_min = -0.05;
    p.stop_max = 0.05;
    p.stop_stiffness = 0.0;
    lrt_axis_set_flat_curve(&p, 1.0, 2000.0); /* v_uderzenia ~ 0.69 m/s = ~870 rad/s */
    init_ok(&a, &p);
    j = lrt_axis_j_total(&a);
    acc = 0.5 * p.ratio / j; /* m/s^2 */
    v_expected = sqrt(2.0 * acc * 0.05);
    for (i = 0; i < 5000 && (lrt_axis_events(&a) & LRT_AXIS_EV_HARDSTOP_MAX) == 0; i++) {
        run_steps(&a, 0.5, 1e-4, 1);
    }
    LRT_CHECK((lrt_axis_events(&a) & LRT_AXIS_EV_HARDSTOP_MAX) != 0);
    LRT_CHECK((lrt_axis_events(&a) & LRT_AXIS_EV_HARDSTOP_MIN) == 0);
    LRT_CHECK_REL(a.impact_speed, v_expected, 0.01);
    LRT_CHECK(a.pos <= 0.05 + 1e-12);
    LRT_CHECK_ABS(a.pos, 0.05, 1e-6);
    LRT_CHECK_ABS(a.vel, 0.0, 1e-12);

    /* dalszy docisk nie przesuwa osi poza zderzak */
    run_steps(&a, 0.5, 1e-3, 100);
    LRT_CHECK(a.pos <= 0.05 + 1e-12);

    lrt_axis_clear_events(&a);
    LRT_CHECK(lrt_axis_events(&a) == 0);
    LRT_CHECK_ABS(a.impact_speed, 0.0, 1e-15);

    /* zderzak dolny */
    lrt_axis_reset(&a, 0.0);
    for (i = 0; i < 5000 && (lrt_axis_events(&a) & LRT_AXIS_EV_HARDSTOP_MIN) == 0; i++) {
        run_steps(&a, -0.5, 1e-4, 1);
    }
    LRT_CHECK((lrt_axis_events(&a) & LRT_AXIS_EV_HARDSTOP_MIN) != 0);
    LRT_CHECK((lrt_axis_events(&a) & LRT_AXIS_EV_HARDSTOP_MAX) == 0);
    LRT_CHECK(a.pos >= -0.05 - 1e-12);
    LRT_CHECK_REL(a.impact_speed, v_expected, 0.01);
}

/* 19. Zderzak sprezysty bez tlumienia: max penetracja = v*sqrt(M/k) (zachowanie energii). */
static void test_spring_hardstop_penetration(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double m_eff;
    double v0 = 0.3;
    double k = 1e6;
    double pen_max = 0.0;
    int i;

    p.use_stops = 1;
    p.stop_min = -1.0;
    p.stop_max = 0.05;
    p.stop_stiffness = k;
    p.stop_damping_ratio = 0.0;
    init_ok(&a, &p);
    m_eff = lrt_axis_j_total(&a) / (p.ratio * p.ratio);
    lrt_axis_reset(&a, 0.049);
    a.w_m = v0 / p.ratio;
    a.w_l = a.w_m;
    a.vel = v0;
    for (i = 0; i < 4000; i++) {
        double pen;

        run_steps(&a, 0.0, 2e-5, 1);
        pen = a.pos - 0.05;
        if (pen > pen_max) {
            pen_max = pen;
        }
    }
    LRT_CHECK((lrt_axis_events(&a) & LRT_AXIS_EV_HARDSTOP_MAX) != 0);
    LRT_CHECK_REL(a.impact_speed, v0, 0.01);
    LRT_CHECK_REL(pen_max, v0 * sqrt(m_eff / k), 0.01);
    LRT_CHECK(a.vel < 0.0 || a.pos < 0.05); /* odbicie: wraca ze zderzaka */
}

/* 20. Walidacja parametrow: kazdy blad ma wlasny kod i komunikat. */
static void test_params_validation(void)
{
    lrt_axis_params p;
    lrt_axis a;
    int rc;

    LRT_CHECK(lrt_axis_params_check(NULL) == LRT_AXIS_ERR_NULL);
    LRT_CHECK(lrt_axis_init(NULL, NULL) == LRT_AXIS_ERR_NULL);

    p = base_params();
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_OK);

    p = base_params();
    p.load = -1.0;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_INERTIA);
    p = base_params();
    p.j_motor = 0.0;
    p.j_screw = 0.0;
    p.load = 0.0;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_INERTIA);
    p = base_params();
    p.ratio = 0.0;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_RATIO);
    p = base_params();
    p.n_curve = 1;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_CURVE);
    p = base_params();
    p.curve[1].omega = 0.0; /* nie rosnaco */
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_CURVE);
    p = base_params();
    p.curve[1].torque = -0.1;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_CURVE);
    p = base_params();
    p.friction_coulomb = 0.3;
    p.friction_static = 0.2;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_FRICTION);
    p = base_params();
    p.friction_viscous = -1e-3;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_FRICTION);
    p = base_params();
    p.backlash = -1e-4;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_BACKLASH);
    p = base_params();
    p.backlash = 1e-4;
    p.load = 0.0;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_BACKLASH);
    p = base_params();
    p.stiffness = -5.0;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_STIFFNESS);
    p = base_params();
    p.use_stops = 1;
    p.stop_min = 0.1;
    p.stop_max = 0.1;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_STOPS);
    p = base_params();
    p.gravity_force = NAN;
    LRT_CHECK(lrt_axis_params_check(&p) == LRT_AXIS_ERR_NUMERIC);

    /* init z blednymi parametrami zwraca ten sam kod */
    p = base_params();
    p.ratio = -1.0;
    rc = lrt_axis_init(&a, &p);
    LRT_CHECK(rc == LRT_AXIS_ERR_RATIO);

    for (rc = LRT_AXIS_ERR_NUMERIC; rc <= LRT_AXIS_OK; rc++) {
        LRT_CHECK(strlen(lrt_axis_strerror(rc)) >= 2);
    }
    LRT_CHECK(strlen(lrt_axis_strerror(-99)) >= 2);
    LRT_CHECK(strcmp(lrt_axis_strerror(LRT_AXIS_OK), "OK") == 0);
    LRT_CHECK(strcmp(lrt_axis_strerror(LRT_AXIS_ERR_RATIO), lrt_axis_strerror(-99)) != 0);
}

/* 21. Bledy kroku: dt <= 0, NaN; stan nie jest zmieniany. */
static void test_step_rejects_bad_input_without_state_change(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double pos;
    double w;

    init_ok(&a, &p);
    run_steps(&a, 0.5, 1e-3, 5);
    pos = a.pos;
    w = a.w_m;
    LRT_CHECK(lrt_axis_step(&a, 0.5, 0.0) == LRT_AXIS_ERR_DT);
    LRT_CHECK(lrt_axis_step(&a, 0.5, -1e-3) == LRT_AXIS_ERR_DT);
    LRT_CHECK(lrt_axis_step(&a, 0.5, NAN) == LRT_AXIS_ERR_DT);
    LRT_CHECK(lrt_axis_step(&a, NAN, 1e-3) == LRT_AXIS_ERR_NUMERIC);
    LRT_CHECK(lrt_axis_step(&a, INFINITY, 1e-3) == LRT_AXIS_ERR_NUMERIC);
    LRT_CHECK(lrt_axis_step(NULL, 0.5, 1e-3) == LRT_AXIS_ERR_NULL);
    LRT_CHECK(a.pos == pos);
    LRT_CHECK(a.w_m == w);
}

/* 22. Bardzo sztywne polaczenie: podkroki ograniczone do LRT_AXIS_MAX_SUBSTEPS (flaga). */
static void test_substeps_capped_flag(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;

    p.stiffness = 3e5;
    init_ok(&a, &p);
    LRT_CHECK(lrt_axis_step(&a, 0.5, 1e-3) == LRT_AXIS_OK);
    LRT_CHECK((lrt_axis_events(&a) & LRT_AXIS_EV_SUBSTEPS_CAPPED) != 0);
    LRT_CHECK(isfinite(a.pos));
}

/* 23. Reset ustawia pozycje, zeruje predkosci i zdarzenia. */
static void test_reset_clears_state(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;

    init_ok(&a, &p);
    run_steps(&a, 10.0, 1e-3, 20);
    LRT_CHECK(a.vel != 0.0);
    LRT_CHECK(lrt_axis_events(&a) != 0);
    lrt_axis_reset(&a, 0.2);
    LRT_CHECK_ABS(a.pos, 0.2, 1e-15);
    LRT_CHECK_ABS(a.vel, 0.0, 1e-15);
    LRT_CHECK_ABS(a.th_m * p.ratio, 0.2, 1e-12);
    LRT_CHECK(lrt_axis_events(&a) == 0);
}

/* ------------------------------------------------------------------------- */
/* Parametry zmieniane w locie (REQ-VD-04)                                    */
/* ------------------------------------------------------------------------- */

/* REQ-VD-04: wieksza masa w locie => mniejsze przyspieszenie zgodnie z a = T/J; stan zachowany. */
static void test_live_load_change_follows_inertia_formula(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    lrt_live_log log;
    double j1;
    double j2;
    double w0;
    double th0;

    lrt_live_log_init(&log);
    init_ok(&a, &p);
    j1 = lrt_axis_j_total(&a);
    run_steps(&a, 0.3, 1e-4, 50);
    LRT_CHECK_REL(a.w_m, 0.3 / j1 * 0.005, 0.01);
    w0 = a.w_m;
    th0 = a.th_m;
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_LOAD, 200.0, &log) == LRT_AXIS_OK);
    j2 = lrt_axis_j_total(&a);
    LRT_CHECK(j2 > j1);
    LRT_CHECK_ABS(a.w_m, w0, 0.0); /* predkosc i polozenie bez skoku */
    LRT_CHECK_ABS(a.th_m, th0, 0.0);
    run_steps(&a, 0.3, 1e-4, 50);
    LRT_CHECK_REL(a.w_m - w0, 0.3 / j2 * 0.005, 0.01);
    LRT_CHECK(j2 / j1 > 2.0);
}

/* REQ-VD-04: dziennik zapisuje czas modelu, wartosc przed i po; bledy nie trafiaja do dziennika. */
static void test_live_log_records_time_and_values(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    lrt_live_log log;
    lrt_live_entry e;
    double v;

    lrt_live_log_init(&log);
    init_ok(&a, &p);
    run_steps(&a, 0.1, 1e-3, 20);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_FRICTION_VISCOUS, 0.002, &log) == LRT_AXIS_OK);
    run_steps(&a, 0.1, 1e-3, 30);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_SUPPLY_SCALE, 0.5, &log) == LRT_AXIS_OK);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_LOAD, -1.0, &log) == LRT_AXIS_ERR_INERTIA);
    LRT_CHECK(lrt_axis_set_live(&a, 99, 1.0, &log) == LRT_AXIS_ERR_LIVE_ID);
    LRT_CHECK(lrt_live_log_size(&log) == 2u);
    LRT_CHECK(lrt_live_log_get(&log, 0, &e) == 0);
    LRT_CHECK(e.param == LRT_LIVE_FRICTION_VISCOUS);
    LRT_CHECK_ABS(e.t, 0.020, 1e-9);
    LRT_CHECK_ABS(e.old_value, 0.0, 0.0);
    LRT_CHECK_ABS(e.new_value, 0.002, 0.0);
    LRT_CHECK(lrt_live_log_get(&log, 1, &e) == 0);
    LRT_CHECK(e.param == LRT_LIVE_SUPPLY_SCALE);
    LRT_CHECK_ABS(e.t, 0.050, 1e-9);
    LRT_CHECK_ABS(e.old_value, 1.0, 0.0);
    LRT_CHECK(lrt_live_log_get(&log, 2, &e) == -1);
    LRT_CHECK(lrt_axis_get_live(&a, LRT_LIVE_SUPPLY_SCALE, &v) == LRT_AXIS_OK);
    LRT_CHECK_ABS(v, 0.5, 0.0);
    LRT_CHECK(strcmp(lrt_live_param_name(LRT_LIVE_BACKLASH), "backlash") == 0);
    LRT_CHECK(lrt_live_param_name(LRT_LIVE_COUNT) == NULL);
}

/* REQ-VD-04: bufor kolowy dziennika nadpisuje najstarsze wpisy i liczy utracone. */
static void test_live_log_ring_overwrites_oldest(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    lrt_live_log log;
    lrt_live_entry e;
    int i;

    lrt_live_log_init(&log);
    init_ok(&a, &p);
    for (i = 1; i <= LRT_LIVE_LOG_SIZE + 6; i++) {
        LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_LOAD, (double)i, &log) == LRT_AXIS_OK);
    }
    LRT_CHECK(lrt_live_log_size(&log) == (unsigned)LRT_LIVE_LOG_SIZE);
    LRT_CHECK(lrt_live_log_dropped(&log) == 6u);
    LRT_CHECK(lrt_live_log_get(&log, 0, &e) == 0);
    LRT_CHECK_ABS(e.new_value, 7.0, 0.0);
    LRT_CHECK(lrt_live_log_get(&log, LRT_LIVE_LOG_SIZE - 1, &e) == 0);
    LRT_CHECK_ABS(e.new_value, (double)(LRT_LIVE_LOG_SIZE + 6), 0.0);
}

/* REQ-VD-04: napiecie zasilania skaluje moment dostepny; tarcie w locie zmienia hamowanie. */
static void test_live_supply_and_friction(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double full;

    init_ok(&a, &p);
    full = lrt_axis_torque_limit(&a, 100.0);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_SUPPLY_SCALE, 0.6, NULL) == LRT_AXIS_OK);
    LRT_CHECK_REL(lrt_axis_torque_limit(&a, 100.0), 0.6 * full, 1e-12);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_SUPPLY_SCALE, 2.5, NULL) == LRT_AXIS_ERR_LIVE_ID);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_SUPPLY_SCALE, 0.0, NULL) == LRT_AXIS_ERR_LIVE_ID);

    /* tarcie Coulomba: wybieg z predkosci w0 trwa t = J*w0/tau_c */
    init_ok(&a, &p);
    run_steps(&a, 0.3, 1e-4, 50);
    {
        double w0 = a.w_m;
        double j = lrt_axis_j_total(&a);
        int n = 0;

        LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_FRICTION_STATIC, 0.05, NULL) == LRT_AXIS_OK);
        LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_FRICTION_COULOMB, 0.05, NULL) == LRT_AXIS_OK);
        while (a.w_m > 1e-9 && n < 100000) {
            run_steps(&a, 0.0, 1e-4, 1);
            n++;
        }
        LRT_CHECK_REL((double)n * 1e-4, j * w0 / 0.05, 0.02);
    }
}

/* REQ-VD-04: bledne wartosci i zmiany trybu luzu sa odrzucane bez zmiany stanu. */
static void test_live_rejects_invalid_without_change(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    lrt_axis before;

    init_ok(&a, &p);
    run_steps(&a, 0.2, 1e-3, 5);
    before = a;
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_LOAD, NAN, NULL) == LRT_AXIS_ERR_LIVE_ID);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_J_MOTOR, INFINITY, NULL) == LRT_AXIS_ERR_LIVE_ID);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_FRICTION_COULOMB, 0.5, NULL) ==
              LRT_AXIS_ERR_FRICTION); /* static = 0 < coulomb */
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_BACKLASH, -0.001, NULL) == LRT_AXIS_ERR_BACKLASH);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_BACKLASH, 0.0005, NULL) == LRT_AXIS_ERR_LIVE_MODE);
    LRT_CHECK(lrt_axis_set_live(NULL, LRT_LIVE_LOAD, 1.0, NULL) == LRT_AXIS_ERR_NULL);
    LRT_CHECK(memcmp(&a, &before, sizeof(a)) == 0);
}

/* REQ-VD-04: luz zmieniany w locie w modelu dwuczlonowym (stiffness > 0 od poczatku). */
static void test_live_backlash_in_two_body_model(void)
{
    lrt_axis_params p = base_params();
    lrt_axis a;
    double travel;

    p.stiffness = 1.0e4;
    init_ok(&a, &p);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_BACKLASH, 0.0004, NULL) == LRT_AXIS_OK);
    LRT_CHECK_ABS(a.gap_half, 0.5 * 0.0004 / p.ratio, 1e-12);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_BACKLASH, 0.0, NULL) == LRT_AXIS_OK);
    LRT_CHECK_ABS(a.gap_half, 0.0, 0.0);
    LRT_CHECK(lrt_axis_set_live(&a, LRT_LIVE_BACKLASH, 0.0004, NULL) == LRT_AXIS_OK);
    /* silnik rusza w kierunku dodatnim: wal przebywa luz zanim obciazenie ruszy */
    run_steps(&a, 0.05, 1e-4, 200);
    travel = a.th_m - a.th_l;
    LRT_CHECK(travel > 0.0);
    LRT_CHECK(travel <= a.gap_half * 2.0 + 1e-3);
}

int main(void)
{
    LRT_RUN(test_const_torque_matches_analytic);
    LRT_RUN(test_mass_gives_f_equals_ma);
    LRT_RUN(test_heavier_load_accelerates_slower);
    LRT_RUN(test_reflected_inertia_linear_and_rotary);
    LRT_RUN(test_rotary_axis_motion);
    LRT_RUN(test_torque_curve_interpolation);
    LRT_RUN(test_torque_clipped_by_curve);
    LRT_RUN(test_viscous_friction_exponential);
    LRT_RUN(test_coulomb_friction_reduces_acceleration);
    LRT_RUN(test_static_friction_breakaway);
    LRT_RUN(test_coulomb_coast_stop_time);
    LRT_RUN(test_gravity_free_fall_and_hold);
    LRT_RUN(test_coasting_conserves_velocity);
    LRT_RUN(test_step_size_independence);
    LRT_RUN(test_backlash_total_travel_on_reversal);
    LRT_RUN(test_backlash_load_moves_after_gap_closes);
    LRT_RUN(test_stiff_coupling_equals_rigid_body);
    LRT_RUN(test_rigid_hardstop_max_and_min);
    LRT_RUN(test_spring_hardstop_penetration);
    LRT_RUN(test_params_validation);
    LRT_RUN(test_step_rejects_bad_input_without_state_change);
    LRT_RUN(test_substeps_capped_flag);
    LRT_RUN(test_reset_clears_state);
    LRT_RUN(test_live_load_change_follows_inertia_formula);
    LRT_RUN(test_live_log_records_time_and_values);
    LRT_RUN(test_live_log_ring_overwrites_oldest);
    LRT_RUN(test_live_supply_and_friction);
    LRT_RUN(test_live_rejects_invalid_without_change);
    LRT_RUN(test_live_backlash_in_two_body_model);
    return lrt_summary();
}
