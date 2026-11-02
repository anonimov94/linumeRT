/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - Plant: parametry zmieniane w locie i dziennik zmian (REQ-VD-04).
 * Model-Author: Claude · sesja 013
 *
 * Wspolny dla osi (axis.h: masa, J, tarcie, luz, napiecie) i napedu (drive.h: limit momentu,
 * estymata J regulatora). Dziennik to bufor kolowy o stalym rozmiarze: zapis bez alokacji
 * i bez I/O, mozna go wolac z petli czasu rzeczywistego (CLAUDE.md §5).
 */
#ifndef LRT_PLANT_LIVE_H
#define LRT_PLANT_LIVE_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    /* os: lrt_axis_set_live() */
    LRT_LIVE_LOAD = 0,           /* masa [kg] albo moment bezwladnosci [kg*m^2], >= 0 */
    LRT_LIVE_J_MOTOR,            /* wirnik [kg*m^2], >= 0 */
    LRT_LIVE_J_SCREW,            /* sruba/sprzeglo [kg*m^2], >= 0 */
    LRT_LIVE_FRICTION_COULOMB,   /* [N*m], 0 <= wartosc <= friction_static */
    LRT_LIVE_FRICTION_STATIC,    /* [N*m], >= friction_coulomb */
    LRT_LIVE_FRICTION_VISCOUS,   /* [N*m*s/rad], >= 0 */
    LRT_LIVE_BACKLASH,           /* luz [m] albo [rad]; nie zmienia trybu sztywny/dwuczlonowy */
    LRT_LIVE_SUPPLY_SCALE,       /* napiecie zasilania / znamionowe, 0.05..2 */
    /* naped: lrt_drive_set_live() */
    LRT_LIVE_TORQUE_LIMIT,       /* 6072h [promile znamionowego], 0..max z momentu szczytowego */
    LRT_LIVE_INERTIA_EST,        /* estymata J dla FF przyspieszenia [kg*m^2], 0..1e3 */
    LRT_LIVE_COUNT
} lrt_live_param;

#define LRT_LIVE_LOG_SIZE 64

/* Wpis dziennika zmian: czas modelu, parametr, wartosc przed i po. */
typedef struct {
    double t;
    int param;
    double old_value;
    double new_value;
} lrt_live_entry;

/* Dziennik zmian: bufor kolowy o stalym rozmiarze (bez alokacji); najstarsze wpisy
 * sa nadpisywane, licznik `total` liczy wszystkie zapisane zmiany. */
typedef struct {
    lrt_live_entry entries[LRT_LIVE_LOG_SIZE];
    unsigned total;
} lrt_live_log;

const char *lrt_live_param_name(int param); /* np. "load"; NULL dla nieznanego */

void lrt_live_log_init(lrt_live_log *log);
/* Dopisuje wpis (log == NULL: nic nie robi). Uzywane przez lrt_axis/lrt_drive_set_live(). */
void lrt_live_log_append(lrt_live_log *log, double t, int param, double old_value,
                         double new_value);
unsigned lrt_live_log_size(const lrt_live_log *log);    /* liczba dostepnych wpisow */
unsigned lrt_live_log_dropped(const lrt_live_log *log); /* nadpisane (utracone) wpisy */
/* Wpis o numerze i (0 = najstarszy dostepny). Zwraca 0 albo -1, gdy i poza zakresem. */
int lrt_live_log_get(const lrt_live_log *log, unsigned i, lrt_live_entry *out);

#ifdef __cplusplus
}
#endif

#endif /* LRT_PLANT_LIVE_H */
