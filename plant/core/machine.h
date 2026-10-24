/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - Plant: wirtualna obrabiarka zlozona z osi i napedow (C11, bez zaleznosci).
 * Model-Author: Claude · sesja 014
 *
 * Maszyna = napedy (lrt_drive + lrt_axis na kazdy silnik), osie maszyny (1 albo 2 napedy;
 * 2 = gantry z alarmem rozjazdu), lancuch kinematyczny (kinematyka prosta pozycji narzedzia),
 * twarde zderzaki, krancowki i czujniki bazowe, impuls indeksu silnika, petla E-STOP, sonda
 * i mapa wejsc/wyjsc cyfrowych (32 bity jak `digital_in`/`digital_out` w LRT-NET v1).
 * REQ-VM-02 ... REQ-VM-05.
 *
 * Konfiguracja: lrt_machine_cfg wypelniany kluczami "nazwa wartosc" (lrt_machine_cfg_set),
 * zeby warstwa Pythona (linumert_plant.build_machine, ctypes) nie musiala odwzorowywac
 * ukladu struktur C. Klucze (N, J, L, S = indeksy od 0):
 *   drive.N.type                        0 serwo CSP, 1 krokowiec, 2 serwo krokowe
 *   drive.N.<pole lrt_drive_params>     np. drive.0.kp_pos, drive.0.counts_per_rev
 *   drive.N.index_input / index_width   wejscie impulsu indeksu (-1 = brak), szerokosc [rad]
 *   mech.N.<pole lrt_axis_params>       mechanika silnika N: kind, j_motor, load, ratio, ...
 *                                       (zderzaki ustawia maszyna z joint.J.stop_*)
 *   joint.J.kind / drive0 / drive1      0 liniowa [m], 1 obrotowa [rad]; drive1 = -1: jeden naped
 *   joint.J.max_skew                    dopuszczalny rozjazd gantry [m] (> 0 przy 2 napedach)
 *   joint.J.stop_min / stop_max         polozenie zderzakow [m|rad]; use_stops = 1 wlacza
 *   joint.J.use_stops / stop_k / stop_c sztywnosc [N/m|N*m/rad] i tlumienie [N*s/m|N*m*s/rad]
 *   joint.J.stop_fault                  1 = wjazd w zderzak daje awarie napedu HW_LIMIT
 *   joint.J.initial                     polozenie startowe [m|rad]
 *   joint.J.initial_random / initial_min / initial_max
 *                                       1 = start losowy w [min, max] z ziarna machine.seed
 *   drive.N.din_neg_limit / din_pos_limit / din_home
 *                                       styk switch.S na wejsciu napedu (tryb 6), -1 = brak
 *   drive.N.encoder / home_offset / hardstop_time_s   patrz lrt_drive_params (sesja 015)
 *   link.L.kind / joint / parent        czlon: 0 liniowy, 1 obrotowy; os maszyny (-1 = staly);
 *                                       rodzic (-1 = rama maszyny, musi miec mniejszy indeks)
 *   link.L.ax ay az / ox oy oz          wektor osi i przesuniecie wzgledem rodzica [m]
 *   link.L.branch                       0 = galaz narzedzia, 1 = galaz detalu (stol)
 *   switch.S.joint / role / side        os, 0 krancowka / 1 czujnik bazowy, -1 aktywny ponizej
 *                                       polozenia, +1 powyzej
 *   switch.S.position / hysteresis      [m|rad]
 *   switch.S.nc / input / bounce        1 = styk NC; bit wejscia 0..31 (-1 = tylko naped);
 *                                       czas drgan styku [s]
 *   switch.S.drive                      -1 = polozenie osi, N = polozenie napedu N tej osi
 *                                       (osobne czujniki stron gantry)
 *   estop.input / estop.nc / estop.action    action: 0 = STO (awaria STO), 1 = quick stop
 *   probe.type                          0 brak, 1 prostopadloscian (przygotowka), 2 plytka
 *   probe.input / probe.nc / probe.tip_length
 *   probe.min_x ... probe.max_z         [m] w ukladzie detalu; plytka: kontakt, gdy z <= max_z
 *   spindle.drive                       naped wrzeciona (-1 = brak)
 *   machine.seed                        ziarno drgan stykow (0 = stala domyslna)
 * Krzywa momentu silnika N: lrt_machine_cfg_curve().
 *
 * Wejscia: bit = 1, gdy obwod wejscia jest zamkniety. Kilka stykow NC na jednym wejsciu to
 * lancuch szeregowy (zamkniety, gdy wszystkie zamkniete), kilka NO - rownolegly (zamkniety,
 * gdy ktorykolwiek zamkniety). Mieszanie NC i NO na jednym wejsciu jest bledem konfiguracji.
 *
 * Zasady (CLAUDE.md §5): po lrt_machine_init() zadnych alokacji ani I/O; lrt_machine_step()
 * ma ograniczony czas wykonania. NIEZWERYFIKOWANE NA SPRZECIE.
 */
#ifndef LRT_PLANT_MACHINE_H
#define LRT_PLANT_MACHINE_H

#include <stdint.h>

#include "axis.h"
#include "drive.h"
#include "live.h"

#ifdef __cplusplus
extern "C" {
#endif

#define LRT_MACHINE_MAX_JOINTS 6
#define LRT_MACHINE_MAX_DRIVES 13 /* 6 osi x 2 napedy + wrzeciono */
#define LRT_MACHINE_MAX_SUBSTEPS 100
#define LRT_MACHINE_MAX_LINKS 12
#define LRT_MACHINE_MAX_SWITCHES 24
#define LRT_MACHINE_MAX_IO 32

typedef enum {
    LRT_MACHINE_OK = 0,
    LRT_MACHINE_ERR_NULL = -1,
    LRT_MACHINE_ERR_KEY = -2,     /* nieznany klucz konfiguracji */
    LRT_MACHINE_ERR_INDEX = -3,   /* indeks w kluczu poza zakresem */
    LRT_MACHINE_ERR_VALUE = -4,   /* NaN/inf albo wartosc niedozwolona dla klucza */
    LRT_MACHINE_ERR_DRIVE = -5,   /* parametry napedu niepoprawne (err_detail = kod lrt_drive) */
    LRT_MACHINE_ERR_MECH = -6,    /* mechanika niepoprawna (err_detail = kod lrt_axis) */
    LRT_MACHINE_ERR_JOINT = -7,   /* os maszyny: brak napedu, naped uzyty dwa razy, rodzaj itp. */
    LRT_MACHINE_ERR_LINK = -8,    /* lancuch: kolejnosc rodzicow, wektor zerowy, galaz, os */
    LRT_MACHINE_ERR_SWITCH = -9,  /* krancowka/czujnik: os, strona, histereza, czas drgan */
    LRT_MACHINE_ERR_IO = -10,     /* bit wejscia poza 0..31 albo NC i NO na jednym wejsciu */
    LRT_MACHINE_ERR_PROBE = -11,  /* sonda: typ, wymiary, wejscie */
    LRT_MACHINE_ERR_DT = -12,     /* dt <= 0, za duze albo nieskonczone */
    LRT_MACHINE_ERR_STEP = -13    /* blad kroku osi albo napedu (err_detail = kod) */
} lrt_machine_status;

/* Zdarzenia maszyny (zatrzaskiwane do lrt_machine_clear_events()). Nazwy jak w docs/PLANT.md. */
enum {
    LRT_MACHINE_EV_CRASH_HARDSTOP = 1u << 0, /* wjazd w twardy zderzak */
    LRT_MACHINE_EV_LIMIT_TRIP = 1u << 1,     /* zadzialanie krancowki */
    LRT_MACHINE_EV_GANTRY_SKEW = 1u << 2,    /* rozjazd napedow gantry ponad max_skew */
    LRT_MACHINE_EV_ESTOP = 1u << 3,          /* petla E-STOP otwarta */
    LRT_MACHINE_EV_PROBE = 1u << 4,          /* kontakt sondy */
    LRT_MACHINE_EV_DRIVE_FAULT = 1u << 5,    /* ktorys naped przeszedl w FAULT */
    LRT_MACHINE_EV_HOME_SENSOR = 1u << 6     /* zadzialanie czujnika bazowego */
};

typedef enum { LRT_ESTOP_STO = 0, LRT_ESTOP_QUICK_STOP = 1 } lrt_estop_action;
typedef enum { LRT_PROBE_NONE = 0, LRT_PROBE_BOX = 1, LRT_PROBE_PLATE = 2 } lrt_probe_type;
typedef enum { LRT_BRANCH_TOOL = 0, LRT_BRANCH_WORKPIECE = 1 } lrt_link_branch;
typedef enum { LRT_SWITCH_LIMIT = 0, LRT_SWITCH_HOME = 1 } lrt_switch_role;

typedef struct {
    int used;
    int curve_set;
    lrt_drive_params drive;
    lrt_axis_params mech;
    int index_input;    /* -1 = brak */
    double index_width; /* [rad] szerokosc impulsu indeksu na obrot silnika */
    /* Styki podlaczone do wejsc napedu (bazowanie w napedzie, tryb 6): indeks krancowki albo
     * czujnika (switch.S), -1 = brak. */
    int din_neg_limit, din_pos_limit, din_home;
} lrt_machine_drive_cfg;

typedef struct {
    int used;
    int kind;     /* LRT_AXIS_LINEAR / LRT_AXIS_ROTARY */
    int drive[2]; /* drive[1] = -1: os z jednym napedem */
    double max_skew;
    int use_stops;
    double stop_min, stop_max;
    double stop_k, stop_c;
    int stop_fault;
    double initial;
    /* Pozycja startowa losowa (ziarno machine.seed) w [initial_min, initial_max] (REQ-VM-07). */
    int initial_random;
    double initial_min, initial_max;
} lrt_machine_joint_cfg;

typedef struct {
    int used;
    int kind;   /* LRT_AXIS_LINEAR / LRT_AXIS_ROTARY */
    int joint;  /* -1 = czlon staly */
    int parent; /* -1 = rama maszyny */
    int branch; /* lrt_link_branch */
    double axis[3];
    double offset[3];
} lrt_machine_link_cfg;

typedef struct {
    int used;
    int joint;
    int role; /* lrt_switch_role */
    int side; /* -1 / +1 */
    double position;
    double hysteresis;
    int nc;
    int input;     /* bit wejscia mastera; -1 = styk tylko na wejsciu napedu */
    double bounce; /* [s] */
    int drive;     /* -1: polozenie osi; >= 0: polozenie jednego napedu (gantry, sesja 015) */
} lrt_machine_switch_cfg;

typedef struct {
    int n_drives, n_joints, n_links, n_switches; /* najwyzszy uzyty indeks + 1 */
    lrt_machine_drive_cfg drives[LRT_MACHINE_MAX_DRIVES];
    lrt_machine_joint_cfg joints[LRT_MACHINE_MAX_JOINTS];
    lrt_machine_link_cfg links[LRT_MACHINE_MAX_LINKS];
    lrt_machine_switch_cfg switches[LRT_MACHINE_MAX_SWITCHES];
    int estop_input; /* -1 = brak (tylko testy; generator konfiguracji wymaga E-STOP) */
    int estop_nc;
    int estop_action;
    int probe_type;
    int probe_input;
    int probe_nc;
    double probe_tip_length;
    double probe_min[3], probe_max[3];
    int spindle_drive;
    uint32_t seed;
} lrt_machine_cfg;

typedef struct {
    lrt_drive drive;
    lrt_axis axis;
    uint16_t controlword;
    int32_t target;
    int32_t applied;      /* cel 607Ah przekazany napedowi w ostatnim kroku (ramka napedu) */
    int32_t cycle_from;   /* applied na poczatku cyklu mastera (interpolacja podkrokow) */
    int32_t cycle_offset; /* przesuniecie ramki napedu na poczatku cyklu */
    int cycle_interp;     /* 1 = cel interpolowany w tym cyklu (CSP, praca) */
    int was_fault;
    int in_stop;       /* kontakt ze zderzakiem w poprzednim kroku */
    long rev;          /* numer obrotu silnika (floor(theta/2pi)) */
    int index_pulse;   /* impuls indeksu w ostatnim kroku */
    long index_count;
    double index_latch; /* polozenie osi napedu przy ostatnim impulsie [m|rad] */
} lrt_machine_slot;

typedef struct {
    int tripped;       /* stan logiczny (po histerezie) */
    int closed;        /* stan styku po drganiach */
    double bounce_left;
} lrt_machine_switch_state;

typedef struct {
    lrt_machine_cfg c;
    lrt_machine_slot slots[LRT_MACHINE_MAX_DRIVES];
    lrt_machine_switch_state sw[LRT_MACHINE_MAX_SWITCHES];

    double joint_pos[LRT_MACHINE_MAX_JOINTS];
    double joint_vel[LRT_MACHINE_MAX_JOINTS];
    double skew[LRT_MACHINE_MAX_JOINTS];   /* drive0 - drive1 [m|rad] */
    unsigned joint_events[LRT_MACHINE_MAX_JOINTS];
    double impact_speed[LRT_MACHINE_MAX_JOINTS];
    int skew_exceeded[LRT_MACHINE_MAX_JOINTS];

    double tool_machine[3];   /* koniec narzedzia w ukladzie maszyny [m] */
    double tool_workpiece[3]; /* koniec narzedzia w ukladzie detalu [m] */
    double tool_length;       /* [m] od nosa wrzeciona */

    uint32_t inputs;
    uint32_t outputs;
    int estop_pressed;
    int probe_contact;
    unsigned events;
    double time;
    uint32_t rng;
    lrt_live_log log;
    int ip_k, ip_n; /* podkrok k z n w lrt_machine_step_cycle (ip_n = 0: bez interpolacji) */

    int err_index;  /* element, ktorego dotyczy ostatni blad init/step (-1 = brak) */
    int err_detail; /* kod bledu osi/napedu dla ERR_DRIVE/ERR_MECH/ERR_STEP */
} lrt_machine;

/* --- konfiguracja --------------------------------------------------------------------- */
void lrt_machine_cfg_init(lrt_machine_cfg *c);
/* Ustawia klucz (patrz naglowek). Zwraca LRT_MACHINE_OK, ERR_KEY, ERR_INDEX albo ERR_VALUE. */
int lrt_machine_cfg_set(lrt_machine_cfg *c, const char *key, double value);
/* Dopisuje punkt krzywej momentu napedu N; pierwszy punkt zastepuje krzywa domyslna. */
int lrt_machine_cfg_curve(lrt_machine_cfg *c, int drive, double omega, double torque);

/* --- cykl zycia ----------------------------------------------------------------------- */
/* Sprawdza konfiguracje, inicjalizuje napedy i osie, stawia osie w joint.J.initial. */
int lrt_machine_init(lrt_machine *m, const lrt_machine_cfg *c);
/* Jeden krok dt [s] wszystkich napedow i osi, potem czujniki, kinematyka i wejscia. */
int lrt_machine_step(lrt_machine *m, double dt);
/* Jeden cykl mastera dt [s] w n podkrokach dt/n (1..LRT_MACHINE_MAX_SUBSTEPS). Cel ustawiony
 * na ten cykl napedy w CSP dostaja liniowo rozlozony na podkroki (jak interpolacja 60C2h
 * w napedzie CSP albo stepgen rozkladajacy impulsy w okresie) - wynik nie zalezy od n poza
 * dokladnoscia calkowania. Bez interpolacji skok celu trafia do pierwszego podkroku i FF
 * predkosci napedu widzi n-krotny impuls (ustalenie sesji 049). */
int lrt_machine_step_cycle(lrt_machine *m, double dt, int n);
const char *lrt_machine_strerror(int status);
/* Element i kod szczegolowy ostatniego bledu init/step (dla wiazania bez dostepu do struktury). */
int lrt_machine_err_index(const lrt_machine *m);
int lrt_machine_err_detail(const lrt_machine *m);
/* Rozmiary struktur dla wiazania ctypes (bufor alokowany po stronie Pythona). */
unsigned long lrt_machine_cfg_size(void);
unsigned long lrt_machine_size(void);

/* --- wejscia mastera (LRT-NET) -------------------------------------------------------- */
int lrt_machine_set_controlword(lrt_machine *m, int drive, uint16_t controlword);
int lrt_machine_set_target(lrt_machine *m, int drive, int32_t counts);
/* Pozycja zadana osi maszyny [m|rad] przeliczona na impulsy kazdego napedu osi. */
int lrt_machine_set_joint_target(lrt_machine *m, int joint, double position);
int32_t lrt_machine_counts_for(const lrt_machine *m, int drive, double position);
void lrt_machine_set_outputs(lrt_machine *m, uint32_t outputs);
uint32_t lrt_machine_outputs(const lrt_machine *m);

/* --- otoczenie (panel, scenariusze) --------------------------------------------------- */
void lrt_machine_set_estop(lrt_machine *m, int pressed);
int lrt_machine_set_tool_length(lrt_machine *m, double length);
/* Ustawia polozenie osi (wszystkie jej napedy) bez dynamiki; zeruje predkosci. Do uzycia przed
 * wlaczeniem napedow (wlaczone serwo zobaczy skok polozenia). */
int lrt_machine_set_joint_position(lrt_machine *m, int joint, double position);
/* Przesuwa tylko jeden naped (np. gantry: symulacja poslizgu jednej strony). */
int lrt_machine_set_drive_position(lrt_machine *m, int drive, double position);
/* Zmiana parametru w locie (REQ-VD-04) napedu N: os albo naped wedlug parametru. */
int lrt_machine_set_live(lrt_machine *m, int drive, int param, double value);

/* --- wyjscia -------------------------------------------------------------------------- */
uint32_t lrt_machine_inputs(const lrt_machine *m);
unsigned lrt_machine_events(const lrt_machine *m);
unsigned lrt_machine_joint_events(const lrt_machine *m, int joint);
void lrt_machine_clear_events(lrt_machine *m);
double lrt_machine_joint_position(const lrt_machine *m, int joint);
double lrt_machine_joint_velocity(const lrt_machine *m, int joint);
double lrt_machine_joint_skew(const lrt_machine *m, int joint);
double lrt_machine_impact_speed(const lrt_machine *m, int joint);
double lrt_machine_drive_position(const lrt_machine *m, int drive);
long lrt_machine_index_count(const lrt_machine *m, int drive);
double lrt_machine_index_latch(const lrt_machine *m, int drive);
int lrt_machine_tool_tip(const lrt_machine *m, int workpiece_frame, double out[3]);
double lrt_machine_time(const lrt_machine *m);
/* Wskazniki do napedu i osi napedu N (NULL poza zakresem) - pelne API drive.h/axis.h. */
lrt_drive *lrt_machine_drive(lrt_machine *m, int drive);
lrt_axis *lrt_machine_axis(lrt_machine *m, int drive);
const lrt_live_log *lrt_machine_live_log(const lrt_machine *m);

/* Kinematyka prosta bez stanu maszyny: q[J] = polozenia osi; wynik jak lrt_machine_tool_tip. */
int lrt_machine_forward(const lrt_machine_cfg *c, const double *q, double tool_length,
                        int workpiece_frame, double out[3]);

#ifdef __cplusplus
}
#endif

#endif /* LRT_PLANT_MACHINE_H */
