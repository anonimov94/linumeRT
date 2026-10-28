/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - Plant, rdzen dynamiki osi (C11, bez zaleznosci poza libc/libm).
 * Model-Author: Claude
 *
 * Model mechaniki jednej osi (liniowej albo obrotowej) sterowanej momentem
 * silnika. Wszystkie wielkosci w SI: m, rad, kg, kg*m^2, N, N*m, s.
 *
 * Uklady wspolrzednych:
 *  - wal silnika: theta_m [rad], omega_m [rad/s], moment silnika [N*m];
 *  - obciazenie: pozycja i predkosc w jednostkach osi (m albo rad);
 *    ratio = przemieszczenie obciazenia na 1 rad walu silnika
 *    (sruba: skok/(2*pi) w m/rad; oś obrotowa: 1/przelozenie w rad/rad).
 *
 * Zasady (CLAUDE.md §5): po lrt_axis_init() zadnych alokacji, zadnego I/O,
 * czas wykonania lrt_axis_step() ograniczony (liczba podkrokow <= LRT_AXIS_MAX_SUBSTEPS).
 * NIEZWERYFIKOWANE NA SPRZECIE: model fizyczny sprawdzony tylko wzorami analitycznymi.
 */
#ifndef LRT_PLANT_AXIS_H
#define LRT_PLANT_AXIS_H

#include "live.h"

#ifdef __cplusplus
extern "C" {
#endif

#define LRT_AXIS_CURVE_MAX 16
#define LRT_AXIS_MAX_SUBSTEPS 2000
/* Domyslna sztywnosc kontaktu przy luzie, gdy stiffness == 0 [N*m/rad na wale silnika]. */
#define LRT_AXIS_DEFAULT_CONTACT_STIFFNESS 1000.0

typedef enum {
    LRT_AXIS_LINEAR = 0, /* load w kg, ratio w m/rad */
    LRT_AXIS_ROTARY = 1  /* load w kg*m^2, ratio w rad/rad */
} lrt_axis_kind;

/* Kody bledow (ujemne) zwracane przez lrt_axis_init() i lrt_axis_step(). */
typedef enum {
    LRT_AXIS_OK = 0,
    LRT_AXIS_ERR_NULL = -1,
    LRT_AXIS_ERR_INERTIA = -2,   /* j_motor/j_screw/load: ujemne lub suma <= 0 */
    LRT_AXIS_ERR_RATIO = -3,     /* ratio <= 0 */
    LRT_AXIS_ERR_CURVE = -4,     /* krzywa: <2 punkty, omega nie rosnaca, moment < 0 */
    LRT_AXIS_ERR_FRICTION = -5,  /* tarcie ujemne albo static < coulomb */
    LRT_AXIS_ERR_BACKLASH = -6,  /* luz ujemny albo (luz > 0 i load <= 0) */
    LRT_AXIS_ERR_STIFFNESS = -7, /* sztywnosc/tlumienie ujemne */
    LRT_AXIS_ERR_STOPS = -8,     /* stop_min >= stop_max */
    LRT_AXIS_ERR_DT = -9,        /* dt <= 0 albo nieskonczone */
    LRT_AXIS_ERR_NUMERIC = -10,  /* NaN/inf w stanie lub momencie zadanym */
    LRT_AXIS_ERR_LIVE_ID = -11,  /* nieznany parametr zmieniany w locie albo wartosc poza zakresem */
    LRT_AXIS_ERR_LIVE_MODE = -12 /* zmiana wlaczylaby/wylaczyla model luzu - wymaga przeladowania */
} lrt_axis_status;

/* Flagi zdarzen (zatrzaskiwane do lrt_axis_clear_events()). */
enum {
    LRT_AXIS_EV_HARDSTOP_MIN = 1 << 0,   /* uderzenie w zderzak dolny */
    LRT_AXIS_EV_HARDSTOP_MAX = 1 << 1,   /* uderzenie w zderzak gorny */
    LRT_AXIS_EV_TORQUE_LIMITED = 1 << 2, /* moment zadany obciety krzywa */
    LRT_AXIS_EV_SUBSTEPS_CAPPED = 1 << 3 /* dt wymagal wiecej niz LRT_AXIS_MAX_SUBSTEPS */
};

typedef struct {
    double omega; /* predkosc walu silnika [rad/s], >= 0, rosnaco */
    double torque; /* maksymalny moment przy tej predkosci [N*m], >= 0 */
} lrt_curve_point;

typedef struct {
    lrt_axis_kind kind;

    /* Bezwladnosci */
    double j_motor; /* wirnik [kg*m^2] */
    double j_screw; /* sruba/sprzeglo/przekladnia po stronie silnika [kg*m^2] */
    double load;    /* masa [kg] (LINEAR) albo moment bezwladnosci [kg*m^2] (ROTARY) */
    double ratio;   /* jednostki osi na rad walu silnika (> 0) */

    /* Krzywa moment-predkosc: liniowa interpolacja, symetryczna wzgledem znaku
     * predkosci; powyzej ostatniego punktu moment dostepny = 0. */
    lrt_curve_point curve[LRT_AXIS_CURVE_MAX];
    int n_curve;

    /* Tarcie sprowadzone do walu silnika, dziala na obciazenie.
     * friction_static >= friction_coulomb (moment odrywania). */
    double friction_coulomb; /* [N*m] */
    double friction_static;  /* [N*m] */
    double friction_viscous; /* [N*m*s/rad] */

    /* Stala sila zewnetrzna na obciazenie (znak: + w strone rosnacej pozycji),
     * np. grawitacja osi Z = -masa*9.81 [N]; dla ROTARY [N*m]. */
    double gravity_force;

    /* Luz (calkowita szerokosc, w jednostkach osi) i sztywnosc/tlumienie polaczenia.
     * Tryb dwuczlonowy wlacza sie, gdy backlash > 0 albo stiffness > 0.
     * stiffness == 0 przy luzie > 0 => LRT_AXIS_DEFAULT_CONTACT_STIFFNESS. */
    double backlash;       /* [m] albo [rad] */
    double stiffness;      /* [N*m/rad na wale silnika] */
    double damping_ratio;  /* wzgledny wspolczynnik tlumienia kontaktu (0 = brak) */

    /* Twarde zderzaki w jednostkach osi. stop_stiffness == 0 => zderzak sztywny
     * (zderzenie niesprezyste: predkosc do zderzaka zerowana, pozycja obcinana). */
    int use_stops;
    double stop_min;
    double stop_max;
    double stop_stiffness;     /* [N/m] albo [N*m/rad] na obciazeniu */
    double stop_damping_ratio; /* 0 = brak tlumienia */
} lrt_axis_params;

typedef struct {
    lrt_axis_params p;

    /* Wielkosci pochodne (liczone w lrt_axis_init) */
    double j_m;           /* j_motor + j_screw */
    double j_l;           /* load * ratio^2 (sprowadzone do walu) */
    double j_tot;         /* j_m + j_l */
    int two_body;         /* 1 = luz/podatnosc modelowane */
    double gap_half;      /* polowa luzu na wale silnika [rad] */
    double k_contact;     /* [N*m/rad] */
    double c_contact;     /* [N*m*s/rad] */
    double k_stop;        /* sztywnosc zderzaka przeliczona na wal [N*m/rad] */
    double c_stop;        /* tlumienie zderzaka na wale [N*m*s/rad] */
    double dt_sub_max;    /* najwiekszy stabilny podkrok [s] */

    /* Stan */
    double th_m, w_m;     /* wal silnika */
    double th_l, w_l;     /* obciazenie (w radianach walu; w trybie sztywnym = silnik) */
    double pos, vel;      /* obciazenie w jednostkach osi (th_l*ratio, w_l*ratio) */

    /* Wyniki ostatniego lrt_axis_step() */
    double torque_applied; /* moment silnika po obcieciu krzywa [N*m] */
    double contact_torque; /* moment przenoszony przez luz/sztywnosc [N*m] */
    int sticking;          /* 1 = obciazenie stoi w tarciu statycznym */
    int stop_contact;      /* -1/0/+1: kontakt ze zderzakiem dolnym/brak/gornym (wewnetrzne) */
    unsigned events;       /* LRT_AXIS_EV_* (zatrzask) */
    double impact_speed;   /* najwieksza predkosc uderzenia w zderzak od ostatniego clear [jedn./s] */

    /* Czas modelu i parametry zmieniane w locie (REQ-VD-04) */
    double time;           /* czas od lrt_axis_init() [s]; rosnie tylko po udanym kroku */
    double supply_scale;   /* napiecie zasilania wzgledem znamionowego (mnoznik krzywej momentu) */
} lrt_axis;

/* Parametry zmieniane w trakcie pracy (REQ-VD-04): lrt_live_param i dziennik w live.h.
 * Os obsluguje LRT_LIVE_LOAD..LRT_LIVE_SUPPLY_SCALE; limit momentu i estymata J regulatora
 * zmieniaja sie przez lrt_drive_set_live(). */

/* Wypelnia parametry wartosciami domyslnymi (liniowa os 5 mm/obr, plaska krzywa 1 N*m
 * do 300 rad/s, brak tarcia, luzu, grawitacji i zderzakow; damping_ratio = 0.7). */
void lrt_axis_params_default(lrt_axis_params *p);

/* Wygodny ustawiacz plaskiej krzywej: moment tau do omega_max. */
void lrt_axis_set_flat_curve(lrt_axis_params *p, double tau, double omega_max);

/* Sprawdza parametry; zwraca LRT_AXIS_OK albo kod bledu (nic nie modyfikuje). */
int lrt_axis_params_check(const lrt_axis_params *p);

/* Komunikat po polsku dla kodu statusu. */
const char *lrt_axis_strerror(int status);

/* Inicjalizacja (kopiuje parametry, liczy wielkosci pochodne, zeruje stan w pos=0). */
int lrt_axis_init(lrt_axis *a, const lrt_axis_params *p);

/* Ustawia pozycje obciazenia i zeruje predkosci; luz wyrownany na srodek szczeliny. */
void lrt_axis_reset(lrt_axis *a, double pos);

/* Dostepny moment silnika przy predkosci omega (wartosc bezwzgledna) z krzywej. */
double lrt_axis_torque_limit(const lrt_axis *a, double omega);

/* Bezwladnosc zastepcza na wale silnika (j_motor + j_screw + load*ratio^2). */
double lrt_axis_j_total(const lrt_axis *a);

/* Jeden krok czasu dt [s] z podkrokami; torque_cmd w N*m na wale silnika.
 * Zwraca LRT_AXIS_OK albo kod bledu (stan nie jest zmieniany przy bledzie). */
int lrt_axis_step(lrt_axis *a, double torque_cmd, double dt);

/* Zmiana parametru w locie (REQ-VD-04). Stan dynamiki (polozenie, predkosc) jest zachowany,
 * wielkosci pochodne sa liczone od nowa. `log` moze byc NULL. Przy bledzie nic nie zmienia
 * i nie dopisuje do dziennika. Zwraca LRT_AXIS_OK, LRT_AXIS_ERR_LIVE_ID (nieznany parametr,
 * NaN/inf, wartosc poza zakresem), LRT_AXIS_ERR_LIVE_MODE (luz: zmiana z/na zero w modelu
 * sztywnym - ustaw stiffness > 0, zeby model dwuczlonowy byl aktywny od poczatku) albo
 * kod walidacji parametrow osi (np. LRT_AXIS_ERR_FRICTION). */
int lrt_axis_set_live(lrt_axis *a, int param, double value, lrt_live_log *log);
int lrt_axis_get_live(const lrt_axis *a, int param, double *value);


/* Zdarzenia: odczyt i zerowanie flag oraz impact_speed. */
unsigned lrt_axis_events(const lrt_axis *a);
void lrt_axis_clear_events(lrt_axis *a);

#ifdef __cplusplus
}
#endif

#endif /* LRT_PLANT_AXIS_H */
