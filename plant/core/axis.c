/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - Plant, rdzen dynamiki osi. Opis modelu: axis.h.
 * Model-Author: Claude
 *
 * Calkowanie: półjawny (symplektyczny) Euler dla predkosci, trapez dla pozycji
 * (dokladny przy stalym przyspieszeniu); tarcie lepkie niejawnie (bezwzglednie stabilne),
 * tarcie suche z przejsciem przez zero => stan przylgniecia (stick) z momentem odrywania.
 */
#include "axis.h"

#include <math.h>
#include <string.h>

#define LRT_NO_LIMIT_DT 1e9
#define LRT_STICK_EPS 1e-12
#define LRT_STABILITY_FRACTION 0.05 /* podkrok <= 5 % okresu wlasnego sprezyny / (2*pi) */

/* ---------- parametry ---------- */

void lrt_axis_params_default(lrt_axis_params *p)
{
    if (p == NULL) {
        return;
    }
    memset(p, 0, sizeof(*p));
    p->kind = LRT_AXIS_LINEAR;
    p->j_motor = 5e-5;
    p->j_screw = 2e-5;
    p->load = 20.0;
    p->ratio = 0.005 / (2.0 * 3.14159265358979323846);
    lrt_axis_set_flat_curve(p, 1.0, 300.0);
    p->damping_ratio = 0.7;
    p->stop_damping_ratio = 0.7;
}

void lrt_axis_set_flat_curve(lrt_axis_params *p, double tau, double omega_max)
{
    if (p == NULL) {
        return;
    }
    p->curve[0].omega = 0.0;
    p->curve[0].torque = tau;
    p->curve[1].omega = omega_max;
    p->curve[1].torque = tau;
    p->n_curve = 2;
}

static int bad(double x)
{
    return !isfinite(x);
}

int lrt_axis_params_check(const lrt_axis_params *p)
{
    int i;
    int two_body;

    if (p == NULL) {
        return LRT_AXIS_ERR_NULL;
    }
    if (p->kind != LRT_AXIS_LINEAR && p->kind != LRT_AXIS_ROTARY) {
        return LRT_AXIS_ERR_INERTIA;
    }
    if (bad(p->ratio) || p->ratio <= 0.0) {
        return LRT_AXIS_ERR_RATIO;
    }
    if (bad(p->j_motor) || bad(p->j_screw) || bad(p->load) || p->j_motor < 0.0 ||
        p->j_screw < 0.0 || p->load < 0.0 ||
        p->j_motor + p->j_screw + p->load * p->ratio * p->ratio <= 0.0) {
        return LRT_AXIS_ERR_INERTIA;
    }
    if (p->n_curve < 2 || p->n_curve > LRT_AXIS_CURVE_MAX) {
        return LRT_AXIS_ERR_CURVE;
    }
    for (i = 0; i < p->n_curve; i++) {
        if (bad(p->curve[i].omega) || bad(p->curve[i].torque) || p->curve[i].omega < 0.0 ||
            p->curve[i].torque < 0.0) {
            return LRT_AXIS_ERR_CURVE;
        }
        if (i > 0 && p->curve[i].omega <= p->curve[i - 1].omega) {
            return LRT_AXIS_ERR_CURVE;
        }
    }
    if (bad(p->friction_coulomb) || bad(p->friction_static) || bad(p->friction_viscous) ||
        p->friction_coulomb < 0.0 || p->friction_static < 0.0 || p->friction_viscous < 0.0 ||
        p->friction_static < p->friction_coulomb) {
        return LRT_AXIS_ERR_FRICTION;
    }
    if (bad(p->gravity_force)) {
        return LRT_AXIS_ERR_NUMERIC;
    }
    if (bad(p->backlash) || p->backlash < 0.0) {
        return LRT_AXIS_ERR_BACKLASH;
    }
    if (bad(p->stiffness) || bad(p->damping_ratio) || bad(p->stop_stiffness) ||
        bad(p->stop_damping_ratio) || p->stiffness < 0.0 || p->damping_ratio < 0.0 ||
        p->stop_stiffness < 0.0 || p->stop_damping_ratio < 0.0) {
        return LRT_AXIS_ERR_STIFFNESS;
    }
    two_body = (p->backlash > 0.0 || p->stiffness > 0.0);
    if (two_body && (p->load <= 0.0 || p->j_motor + p->j_screw <= 0.0)) {
        return LRT_AXIS_ERR_BACKLASH;
    }
    if (p->use_stops &&
        (bad(p->stop_min) || bad(p->stop_max) || !(p->stop_min < p->stop_max))) {
        return LRT_AXIS_ERR_STOPS;
    }
    return LRT_AXIS_OK;
}

const char *lrt_axis_strerror(int status)
{
    switch (status) {
    case LRT_AXIS_OK:
        return "OK";
    case LRT_AXIS_ERR_NULL:
        return "pusty wskaznik";
    case LRT_AXIS_ERR_INERTIA:
        return "bezwladnosc: wartosci ujemne albo zerowa suma bezwladnosci";
    case LRT_AXIS_ERR_RATIO:
        return "przelozenie (ratio) musi byc dodatnie i skonczone";
    case LRT_AXIS_ERR_CURVE:
        return "krzywa moment-predkosc: 2..16 punktow, omega rosnaco, moment >= 0";
    case LRT_AXIS_ERR_FRICTION:
        return "tarcie: wartosci >= 0 i friction_static >= friction_coulomb";
    case LRT_AXIS_ERR_BACKLASH:
        return "luz ujemny albo model z luzem/podatnoscia bez masy obciazenia";
    case LRT_AXIS_ERR_STIFFNESS:
        return "sztywnosc/tlumienie nie moga byc ujemne";
    case LRT_AXIS_ERR_STOPS:
        return "zderzaki: stop_min musi byc mniejsze od stop_max";
    case LRT_AXIS_ERR_DT:
        return "krok czasu musi byc dodatni i skonczony";
    case LRT_AXIS_ERR_NUMERIC:
        return "wartosc nieskonczona lub NaN (stan przywrocony)";
    case LRT_AXIS_ERR_LIVE_ID:
        return "nieznany parametr zmieniany w locie albo wartosc poza zakresem";
    case LRT_AXIS_ERR_LIVE_MODE:
        return "zmiana wymaga przeladowania modelu (luz w modelu sztywnym)";
    default:
        return "nieznany kod bledu";
    }
}

/* ---------- inicjalizacja ---------- */

/* Wielkosci pochodne z parametrow (wspolne dla init i zmian w locie). */
static void derive(lrt_axis *a)
{
    const lrt_axis_params *p = &a->p;
    double j_eq;
    double j_stop;
    double wn2;

    a->j_m = p->j_motor + p->j_screw;
    a->j_l = p->load * p->ratio * p->ratio;
    a->j_tot = a->j_m + a->j_l;
    a->two_body = (p->backlash > 0.0 || p->stiffness > 0.0) ? 1 : 0;
    a->gap_half = 0.5 * p->backlash / p->ratio;

    wn2 = 0.0;
    a->k_contact = 0.0;
    a->c_contact = 0.0;
    a->k_stop = 0.0;
    a->c_stop = 0.0;
    if (a->two_body) {
        a->k_contact = (p->stiffness > 0.0) ? p->stiffness : LRT_AXIS_DEFAULT_CONTACT_STIFFNESS;
        j_eq = a->j_m * a->j_l / (a->j_m + a->j_l);
        a->c_contact = 2.0 * p->damping_ratio * sqrt(a->k_contact * j_eq);
        wn2 += a->k_contact * (1.0 / a->j_m + 1.0 / a->j_l);
    }
    j_stop = a->two_body ? a->j_l : a->j_tot;
    if (p->use_stops && p->stop_stiffness > 0.0) {
        a->k_stop = p->stop_stiffness * p->ratio * p->ratio;
        a->c_stop = 2.0 * p->stop_damping_ratio * sqrt(a->k_stop * j_stop);
        wn2 += a->k_stop / j_stop;
    }
    a->dt_sub_max = (wn2 > 0.0) ? LRT_STABILITY_FRACTION / sqrt(wn2) : LRT_NO_LIMIT_DT;
}

int lrt_axis_init(lrt_axis *a, const lrt_axis_params *p)
{
    int rc;

    if (a == NULL) {
        return LRT_AXIS_ERR_NULL;
    }
    rc = lrt_axis_params_check(p);
    if (rc != LRT_AXIS_OK) {
        return rc;
    }
    memset(a, 0, sizeof(*a));
    a->p = *p;
    a->supply_scale = 1.0;
    derive(a);
    lrt_axis_reset(a, 0.0);
    return LRT_AXIS_OK;
}

void lrt_axis_reset(lrt_axis *a, double pos)
{
    if (a == NULL) {
        return;
    }
    a->th_l = pos / a->p.ratio;
    a->th_m = a->th_l;
    a->w_m = 0.0;
    a->w_l = 0.0;
    a->pos = pos;
    a->vel = 0.0;
    a->torque_applied = 0.0;
    a->contact_torque = 0.0;
    a->sticking = 0;
    a->stop_contact = 0;
    a->events = 0;
    a->impact_speed = 0.0;
}

double lrt_axis_torque_limit(const lrt_axis *a, double omega)
{
    const lrt_curve_point *c;
    int i;
    int n;
    double w = fabs(omega);

    if (a == NULL || a->p.n_curve < 2) {
        return 0.0;
    }
    c = a->p.curve;
    n = a->p.n_curve;
    if (w <= c[0].omega) {
        return c[0].torque * a->supply_scale;
    }
    for (i = 1; i < n; i++) {
        if (w <= c[i].omega) {
            double f = (w - c[i - 1].omega) / (c[i].omega - c[i - 1].omega);
            return (c[i - 1].torque + f * (c[i].torque - c[i - 1].torque)) * a->supply_scale;
        }
    }
    return 0.0;
}

double lrt_axis_j_total(const lrt_axis *a)
{
    return (a == NULL) ? 0.0 : a->j_tot;
}

unsigned lrt_axis_events(const lrt_axis *a)
{
    return (a == NULL) ? 0u : a->events;
}

void lrt_axis_clear_events(lrt_axis *a)
{
    if (a != NULL) {
        a->events = 0;
        a->impact_speed = 0.0;
    }
}

/* ---------- fizyka ---------- */

/* Predkosc po kroku h dla ciala o bezwladnosci J pod momentem zewnetrznym tau_ext
 * z tarciem lepkim, Coulomba i statycznym (wszystko wg parametrow osi). */
static double integrate_vel(const lrt_axis_params *p, double w, double tau_ext, double J,
                            double h, int *stuck)
{
    const double tc = p->friction_coulomb;
    const double ts = (p->friction_static > tc) ? p->friction_static : tc;
    double sgn;
    double w1;

    *stuck = 0;
    if (fabs(w) < LRT_STICK_EPS) {
        w = 0.0;
        if (fabs(tau_ext) <= ts) {
            *stuck = 1;
            return 0.0;
        }
        sgn = (tau_ext > 0.0) ? 1.0 : -1.0;
    } else {
        sgn = (w > 0.0) ? 1.0 : -1.0;
    }
    w1 = (w + h * (tau_ext - tc * sgn) / J) / (1.0 + h * p->friction_viscous / J);
    if (w != 0.0 && w1 * sgn < 0.0) {
        w1 = 0.0; /* przejscie przez zero: przylgniecie */
    }
    return w1;
}

/* Moment ze zderzaka sprezystego na wale (0 gdy sztywny albo brak kontaktu).
 * pos/vel w jednostkach osi. Ustawia zdarzenia i zapamietuje uderzenie. */
static double stop_torque(lrt_axis *a, double pos, double vel)
{
    const lrt_axis_params *p = &a->p;
    double pen;
    double side;
    double tq;

    if (!p->use_stops || a->k_stop <= 0.0) {
        return 0.0;
    }
    if (pos > p->stop_max) {
        pen = pos - p->stop_max;
        side = 1.0;
    } else if (pos < p->stop_min) {
        pen = p->stop_min - pos;
        side = -1.0;
    } else {
        a->stop_contact = 0;
        return 0.0;
    }
    if (a->stop_contact == 0) {
        double v_in = side * vel;
        if (v_in > a->impact_speed) {
            a->impact_speed = v_in;
        }
        a->stop_contact = (side > 0.0) ? 1 : -1;
    }
    a->events |= (side > 0.0) ? LRT_AXIS_EV_HARDSTOP_MAX : LRT_AXIS_EV_HARDSTOP_MIN;
    tq = a->k_stop * (pen / p->ratio) + a->c_stop * (side * vel / p->ratio);
    if (tq < 0.0) {
        tq = 0.0;
    }
    return -side * tq;
}

/* Zderzak sztywny: obcina pozycje, zeruje predkosc do zderzaka, zapisuje uderzenie. */
static void rigid_stop(lrt_axis *a, double *th, double *w)
{
    const lrt_axis_params *p = &a->p;
    double pos;

    if (!p->use_stops || a->k_stop > 0.0) {
        return; /* brak zderzakow albo zderzak sprezysty (obsluga w stop_torque) */
    }
    pos = *th * p->ratio;
    if (pos > p->stop_max) {
        double v = *w * p->ratio;
        if (a->stop_contact == 0 && v > a->impact_speed) {
            a->impact_speed = v;
        }
        a->stop_contact = 1;
        a->events |= LRT_AXIS_EV_HARDSTOP_MAX;
        *th = p->stop_max / p->ratio;
        if (*w > 0.0) {
            *w = 0.0;
        }
    } else if (pos < p->stop_min) {
        double v = -*w * p->ratio;
        if (a->stop_contact == 0 && v > a->impact_speed) {
            a->impact_speed = v;
        }
        a->stop_contact = -1;
        a->events |= LRT_AXIS_EV_HARDSTOP_MIN;
        *th = p->stop_min / p->ratio;
        if (*w < 0.0) {
            *w = 0.0;
        }
    } else {
        a->stop_contact = 0;
    }
}

/* Moment przenoszony przez luz/sprezystosc od strony silnika na obciazenie. */
static double contact_torque(const lrt_axis *a)
{
    double d = a->th_m - a->th_l;
    double pen;
    double tq;

    if (d > a->gap_half) {
        pen = d - a->gap_half;
    } else if (d < -a->gap_half) {
        pen = d + a->gap_half;
    } else {
        return 0.0;
    }
    tq = a->k_contact * pen + a->c_contact * (a->w_m - a->w_l);
    if ((pen > 0.0 && tq < 0.0) || (pen < 0.0 && tq > 0.0)) {
        tq = 0.0; /* kontakt nie przenosi rozciagania */
    }
    return tq;
}

static void substep(lrt_axis *a, double tau_cmd, double h)
{
    const lrt_axis_params *p = &a->p;
    double limit = lrt_axis_torque_limit(a, a->w_m);
    double tau = tau_cmd;
    double tau_g = p->gravity_force * p->ratio;
    double w_new;
    int stuck = 0;

    if (tau > limit) {
        tau = limit;
    } else if (tau < -limit) {
        tau = -limit;
    }
    if (tau != tau_cmd) {
        a->events |= LRT_AXIS_EV_TORQUE_LIMITED;
    }
    a->torque_applied = tau;

    if (!a->two_body) {
        double tau_ext = tau + tau_g + stop_torque(a, a->th_m * p->ratio, a->w_m * p->ratio);

        w_new = integrate_vel(p, a->w_m, tau_ext, a->j_tot, h, &stuck);
        a->th_m += 0.5 * (a->w_m + w_new) * h;
        a->w_m = w_new;
        rigid_stop(a, &a->th_m, &a->w_m);
        a->th_l = a->th_m;
        a->w_l = a->w_m;
        a->contact_torque = tau;
    } else {
        double tau_c = contact_torque(a);
        double tau_ext_l = tau_c + tau_g + stop_torque(a, a->th_l * p->ratio, a->w_l * p->ratio);
        double w_m_new = a->w_m + h * (tau - tau_c) / a->j_m;

        w_new = integrate_vel(p, a->w_l, tau_ext_l, a->j_l, h, &stuck);
        a->th_m += 0.5 * (a->w_m + w_m_new) * h;
        a->th_l += 0.5 * (a->w_l + w_new) * h;
        a->w_m = w_m_new;
        a->w_l = w_new;
        rigid_stop(a, &a->th_l, &a->w_l);
        a->contact_torque = tau_c;
    }
    a->sticking = stuck;
    a->pos = a->th_l * p->ratio;
    a->vel = a->w_l * p->ratio;
}

int lrt_axis_step(lrt_axis *a, double torque_cmd, double dt)
{
    lrt_axis saved;
    double nd;
    int n;
    int i;
    double h;

    if (a == NULL) {
        return LRT_AXIS_ERR_NULL;
    }
    if (bad(dt) || dt <= 0.0) {
        return LRT_AXIS_ERR_DT;
    }
    if (bad(torque_cmd)) {
        return LRT_AXIS_ERR_NUMERIC;
    }
    saved = *a;

    nd = ceil(dt / a->dt_sub_max);
    if (nd < 1.0) {
        nd = 1.0;
    }
    if (nd > (double)LRT_AXIS_MAX_SUBSTEPS) {
        nd = (double)LRT_AXIS_MAX_SUBSTEPS;
        a->events |= LRT_AXIS_EV_SUBSTEPS_CAPPED;
    }
    n = (int)nd;
    h = dt / nd;
    for (i = 0; i < n; i++) {
        substep(a, torque_cmd, h);
    }
    if (bad(a->th_m) || bad(a->w_m) || bad(a->th_l) || bad(a->w_l)) {
        *a = saved;
        return LRT_AXIS_ERR_NUMERIC;
    }
    a->time += dt;
    return LRT_AXIS_OK;
}

/* ---------- parametry zmieniane w locie (REQ-VD-04) ---------- */

int lrt_axis_get_live(const lrt_axis *a, int param, double *value)
{
    if (a == NULL || value == NULL) {
        return LRT_AXIS_ERR_NULL;
    }
    switch (param) {
    case LRT_LIVE_LOAD:
        *value = a->p.load;
        break;
    case LRT_LIVE_J_MOTOR:
        *value = a->p.j_motor;
        break;
    case LRT_LIVE_J_SCREW:
        *value = a->p.j_screw;
        break;
    case LRT_LIVE_FRICTION_COULOMB:
        *value = a->p.friction_coulomb;
        break;
    case LRT_LIVE_FRICTION_STATIC:
        *value = a->p.friction_static;
        break;
    case LRT_LIVE_FRICTION_VISCOUS:
        *value = a->p.friction_viscous;
        break;
    case LRT_LIVE_BACKLASH:
        *value = a->p.backlash;
        break;
    case LRT_LIVE_SUPPLY_SCALE:
        *value = a->supply_scale;
        break;
    default:
        return LRT_AXIS_ERR_LIVE_ID;
    }
    return LRT_AXIS_OK;
}

int lrt_axis_set_live(lrt_axis *a, int param, double value, lrt_live_log *log)
{
    lrt_axis_params q;
    double old_value;
    int rc;

    if (a == NULL) {
        return LRT_AXIS_ERR_NULL;
    }
    if (param < 0 || param > LRT_LIVE_SUPPLY_SCALE || bad(value)) {
        return LRT_AXIS_ERR_LIVE_ID;
    }
    (void)lrt_axis_get_live(a, param, &old_value);
    q = a->p;
    switch (param) {
    case LRT_LIVE_LOAD:
        q.load = value;
        break;
    case LRT_LIVE_J_MOTOR:
        q.j_motor = value;
        break;
    case LRT_LIVE_J_SCREW:
        q.j_screw = value;
        break;
    case LRT_LIVE_FRICTION_COULOMB:
        q.friction_coulomb = value;
        break;
    case LRT_LIVE_FRICTION_STATIC:
        q.friction_static = value;
        break;
    case LRT_LIVE_FRICTION_VISCOUS:
        q.friction_viscous = value;
        break;
    case LRT_LIVE_BACKLASH:
        q.backlash = value;
        break;
    case LRT_LIVE_SUPPLY_SCALE:
        if (value < 0.05 || value > 2.0) {
            return LRT_AXIS_ERR_LIVE_ID;
        }
        break;
    default:
        return LRT_AXIS_ERR_LIVE_ID;
    }
    if (param != LRT_LIVE_SUPPLY_SCALE) {
        rc = lrt_axis_params_check(&q);
        if (rc != LRT_AXIS_OK) {
            return rc;
        }
        if (((q.backlash > 0.0 || q.stiffness > 0.0) ? 1 : 0) != a->two_body) {
            return LRT_AXIS_ERR_LIVE_MODE;
        }
        a->p = q;
        derive(a);
    } else {
        a->supply_scale = value;
    }
    lrt_live_log_append(log, a->time, param, old_value, value);
    return LRT_AXIS_OK;
}
