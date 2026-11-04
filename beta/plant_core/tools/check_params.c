/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - Plant: narzedzie sprawdzajace parametry napedu i osi walidatorami rdzenia C.
 * Model-Author: Claude
 *
 * Czyta ze stdin linie "nazwa wartosc" (komentarze od '#'), uzupelnia domyslne parametry
 * (lrt_drive_params_default, lrt_axis_params_default) i wola lrt_drive_params_check,
 * lrt_axis_params_check oraz lrt_drive_init / lrt_axis_init. Wypisuje jedna linie:
 *   OK                      - parametry poprawne,
 *   ERR <drive|axis|input>: <komunikat po polsku>.
 * Kod wyjscia: 0 = OK, 1 = blad parametrow, 2 = blad skladni wejscia.
 * Z opcja --simulate dodatkowo wykonuje krotki test dynamiki (linia "SIM ...").
 * Narzedzie jest poza rdzeniem RT (uzywa stdio); sluzy testom (tests/test_drive_library.py).
 *
 * Nazwy: "type" (0 CSP, 1 krokowiec open, 2 krokowiec closed), "drive.<pole>",
 * "axis.<pole>", "curve <omega> <moment>" (kolejne punkty krzywej; pierwsze wywolanie
 * zastepuje krzywa domyslna).
 */
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../axis.h"
#include "../drive.h"

typedef struct {
    const char *name;
    size_t offset;
    char kind; /* d = double, u = uint32, h = uint16, i = int, c = int8, s = int16 */
} field;

#define DF(n, k) {#n, offsetof(lrt_drive_params, n), k}
#define AF(n, k) {#n, offsetof(lrt_axis_params, n), k}

static const field drive_fields[] = {
    DF(counts_per_rev, 'd'),      DF(enc_noise_counts, 'd'),   DF(enc_noise_seed, 'u'),
    DF(rated_torque, 'd'),        DF(peak_torque, 'd'),        DF(peak_time_s, 'd'),
    DF(torque_limit_permille, 'h'), DF(kp_pos, 'd'),           DF(kv, 'd'),
    DF(ti, 'd'),                  DF(kff_vel, 'd'),            DF(kff_acc, 'd'),
    DF(inertia_est, 'd'),         DF(vel_filter_hz, 'd'),      DF(ff_filter_hz, 'd'),
    DF(max_speed, 'd'),           DF(following_window, 'u'),   DF(following_window_ms, 'h'),
    DF(quick_stop_decel, 'u'),    DF(quick_stop_option, 's'),  DF(fault_reaction_option, 's'),
    DF(standstill_speed, 'd'),    DF(boot_time_s, 'd'),        DF(full_steps_per_rev, 'i'),
    DF(stepper_damping_ratio, 'd'), DF(homing_method, 'c'),    DF(homing_speed_switch, 'u'),
    DF(homing_speed_zero, 'u'),   DF(homing_accel, 'u'),
};

static const field axis_fields[] = {
    AF(kind, 'i'),          AF(j_motor, 'd'),         AF(j_screw, 'd'),
    AF(load, 'd'),          AF(ratio, 'd'),           AF(friction_coulomb, 'd'),
    AF(friction_static, 'd'), AF(friction_viscous, 'd'), AF(gravity_force, 'd'),
    AF(backlash, 'd'),      AF(stiffness, 'd'),       AF(damping_ratio, 'd'),
};

static int set_field(void *base, const field *f, double v)
{
    char *p = (char *)base + f->offset;

    switch (f->kind) {
    case 'd':
        *(double *)p = v;
        break;
    case 'u':
        *(uint32_t *)p = (uint32_t)v;
        break;
    case 'h':
        *(uint16_t *)p = (uint16_t)v;
        break;
    case 'i':
        *(int *)p = (int)v;
        break;
    case 'c':
        *(int8_t *)p = (int8_t)v;
        break;
    case 's':
        *(int16_t *)p = (int16_t)v;
        break;
    default:
        return -1;
    }
    return 0;
}

static const field *find(const field *tab, size_t n, const char *name)
{
    size_t i;

    for (i = 0; i < n; i++) {
        if (strcmp(tab[i].name, name) == 0) {
            return &tab[i];
        }
    }
    return NULL;
}

/* Krotki test dynamiki: wlaczenie napedu i ruch 0,5 obr. po profilu cosinusowym (1 s) + 0,5 s
 * wybiegu. Wypisuje "SIM state=<n> fault=<n> err_counts=<n> lost_steps=<n>". */
static int simulate(const lrt_drive_params *dp, const lrt_axis_params *ap)
{
    lrt_drive d;
    lrt_axis a;
    lrt_drive_feedback fb;
    double dt = (dp->type == LRT_DRIVE_STEPPER_OPEN) ? 1.0e-4 : 1.0e-3;
    double amp = 0.5 * dp->counts_per_rev;
    double t = 0.0;
    double tau = 0.0;
    long n;
    long i;
    int32_t target = 0;
    int rc;

    rc = lrt_axis_init(&a, ap);
    if (rc == LRT_AXIS_OK) {
        rc = lrt_drive_init(&d, dp);
    }
    if (rc != LRT_AXIS_OK && rc != LRT_DRIVE_OK) {
        printf("ERR sim: init %d\n", rc);
        return 1;
    }
    n = (long)((dp->boot_time_s + 0.2 + 1.5) / dt);
    for (i = 0; i < n; i++) {
        double prog = 0.0;

        fb.theta_m = a.th_m;
        fb.omega_m = a.w_m;
        fb.torque_avail = lrt_axis_torque_limit(&a, a.w_m < 0 ? -a.w_m : a.w_m);
        fb.j_total = lrt_axis_j_total(&a);
        if (t >= dp->boot_time_s + 0.2) {
            double s = t - dp->boot_time_s - 0.2;

            prog = (s >= 1.0) ? 1.0 : 0.5 * (1.0 - cos(3.14159265358979323846 * s));
        }
        target = (int32_t)(amp * prog + 0.5);
        lrt_drive_set_target_position(&d, target);
        if (t < dp->boot_time_s + 0.02) {
            lrt_drive_set_controlword(&d, 0);
        } else if (t < dp->boot_time_s + 0.1) {
            lrt_drive_set_controlword(&d, LRT_CW_CMD_SHUTDOWN);
        } else if (t < dp->boot_time_s + 0.12) {
            lrt_drive_set_controlword(&d, LRT_CW_CMD_SWITCH_ON);
        } else {
            lrt_drive_set_controlword(&d, LRT_CW_CMD_ENABLE_OPERATION);
        }
        rc = lrt_drive_step(&d, &fb, dt, &tau);
        if (rc == LRT_DRIVE_OK) {
            rc = lrt_axis_step(&a, tau, dt);
        }
        if (rc != LRT_DRIVE_OK) {
            printf("ERR sim: krok %d\n", rc);
            return 1;
        }
        t += dt;
    }
    printf("SIM state=%d fault=%d err_counts=%ld lost_steps=%d\n", (int)lrt_drive_get_state(&d),
           d.fault, (long)(target - (int32_t)floor(a.th_m * d.counts_per_rad + 0.5)),
           lrt_drive_lost_steps(&d));
    return 0;
}

int main(int argc, char **argv)
{
    char line[256];
    lrt_drive_params dp;
    lrt_axis_params ap;
    lrt_drive drive;
    lrt_axis axis;
    int type = 0;
    int curve_n = 0;
    int rc;
    static char pairs[512][256];
    size_t n_pairs = 0;
    size_t i;

    /* Pierwszy przebieg: typ napedu (domyslne zaleza od typu). */
    while (fgets(line, sizeof(line), stdin) != NULL && n_pairs < 512) {
        char *hash = strchr(line, '#');

        if (hash != NULL) {
            *hash = '\0';
        }
        if (strspn(line, " \t\r\n") == strlen(line)) {
            continue;
        }
        memcpy(pairs[n_pairs], line, sizeof(line));
        if (strncmp(line, "type ", 5) == 0) {
            type = atoi(line + 5);
        }
        n_pairs++;
    }
    lrt_drive_params_default(&dp, (lrt_drive_type)type);
    dp.type = (lrt_drive_type)type;
    lrt_axis_params_default(&ap);
    for (i = 0; i < n_pairs; i++) {
        char name[64];
        double a;
        double b;
        int got = sscanf(pairs[i], "%63s %lf %lf", name, &a, &b);

        if (got < 2) {
            printf("ERR input: zla skladnia linii: %s", pairs[i]);
            return 2;
        }
        if (strcmp(name, "type") == 0) {
            continue;
        }
        if (strcmp(name, "curve") == 0) {
            if (got != 3 || curve_n >= LRT_AXIS_CURVE_MAX) {
                printf("ERR input: zly punkt krzywej: %s", pairs[i]);
                return 2;
            }
            ap.curve[curve_n].omega = a;
            ap.curve[curve_n].torque = b;
            curve_n++;
            ap.n_curve = curve_n;
        } else if (strncmp(name, "drive.", 6) == 0) {
            const field *f = find(drive_fields, sizeof(drive_fields) / sizeof(drive_fields[0]),
                                  name + 6);

            if (f == NULL || set_field(&dp, f, a) != 0) {
                printf("ERR input: nieznane pole napedu: %s\n", name);
                return 2;
            }
        } else if (strncmp(name, "axis.", 5) == 0) {
            const field *f = find(axis_fields, sizeof(axis_fields) / sizeof(axis_fields[0]),
                                  name + 5);

            if (f == NULL || set_field(&ap, f, a) != 0) {
                printf("ERR input: nieznane pole osi: %s\n", name);
                return 2;
            }
        } else {
            printf("ERR input: nieznana nazwa: %s\n", name);
            return 2;
        }
    }
    rc = lrt_drive_params_check(&dp);
    if (rc == LRT_DRIVE_OK) {
        rc = lrt_drive_init(&drive, &dp);
    }
    if (rc != LRT_DRIVE_OK) {
        printf("ERR drive: %s\n", lrt_drive_strerror(rc));
        return 1;
    }
    rc = lrt_axis_params_check(&ap);
    if (rc == LRT_AXIS_OK) {
        rc = lrt_axis_init(&axis, &ap);
    }
    if (rc != LRT_AXIS_OK) {
        printf("ERR axis: %s\n", lrt_axis_strerror(rc));
        return 1;
    }
    printf("OK\n");
    if (argc > 1 && strcmp(argv[1], "--simulate") == 0) {
        return simulate(&dp, &ap);
    }
    return 0;
}
