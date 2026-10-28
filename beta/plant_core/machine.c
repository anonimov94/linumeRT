/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - Plant: wirtualna obrabiarka zlozona z osi i napedow (machine.h).
 * Model-Author: Claude · sesja 014
 *
 * NIEZWERYFIKOWANE NA SPRZECIE: model sprawdzony testami analitycznymi (tests/test_machine.c).
 */
#include "machine.h"

#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define LRT_TWO_PI 6.283185307179586476925286766559

/* ---- tablice pol (klucze drive.N.* i mech.N.*) ------------------------------------- */

typedef struct {
    const char *name;
    size_t offset;
    char kind; /* d double, u uint32, h uint16, i int, c int8, s int16 */
} lrt_field;

#define DF(n, k) {#n, offsetof(lrt_drive_params, n), k}
#define MF(n, k) {#n, offsetof(lrt_axis_params, n), k}

static const lrt_field drive_fields[] = {
    DF(counts_per_rev, 'd'),        DF(enc_noise_counts, 'd'),    DF(enc_noise_seed, 'u'),
    DF(rated_torque, 'd'),          DF(peak_torque, 'd'),         DF(peak_time_s, 'd'),
    DF(torque_limit_permille, 'h'), DF(kp_pos, 'd'),              DF(kv, 'd'),
    DF(ti, 'd'),                    DF(kff_vel, 'd'),             DF(kff_acc, 'd'),
    DF(inertia_est, 'd'),           DF(vel_filter_hz, 'd'),       DF(ff_filter_hz, 'd'),
    DF(max_speed, 'd'),             DF(following_window, 'u'),    DF(following_window_ms, 'h'),
    DF(quick_stop_decel, 'u'),      DF(quick_stop_option, 's'),   DF(fault_reaction_option, 's'),
    DF(standstill_speed, 'd'),      DF(boot_time_s, 'd'),         DF(full_steps_per_rev, 'i'),
    DF(stepper_damping_ratio, 'd'), DF(homing_method, 'c'),       DF(homing_speed_switch, 'u'),
    DF(homing_speed_zero, 'u'),     DF(homing_accel, 'u'),        DF(home_offset, 'i'),
    DF(hardstop_time_s, 'd'),       DF(encoder, 'i'),
};

static const lrt_field mech_fields[] = {
    MF(j_motor, 'd'),          MF(j_screw, 'd'),          MF(load, 'd'),
    MF(ratio, 'd'),            MF(friction_coulomb, 'd'), MF(friction_static, 'd'),
    MF(friction_viscous, 'd'), MF(gravity_force, 'd'),    MF(backlash, 'd'),
    MF(stiffness, 'd'),        MF(damping_ratio, 'd'),
};

#define N_FIELDS(t) ((int)(sizeof(t) / sizeof((t)[0])))

static int is_int(double v, double lo, double hi)
{
    return isfinite(v) && v == floor(v) && v >= lo && v <= hi;
}

static int set_field(void *base, const lrt_field *f, double v)
{
    char *p = (char *)base + f->offset;

    switch (f->kind) {
    case 'd':
        *(double *)(void *)p = v;
        return LRT_MACHINE_OK;
    case 'u':
        if (!is_int(v, 0.0, 4294967295.0)) {
            return LRT_MACHINE_ERR_VALUE;
        }
        *(uint32_t *)(void *)p = (uint32_t)v;
        return LRT_MACHINE_OK;
    case 'h':
        if (!is_int(v, 0.0, 65535.0)) {
            return LRT_MACHINE_ERR_VALUE;
        }
        *(uint16_t *)(void *)p = (uint16_t)v;
        return LRT_MACHINE_OK;
    case 's':
        if (!is_int(v, -32768.0, 32767.0)) {
            return LRT_MACHINE_ERR_VALUE;
        }
        *(int16_t *)(void *)p = (int16_t)v;
        return LRT_MACHINE_OK;
    case 'c':
        if (!is_int(v, -128.0, 127.0)) {
            return LRT_MACHINE_ERR_VALUE;
        }
        *(int8_t *)(void *)p = (int8_t)v;
        return LRT_MACHINE_OK;
    default: /* 'i' */
        if (!is_int(v, -2147483647.0, 2147483647.0)) {
            return LRT_MACHINE_ERR_VALUE;
        }
        *(int *)(void *)p = (int)v;
        return LRT_MACHINE_OK;
    }
}

static int set_from_table(void *base, const lrt_field *t, int n, const char *name, double v)
{
    int i;

    for (i = 0; i < n; i++) {
        if (strcmp(t[i].name, name) == 0) {
            return set_field(base, &t[i], v);
        }
    }
    return LRT_MACHINE_ERR_KEY;
}

/* ---- konfiguracja ------------------------------------------------------------------ */

void lrt_machine_cfg_init(lrt_machine_cfg *c)
{
    if (c == NULL) {
        return;
    }
    memset(c, 0, sizeof(*c));
    c->estop_input = -1;
    c->estop_nc = 1;
    c->estop_action = LRT_ESTOP_STO;
    c->probe_type = LRT_PROBE_NONE;
    c->probe_input = -1;
    c->probe_nc = 0;
    c->spindle_drive = -1;
}

static lrt_machine_drive_cfg *touch_drive(lrt_machine_cfg *c, int n)
{
    lrt_machine_drive_cfg *d = &c->drives[n];

    if (!d->used) {
        lrt_drive_params_default(&d->drive, LRT_DRIVE_SERVO_CSP);
        lrt_axis_params_default(&d->mech);
        d->index_input = -1;
        d->index_width = 0.01;
        d->din_neg_limit = -1;
        d->din_pos_limit = -1;
        d->din_home = -1;
        d->used = 1;
    }
    if (n + 1 > c->n_drives) {
        c->n_drives = n + 1;
    }
    return d;
}

static lrt_machine_joint_cfg *touch_joint(lrt_machine_cfg *c, int n)
{
    lrt_machine_joint_cfg *j = &c->joints[n];

    if (!j->used) {
        j->used = 1;
        j->kind = LRT_AXIS_LINEAR;
        j->drive[0] = -1;
        j->drive[1] = -1;
    }
    if (n + 1 > c->n_joints) {
        c->n_joints = n + 1;
    }
    return j;
}

static lrt_machine_link_cfg *touch_link(lrt_machine_cfg *c, int n)
{
    lrt_machine_link_cfg *l = &c->links[n];

    if (!l->used) {
        l->used = 1;
        l->kind = LRT_AXIS_LINEAR;
        l->joint = -1;
        l->parent = -1;
        l->branch = LRT_BRANCH_TOOL;
        l->axis[2] = 1.0;
    }
    if (n + 1 > c->n_links) {
        c->n_links = n + 1;
    }
    return l;
}

static lrt_machine_switch_cfg *touch_switch(lrt_machine_cfg *c, int n)
{
    lrt_machine_switch_cfg *s = &c->switches[n];

    if (!s->used) {
        s->used = 1;
        s->joint = -1;
        s->role = LRT_SWITCH_LIMIT;
        s->side = -1;
        s->nc = 1;
        s->input = -1;
        s->drive = -1;
    }
    if (n + 1 > c->n_switches) {
        c->n_switches = n + 1;
    }
    return s;
}

/* "sekcja.N.pole" albo "sekcja.pole"; zwraca 0 przy poprawnej skladni. */
static int split_key(const char *key, char *sec, size_t sec_size, long *index, const char **field)
{
    const char *dot = strchr(key, '.');
    size_t len;

    if (dot == NULL) {
        return -1;
    }
    len = (size_t)(dot - key);
    if (len == 0 || len >= sec_size) {
        return -1;
    }
    memcpy(sec, key, len);
    sec[len] = '\0';
    *index = -1;
    if (dot[1] >= '0' && dot[1] <= '9') {
        char *end;
        *index = strtol(dot + 1, &end, 10);
        if (*end != '.') {
            return -1;
        }
        *field = end + 1;
    } else {
        *field = dot + 1;
    }
    return (**field == '\0') ? -1 : 0;
}

static int set_int(int *dst, double v, double lo, double hi)
{
    if (!is_int(v, lo, hi)) {
        return LRT_MACHINE_ERR_VALUE;
    }
    *dst = (int)v;
    return LRT_MACHINE_OK;
}

static int cfg_drive(lrt_machine_cfg *c, int n, const char *f, double v)
{
    lrt_machine_drive_cfg *d;
    int rc;

    if (n < 0 || n >= LRT_MACHINE_MAX_DRIVES) {
        return LRT_MACHINE_ERR_INDEX;
    }
    d = touch_drive(c, n);
    if (strcmp(f, "type") == 0) {
        int t;
        rc = set_int(&t, v, 0.0, 2.0);
        if (rc == LRT_MACHINE_OK) {
            d->drive.type = (lrt_drive_type)t;
        }
        return rc;
    }
    if (strcmp(f, "index_input") == 0) {
        return set_int(&d->index_input, v, -1.0, LRT_MACHINE_MAX_IO - 1.0);
    }
    if (strcmp(f, "index_width") == 0) {
        if (!(v > 0.0 && v < LRT_TWO_PI)) {
            return LRT_MACHINE_ERR_VALUE;
        }
        d->index_width = v;
        return LRT_MACHINE_OK;
    }
    if (strcmp(f, "din_neg_limit") == 0) {
        return set_int(&d->din_neg_limit, v, -1.0, LRT_MACHINE_MAX_SWITCHES - 1.0);
    }
    if (strcmp(f, "din_pos_limit") == 0) {
        return set_int(&d->din_pos_limit, v, -1.0, LRT_MACHINE_MAX_SWITCHES - 1.0);
    }
    if (strcmp(f, "din_home") == 0) {
        return set_int(&d->din_home, v, -1.0, LRT_MACHINE_MAX_SWITCHES - 1.0);
    }
    return set_from_table(&d->drive, drive_fields, N_FIELDS(drive_fields), f, v);
}

static int cfg_mech(lrt_machine_cfg *c, int n, const char *f, double v)
{
    lrt_machine_drive_cfg *d;

    if (n < 0 || n >= LRT_MACHINE_MAX_DRIVES) {
        return LRT_MACHINE_ERR_INDEX;
    }
    d = touch_drive(c, n);
    if (strcmp(f, "kind") == 0) {
        int k;
        int rc = set_int(&k, v, 0.0, 1.0);
        if (rc == LRT_MACHINE_OK) {
            d->mech.kind = (lrt_axis_kind)k;
        }
        return rc;
    }
    return set_from_table(&d->mech, mech_fields, N_FIELDS(mech_fields), f, v);
}

static int cfg_joint(lrt_machine_cfg *c, int n, const char *f, double v)
{
    lrt_machine_joint_cfg *j;

    if (n < 0 || n >= LRT_MACHINE_MAX_JOINTS) {
        return LRT_MACHINE_ERR_INDEX;
    }
    j = touch_joint(c, n);
    if (strcmp(f, "kind") == 0) {
        return set_int(&j->kind, v, 0.0, 1.0);
    }
    if (strcmp(f, "drive0") == 0) {
        return set_int(&j->drive[0], v, -1.0, LRT_MACHINE_MAX_DRIVES - 1.0);
    }
    if (strcmp(f, "drive1") == 0) {
        return set_int(&j->drive[1], v, -1.0, LRT_MACHINE_MAX_DRIVES - 1.0);
    }
    if (strcmp(f, "use_stops") == 0) {
        return set_int(&j->use_stops, v, 0.0, 1.0);
    }
    if (strcmp(f, "stop_fault") == 0) {
        return set_int(&j->stop_fault, v, 0.0, 1.0);
    }
    if (strcmp(f, "initial_random") == 0) {
        return set_int(&j->initial_random, v, 0.0, 1.0);
    }
    if (!isfinite(v)) {
        return LRT_MACHINE_ERR_VALUE;
    }
    if (strcmp(f, "max_skew") == 0) {
        j->max_skew = v;
    } else if (strcmp(f, "stop_min") == 0) {
        j->stop_min = v;
    } else if (strcmp(f, "stop_max") == 0) {
        j->stop_max = v;
    } else if (strcmp(f, "stop_k") == 0) {
        j->stop_k = v;
    } else if (strcmp(f, "stop_c") == 0) {
        j->stop_c = v;
    } else if (strcmp(f, "initial") == 0) {
        j->initial = v;
    } else if (strcmp(f, "initial_min") == 0) {
        j->initial_min = v;
    } else if (strcmp(f, "initial_max") == 0) {
        j->initial_max = v;
    } else {
        return LRT_MACHINE_ERR_KEY;
    }
    return LRT_MACHINE_OK;
}

static int cfg_link(lrt_machine_cfg *c, int n, const char *f, double v)
{
    static const char *const vec[6] = {"ax", "ay", "az", "ox", "oy", "oz"};
    lrt_machine_link_cfg *l;
    int i;

    if (n < 0 || n >= LRT_MACHINE_MAX_LINKS) {
        return LRT_MACHINE_ERR_INDEX;
    }
    l = touch_link(c, n);
    if (strcmp(f, "kind") == 0) {
        return set_int(&l->kind, v, 0.0, 1.0);
    }
    if (strcmp(f, "joint") == 0) {
        return set_int(&l->joint, v, -1.0, LRT_MACHINE_MAX_JOINTS - 1.0);
    }
    if (strcmp(f, "parent") == 0) {
        return set_int(&l->parent, v, -1.0, LRT_MACHINE_MAX_LINKS - 1.0);
    }
    if (strcmp(f, "branch") == 0) {
        return set_int(&l->branch, v, 0.0, 1.0);
    }
    for (i = 0; i < 6; i++) {
        if (strcmp(f, vec[i]) == 0) {
            if (!isfinite(v)) {
                return LRT_MACHINE_ERR_VALUE;
            }
            if (i < 3) {
                l->axis[i] = v;
            } else {
                l->offset[i - 3] = v;
            }
            return LRT_MACHINE_OK;
        }
    }
    return LRT_MACHINE_ERR_KEY;
}

static int cfg_switch(lrt_machine_cfg *c, int n, const char *f, double v)
{
    lrt_machine_switch_cfg *s;

    if (n < 0 || n >= LRT_MACHINE_MAX_SWITCHES) {
        return LRT_MACHINE_ERR_INDEX;
    }
    s = touch_switch(c, n);
    if (strcmp(f, "joint") == 0) {
        return set_int(&s->joint, v, 0.0, LRT_MACHINE_MAX_JOINTS - 1.0);
    }
    if (strcmp(f, "role") == 0) {
        return set_int(&s->role, v, 0.0, 1.0);
    }
    if (strcmp(f, "side") == 0) {
        if (v != -1.0 && v != 1.0) {
            return LRT_MACHINE_ERR_VALUE;
        }
        s->side = (int)v;
        return LRT_MACHINE_OK;
    }
    if (strcmp(f, "nc") == 0) {
        return set_int(&s->nc, v, 0.0, 1.0);
    }
    if (strcmp(f, "input") == 0) {
        return set_int(&s->input, v, -1.0, LRT_MACHINE_MAX_IO - 1.0);
    }
    if (strcmp(f, "drive") == 0) {
        return set_int(&s->drive, v, -1.0, LRT_MACHINE_MAX_DRIVES - 1.0);
    }
    if (!isfinite(v)) {
        return LRT_MACHINE_ERR_VALUE;
    }
    if (strcmp(f, "position") == 0) {
        s->position = v;
    } else if (strcmp(f, "hysteresis") == 0) {
        s->hysteresis = v;
    } else if (strcmp(f, "bounce") == 0) {
        s->bounce = v;
    } else {
        return LRT_MACHINE_ERR_KEY;
    }
    return LRT_MACHINE_OK;
}

static int cfg_probe(lrt_machine_cfg *c, const char *f, double v)
{
    static const char *const box[6] = {"min_x", "min_y", "min_z", "max_x", "max_y", "max_z"};
    int i;

    if (strcmp(f, "type") == 0) {
        return set_int(&c->probe_type, v, 0.0, 2.0);
    }
    if (strcmp(f, "input") == 0) {
        return set_int(&c->probe_input, v, -1.0, LRT_MACHINE_MAX_IO - 1.0);
    }
    if (strcmp(f, "nc") == 0) {
        return set_int(&c->probe_nc, v, 0.0, 1.0);
    }
    if (!isfinite(v)) {
        return LRT_MACHINE_ERR_VALUE;
    }
    if (strcmp(f, "tip_length") == 0) {
        c->probe_tip_length = v;
        return LRT_MACHINE_OK;
    }
    for (i = 0; i < 6; i++) {
        if (strcmp(f, box[i]) == 0) {
            if (i < 3) {
                c->probe_min[i] = v;
            } else {
                c->probe_max[i - 3] = v;
            }
            return LRT_MACHINE_OK;
        }
    }
    return LRT_MACHINE_ERR_KEY;
}

int lrt_machine_cfg_set(lrt_machine_cfg *c, const char *key, double value)
{
    char sec[16];
    long index;
    const char *f;

    if (c == NULL || key == NULL) {
        return LRT_MACHINE_ERR_NULL;
    }
    if (split_key(key, sec, sizeof(sec), &index, &f) != 0) {
        return LRT_MACHINE_ERR_KEY;
    }
    if (strcmp(sec, "drive") == 0 && index >= 0) {
        return cfg_drive(c, (int)(index > 1000 ? 1000 : index), f, value);
    }
    if (strcmp(sec, "mech") == 0 && index >= 0) {
        return cfg_mech(c, (int)(index > 1000 ? 1000 : index), f, value);
    }
    if (strcmp(sec, "joint") == 0 && index >= 0) {
        return cfg_joint(c, (int)(index > 1000 ? 1000 : index), f, value);
    }
    if (strcmp(sec, "link") == 0 && index >= 0) {
        return cfg_link(c, (int)(index > 1000 ? 1000 : index), f, value);
    }
    if (strcmp(sec, "switch") == 0 && index >= 0) {
        return cfg_switch(c, (int)(index > 1000 ? 1000 : index), f, value);
    }
    if (index >= 0) {
        return LRT_MACHINE_ERR_KEY;
    }
    if (strcmp(sec, "estop") == 0) {
        if (strcmp(f, "input") == 0) {
            return set_int(&c->estop_input, value, -1.0, LRT_MACHINE_MAX_IO - 1.0);
        }
        if (strcmp(f, "nc") == 0) {
            return set_int(&c->estop_nc, value, 0.0, 1.0);
        }
        if (strcmp(f, "action") == 0) {
            return set_int(&c->estop_action, value, 0.0, 1.0);
        }
        return LRT_MACHINE_ERR_KEY;
    }
    if (strcmp(sec, "probe") == 0) {
        return cfg_probe(c, f, value);
    }
    if (strcmp(sec, "spindle") == 0 && strcmp(f, "drive") == 0) {
        return set_int(&c->spindle_drive, value, -1.0, LRT_MACHINE_MAX_DRIVES - 1.0);
    }
    if (strcmp(sec, "machine") == 0 && strcmp(f, "seed") == 0) {
        if (!is_int(value, 0.0, 4294967295.0)) {
            return LRT_MACHINE_ERR_VALUE;
        }
        c->seed = (uint32_t)value;
        return LRT_MACHINE_OK;
    }
    return LRT_MACHINE_ERR_KEY;
}

int lrt_machine_cfg_curve(lrt_machine_cfg *c, int drive, double omega, double torque)
{
    lrt_machine_drive_cfg *d;

    if (c == NULL) {
        return LRT_MACHINE_ERR_NULL;
    }
    if (drive < 0 || drive >= LRT_MACHINE_MAX_DRIVES) {
        return LRT_MACHINE_ERR_INDEX;
    }
    if (!isfinite(omega) || !isfinite(torque)) {
        return LRT_MACHINE_ERR_VALUE;
    }
    d = touch_drive(c, drive);
    if (!d->curve_set) {
        d->mech.n_curve = 0;
        d->curve_set = 1;
    }
    if (d->mech.n_curve >= LRT_AXIS_CURVE_MAX) {
        return LRT_MACHINE_ERR_INDEX;
    }
    d->mech.curve[d->mech.n_curve].omega = omega;
    d->mech.curve[d->mech.n_curve].torque = torque;
    d->mech.n_curve++;
    return LRT_MACHINE_OK;
}

/* ---- kinematyka prosta ------------------------------------------------------------- */

typedef struct {
    double r[9]; /* macierz obrotu, wierszami */
    double t[3];
} lrt_frame;

static void frame_identity(lrt_frame *f)
{
    memset(f, 0, sizeof(*f));
    f->r[0] = f->r[4] = f->r[8] = 1.0;
}

/* Obrot o kat q wokol wektora jednostkowego u (wzor Rodriguesa). */
static void rotation(const double u[3], double q, double r[9])
{
    double c = cos(q);
    double s = sin(q);
    double k = 1.0 - c;

    r[0] = c + u[0] * u[0] * k;
    r[1] = u[0] * u[1] * k - u[2] * s;
    r[2] = u[0] * u[2] * k + u[1] * s;
    r[3] = u[1] * u[0] * k + u[2] * s;
    r[4] = c + u[1] * u[1] * k;
    r[5] = u[1] * u[2] * k - u[0] * s;
    r[6] = u[2] * u[0] * k - u[1] * s;
    r[7] = u[2] * u[1] * k + u[0] * s;
    r[8] = c + u[2] * u[2] * k;
}

/* out = a * b (najpierw b w ukladzie a). out moze byc rowne b. */
static void frame_compose(const lrt_frame *a, const lrt_frame *b, lrt_frame *out)
{
    lrt_frame res;
    int i;
    int j;

    for (i = 0; i < 3; i++) {
        for (j = 0; j < 3; j++) {
            res.r[3 * i + j] = a->r[3 * i] * b->r[j] + a->r[3 * i + 1] * b->r[3 + j] +
                               a->r[3 * i + 2] * b->r[6 + j];
        }
        res.t[i] = a->r[3 * i] * b->t[0] + a->r[3 * i + 1] * b->t[1] + a->r[3 * i + 2] * b->t[2] +
                   a->t[i];
    }
    *out = res;
}

static double norm3(const double v[3])
{
    return sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
}

static int forward(const lrt_machine_cfg *c, const double *q, double tool_length,
                   double tool_m[3], double tool_w[3])
{
    lrt_frame frames[LRT_MACHINE_MAX_LINKS];
    lrt_frame tool;
    lrt_frame wp;
    double p[3];
    int l;
    int i;

    frame_identity(&tool);
    frame_identity(&wp);
    for (l = 0; l < c->n_links; l++) {
        const lrt_machine_link_cfg *k = &c->links[l];
        lrt_frame local;
        double u[3];
        double n = norm3(k->axis);
        double qv = (k->joint >= 0) ? q[k->joint] : 0.0;

        if (n <= 0.0 || k->parent >= l) {
            return LRT_MACHINE_ERR_LINK;
        }
        for (i = 0; i < 3; i++) {
            u[i] = k->axis[i] / n;
        }
        frame_identity(&local);
        if (k->kind == LRT_AXIS_ROTARY) {
            rotation(u, qv, local.r);
            for (i = 0; i < 3; i++) {
                local.t[i] = k->offset[i];
            }
        } else {
            for (i = 0; i < 3; i++) {
                local.t[i] = k->offset[i] + u[i] * qv;
            }
        }
        if (k->parent >= 0) {
            frame_compose(&frames[k->parent], &local, &frames[l]);
        } else {
            frames[l] = local;
        }
        if (k->branch == LRT_BRANCH_WORKPIECE) {
            wp = frames[l];
        } else {
            tool = frames[l];
        }
    }
    /* koniec narzedzia: (0, 0, -L) w ukladzie ostatniego czlonu galezi narzedzia */
    for (i = 0; i < 3; i++) {
        tool_m[i] = tool.r[3 * i + 2] * (-tool_length) + tool.t[i];
        p[i] = tool_m[i] - wp.t[i];
    }
    /* uklad detalu: R_wp^T * (p - t_wp) */
    for (i = 0; i < 3; i++) {
        tool_w[i] = wp.r[i] * p[0] + wp.r[3 + i] * p[1] + wp.r[6 + i] * p[2];
    }
    return LRT_MACHINE_OK;
}

int lrt_machine_forward(const lrt_machine_cfg *c, const double *q, double tool_length,
                        int workpiece_frame, double out[3])
{
    double m[3];
    double w[3];
    int rc;
    int i;

    if (c == NULL || q == NULL || out == NULL) {
        return LRT_MACHINE_ERR_NULL;
    }
    if (c->n_links < 0 || c->n_links > LRT_MACHINE_MAX_LINKS) {
        return LRT_MACHINE_ERR_LINK;
    }
    for (i = 0; i < c->n_links; i++) {
        if (c->links[i].joint >= c->n_joints) {
            return LRT_MACHINE_ERR_LINK;
        }
    }
    rc = forward(c, q, tool_length, m, w);
    if (rc == LRT_MACHINE_OK) {
        for (i = 0; i < 3; i++) {
            out[i] = workpiece_frame ? w[i] : m[i];
        }
    }
    return rc;
}

/* ---- walidacja i inicjalizacja ----------------------------------------------------- */

static int fail(lrt_machine *m, int status, int index, int detail)
{
    m->err_index = index;
    m->err_detail = detail;
    return status;
}

/* Wspolczynnik tlumienia zderzaka z tlumienia fizycznego c [N*s/m] dla masy odbitej osi. */
static double stop_damping_ratio(const lrt_axis_params *p, double k, double c)
{
    double m_eff;

    if (k <= 0.0 || c <= 0.0) {
        return 0.0;
    }
    if (p->backlash > 0.0 || p->stiffness > 0.0) {
        m_eff = p->load; /* model dwuczlonowy: zderzak dziala na obciazenie */
    } else {
        m_eff = (p->j_motor + p->j_screw) / (p->ratio * p->ratio) + p->load;
    }
    return (m_eff > 0.0) ? c / (2.0 * sqrt(k * m_eff)) : 0.0;
}

static int check_joints(lrt_machine *m, int *owner)
{
    const lrt_machine_cfg *c = &m->c;
    int j;
    int s;
    int k;

    if (c->n_joints < 1) {
        return fail(m, LRT_MACHINE_ERR_JOINT, -1, 0);
    }
    for (s = 0; s < LRT_MACHINE_MAX_DRIVES; s++) {
        owner[s] = -2; /* -2 = nieprzypisany, -1 = wrzeciono, >= 0 = os */
    }
    for (j = 0; j < c->n_joints; j++) {
        const lrt_machine_joint_cfg *jc = &c->joints[j];
        int n = 0;

        if (!jc->used) {
            return fail(m, LRT_MACHINE_ERR_INDEX, j, 0);
        }
        for (k = 0; k < 2; k++) {
            int d = jc->drive[k];
            if (d < 0) {
                continue;
            }
            if (d >= c->n_drives || owner[d] != -2 || (int)c->drives[d].mech.kind != jc->kind) {
                return fail(m, LRT_MACHINE_ERR_JOINT, j, d);
            }
            owner[d] = j;
            n++;
        }
        if (jc->drive[0] < 0 || n == 0) {
            return fail(m, LRT_MACHINE_ERR_JOINT, j, -1);
        }
        if (n == 2 && !(jc->max_skew > 0.0)) {
            return fail(m, LRT_MACHINE_ERR_JOINT, j, -1);
        }
        if (jc->stop_k < 0.0 || jc->stop_c < 0.0 ||
            (jc->use_stops && !(jc->stop_min < jc->stop_max)) ||
            (jc->initial_random && !(jc->initial_min <= jc->initial_max))) {
            return fail(m, LRT_MACHINE_ERR_JOINT, j, -1);
        }
    }
    if (c->spindle_drive >= 0) {
        int d = c->spindle_drive;
        if (d >= c->n_drives || owner[d] != -2 || (int)c->drives[d].mech.kind != LRT_AXIS_ROTARY) {
            return fail(m, LRT_MACHINE_ERR_JOINT, -1, d);
        }
        owner[d] = -1;
    }
    for (s = 0; s < c->n_drives; s++) {
        if (owner[s] == -2) {
            return fail(m, LRT_MACHINE_ERR_JOINT, -1, s); /* naped nieprzypisany */
        }
    }
    return LRT_MACHINE_OK;
}

static int check_links(lrt_machine *m)
{
    const lrt_machine_cfg *c = &m->c;
    int used[LRT_MACHINE_MAX_JOINTS] = {0};
    int l;
    int j;

    for (l = 0; l < c->n_links; l++) {
        const lrt_machine_link_cfg *k = &c->links[l];

        if (!k->used) {
            return fail(m, LRT_MACHINE_ERR_INDEX, l, 0);
        }
        if (k->parent >= l || norm3(k->axis) < 1e-12 ||
            (k->parent >= 0 && c->links[k->parent].branch != k->branch) ||
            k->joint >= c->n_joints) {
            return fail(m, LRT_MACHINE_ERR_LINK, l, 0);
        }
        if (k->joint >= 0) {
            if (used[k->joint] || c->joints[k->joint].kind != k->kind) {
                return fail(m, LRT_MACHINE_ERR_LINK, l, k->joint);
            }
            used[k->joint] = 1;
        }
    }
    if (c->n_links > 0) {
        for (j = 0; j < c->n_joints; j++) {
            if (!used[j]) {
                return fail(m, LRT_MACHINE_ERR_LINK, -1, j); /* os bez czlonu */
            }
        }
    }
    return LRT_MACHINE_OK;
}

/* Rejestruje styk na wejsciu; NC i NO na jednym wejsciu to blad. */
static int io_claim(signed char *contact, int input, int nc)
{
    if (input < 0) {
        return 0;
    }
    if (contact[input] == 0) {
        contact[input] = nc ? 1 : 2;
        return 0;
    }
    return contact[input] == (nc ? 1 : 2) ? 0 : -1;
}

static int check_io(lrt_machine *m)
{
    const lrt_machine_cfg *c = &m->c;
    signed char contact[LRT_MACHINE_MAX_IO];
    int s;

    memset(contact, 0, sizeof(contact));
    for (s = 0; s < c->n_switches; s++) {
        const lrt_machine_switch_cfg *w = &c->switches[s];
        if (!w->used) {
            return fail(m, LRT_MACHINE_ERR_INDEX, s, 0);
        }
        if (w->joint < 0 || w->joint >= c->n_joints || !(w->hysteresis >= 0.0) ||
            !(w->bounce >= 0.0) ||
            (w->drive >= 0 && c->joints[w->joint].drive[0] != w->drive &&
             c->joints[w->joint].drive[1] != w->drive)) {
            return fail(m, LRT_MACHINE_ERR_SWITCH, s, 0); /* naped czujnika spoza osi */
        }
        if (io_claim(contact, w->input, w->nc) != 0) {
            return fail(m, LRT_MACHINE_ERR_IO, w->input, s);
        }
    }
    for (s = 0; s < c->n_drives; s++) {
        const lrt_machine_drive_cfg *dc = &c->drives[s];
        if (io_claim(contact, dc->index_input, 0) != 0) {
            return fail(m, LRT_MACHINE_ERR_IO, dc->index_input, -1);
        }
        if (dc->din_neg_limit >= c->n_switches || dc->din_pos_limit >= c->n_switches ||
            dc->din_home >= c->n_switches) {
            return fail(m, LRT_MACHINE_ERR_SWITCH, -1, s); /* styk napedu nie istnieje */
        }
    }
    if (io_claim(contact, c->estop_input, c->estop_nc) != 0) {
        return fail(m, LRT_MACHINE_ERR_IO, c->estop_input, -1);
    }
    if (c->probe_type != LRT_PROBE_NONE) {
        int i;
        if (c->probe_input < 0 || !(c->probe_tip_length >= 0.0)) {
            return fail(m, LRT_MACHINE_ERR_PROBE, -1, 0);
        }
        for (i = 0; i < 3; i++) {
            if (!(c->probe_min[i] < c->probe_max[i]) && (i < 2 || c->probe_type == LRT_PROBE_BOX)) {
                return fail(m, LRT_MACHINE_ERR_PROBE, i, 0);
            }
        }
        if (io_claim(contact, c->probe_input, c->probe_nc) != 0) {
            return fail(m, LRT_MACHINE_ERR_IO, c->probe_input, -1);
        }
    }
    return LRT_MACHINE_OK;
}

static void update_inputs(lrt_machine *m);
static void refresh(lrt_machine *m);
static uint32_t next_rng(lrt_machine *m);

int lrt_machine_init(lrt_machine *m, const lrt_machine_cfg *c)
{
    int owner[LRT_MACHINE_MAX_DRIVES];
    int rc;
    int s;
    int j;

    if (m == NULL || c == NULL) {
        return LRT_MACHINE_ERR_NULL;
    }
    memset(m, 0, sizeof(*m));
    m->c = *c;
    m->err_index = -1;
    if (c->n_drives < 1 || c->n_drives > LRT_MACHINE_MAX_DRIVES ||
        c->n_joints > LRT_MACHINE_MAX_JOINTS || c->n_links > LRT_MACHINE_MAX_LINKS ||
        c->n_switches > LRT_MACHINE_MAX_SWITCHES) {
        return fail(m, LRT_MACHINE_ERR_INDEX, -1, 0);
    }
    for (s = 0; s < c->n_drives; s++) {
        if (!c->drives[s].used) {
            return fail(m, LRT_MACHINE_ERR_INDEX, s, 0);
        }
    }
    rc = check_joints(m, owner);
    if (rc == LRT_MACHINE_OK) {
        rc = check_links(m);
    }
    if (rc == LRT_MACHINE_OK) {
        rc = check_io(m);
    }
    if (rc != LRT_MACHINE_OK) {
        return rc;
    }

    for (s = 0; s < c->n_drives; s++) {
        lrt_axis_params ap = c->drives[s].mech;
        lrt_machine_slot *sl = &m->slots[s];

        ap.use_stops = 0;
        if (owner[s] >= 0 && c->joints[owner[s]].use_stops) {
            const lrt_machine_joint_cfg *jc = &c->joints[owner[s]];
            ap.use_stops = 1;
            ap.stop_min = jc->stop_min;
            ap.stop_max = jc->stop_max;
            ap.stop_stiffness = jc->stop_k;
            ap.stop_damping_ratio = stop_damping_ratio(&ap, jc->stop_k, jc->stop_c);
        }
        rc = lrt_drive_init(&sl->drive, &c->drives[s].drive);
        if (rc != LRT_DRIVE_OK) {
            return fail(m, LRT_MACHINE_ERR_DRIVE, s, rc);
        }
        rc = lrt_axis_init(&sl->axis, &ap);
        if (rc != LRT_AXIS_OK) {
            return fail(m, LRT_MACHINE_ERR_MECH, s, rc);
        }
        sl->target = 0;
        sl->applied = 0;
    }
    m->rng = c->seed ? c->seed : 0x2545F491u;
    for (j = 0; j < c->n_joints; j++) {
        lrt_machine_joint_cfg *jc = &m->c.joints[j];
        if (jc->initial_random) {
            /* Start po wlaczeniu: losowo w zakresie, powtarzalnie dla ziarna (REQ-VM-07). */
            double u = (double)(next_rng(m) >> 8) * (1.0 / 16777216.0);
            jc->initial = jc->initial_min + u * (jc->initial_max - jc->initial_min);
        }
    }
    m->tool_length = c->probe_type != LRT_PROBE_NONE ? c->probe_tip_length : 0.0;
    lrt_live_log_init(&m->log);
    for (s = 0; s < c->n_switches; s++) {
        m->sw[s].tripped = -1; /* nieznany: pierwsza ocena bez histerezy i bez zdarzenia */
    }
    for (j = 0; j < c->n_joints; j++) {
        int k;
        for (k = 0; k < 2; k++) {
            if (c->joints[j].drive[k] >= 0) {
                lrt_axis_reset(&m->slots[c->joints[j].drive[k]].axis, m->c.joints[j].initial);
            }
        }
    }
    refresh(m);
    m->events = 0;
    for (j = 0; j < LRT_MACHINE_MAX_JOINTS; j++) {
        m->joint_events[j] = 0;
    }
    m->err_index = -1;
    m->err_detail = 0;
    return LRT_MACHINE_OK;
}

/* ---- krok -------------------------------------------------------------------------- */

static uint32_t next_rng(lrt_machine *m)
{
    uint32_t x = m->rng;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    m->rng = x;
    return x;
}

static int joint_of(const lrt_machine *m, int drive)
{
    int j;

    for (j = 0; j < m->c.n_joints; j++) {
        if (m->c.joints[j].drive[0] == drive || m->c.joints[j].drive[1] == drive) {
            return j;
        }
    }
    return -1;
}

/* Stan logiczny styku S (po drganiach): 1 = zadzialal. */
static int switch_active(const lrt_machine *m, int s)
{
    if (s < 0) {
        return 0;
    }
    return m->c.switches[s].nc ? !m->sw[s].closed : m->sw[s].closed;
}

/* Wejscia napedu N z poprzedniego kroku: styki na jego wejsciach i impuls indeksu. */
static unsigned drive_inputs(const lrt_machine *m, int s)
{
    const lrt_machine_drive_cfg *dc = &m->c.drives[s];
    unsigned in = 0u;

    if (switch_active(m, dc->din_neg_limit)) {
        in |= LRT_DIN_NEG_LIMIT;
    }
    if (switch_active(m, dc->din_pos_limit)) {
        in |= LRT_DIN_POS_LIMIT;
    }
    if (switch_active(m, dc->din_home)) {
        in |= LRT_DIN_HOME;
    }
    if (m->slots[s].index_pulse) {
        in |= LRT_DIN_INDEX;
    }
    return in;
}

static void joint_event(lrt_machine *m, int joint, unsigned ev)
{
    m->events |= ev;
    if (joint >= 0) {
        m->joint_events[joint] |= ev;
    }
}

static void update_joints(lrt_machine *m)
{
    int j;

    for (j = 0; j < m->c.n_joints; j++) {
        const lrt_machine_joint_cfg *jc = &m->c.joints[j];
        const lrt_axis *a0 = &m->slots[jc->drive[0]].axis;

        if (jc->drive[1] >= 0) {
            const lrt_axis *a1 = &m->slots[jc->drive[1]].axis;
            int over;
            m->joint_pos[j] = 0.5 * (a0->pos + a1->pos);
            m->joint_vel[j] = 0.5 * (a0->vel + a1->vel);
            m->skew[j] = a0->pos - a1->pos;
            over = fabs(m->skew[j]) > jc->max_skew;
            if (over && !m->skew_exceeded[j]) {
                joint_event(m, j, LRT_MACHINE_EV_GANTRY_SKEW);
            }
            m->skew_exceeded[j] = over;
        } else {
            m->joint_pos[j] = a0->pos;
            m->joint_vel[j] = a0->vel;
            m->skew[j] = 0.0;
        }
    }
}

static void update_switches(lrt_machine *m, double dt)
{
    int s;

    for (s = 0; s < m->c.n_switches; s++) {
        const lrt_machine_switch_cfg *w = &m->c.switches[s];
        lrt_machine_switch_state *st = &m->sw[s];
        double p = w->drive >= 0 ? m->slots[w->drive].axis.pos : m->joint_pos[w->joint];
        double over = (p - w->position) * w->side; /* > 0: po stronie aktywnej */
        int tripped = st->tripped;
        int logical;

        if (tripped < 0) {
            tripped = over >= 0.0;
        } else if (!tripped && over >= 0.0) {
            tripped = 1;
        } else if (tripped && over < -w->hysteresis) {
            tripped = 0;
        }
        if (st->tripped >= 0 && tripped != st->tripped) {
            if (tripped) {
                joint_event(m, w->joint, w->role == LRT_SWITCH_LIMIT ? LRT_MACHINE_EV_LIMIT_TRIP
                                                                    : LRT_MACHINE_EV_HOME_SENSOR);
            }
            if (w->bounce > 0.0) {
                st->bounce_left = w->bounce;
            }
        }
        st->tripped = tripped;
        logical = w->nc ? !tripped : tripped;
        if (st->bounce_left > 0.0) {
            st->closed = (int)(next_rng(m) >> 31);
            st->bounce_left -= dt;
        } else {
            st->closed = logical;
        }
    }
}

static void update_kinematics(lrt_machine *m)
{
    int contact = 0;
    const double *w = m->tool_workpiece;

    forward(&m->c, m->joint_pos, m->tool_length, m->tool_machine, m->tool_workpiece);
    if (m->c.probe_type != LRT_PROBE_NONE) {
        const double *lo = m->c.probe_min;
        const double *hi = m->c.probe_max;
        contact = w[0] >= lo[0] && w[0] <= hi[0] && w[1] >= lo[1] && w[1] <= hi[1] &&
                  w[2] <= hi[2] && (m->c.probe_type == LRT_PROBE_PLATE || w[2] >= lo[2]);
        if (contact && !m->probe_contact) {
            joint_event(m, -1, LRT_MACHINE_EV_PROBE);
        }
    }
    m->probe_contact = contact;
}

/* Wejscia: NC szeregowo (AND zamknietych), NO rownolegle (OR). */
static void update_inputs(lrt_machine *m)
{
    const lrt_machine_cfg *c = &m->c;
    unsigned char has_nc[LRT_MACHINE_MAX_IO];
    unsigned char all_closed[LRT_MACHINE_MAX_IO];
    unsigned char any_closed[LRT_MACHINE_MAX_IO];
    uint32_t in = 0;
    int i;
    int s;

    for (i = 0; i < LRT_MACHINE_MAX_IO; i++) {
        has_nc[i] = 0;
        all_closed[i] = 1;
        any_closed[i] = 0;
    }
#define LRT_CONTACT(input, nc, closed)                                                       \
    do {                                                                                     \
        int in_ = (input);                                                                   \
        if (in_ >= 0) {                                                                      \
            if (nc) {                                                                        \
                has_nc[in_] = 1;                                                             \
            }                                                                                \
            if (closed) {                                                                    \
                any_closed[in_] = 1;                                                         \
            } else {                                                                         \
                all_closed[in_] = 0;                                                         \
            }                                                                                \
        }                                                                                    \
    } while (0)
    for (s = 0; s < c->n_switches; s++) {
        LRT_CONTACT(c->switches[s].input, c->switches[s].nc, m->sw[s].closed);
    }
    for (s = 0; s < c->n_drives; s++) {
        const lrt_machine_slot *sl = &m->slots[s];
        double frac = fmod(sl->axis.th_m, LRT_TWO_PI);
        if (frac < 0.0) {
            frac += LRT_TWO_PI;
        }
        LRT_CONTACT(c->drives[s].index_input, 0,
                    sl->index_pulse || frac < c->drives[s].index_width);
    }
    LRT_CONTACT(c->estop_input, c->estop_nc,
                c->estop_nc ? !m->estop_pressed : m->estop_pressed);
    if (c->probe_type != LRT_PROBE_NONE) {
        LRT_CONTACT(c->probe_input, c->probe_nc, c->probe_nc ? !m->probe_contact : m->probe_contact);
    }
#undef LRT_CONTACT
    for (i = 0; i < LRT_MACHINE_MAX_IO; i++) {
        int level = has_nc[i] ? all_closed[i] && any_closed[i] : any_closed[i];
        if (level) {
            in |= 1u << i;
        }
    }
    m->inputs = in;
}

/* Cel napedu w biezacym podkroku: poza lrt_machine_step_cycle albo poza CSP - cel mastera;
 * w cyklu - liniowo od celu z poczatku cyklu (w ramce przesunietej przez baze w napedzie). */
static int32_t substep_target(const lrt_machine *m, const lrt_machine_slot *sl)
{
    double from;

    if (m->ip_n <= 1 || !sl->cycle_interp) {
        return sl->target;
    }
    from = (double)sl->cycle_from -
           ((double)lrt_drive_position_offset(&sl->drive) - (double)sl->cycle_offset);
    return (int32_t)lround(from + ((double)sl->target - from) * m->ip_k / m->ip_n);
}

int lrt_machine_step_cycle(lrt_machine *m, double dt, int n)
{
    int s;
    int k;
    int rc = LRT_MACHINE_OK;

    if (m == NULL) {
        return LRT_MACHINE_ERR_NULL;
    }
    if (n < 1 || n > LRT_MACHINE_MAX_SUBSTEPS || !(dt > 0.0) || !isfinite(dt)) {
        return fail(m, LRT_MACHINE_ERR_DT, -1, 0);
    }
    for (s = 0; s < m->c.n_drives; s++) {
        lrt_machine_slot *sl = &m->slots[s];

        sl->cycle_from = sl->applied;
        sl->cycle_offset = lrt_drive_position_offset(&sl->drive);
        sl->cycle_interp = lrt_drive_get_state(&sl->drive) == LRT_DRIVE_OPERATION_ENABLED &&
                           sl->drive.mode_of_operation == LRT_MODE_CSP;
    }
    m->ip_n = n;
    for (k = 1; k <= n && rc == LRT_MACHINE_OK; k++) {
        m->ip_k = k;
        rc = lrt_machine_step(m, dt / n);
    }
    m->ip_n = 0;
    m->ip_k = 0;
    return rc;
}

int lrt_machine_step(lrt_machine *m, double dt)
{
    int s;

    if (m == NULL) {
        return LRT_MACHINE_ERR_NULL;
    }
    if (!(dt > 0.0) || dt > LRT_DRIVE_MAX_DT || !isfinite(dt)) {
        return fail(m, LRT_MACHINE_ERR_DT, -1, 0);
    }
    for (s = 0; s < m->c.n_drives; s++) {
        lrt_machine_slot *sl = &m->slots[s];
        lrt_drive_feedback fb;
        uint16_t cw = sl->controlword;
        double tau = 0.0;
        unsigned ev;
        long rev;
        int rc;
        int joint;

        if (m->estop_pressed && m->c.estop_action == LRT_ESTOP_QUICK_STOP) {
            cw = (uint16_t)(cw & ~LRT_CW_QUICK_STOP);
        }
        lrt_drive_set_controlword(&sl->drive, cw);
        lrt_drive_set_target_position(&sl->drive, substep_target(m, sl));
        lrt_drive_set_inputs(&sl->drive, drive_inputs(m, s));
        fb.theta_m = sl->axis.th_m;
        fb.omega_m = sl->axis.w_m;
        fb.torque_avail = lrt_axis_torque_limit(&sl->axis, fabs(sl->axis.w_m));
        fb.j_total = lrt_axis_j_total(&sl->axis);
        rc = lrt_drive_step(&sl->drive, &fb, dt, &tau);
        if (rc != LRT_DRIVE_OK) {
            return fail(m, LRT_MACHINE_ERR_STEP, s, rc);
        }
        sl->applied = sl->drive.target_counts; /* po ewentualnym przesunieciu ramki (baza) */
        rc = lrt_axis_step(&sl->axis, tau, dt);
        if (rc != LRT_AXIS_OK) {
            return fail(m, LRT_MACHINE_ERR_STEP, s, rc);
        }
        joint = joint_of(m, s);

        ev = lrt_axis_events(&sl->axis) & (LRT_AXIS_EV_HARDSTOP_MIN | LRT_AXIS_EV_HARDSTOP_MAX);
        if (ev && joint >= 0) {
            if (sl->axis.impact_speed > m->impact_speed[joint]) {
                m->impact_speed[joint] = sl->axis.impact_speed;
            }
            if (!sl->in_stop) {
                joint_event(m, joint, LRT_MACHINE_EV_CRASH_HARDSTOP); /* nowy kontakt */
            }
            if (m->c.joints[joint].stop_fault &&
                lrt_drive_get_state(&sl->drive) != LRT_DRIVE_FAULT &&
                lrt_drive_get_state(&sl->drive) != LRT_DRIVE_FAULT_REACTION_ACTIVE) {
                lrt_drive_inject_fault(&sl->drive, LRT_DRIVE_FAULT_HW_LIMIT, 0);
            }
        }
        sl->in_stop = ev != 0;
        lrt_axis_clear_events(&sl->axis);

        if (lrt_drive_get_state(&sl->drive) == LRT_DRIVE_FAULT) {
            if (!sl->was_fault) {
                joint_event(m, joint, LRT_MACHINE_EV_DRIVE_FAULT);
            }
            sl->was_fault = 1;
        } else {
            sl->was_fault = 0;
        }

        rev = (long)floor(sl->axis.th_m / LRT_TWO_PI);
        sl->index_pulse = rev != sl->rev;
        if (sl->index_pulse) {
            sl->index_count++;
            sl->index_latch = sl->axis.pos;
            sl->rev = rev;
        }
    }
    update_joints(m);
    update_switches(m, dt);
    update_kinematics(m);
    update_inputs(m);
    m->time += dt;
    return LRT_MACHINE_OK;
}

const char *lrt_machine_strerror(int status)
{
    switch (status) {
    case LRT_MACHINE_OK:
        return "OK";
    case LRT_MACHINE_ERR_NULL:
        return "pusty wskaznik";
    case LRT_MACHINE_ERR_KEY:
        return "nieznany klucz konfiguracji maszyny";
    case LRT_MACHINE_ERR_INDEX:
        return "indeks elementu poza zakresem albo luka w numeracji";
    case LRT_MACHINE_ERR_VALUE:
        return "niedozwolona wartosc klucza konfiguracji";
    case LRT_MACHINE_ERR_DRIVE:
        return "niepoprawne parametry napedu";
    case LRT_MACHINE_ERR_MECH:
        return "niepoprawna mechanika napedu";
    case LRT_MACHINE_ERR_JOINT:
        return "niepoprawna os maszyny (napedy, rodzaj, rozjazd gantry, zderzaki)";
    case LRT_MACHINE_ERR_LINK:
        return "niepoprawny lancuch kinematyczny";
    case LRT_MACHINE_ERR_SWITCH:
        return "niepoprawna krancowka albo czujnik bazowy";
    case LRT_MACHINE_ERR_IO:
        return "niepoprawne wejscie (bit poza zakresem albo NC i NO na jednym wejsciu)";
    case LRT_MACHINE_ERR_PROBE:
        return "niepoprawna konfiguracja sondy";
    case LRT_MACHINE_ERR_DT:
        return "niepoprawny krok czasu";
    case LRT_MACHINE_ERR_STEP:
        return "blad kroku osi albo napedu";
    default:
        return "nieznany kod bledu maszyny";
    }
}

int lrt_machine_err_index(const lrt_machine *m)
{
    return m != NULL ? m->err_index : -1;
}

int lrt_machine_err_detail(const lrt_machine *m)
{
    return m != NULL ? m->err_detail : 0;
}

unsigned long lrt_machine_cfg_size(void)
{
    return (unsigned long)sizeof(lrt_machine_cfg);
}

unsigned long lrt_machine_size(void)
{
    return (unsigned long)sizeof(lrt_machine);
}

/* ---- wejscia, otoczenie, wyjscia ---------------------------------------------------- */

static int valid_drive(const lrt_machine *m, int drive)
{
    return m != NULL && drive >= 0 && drive < m->c.n_drives;
}

static int valid_joint(const lrt_machine *m, int joint)
{
    return m != NULL && joint >= 0 && joint < m->c.n_joints;
}

int lrt_machine_set_controlword(lrt_machine *m, int drive, uint16_t controlword)
{
    if (!valid_drive(m, drive)) {
        return LRT_MACHINE_ERR_INDEX;
    }
    m->slots[drive].controlword = controlword;
    return LRT_MACHINE_OK;
}

int lrt_machine_set_target(lrt_machine *m, int drive, int32_t counts)
{
    if (!valid_drive(m, drive)) {
        return LRT_MACHINE_ERR_INDEX;
    }
    m->slots[drive].target = counts;
    return LRT_MACHINE_OK;
}

int32_t lrt_machine_counts_for(const lrt_machine *m, int drive, double position)
{
    double counts;

    if (!valid_drive(m, drive) || !isfinite(position)) {
        return 0;
    }
    /* Kat walu w impulsach minus przesuniecie przetwornika (enkoder przyrostowy, baza). */
    counts = position / m->slots[drive].axis.p.ratio * m->slots[drive].drive.counts_per_rad -
             (double)lrt_drive_position_offset(&m->slots[drive].drive);
    if (counts > 2147483647.0) {
        counts = 2147483647.0;
    } else if (counts < -2147483647.0) {
        counts = -2147483647.0;
    }
    return (int32_t)lround(counts);
}

int lrt_machine_set_joint_target(lrt_machine *m, int joint, double position)
{
    int k;

    if (!valid_joint(m, joint)) {
        return LRT_MACHINE_ERR_INDEX;
    }
    if (!isfinite(position)) {
        return LRT_MACHINE_ERR_VALUE;
    }
    for (k = 0; k < 2; k++) {
        int d = m->c.joints[joint].drive[k];
        if (d >= 0) {
            m->slots[d].target = lrt_machine_counts_for(m, d, position);
        }
    }
    return LRT_MACHINE_OK;
}

void lrt_machine_set_outputs(lrt_machine *m, uint32_t outputs)
{
    if (m != NULL) {
        m->outputs = outputs;
    }
}

uint32_t lrt_machine_outputs(const lrt_machine *m)
{
    return m != NULL ? m->outputs : 0u;
}

void lrt_machine_set_estop(lrt_machine *m, int pressed)
{
    int s;

    if (m == NULL || (pressed != 0) == m->estop_pressed) {
        return;
    }
    m->estop_pressed = pressed != 0;
    if (m->estop_pressed) {
        joint_event(m, -1, LRT_MACHINE_EV_ESTOP);
    }
    if (m->c.estop_action == LRT_ESTOP_STO) {
        for (s = 0; s < m->c.n_drives; s++) {
            if (m->estop_pressed) {
                lrt_drive_inject_fault(&m->slots[s].drive, LRT_DRIVE_FAULT_STO, 1);
            } else {
                lrt_drive_clear_fault_cause(&m->slots[s].drive, LRT_DRIVE_FAULT_STO);
            }
        }
    }
    update_inputs(m);
}

int lrt_machine_set_tool_length(lrt_machine *m, double length)
{
    if (m == NULL) {
        return LRT_MACHINE_ERR_NULL;
    }
    if (!(length >= 0.0) || !isfinite(length)) {
        return LRT_MACHINE_ERR_VALUE;
    }
    m->tool_length = length;
    update_kinematics(m);
    update_inputs(m);
    return LRT_MACHINE_OK;
}

static void refresh(lrt_machine *m)
{
    int s;

    for (s = 0; s < m->c.n_drives; s++) {
        m->slots[s].rev = (long)floor(m->slots[s].axis.th_m / LRT_TWO_PI);
        m->slots[s].index_pulse = 0;
    }
    update_joints(m);
    update_switches(m, 0.0);
    update_kinematics(m);
    update_inputs(m);
}

int lrt_machine_set_drive_position(lrt_machine *m, int drive, double position)
{
    if (!valid_drive(m, drive)) {
        return LRT_MACHINE_ERR_INDEX;
    }
    if (!isfinite(position)) {
        return LRT_MACHINE_ERR_VALUE;
    }
    lrt_axis_reset(&m->slots[drive].axis, position);
    refresh(m);
    return LRT_MACHINE_OK;
}

int lrt_machine_set_joint_position(lrt_machine *m, int joint, double position)
{
    int k;

    if (!valid_joint(m, joint)) {
        return LRT_MACHINE_ERR_INDEX;
    }
    if (!isfinite(position)) {
        return LRT_MACHINE_ERR_VALUE;
    }
    for (k = 0; k < 2; k++) {
        int d = m->c.joints[joint].drive[k];
        if (d >= 0) {
            lrt_axis_reset(&m->slots[d].axis, position);
        }
    }
    refresh(m);
    return LRT_MACHINE_OK;
}

int lrt_machine_set_live(lrt_machine *m, int drive, int param, double value)
{
    lrt_machine_slot *sl;
    int rc;

    if (!valid_drive(m, drive)) {
        return LRT_MACHINE_ERR_INDEX;
    }
    sl = &m->slots[drive];
    if (param == LRT_LIVE_TORQUE_LIMIT || param == LRT_LIVE_INERTIA_EST) {
        rc = lrt_drive_set_live(&sl->drive, param, value, &m->log);
        return rc == LRT_DRIVE_OK ? LRT_MACHINE_OK : fail(m, LRT_MACHINE_ERR_DRIVE, drive, rc);
    }
    rc = lrt_axis_set_live(&sl->axis, param, value, &m->log);
    return rc == LRT_AXIS_OK ? LRT_MACHINE_OK : fail(m, LRT_MACHINE_ERR_MECH, drive, rc);
}

uint32_t lrt_machine_inputs(const lrt_machine *m)
{
    return m != NULL ? m->inputs : 0u;
}

unsigned lrt_machine_events(const lrt_machine *m)
{
    return m != NULL ? m->events : 0u;
}

unsigned lrt_machine_joint_events(const lrt_machine *m, int joint)
{
    return valid_joint(m, joint) ? m->joint_events[joint] : 0u;
}

void lrt_machine_clear_events(lrt_machine *m)
{
    int j;

    if (m == NULL) {
        return;
    }
    m->events = 0;
    for (j = 0; j < LRT_MACHINE_MAX_JOINTS; j++) {
        m->joint_events[j] = 0;
        m->impact_speed[j] = 0.0;
    }
}

double lrt_machine_joint_position(const lrt_machine *m, int joint)
{
    return valid_joint(m, joint) ? m->joint_pos[joint] : 0.0;
}

double lrt_machine_joint_velocity(const lrt_machine *m, int joint)
{
    return valid_joint(m, joint) ? m->joint_vel[joint] : 0.0;
}

double lrt_machine_joint_skew(const lrt_machine *m, int joint)
{
    return valid_joint(m, joint) ? m->skew[joint] : 0.0;
}

double lrt_machine_impact_speed(const lrt_machine *m, int joint)
{
    return valid_joint(m, joint) ? m->impact_speed[joint] : 0.0;
}

double lrt_machine_drive_position(const lrt_machine *m, int drive)
{
    return valid_drive(m, drive) ? m->slots[drive].axis.pos : 0.0;
}

long lrt_machine_index_count(const lrt_machine *m, int drive)
{
    return valid_drive(m, drive) ? m->slots[drive].index_count : 0;
}

double lrt_machine_index_latch(const lrt_machine *m, int drive)
{
    return valid_drive(m, drive) ? m->slots[drive].index_latch : 0.0;
}

int lrt_machine_tool_tip(const lrt_machine *m, int workpiece_frame, double out[3])
{
    int i;

    if (m == NULL || out == NULL) {
        return LRT_MACHINE_ERR_NULL;
    }
    for (i = 0; i < 3; i++) {
        out[i] = workpiece_frame ? m->tool_workpiece[i] : m->tool_machine[i];
    }
    return LRT_MACHINE_OK;
}

double lrt_machine_time(const lrt_machine *m)
{
    return m != NULL ? m->time : 0.0;
}

lrt_drive *lrt_machine_drive(lrt_machine *m, int drive)
{
    return valid_drive(m, drive) ? &m->slots[drive].drive : NULL;
}

lrt_axis *lrt_machine_axis(lrt_machine *m, int drive)
{
    return valid_drive(m, drive) ? &m->slots[drive].axis : NULL;
}

const lrt_live_log *lrt_machine_live_log(const lrt_machine *m)
{
    return m != NULL ? &m->log : NULL;
}
