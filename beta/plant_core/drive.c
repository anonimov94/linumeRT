/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - Plant, modul napedu wirtualnego (CiA 402, CSP, krokowiec).
 * Model-Author: Claude
 *
 * Kolejnosc pracy lrt_drive_step():
 *   1. pomiar (kwantyzacja enkodera, szum, filtr predkosci),
 *   2. wykrycie awarii (wstrzykniete, okno bledu nadazania, I2t),
 *   3. maszyna stanow wg slowa sterujacego,
 *   4. moment zadany dla biezacego stanu,
 *   5. I2t, raportowane wartosci.
 * Awaria wykryta w kroku n daje moment zero juz w kroku n. Przeciazenie I2t jest wykrywane
 * w kroku n+1 po przekroczeniu progu (opoznienie jednego kroku).
 * Zadnych alokacji ani I/O (CLAUDE.md §5).
 */
#include "drive.h"

#include <math.h>
#include <string.h>

#define TWO_PI 6.283185307179586476925286766559
#define RAMP_TIMEOUT_S 10.0
#define WARN_FRACTION 0.8
#define OVERLOAD_RESET_FRACTION 0.5
#define SLIP_HYSTERESIS 0.6
/* Tlumienie wzgledem pola nie moze przewyzszyc 20 % amplitudy momentu: w prawdziwym
 * krokowcu jest slabe wobec momentu reluktancyjnego i nie maskuje poslizgu. */
#define STEPPER_DAMPING_CAP 0.2
#define RNG_DEFAULT_SEED 0x9E3779B9u

/* ------------------------------------------------------------------------- */
/* Tabela awarii (jedno zrodlo prawdy: LRT_DRIVE_FAULT_LIST w drive.h)         */
/* ------------------------------------------------------------------------- */

typedef struct {
    int fault;
    uint16_t cia;
    const char *alarm;
} fault_row;

static const fault_row FAULT_TABLE[] = {
#define LRT_DRIVE_FAULT_ROW(name, num, cia, alarm) {(num), (cia), (alarm)},
    LRT_DRIVE_FAULT_LIST(LRT_DRIVE_FAULT_ROW)
#undef LRT_DRIVE_FAULT_ROW
};

static const fault_row *find_fault(int fault)
{
    size_t i;

    for (i = 0; i < sizeof(FAULT_TABLE) / sizeof(FAULT_TABLE[0]); i++) {
        if (FAULT_TABLE[i].fault == fault) {
            return &FAULT_TABLE[i];
        }
    }
    return NULL;
}

const char *lrt_drive_fault_alarm(int fault)
{
    const fault_row *r = find_fault(fault);

    return r != NULL ? r->alarm : NULL;
}

uint16_t lrt_drive_fault_error_code(int fault)
{
    const fault_row *r = find_fault(fault);

    return r != NULL ? r->cia : 0;
}

/* ------------------------------------------------------------------------- */
/* Pomocnicze                                                                 */
/* ------------------------------------------------------------------------- */

static int32_t sat_i32(double x)
{
    if (x >= 2147483647.0) {
        return INT32_MAX;
    }
    if (x <= -2147483648.0) {
        return INT32_MIN;
    }
    return (int32_t)x;
}

static int32_t round_i32(double x)
{
    return sat_i32(floor(x + 0.5));
}

static int16_t sat_i16(double x)
{
    if (x >= 32767.0) {
        return INT16_MAX;
    }
    if (x <= -32768.0) {
        return INT16_MIN;
    }
    return (int16_t)x;
}

static double clampd(double x, double lo, double hi)
{
    if (x < lo) {
        return lo;
    }
    if (x > hi) {
        return hi;
    }
    return x;
}

/* Wspolczynnik filtru jednobiegunowego dla kroku dt i czestotliwosci granicznej hz. */
static double lpf_alpha(double dt, double hz)
{
    double tau = 1.0 / (TWO_PI * hz);

    return dt / (dt + tau);
}

static uint32_t rng_next(uint32_t *s)
{
    uint32_t x = *s;

    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *s = x;
    return x;
}

/* Przyblizenie rozkladu normalnego (suma 12 jednostajnych - 6): srednia 0, wariancja 1. */
static double rng_gauss(uint32_t *s)
{
    double sum = 0.0;
    int i;

    for (i = 0; i < 12; i++) {
        sum += (double)(rng_next(s) >> 8) * (1.0 / 16777216.0);
    }
    return sum - 6.0;
}

/* Najwieksza dozwolona wartosc 6072h [promile] wynikajaca z momentu szczytowego. */
static unsigned max_torque_permille(const lrt_drive_params *p)
{
    if (p->peak_torque > p->rated_torque) {
        return (unsigned)(p->peak_torque / p->rated_torque * 1000.0);
    }
    return 1000u;
}

/* Pozycja rzeczywista w ramce raportowanej [impulsy]: krokowiec bez sprzezenia zna tylko
 * pozycje pola. */
static double actual_counts(const lrt_drive *d)
{
    return d->p.type == LRT_DRIVE_STEPPER_OPEN ? (double)d->pos_report : (double)d->pos_meas;
}

/* Bazowanie bez ruchu: trzyma biezaca pozycje (wejscie w tryb 6, przerwanie). */
static void homing_hold(lrt_drive *d)
{
    d->hm_phase = LRT_HM_IDLE;
    d->hm_vel = 0.0;
    d->hm_vel_goal = 0.0;
    d->hm_push_timer = 0.0;
    d->hm_target = actual_counts(d);
}

/* ------------------------------------------------------------------------- */
/* Parametry                                                                  */
/* ------------------------------------------------------------------------- */

void lrt_drive_tune_servo(lrt_drive_params *p, double j_total, double vel_bandwidth, double dt)
{
    double bw = vel_bandwidth;

    if (p == NULL || !(j_total > 0.0) || !(bw > 0.0) || !(dt > 0.0)) {
        return;
    }
    if (bw > 0.15 / dt) {
        bw = 0.15 / dt;
    }
    p->inertia_est = j_total;
    p->kv = j_total * bw;
    p->ti = 4.0 / bw;
    p->kp_pos = bw / 5.0;
}

void lrt_drive_params_default(lrt_drive_params *p, lrt_drive_type type)
{
    if (p == NULL) {
        return;
    }
    memset(p, 0, sizeof(*p));
    if (type != LRT_DRIVE_STEPPER_OPEN && type != LRT_DRIVE_STEPPER_CLOSED) {
        type = LRT_DRIVE_SERVO_CSP;
    }
    p->type = type;
    p->vel_filter_hz = 400.0;
    p->ff_filter_hz = 300.0;
    p->max_speed = 500.0;
    p->kff_vel = 1.0;
    p->kff_acc = 1.0;
    p->quick_stop_option = 2;
    p->fault_reaction_option = 0;
    p->standstill_speed = 0.1;
    p->homing_method = 35;
    p->full_steps_per_rev = 200;
    p->stepper_damping_ratio = 0.2;

    if (type == LRT_DRIVE_SERVO_CSP) {
        p->counts_per_rev = 131072.0;
        p->rated_torque = 1.27;
        p->peak_torque = 3.8;
        p->peak_time_s = 1.0;
        p->torque_limit_permille = (uint16_t)max_torque_permille(p);
        lrt_drive_tune_servo(p, 1.0e-4, 300.0, 1.0e-3);
        p->following_window = 3640u; /* ok. 10 stopni */
        p->following_window_ms = 20u;
        p->quick_stop_decel = 26214400u; /* 200 obr/s^2 */
    } else if (type == LRT_DRIVE_STEPPER_OPEN) {
        p->counts_per_rev = 3200.0; /* 200 krokow x 16 mikrokrokow */
        p->rated_torque = 3.0;
        p->peak_torque = 3.0;
        p->torque_limit_permille = 1000u;
        p->following_window = 0xFFFFFFFFu; /* nie dotyczy napedu bez sprzezenia */
        p->following_window_ms = 0u;
        p->quick_stop_decel = 160000u; /* 50 obr/s^2 */
    } else {
        p->counts_per_rev = 4000.0; /* enkoder 1000 linii x 4 */
        p->rated_torque = 2.2;
        p->peak_torque = 2.2;
        p->torque_limit_permille = 1000u;
        lrt_drive_tune_servo(p, 2.0e-4, 200.0, 1.0e-3);
        p->following_window = 200u; /* ok. 18 stopni */
        p->following_window_ms = 10u;
        p->quick_stop_decel = 200000u; /* 50 obr/s^2 */
    }
    p->homing_speed_switch = (uint32_t)p->counts_per_rev;
    p->homing_speed_zero = (uint32_t)(p->counts_per_rev / 4.0);
    p->homing_accel = p->quick_stop_decel;
    p->home_offset = 0;
    p->hardstop_time_s = 0.05;
    p->encoder = LRT_ENC_IDEAL;
}

int lrt_drive_params_check(const lrt_drive_params *p)
{
    if (p == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    if (p->type != LRT_DRIVE_SERVO_CSP && p->type != LRT_DRIVE_STEPPER_OPEN &&
        p->type != LRT_DRIVE_STEPPER_CLOSED) {
        return LRT_DRIVE_ERR_TYPE;
    }
    if (!isfinite(p->counts_per_rev) || p->counts_per_rev < 1.0 || p->counts_per_rev > 1.0e9 ||
        !isfinite(p->enc_noise_counts) || p->enc_noise_counts < 0.0 ||
        p->enc_noise_counts > 1.0e6 || p->encoder < LRT_ENC_IDEAL ||
        p->encoder > LRT_ENC_ABSOLUTE ||
        (p->type == LRT_DRIVE_STEPPER_OPEN && p->encoder != LRT_ENC_IDEAL)) {
        return LRT_DRIVE_ERR_RESOLUTION;
    }
    if (!isfinite(p->rated_torque) || p->rated_torque <= 0.0 || !isfinite(p->peak_torque) ||
        p->peak_torque < 0.0 || !isfinite(p->peak_time_s) || p->peak_time_s < 0.0 ||
        p->torque_limit_permille > max_torque_permille(p)) {
        return LRT_DRIVE_ERR_TORQUE;
    }
    if (!isfinite(p->kp_pos) || p->kp_pos < 0.0 || !isfinite(p->kv) || p->kv < 0.0 ||
        !isfinite(p->ti) || p->ti < 0.0 || !isfinite(p->kff_vel) || p->kff_vel < 0.0 ||
        p->kff_vel > 2.0 || !isfinite(p->kff_acc) || p->kff_acc < 0.0 || p->kff_acc > 2.0 ||
        !isfinite(p->inertia_est) || p->inertia_est < 0.0 || !isfinite(p->vel_filter_hz) ||
        p->vel_filter_hz <= 0.0 || !isfinite(p->ff_filter_hz) || p->ff_filter_hz <= 0.0 ||
        !isfinite(p->max_speed) || p->max_speed <= 0.0) {
        return LRT_DRIVE_ERR_GAINS;
    }
    if (p->quick_stop_decel == 0u || !isfinite(p->standstill_speed) ||
        p->standstill_speed <= 0.0 || !isfinite(p->boot_time_s) || p->boot_time_s < 0.0 ||
        (p->quick_stop_option != 1 && p->quick_stop_option != 2) ||
        (p->fault_reaction_option != 0 && p->fault_reaction_option != 2) ||
        !isfinite(p->hardstop_time_s) || p->hardstop_time_s < 0.0 ||
        p->hardstop_time_s > 10.0) {
        return LRT_DRIVE_ERR_LIMITS;
    }
    if (p->type != LRT_DRIVE_SERVO_CSP &&
        (p->full_steps_per_rev < 4 || p->full_steps_per_rev % 4 != 0 ||
         !isfinite(p->stepper_damping_ratio) || p->stepper_damping_ratio < 0.0 ||
         p->stepper_damping_ratio > 2.0)) {
        return LRT_DRIVE_ERR_STEPPER;
    }
    return LRT_DRIVE_OK;
}

const char *lrt_drive_strerror(int status)
{
    switch (status) {
    case LRT_DRIVE_OK:
        return "brak bledu";
    case LRT_DRIVE_ERR_NULL:
        return "pusty wskaznik";
    case LRT_DRIVE_ERR_TYPE:
        return "nieznany typ napedu";
    case LRT_DRIVE_ERR_RESOLUTION:
        return "rozdzielczosc, szum albo rodzaj enkodera niepoprawny (krokowiec bez sprzezenia "
               "nie ma enkodera)";
    case LRT_DRIVE_ERR_TORQUE:
        return "moment znamionowy, szczytowy albo limit niepoprawny";
    case LRT_DRIVE_ERR_GAINS:
        return "wzmocnienia, filtry albo FF poza zakresem";
    case LRT_DRIVE_ERR_LIMITS:
        return "okno bledu, hamowanie, czas rozruchu, czas zderzaka albo opcje poza zakresem";
    case LRT_DRIVE_ERR_STEPPER:
        return "liczba krokow na obrot (wielokrotnosc 4) albo tlumienie krokowca niepoprawne";
    case LRT_DRIVE_ERR_DT:
        return "krok czasu dt niepoprawny";
    case LRT_DRIVE_ERR_NUMERIC:
        return "NaN albo nieskonczonosc w sprzezeniu lub wyniku";
    case LRT_DRIVE_ERR_NO_OBJECT:
        return "obiekt albo podindeks nie istnieje";
    case LRT_DRIVE_ERR_READ_ONLY:
        return "obiekt tylko do odczytu";
    case LRT_DRIVE_ERR_RANGE:
        return "wartosc poza zakresem obiektu";
    case LRT_DRIVE_ERR_UNSUPPORTED:
        return "wartosc nieobslugiwana przez model napedu";
    case LRT_DRIVE_ERR_LIVE:
        return "nieznany parametr zmieniany w locie albo wartosc poza zakresem";
    default:
        return "nieznany kod bledu";
    }
}

/* ------------------------------------------------------------------------- */
/* Inicjalizacja i wejscia                                                    */
/* ------------------------------------------------------------------------- */

int lrt_drive_init(lrt_drive *d, const lrt_drive_params *p)
{
    int rc;

    if (d == NULL || p == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    rc = lrt_drive_params_check(p);
    if (rc != LRT_DRIVE_OK) {
        return rc;
    }
    memset(d, 0, sizeof(*d));
    d->p = *p;
    d->rad_per_count = TWO_PI / p->counts_per_rev;
    d->counts_per_rad = p->counts_per_rev / TWO_PI;
    d->pole_pairs = (double)p->full_steps_per_rev / 4.0;
    if (p->peak_torque > p->rated_torque && p->peak_time_s > 0.0) {
        d->i2t_limit = (p->peak_torque * p->peak_torque - p->rated_torque * p->rated_torque) *
                       p->peak_time_s;
    }
    d->mode_of_operation = 8;
    d->following_window = p->following_window;
    d->following_window_ms = p->following_window_ms;
    d->torque_limit_permille = p->torque_limit_permille;
    d->quick_stop_decel = p->quick_stop_decel;
    d->quick_stop_option = p->quick_stop_option;
    d->fault_reaction_option = p->fault_reaction_option;
    d->homing_method = p->homing_method;
    d->homing_speed_switch = p->homing_speed_switch;
    d->homing_speed_zero = p->homing_speed_zero;
    d->homing_accel = p->homing_accel;
    d->home_offset = p->home_offset;
    d->offset_known = p->encoder == LRT_ENC_IDEAL;
    d->battery_ok = 1;
    d->hm_phase = LRT_HM_IDLE;
    d->state = LRT_DRIVE_NOT_READY;
    d->rng = p->enc_noise_seed != 0u ? p->enc_noise_seed : RNG_DEFAULT_SEED;
    return LRT_DRIVE_OK;
}

void lrt_drive_set_controlword(lrt_drive *d, uint16_t controlword)
{
    if (d != NULL) {
        d->controlword = controlword;
    }
}

void lrt_drive_set_target_position(lrt_drive *d, int32_t counts)
{
    if (d != NULL) {
        d->target_counts = counts;
    }
}

/* ------------------------------------------------------------------------- */
/* Slownik obiektow                                                           */
/* ------------------------------------------------------------------------- */

static int homing_method_valid(int64_t m)
{
    if (m < 0) {
        return m >= -128;
    }
    return (m >= 1 && m <= 14) || (m >= 17 && m <= 30) || (m >= 33 && m <= 35) || m == 37;
}

int lrt_drive_od_read(const lrt_drive *d, uint16_t index, uint8_t sub, int64_t *value)
{
    if (d == NULL || value == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    if (index == 0x6099u) {
        switch (sub) {
        case 0:
            *value = 2;
            return LRT_DRIVE_OK;
        case 1:
            *value = d->homing_speed_switch;
            return LRT_DRIVE_OK;
        case 2:
            *value = d->homing_speed_zero;
            return LRT_DRIVE_OK;
        default:
            return LRT_DRIVE_ERR_NO_OBJECT;
        }
    }
    if (sub != 0) {
        return LRT_DRIVE_ERR_NO_OBJECT;
    }
    switch (index) {
    case 0x603Fu:
        *value = d->error_code;
        return LRT_DRIVE_OK;
    case 0x6040u:
        *value = d->controlword;
        return LRT_DRIVE_OK;
    case 0x6041u:
        *value = lrt_drive_statusword(d);
        return LRT_DRIVE_OK;
    case 0x605Au:
        *value = d->quick_stop_option;
        return LRT_DRIVE_OK;
    case 0x605Eu:
        *value = d->fault_reaction_option;
        return LRT_DRIVE_OK;
    case 0x6060u:
    case 0x6061u:
        *value = d->mode_of_operation;
        return LRT_DRIVE_OK;
    case 0x6064u:
        *value = d->pos_report;
        return LRT_DRIVE_OK;
    case 0x6065u:
        *value = d->following_window;
        return LRT_DRIVE_OK;
    case 0x6066u:
        *value = d->following_window_ms;
        return LRT_DRIVE_OK;
    case 0x606Cu:
        *value = d->vel_report;
        return LRT_DRIVE_OK;
    case 0x6072u:
        *value = d->torque_limit_permille;
        return LRT_DRIVE_OK;
    case 0x6077u:
        *value = d->torque_report;
        return LRT_DRIVE_OK;
    case 0x607Au:
        *value = d->target_counts;
        return LRT_DRIVE_OK;
    case 0x607Cu:
        *value = d->home_offset;
        return LRT_DRIVE_OK;
    case 0x6085u:
        *value = d->quick_stop_decel;
        return LRT_DRIVE_OK;
    case 0x6098u:
        *value = d->homing_method;
        return LRT_DRIVE_OK;
    case 0x609Au:
        *value = d->homing_accel;
        return LRT_DRIVE_OK;
    case 0x60B1u:
        *value = d->velocity_offset;
        return LRT_DRIVE_OK;
    case 0x60B2u:
        *value = d->torque_offset;
        return LRT_DRIVE_OK;
    default:
        return LRT_DRIVE_ERR_NO_OBJECT;
    }
}

int lrt_drive_od_write(lrt_drive *d, uint16_t index, uint8_t sub, int64_t value)
{
    if (d == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    if (index == 0x6099u) {
        if (sub == 0) {
            return LRT_DRIVE_ERR_READ_ONLY;
        }
        if (sub > 2) {
            return LRT_DRIVE_ERR_NO_OBJECT;
        }
        if (value < 1 || value > 0xFFFFFFFFLL) {
            return LRT_DRIVE_ERR_RANGE;
        }
        if (sub == 1) {
            d->homing_speed_switch = (uint32_t)value;
        } else {
            d->homing_speed_zero = (uint32_t)value;
        }
        return LRT_DRIVE_OK;
    }
    if (sub != 0) {
        return LRT_DRIVE_ERR_NO_OBJECT;
    }
    switch (index) {
    case 0x603Fu:
    case 0x6041u:
    case 0x6061u:
    case 0x6064u:
    case 0x606Cu:
    case 0x6077u:
        return LRT_DRIVE_ERR_READ_ONLY;
    case 0x6040u:
        if (value < 0 || value > 0xFFFF) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->controlword = (uint16_t)value;
        return LRT_DRIVE_OK;
    case 0x605Au:
        if (value < INT16_MIN || value > INT16_MAX) {
            return LRT_DRIVE_ERR_RANGE;
        }
        if (value != 1 && value != 2) {
            return LRT_DRIVE_ERR_UNSUPPORTED;
        }
        d->quick_stop_option = (int16_t)value;
        return LRT_DRIVE_OK;
    case 0x605Eu:
        if (value < INT16_MIN || value > INT16_MAX) {
            return LRT_DRIVE_ERR_RANGE;
        }
        if (value != 0 && value != 2) {
            return LRT_DRIVE_ERR_UNSUPPORTED;
        }
        d->fault_reaction_option = (int16_t)value;
        return LRT_DRIVE_OK;
    case 0x6060u:
        if (value < INT8_MIN || value > INT8_MAX) {
            return LRT_DRIVE_ERR_RANGE;
        }
        /* Obslugiwane: CSP (8) i bazowanie (6). Zmiana trybu przerywa bazowanie; w trybie 6
         * naped trzyma biezaca pozycje do startu bazowania. */
        if (value != LRT_MODE_CSP && value != LRT_MODE_HOMING) {
            return LRT_DRIVE_ERR_UNSUPPORTED;
        }
        if (value != d->mode_of_operation) {
            d->mode_of_operation = (int8_t)value;
            homing_hold(d);
        }
        return LRT_DRIVE_OK;
    case 0x6065u:
        if (value < 0 || value > 0xFFFFFFFFLL) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->following_window = (uint32_t)value;
        return LRT_DRIVE_OK;
    case 0x6066u:
        if (value < 0 || value > 0xFFFF) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->following_window_ms = (uint16_t)value;
        return LRT_DRIVE_OK;
    case 0x6072u:
        if (value < 0 || value > (int64_t)max_torque_permille(&d->p)) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->torque_limit_permille = (uint16_t)value;
        return LRT_DRIVE_OK;
    case 0x607Au:
        if (value < INT32_MIN || value > INT32_MAX) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->target_counts = (int32_t)value;
        return LRT_DRIVE_OK;
    case 0x607Cu:
        if (value < INT32_MIN || value > INT32_MAX) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->home_offset = (int32_t)value;
        return LRT_DRIVE_OK;
    case 0x6085u:
        if (value < 1 || value > 0xFFFFFFFFLL) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->quick_stop_decel = (uint32_t)value;
        return LRT_DRIVE_OK;
    case 0x6098u:
        if (!homing_method_valid(value)) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->homing_method = (int8_t)value;
        return LRT_DRIVE_OK;
    case 0x609Au:
        if (value < 1 || value > 0xFFFFFFFFLL) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->homing_accel = (uint32_t)value;
        return LRT_DRIVE_OK;
    case 0x60B1u:
        if (value < INT32_MIN || value > INT32_MAX) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->velocity_offset = (int32_t)value;
        return LRT_DRIVE_OK;
    case 0x60B2u:
        if (value < INT16_MIN || value > INT16_MAX) {
            return LRT_DRIVE_ERR_RANGE;
        }
        d->torque_offset = (int16_t)value;
        return LRT_DRIVE_OK;
    default:
        return LRT_DRIVE_ERR_NO_OBJECT;
    }
}

/* ------------------------------------------------------------------------- */
/* Wyjscia                                                                    */
/* ------------------------------------------------------------------------- */

static int state_produces_torque(const lrt_drive *d)
{
    return d->state == LRT_DRIVE_OPERATION_ENABLED ||
           ((d->state == LRT_DRIVE_QUICK_STOP_ACTIVE ||
             d->state == LRT_DRIVE_FAULT_REACTION_ACTIVE) &&
            d->ramp_active);
}

uint16_t lrt_drive_statusword(const lrt_drive *d)
{
    uint16_t sw;

    if (d == NULL) {
        return 0;
    }
    switch (d->state) {
    case LRT_DRIVE_NOT_READY:
        sw = 0x0000u;
        break;
    case LRT_DRIVE_SWITCH_ON_DISABLED:
        sw = LRT_SW_SWITCH_ON_DISABLED;
        break;
    case LRT_DRIVE_READY_TO_SWITCH_ON:
        sw = LRT_SW_QUICK_STOP | LRT_SW_READY_TO_SWITCH_ON | LRT_SW_VOLTAGE_ENABLED;
        break;
    case LRT_DRIVE_SWITCHED_ON:
        sw = LRT_SW_QUICK_STOP | LRT_SW_READY_TO_SWITCH_ON | LRT_SW_SWITCHED_ON |
             LRT_SW_VOLTAGE_ENABLED;
        break;
    case LRT_DRIVE_OPERATION_ENABLED:
        sw = LRT_SW_QUICK_STOP | LRT_SW_READY_TO_SWITCH_ON | LRT_SW_SWITCHED_ON |
             LRT_SW_OPERATION_ENABLED | LRT_SW_VOLTAGE_ENABLED;
        if (d->mode_of_operation == LRT_MODE_HOMING) {
            /* Tryb 6: bity 10/12/13 = stoi / baza ustalona / blad bazowania. */
            int still = d->hm_vel == 0.0 && (d->hm_phase == LRT_HM_IDLE ||
                                             d->hm_phase == LRT_HM_DONE ||
                                             d->hm_phase == LRT_HM_ERROR);
            if (still) {
                sw |= LRT_SW_TARGET_REACHED;
            }
            if (d->hm_attained && d->hm_phase != LRT_HM_ERROR) {
                sw |= LRT_SW_HOMING_ATTAINED;
            }
            if (d->hm_phase == LRT_HM_ERROR) {
                sw |= LRT_SW_HOMING_ERROR;
            }
            break;
        }
        sw |= LRT_SW_FOLLOWS_COMMAND;
        if (d->follow_exceeded) {
            sw |= LRT_SW_FOLLOWING_ERROR;
        }
        break;
    case LRT_DRIVE_QUICK_STOP_ACTIVE:
        sw = LRT_SW_READY_TO_SWITCH_ON | LRT_SW_SWITCHED_ON | LRT_SW_OPERATION_ENABLED |
             LRT_SW_VOLTAGE_ENABLED;
        break;
    case LRT_DRIVE_FAULT_REACTION_ACTIVE:
        sw = LRT_SW_READY_TO_SWITCH_ON | LRT_SW_SWITCHED_ON | LRT_SW_OPERATION_ENABLED |
             LRT_SW_FAULT | LRT_SW_VOLTAGE_ENABLED;
        break;
    case LRT_DRIVE_FAULT:
    default:
        sw = LRT_SW_FAULT | LRT_SW_VOLTAGE_ENABLED;
        break;
    }
    sw |= LRT_SW_REMOTE;
    if (d->warnings != 0u) {
        sw |= LRT_SW_WARNING;
    }
    if (d->torque_limited && state_produces_torque(d)) {
        sw |= LRT_SW_INTERNAL_LIMIT;
    }
    return sw;
}

int32_t lrt_drive_position_actual(const lrt_drive *d)
{
    return d != NULL ? d->pos_report : 0;
}

int32_t lrt_drive_velocity_actual(const lrt_drive *d)
{
    return d != NULL ? d->vel_report : 0;
}

int16_t lrt_drive_torque_actual(const lrt_drive *d)
{
    return d != NULL ? d->torque_report : 0;
}

uint16_t lrt_drive_error_code(const lrt_drive *d)
{
    return d != NULL ? d->error_code : 0;
}

lrt_drive_state lrt_drive_get_state(const lrt_drive *d)
{
    return d != NULL ? d->state : LRT_DRIVE_NOT_READY;
}

int lrt_drive_lost_steps(const lrt_drive *d)
{
    if (d == NULL || d->p.type != LRT_DRIVE_STEPPER_OPEN) {
        return 0;
    }
    return d->lost_periods * 4;
}

long lrt_drive_slip_events(const lrt_drive *d)
{
    return d != NULL ? d->slip_events : 0L;
}

/* ------------------------------------------------------------------------- */
/* Awarie                                                                     */
/* ------------------------------------------------------------------------- */

int lrt_drive_inject_fault(lrt_drive *d, int fault, int sticky)
{
    if (d == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    if (find_fault(fault) == NULL) {
        return LRT_DRIVE_ERR_RANGE;
    }
    d->pending_fault = fault;
    d->pending_sticky = sticky != 0;
    return LRT_DRIVE_OK;
}

void lrt_drive_clear_fault_cause(lrt_drive *d, int fault)
{
    if (d != NULL && fault > 0 && fault < (int)(8 * sizeof(unsigned))) {
        d->fault_cause_mask &= ~(1u << fault);
    }
}

/* Rozpoczyna hamowanie rampa (quick stop albo reakcja na awarie opcji 2). */
static void start_ramp(lrt_drive *d)
{
    d->ramp_active = 1;
    d->ramp_time = 0.0;
    d->ramp_v = d->p.type == LRT_DRIVE_STEPPER_OPEN ? d->field_omega : d->vel_meas;
}

static void raise_fault(lrt_drive *d, int fault)
{
    int was_torque = state_produces_torque(d);
    int was_ramping = d->ramp_active;

    d->fault = fault;
    d->error_code = lrt_drive_fault_error_code(fault);
    d->state = LRT_DRIVE_FAULT_REACTION_ACTIVE;
    d->ramp_active = 0;
    if (was_torque && d->fault_reaction_option == 2) {
        if (was_ramping) {
            d->ramp_active = 1; /* kontynuuj biezace hamowanie */
        } else {
            start_ramp(d);
        }
    }
}

/* Zwraca 1, gdy wykryto awarie (stan zmieniony na FAULT_REACTION_ACTIVE). */
static int detect_faults(lrt_drive *d, double dt)
{
    lrt_drive_state st = d->state;
    int active = st != LRT_DRIVE_NOT_READY && st != LRT_DRIVE_FAULT &&
                 st != LRT_DRIVE_FAULT_REACTION_ACTIVE;
    int f;

    if (d->pending_fault != 0) {
        f = d->pending_fault;
        d->pending_fault = 0;
        if (d->pending_sticky) {
            d->fault_cause_mask |= 1u << f;
        }
        if (active) {
            raise_fault(d, f);
            return 1;
        }
    }
    if (active && d->abs_lost) {
        d->abs_lost = 0; /* jednorazowo: po resecie pozycja w jednym obrocie, wymagana baza */
        raise_fault(d, LRT_DRIVE_FAULT_ENCODER_BATTERY);
        return 1;
    }
    if (active && d->fault_cause_mask != 0u) {
        for (f = 1; f < LRT_DRIVE_FAULT_COUNT; f++) {
            if ((d->fault_cause_mask & (1u << f)) != 0u) {
                raise_fault(d, f);
                return 1;
            }
        }
    }
    if (st == LRT_DRIVE_OPERATION_ENABLED && d->p.type != LRT_DRIVE_STEPPER_OPEN &&
        d->hm_phase != LRT_HM_PUSH) {
        int64_t e = (int64_t)d->target_counts - (int64_t)d->pos_meas;
        double window_s = (double)d->following_window_ms * 0.001;

        if (e < 0) {
            e = -e;
        }
        d->follow_exceeded = e > (int64_t)d->following_window;
        if (d->follow_exceeded) {
            d->follow_timer += dt;
            if (d->follow_timer >= window_s - 0.5 * dt) {
                raise_fault(d, LRT_DRIVE_FAULT_FOLLOWING_ERROR);
                return 1;
            }
        } else {
            d->follow_timer = 0.0;
        }
    } else {
        d->follow_exceeded = 0;
        d->follow_timer = 0.0;
    }
    if (d->i2t_limit > 0.0 && state_produces_torque(d) && d->i2t_acc > d->i2t_limit) {
        raise_fault(d, LRT_DRIVE_FAULT_OVERLOAD);
        return 1;
    }
    return 0;
}

/* ------------------------------------------------------------------------- */
/* Pomiar                                                                     */
/* ------------------------------------------------------------------------- */

/* Pierwszy pomiar po wlaczeniu ustala przesuniecie przetwornika (REQ-VM-07): przyrostowy
 * zaczyna od zera, absolutny bierze przesuniecie z pliku stanu, a przy utraconym liczniku
 * obrotow zostaje pozycja w jednym obrocie i awaria E-4211 do ponownego bazowania. */
static void establish_offset(lrt_drive *d, double shaft_counts)
{
    double whole = floor(shaft_counts + 0.5);

    if (d->p.encoder == LRT_ENC_INCREMENTAL) {
        d->pos_offset = sat_i32(whole);
    } else if (d->p.encoder == LRT_ENC_ABSOLUTE && d->abs_restored && !d->abs_restore_valid) {
        double turn = d->p.counts_per_rev;
        d->pos_offset = sat_i32(whole - (whole - turn * floor(whole / turn)));
        d->abs_valid = 0;
        d->abs_lost = 1;
    } else if (d->p.encoder == LRT_ENC_ABSOLUTE) {
        d->abs_valid = 1; /* przesuniecie z pliku stanu albo 0 przy pierwszym uruchomieniu */
    }
    d->offset_known = 1;
}

static void update_measurement(lrt_drive *d, const lrt_drive_feedback *fb, double dt)
{
    double counts = fb->theta_m * d->counts_per_rad;
    double raw_v;

    if (!d->offset_known) {
        establish_offset(d, counts);
    }
    if (d->p.enc_noise_counts > 0.0) {
        counts += d->p.enc_noise_counts * rng_gauss(&d->rng);
    }
    d->pos_meas = round_i32(counts - (double)d->pos_offset);
    if (!d->have_meas) {
        d->prev_pos_meas = d->pos_meas;
        d->vel_meas = 0.0;
        d->have_meas = 1;
    }
    raw_v = (double)((int64_t)d->pos_meas - (int64_t)d->prev_pos_meas) * d->rad_per_count / dt;
    d->vel_meas += lpf_alpha(dt, d->p.vel_filter_hz) * (raw_v - d->vel_meas);
    d->prev_pos_meas = d->pos_meas;
}

/* ------------------------------------------------------------------------- */
/* Regulatory                                                                 */
/* ------------------------------------------------------------------------- */

static double torque_limit(const lrt_drive *d, const lrt_drive_feedback *fb)
{
    double lim = (double)d->torque_limit_permille * 0.001 * d->p.rated_torque;

    return fb->torque_avail < lim ? fb->torque_avail : lim;
}

/* Regulator predkosci PI z ograniczeniem i calkowaniem warunkowym (anty-windup).
 * tau_ff - skladnik sprzezenia w przod [N*m]. */
static double velocity_pi(lrt_drive *d, double v_err, double tau_ff, double limit, double dt)
{
    double tau = d->p.kv * v_err + d->integ + tau_ff;
    double tau_c = clampd(tau, -limit, limit);
    int saturated = tau != tau_c;

    d->torque_limited = saturated;
    if (d->p.ti > 0.0 && !(saturated && v_err * tau > 0.0)) {
        d->integ += d->p.kv / d->p.ti * v_err * dt;
        d->integ = clampd(d->integ, -limit, limit);
    }
    return tau_c;
}

static double ctrl_csp(lrt_drive *d, const lrt_drive_feedback *fb, double dt)
{
    double th_t = (double)d->target_counts * d->rad_per_count;
    double raw_v = (double)((int64_t)d->target_counts - (int64_t)d->prev_target) *
                   d->rad_per_count / dt;
    double a_ff = lpf_alpha(dt, d->p.ff_filter_hz);
    double prev_tv = d->tv_f;
    double raw_a;
    double err;
    double v_cmd;
    double tau_ff;
    double limit;

    d->prev_target = d->target_counts;
    d->tv_f += a_ff * (raw_v - d->tv_f);
    raw_a = (d->tv_f - prev_tv) / dt;
    d->ta_f += a_ff * (raw_a - d->ta_f);

    err = th_t - (double)d->pos_meas * d->rad_per_count;
    v_cmd = d->p.kp_pos * err + d->p.kff_vel * d->tv_f +
            (double)d->velocity_offset * d->rad_per_count;
    v_cmd = clampd(v_cmd, -d->p.max_speed, d->p.max_speed);
    tau_ff = d->p.kff_acc * d->p.inertia_est * d->ta_f +
             (double)d->torque_offset * 0.001 * d->p.rated_torque;
    limit = torque_limit(d, fb);
    return velocity_pi(d, v_cmd - d->vel_meas, tau_ff, limit, dt);
}

/* Moment krokowca bez sprzezenia dla zadanego pola (kat th_f, predkosc w_f). Sledzi
 * utracone okresy elektryczne (4 pelne kroki na okres) z histereza. */
static double ctrl_stepper_torque(lrt_drive *d, const lrt_drive_feedback *fb, double th_f,
                                  double w_f)
{
    double amp = torque_limit(d, fb);
    double x = d->pole_pairs * (th_f - fb->theta_m); /* kat elektryczny pola wzgledem wirnika */
    double delta = x - TWO_PI * (double)d->k0;
    double k_e = amp * d->pole_pairs;
    double c = 2.0 * d->p.stepper_damping_ratio * sqrt(k_e * fb->j_total);
    double tau_d = clampd(c * (w_f - fb->omega_m), -STEPPER_DAMPING_CAP * amp,
                          STEPPER_DAMPING_CAP * amp);
    double tau = amp * sin(delta) + tau_d;
    double periods = x / TWO_PI - (double)d->k0;
    double tau_c = clampd(tau, -amp, amp);

    d->torque_limited = tau != tau_c;
    if (fabs(periods - (double)d->lost_periods) > SLIP_HYSTERESIS) {
        int now = (int)floor(periods + 0.5);
        int diff = now - d->lost_periods;

        d->slip_events += diff < 0 ? -diff : diff;
        d->lost_periods = now;
    }
    return tau_c;
}

static double ctrl_stepper_open(lrt_drive *d, const lrt_drive_feedback *fb, double dt)
{
    /* Pole w ramce walu; pos_offset zmienia sie tylko przy bazowaniu w napedzie. */
    double th_f = ((double)d->target_counts + (double)d->pos_offset) * d->rad_per_count;
    double raw_w = (th_f - d->prev_field_theta) / dt;

    d->field_omega += lpf_alpha(dt, d->p.vel_filter_hz) * (raw_w - d->field_omega);
    d->prev_field_theta = th_f;
    d->field_theta = th_f;
    d->pos_report = d->target_counts;
    return ctrl_stepper_torque(d, fb, th_f, d->field_omega);
}

/* Hamowanie rampa do zera (quick stop albo reakcja na awarie). Po zatrzymaniu przechodzi
 * do SWITCH_ON_DISABLED (quick stop) albo FAULT (awaria). */
static double ctrl_ramp(lrt_drive *d, const lrt_drive_feedback *fb, double dt)
{
    double step = (double)d->quick_stop_decel * d->rad_per_count * dt;
    double tau;
    double speed;
    int done;

    if (d->ramp_v > step) {
        d->ramp_v -= step;
    } else if (d->ramp_v < -step) {
        d->ramp_v += step;
    } else {
        d->ramp_v = 0.0;
    }
    d->ramp_time += dt;
    if (d->p.type == LRT_DRIVE_STEPPER_OPEN) {
        d->field_theta += d->ramp_v * dt;
        d->prev_field_theta = d->field_theta;
        d->field_omega = d->ramp_v;
        d->pos_report = round_i32(d->field_theta * d->counts_per_rad - (double)d->pos_offset);
        tau = ctrl_stepper_torque(d, fb, d->field_theta, d->ramp_v);
        speed = fb->omega_m;
    } else {
        tau = velocity_pi(d, d->ramp_v - d->vel_meas, 0.0, torque_limit(d, fb), dt);
        speed = d->vel_meas;
    }
    done = (d->ramp_v == 0.0 && fabs(speed) < d->p.standstill_speed) ||
           d->ramp_time > RAMP_TIMEOUT_S;
    if (done) {
        d->ramp_active = 0;
        d->integ = 0.0;
        d->state = d->state == LRT_DRIVE_QUICK_STOP_ACTIVE ? LRT_DRIVE_SWITCH_ON_DISABLED
                                                          : LRT_DRIVE_FAULT;
        tau = 0.0;
    }
    return tau;
}

/* ------------------------------------------------------------------------- */
/* Maszyna stanow                                                             */
/* ------------------------------------------------------------------------- */

static void enter_operation(lrt_drive *d, const lrt_drive_feedback *fb)
{
    d->state = LRT_DRIVE_OPERATION_ENABLED;
    d->integ = 0.0;
    d->prev_target = d->target_counts;
    d->tv_f = 0.0;
    d->ta_f = 0.0;
    d->follow_timer = 0.0;
    d->follow_exceeded = 0;
    d->ramp_active = 0;
    if (d->mode_of_operation == LRT_MODE_HOMING) {
        homing_hold(d);
        d->target_counts = round_i32(d->hm_target);
        d->prev_target = d->target_counts;
    }
    if (d->p.type == LRT_DRIVE_STEPPER_OPEN) {
        double th_f = ((double)d->target_counts + (double)d->pos_offset) * d->rad_per_count;
        double period = d->p.counts_per_rev / d->pole_pairs; /* impulsy na okres elektryczny */
        int32_t whole = round_i32(d->pole_pairs * (th_f - fb->theta_m) / TWO_PI);

        /* Pole zatrzaskuje sie na najblizszym polozeniu rownowagi wirnika: reszta
         * z dzielenia przez okres elektryczny nie jest "utracona". Cale okresy miedzy polem
         * a wirnikiem trafiaja do pos_offset (sesja 015), wiec pozycja raportowana zawsze
         * odpowiada katowi walu minus przesuniecie, jak w napedach z enkoderem. */
        d->pos_offset = sat_i32((double)d->pos_offset - floor((double)whole * period + 0.5));
        th_f = ((double)d->target_counts + (double)d->pos_offset) * d->rad_per_count;
        d->field_theta = th_f;
        d->prev_field_theta = th_f;
        d->field_omega = 0.0;
        d->k0 = round_i32(d->pole_pairs * (th_f - fb->theta_m) / TWO_PI);
        d->lost_periods = 0;
        d->pos_report = d->target_counts;
    }
}

static void leave_to_disabled(lrt_drive *d)
{
    d->state = LRT_DRIVE_SWITCH_ON_DISABLED;
    d->ramp_active = 0;
    d->integ = 0.0;
}

static void try_fault_reset(lrt_drive *d)
{
    if (d->fault_cause_mask != 0u) {
        return; /* przyczyna trwa */
    }
    if (d->i2t_limit > 0.0 && d->i2t_acc > OVERLOAD_RESET_FRACTION * d->i2t_limit) {
        return; /* naped jeszcze goracy */
    }
    d->error_code = 0;
    d->fault = LRT_DRIVE_FAULT_NONE;
    leave_to_disabled(d);
}

static void run_state_machine(lrt_drive *d, const lrt_drive_feedback *fb, double dt)
{
    uint16_t cw = d->controlword;
    int disable_voltage = (cw & 0x0082u) == 0x0000u;
    int quick_stop = (cw & 0x0086u) == 0x0002u;
    int shutdown = (cw & 0x0087u) == 0x0006u;
    int switch_on = (cw & 0x0087u) == 0x0007u;
    int enable_op = (cw & 0x008Fu) == 0x000Fu;
    int disable_op = (cw & 0x008Fu) == 0x0007u;
    int reset_edge = (cw & LRT_CW_FAULT_RESET) != 0u &&
                     (d->prev_controlword & LRT_CW_FAULT_RESET) == 0u;

    switch (d->state) {
    case LRT_DRIVE_NOT_READY:
        d->boot_timer += dt;
        if (d->boot_timer >= d->p.boot_time_s - 0.5 * dt) {
            d->state = LRT_DRIVE_SWITCH_ON_DISABLED;
        }
        break;
    case LRT_DRIVE_SWITCH_ON_DISABLED:
        if (shutdown) {
            d->state = LRT_DRIVE_READY_TO_SWITCH_ON;
        }
        break;
    case LRT_DRIVE_READY_TO_SWITCH_ON:
        if (disable_voltage || quick_stop) {
            leave_to_disabled(d);
        } else if (switch_on) {
            d->state = LRT_DRIVE_SWITCHED_ON;
        }
        break;
    case LRT_DRIVE_SWITCHED_ON:
        if (disable_voltage || quick_stop) {
            leave_to_disabled(d);
        } else if (shutdown) {
            d->state = LRT_DRIVE_READY_TO_SWITCH_ON;
        } else if (enable_op) {
            enter_operation(d, fb);
        }
        break;
    case LRT_DRIVE_OPERATION_ENABLED:
        if (disable_voltage) {
            leave_to_disabled(d);
        } else if (quick_stop) {
            d->state = LRT_DRIVE_QUICK_STOP_ACTIVE;
            d->ramp_active = 0;
            if (d->quick_stop_option == 2) {
                start_ramp(d);
            }
        } else if (shutdown) {
            d->state = LRT_DRIVE_READY_TO_SWITCH_ON;
            d->integ = 0.0;
        } else if (disable_op) {
            d->state = LRT_DRIVE_SWITCHED_ON;
            d->integ = 0.0;
        }
        break;
    case LRT_DRIVE_QUICK_STOP_ACTIVE:
        if (disable_voltage || !d->ramp_active) {
            leave_to_disabled(d);
        }
        break;
    case LRT_DRIVE_FAULT_REACTION_ACTIVE:
        if (!d->ramp_active) {
            d->state = LRT_DRIVE_FAULT;
        }
        break;
    case LRT_DRIVE_FAULT:
        if (reset_edge) {
            try_fault_reset(d);
        }
        break;
    default:
        break;
    }
}

/* ------------------------------------------------------------------------- */
/* Bazowanie w napedzie (tryb 6, REQ-VM-07 metoda e)                          */
/* ------------------------------------------------------------------------- */

/* Opis metody 6098h. Wlasna interpretacja numeracji z ogolnego opisu profilu (tekst normy
 * niedostepny) - NIEZWERYFIKOWANE wobec normy i prawdziwych napedow:
 *    1 /  2  krancowka ujemna / dodatnia, zjazd do zbocza, potem impuls indeksu
 *    3 /  5  czujnik bazowy, szukanie w kierunku dodatnim / ujemnym, zbocze, indeks
 *   17 / 18  jak 1 / 2 bez indeksu (baza na zboczu krancowki)
 *   19 / 21  jak 3 / 5 bez indeksu
 *   33 / 34  tylko impuls indeksu w kierunku ujemnym / dodatnim
 *   35 / 37  biezaca pozycja = baza (bez ruchu)
 *   -1 / -2  (producenta) twardy zderzak ujemny / dodatni: dojazd z predkoscia 6099h:2
 *            przy limicie 6072h, baza po nasyceniu momentu przez hardstop_time_s
 * Pozostale numery: blad bazowania (bit 13). */
typedef struct {
    unsigned trigger; /* LRT_DIN_* albo 0 */
    int dir;          /* kierunek szukania */
    int index;        /* po zboczu szukaj indeksu */
    int push;         /* twardy zderzak */
} homing_method_desc;

static int homing_describe(int method, homing_method_desc *h)
{
    static const struct {
        int method;
        homing_method_desc desc;
    } table[] = {
        {1, {LRT_DIN_NEG_LIMIT, -1, 1, 0}},  {2, {LRT_DIN_POS_LIMIT, 1, 1, 0}},
        {3, {LRT_DIN_HOME, 1, 1, 0}},        {5, {LRT_DIN_HOME, -1, 1, 0}},
        {17, {LRT_DIN_NEG_LIMIT, -1, 0, 0}}, {18, {LRT_DIN_POS_LIMIT, 1, 0, 0}},
        {19, {LRT_DIN_HOME, 1, 0, 0}},       {21, {LRT_DIN_HOME, -1, 0, 0}},
        {33, {0u, -1, 1, 0}},                {34, {0u, 1, 1, 0}},
        {-1, {0u, -1, 0, 1}},                {-2, {0u, 1, 0, 1}},
    };
    size_t i;

    for (i = 0; i < sizeof(table) / sizeof(table[0]); i++) {
        if (table[i].method == method) {
            *h = table[i].desc;
            return 1;
        }
    }
    return 0;
}

/* Ustala baze: pozycja `at` [ramka raportowana] staje sie 607Ch. Cala ramka (pomiar, cele,
 * pole krokowca) przesuwa sie razem, wiec ruch i regulator nie widza skoku. */
static void homing_set_home(lrt_drive *d, double at)
{
    int32_t delta = round_i32(at - (double)d->home_offset);

    d->pos_offset = sat_i32((double)d->pos_offset + (double)delta);
    d->pos_meas = sat_i32((double)d->pos_meas - (double)delta);
    d->prev_pos_meas = sat_i32((double)d->prev_pos_meas - (double)delta);
    d->pos_report = sat_i32((double)d->pos_report - (double)delta);
    d->target_counts = sat_i32((double)d->target_counts - (double)delta);
    d->prev_target = sat_i32((double)d->prev_target - (double)delta);
    d->hm_target -= (double)delta;
    d->hm_attained = 1;
    if (d->p.encoder == LRT_ENC_ABSOLUTE) {
        d->abs_valid = d->battery_ok;
    }
}

static void homing_start(lrt_drive *d)
{
    homing_method_desc h;
    int method = d->homing_method;

    homing_hold(d);
    d->hm_attained = 0;
    if (method == 35 || method == 37) {
        homing_set_home(d, actual_counts(d));
        d->hm_phase = LRT_HM_DONE;
        return;
    }
    if (!homing_describe(method, &h) || (h.push && d->p.type == LRT_DRIVE_STEPPER_OPEN)) {
        d->hm_phase = LRT_HM_ERROR; /* metoda nieobslugiwana (zderzak wymaga sprzezenia) */
        return;
    }
    d->hm_dir = h.dir;
    if (h.push) {
        d->hm_phase = LRT_HM_PUSH;
        d->hm_vel_goal = (double)h.dir * (double)d->homing_speed_zero;
    } else if (h.trigger == 0u) {
        d->hm_phase = LRT_HM_INDEX;
        d->hm_vel_goal = (double)h.dir * (double)d->homing_speed_zero;
    } else if ((d->inputs & h.trigger) != 0u) {
        d->hm_phase = LRT_HM_BACKOFF; /* juz na sygnale: od razu zjazd */
        d->hm_vel_goal = -(double)h.dir * (double)d->homing_speed_zero;
    } else {
        d->hm_phase = LRT_HM_SEARCH;
        d->hm_vel_goal = (double)h.dir * (double)d->homing_speed_switch;
    }
}

static void homing_stop(lrt_drive *d, int error)
{
    d->hm_phase = error ? LRT_HM_ERROR : LRT_HM_STOP;
    d->hm_vel_goal = 0.0;
}

/* Krok sekwencji bazowania; wywolywany po pomiarze, gdy naped pracuje w trybie 6. Wynik:
 * d->target_counts = pozycja zadana bazowania. */
static void homing_update(lrt_drive *d, double dt)
{
    uint16_t cw = d->controlword;
    int start = (cw & LRT_CW_HOMING_START) != 0u &&
                (d->prev_controlword & LRT_CW_HOMING_START) == 0u;
    int moving = d->hm_phase == LRT_HM_SEARCH || d->hm_phase == LRT_HM_BACKOFF ||
                 d->hm_phase == LRT_HM_INDEX || d->hm_phase == LRT_HM_PUSH;
    int index_edge = (d->inputs & LRT_DIN_INDEX) != 0u && (d->prev_inputs & LRT_DIN_INDEX) == 0u;
    homing_method_desc h = {0u, 0, 0, 0};
    double dv = (double)d->homing_accel * dt;
    double act = actual_counts(d);

    if (start) {
        homing_start(d);
        moving = d->hm_phase != LRT_HM_DONE && d->hm_phase != LRT_HM_ERROR;
    } else if (moving && ((cw & LRT_CW_HOMING_START) == 0u || (cw & LRT_CW_HALT) != 0u)) {
        homing_stop(d, 1); /* przerwane przez mastera: baza nieustalona */
        moving = 0;
    }
    if (moving) {
        (void)homing_describe(d->homing_method, &h);
    }
    switch (d->hm_phase) {
    case LRT_HM_SEARCH:
        if ((d->inputs & h.trigger) != 0u) {
            d->hm_phase = LRT_HM_BACKOFF;
            d->hm_vel_goal = -(double)d->hm_dir * (double)d->homing_speed_zero;
        } else if ((d->inputs & (d->hm_dir > 0 ? LRT_DIN_POS_LIMIT : LRT_DIN_NEG_LIMIT)) != 0u) {
            homing_stop(d, 1); /* krancowka przed czujnikiem: blad */
        }
        break;
    case LRT_HM_BACKOFF:
        /* Zbocze liczy sie dopiero po zawroceniu (predkosc w kierunku zjazdu). */
        if ((d->inputs & h.trigger) == 0u && d->hm_vel * (double)d->hm_dir < 0.0) {
            if (h.index) {
                d->hm_phase = LRT_HM_INDEX;
            } else {
                homing_set_home(d, act);
                act = actual_counts(d);
                homing_stop(d, 0);
            }
        }
        break;
    case LRT_HM_INDEX:
        if (index_edge) {
            homing_set_home(d, act);
            act = actual_counts(d);
            homing_stop(d, 0);
        }
        break;
    case LRT_HM_PUSH:
        d->hm_push_timer = d->torque_limited ? d->hm_push_timer + dt : 0.0;
        if (d->hm_push_timer >= d->p.hardstop_time_s) {
            homing_set_home(d, act);
            act = actual_counts(d);
            /* Zderzak: zatrzymanie od razu w miejscu styku, bez dalszego docisku. */
            d->hm_target = act;
            d->hm_vel = 0.0;
            homing_stop(d, 0);
        }
        break;
    default:
        break;
    }

    if (d->hm_vel < d->hm_vel_goal) {
        d->hm_vel = d->hm_vel + dv < d->hm_vel_goal ? d->hm_vel + dv : d->hm_vel_goal;
    } else if (d->hm_vel > d->hm_vel_goal) {
        d->hm_vel = d->hm_vel - dv > d->hm_vel_goal ? d->hm_vel - dv : d->hm_vel_goal;
    }
    d->hm_target += d->hm_vel * dt;
    if (d->hm_phase == LRT_HM_PUSH && d->following_window != 0xFFFFFFFFu) {
        /* Przy zderzaku cel nie ucieka dalej niz pol okna nadazania od pozycji. */
        double lead = 0.5 * (double)d->following_window;
        d->hm_target = clampd(d->hm_target, act - lead, act + lead);
    }
    if (d->hm_phase == LRT_HM_STOP && d->hm_vel == 0.0) {
        d->hm_phase = LRT_HM_DONE;
    }
    d->target_counts = round_i32(d->hm_target);
}

/* ------------------------------------------------------------------------- */
/* Krok                                                                       */
/* ------------------------------------------------------------------------- */

static double compute_torque(lrt_drive *d, const lrt_drive_feedback *fb, double dt)
{
    double tau = 0.0;

    d->torque_limited = 0;
    switch (d->state) {
    case LRT_DRIVE_OPERATION_ENABLED:
        tau = d->p.type == LRT_DRIVE_STEPPER_OPEN ? ctrl_stepper_open(d, fb, dt)
                                                  : ctrl_csp(d, fb, dt);
        break;
    case LRT_DRIVE_QUICK_STOP_ACTIVE:
    case LRT_DRIVE_FAULT_REACTION_ACTIVE:
        if (d->ramp_active) {
            tau = ctrl_ramp(d, fb, dt);
        }
        break;
    default:
        d->integ = 0.0;
        break;
    }
    if (!state_produces_torque(d)) {
        d->field_omega = 0.0; /* pole nie wiruje, gdy naped nie daje momentu */
    }
    return tau;
}

static void update_overload(lrt_drive *d, double tau, double dt)
{
    if (d->i2t_limit <= 0.0) {
        return;
    }
    d->i2t_acc += (tau * tau - d->p.rated_torque * d->p.rated_torque) * dt;
    if (d->i2t_acc < 0.0) {
        d->i2t_acc = 0.0;
    }
    if (d->i2t_acc > WARN_FRACTION * d->i2t_limit) {
        d->warnings |= LRT_DRIVE_WARN_OVERLOAD;
    } else {
        d->warnings &= ~(unsigned)LRT_DRIVE_WARN_OVERLOAD;
    }
}

static void update_reports(lrt_drive *d, double tau)
{
    d->torque_cmd = tau;
    d->torque_report = sat_i16(floor(tau / d->p.rated_torque * 1000.0 + 0.5));
    if (d->p.type == LRT_DRIVE_STEPPER_OPEN) {
        d->vel_report = round_i32(d->field_omega * d->counts_per_rad);
    } else {
        d->pos_report = d->pos_meas;
        d->vel_report = round_i32(d->vel_meas * d->counts_per_rad);
    }
}

int lrt_drive_step(lrt_drive *d, const lrt_drive_feedback *fb, double dt, double *torque_cmd)
{
    lrt_drive saved;
    double tau;

    if (d == NULL || fb == NULL || torque_cmd == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    if (!isfinite(dt) || dt <= 0.0 || dt > LRT_DRIVE_MAX_DT) {
        return LRT_DRIVE_ERR_DT;
    }
    if (!isfinite(fb->theta_m) || !isfinite(fb->omega_m) || !isfinite(fb->torque_avail) ||
        !isfinite(fb->j_total) || fb->torque_avail < 0.0 || fb->j_total <= 0.0) {
        return LRT_DRIVE_ERR_NUMERIC;
    }
    saved = *d;

    update_measurement(d, fb, dt);
    if (d->state == LRT_DRIVE_OPERATION_ENABLED && d->mode_of_operation == LRT_MODE_HOMING) {
        homing_update(d, dt);
    }
    if (!detect_faults(d, dt)) {
        run_state_machine(d, fb, dt);
    }
    tau = compute_torque(d, fb, dt);
    if (!isfinite(tau)) {
        *d = saved;
        return LRT_DRIVE_ERR_NUMERIC;
    }
    update_overload(d, tau, dt);
    update_reports(d, tau);
    d->prev_controlword = d->controlword;
    d->prev_inputs = d->inputs;
    d->time += dt;
    *torque_cmd = tau;
    return LRT_DRIVE_OK;
}

/* ---------- parametry zmieniane w locie (REQ-VD-04) ---------- */

int lrt_drive_get_live(const lrt_drive *d, int param, double *value)
{
    if (d == NULL || value == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    switch (param) {
    case LRT_LIVE_TORQUE_LIMIT:
        *value = (double)d->torque_limit_permille;
        return LRT_DRIVE_OK;
    case LRT_LIVE_INERTIA_EST:
        *value = d->p.inertia_est;
        return LRT_DRIVE_OK;
    default:
        return LRT_DRIVE_ERR_LIVE;
    }
}

int lrt_drive_set_live(lrt_drive *d, int param, double value, lrt_live_log *log)
{
    double old_value;

    if (d == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    if (!isfinite(value) || lrt_drive_get_live(d, param, &old_value) != LRT_DRIVE_OK) {
        return LRT_DRIVE_ERR_LIVE;
    }
    if (param == LRT_LIVE_TORQUE_LIMIT) {
        if (value < 0.0 || value > (double)max_torque_permille(&d->p) ||
            value != floor(value)) {
            return LRT_DRIVE_ERR_LIVE;
        }
        d->torque_limit_permille = (uint16_t)value;
    } else {
        if (value < 0.0 || value > 1.0e3) {
            return LRT_DRIVE_ERR_LIVE;
        }
        d->p.inertia_est = value;
    }
    lrt_live_log_append(log, d->time, param, old_value, value);
    return LRT_DRIVE_OK;
}

/* ---------- przetwornik i bazowanie (sesja 015, REQ-VM-07) ---------- */

void lrt_drive_set_inputs(lrt_drive *d, unsigned inputs)
{
    if (d != NULL) {
        d->inputs = inputs;
    }
}

int32_t lrt_drive_position_offset(const lrt_drive *d)
{
    return d != NULL ? d->pos_offset : 0;
}

int lrt_drive_set_absolute(lrt_drive *d, int32_t offset, int valid)
{
    if (d == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    if (d->p.encoder != LRT_ENC_ABSOLUTE || d->have_meas) {
        return LRT_DRIVE_ERR_UNSUPPORTED;
    }
    d->pos_offset = offset;
    d->abs_restored = 1;
    d->abs_restore_valid = valid != 0;
    return LRT_DRIVE_OK;
}

int lrt_drive_get_absolute(const lrt_drive *d, int32_t *offset, int *valid)
{
    if (d == NULL || offset == NULL || valid == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    if (d->p.encoder != LRT_ENC_ABSOLUTE) {
        return LRT_DRIVE_ERR_UNSUPPORTED;
    }
    *offset = d->pos_offset;
    *valid = d->abs_valid && d->battery_ok;
    return LRT_DRIVE_OK;
}

int lrt_drive_set_battery(lrt_drive *d, int ok)
{
    if (d == NULL) {
        return LRT_DRIVE_ERR_NULL;
    }
    if (d->p.encoder != LRT_ENC_ABSOLUTE) {
        return LRT_DRIVE_ERR_UNSUPPORTED;
    }
    d->battery_ok = ok != 0;
    return LRT_DRIVE_OK;
}

int lrt_drive_homing_state(const lrt_drive *d)
{
    return d != NULL ? d->hm_phase : LRT_HM_IDLE;
}
