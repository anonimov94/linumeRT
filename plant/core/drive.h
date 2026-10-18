/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - Plant, modul napedu wirtualnego (C11, bez zaleznosci poza libc/libm).
 * Model-Author: Claude
 *
 * Naped stoi miedzy masterem (slowo sterujace, pozycja zadana w impulsach) a osia
 * (lrt_axis, sterowana momentem silnika). Co krok drive liczy moment zadany z pozycji
 * zadanej i sprzezenia zwrotnego; maszyna stanow jest zgodna z ogolnym opisem profilu
 * CiA 402 (wlasna implementacja, bez kopiowania tekstow normy).
 *
 * Typy napedu:
 *  - LRT_DRIVE_SERVO_CSP:      serwo, tryb CSP: P polozenia + PI predkosci + FF predkosci
 *                              i przyspieszenia, ograniczenie momentu, okno bledu nadazania;
 *  - LRT_DRIVE_STEPPER_OPEN:   krokowiec bez sprzezenia: pozycja zadana to pole magnetyczne,
 *                              wirnik podaza za polem (model momentu sin(kat)); gdy moment
 *                              wymagany przekracza dostepny (krzywa pull-out), wirnik gubi
 *                              pelne okresy elektryczne (4 pelne kroki); master o tym nie
 *                              wie: pozycja raportowana to pozycja pola, bez alarmu;
 *  - LRT_DRIVE_STEPPER_CLOSED: serwo krokowe, petla zamknieta jak w CSP, moment ograniczony
 *                              krzywa; blad nadazania ponad okno => awaria.
 *
 * Jednostki: moment [N*m] na wale silnika, kat [rad], czas [s]. Pozycje w obiektach
 * CiA 402 w impulsach (counts_per_rev impulsow na obrot walu silnika).
 *
 * Zasady (CLAUDE.md §5): po lrt_drive_init() zadnych alokacji, zadnego I/O, staly czas kroku.
 * Krok dt musi byc maly wzgledem dynamiki: dla krokowca omega_e*dt << 1, gdzie
 * omega_e = sqrt(moment_dostepny * pary_biegunow / J) (patrz tests/test_drive.c: dt = 100 us).
 * NIEZWERYFIKOWANE NA SPRZECIE: model sprawdzony tylko wzorami analitycznymi.
 */
#ifndef LRT_PLANT_DRIVE_H
#define LRT_PLANT_DRIVE_H

#include <stdint.h>

#include "live.h"

#ifdef __cplusplus
extern "C" {
#endif

#define LRT_DRIVE_MAX_DT 0.01 /* najwiekszy dozwolony krok [s] */

typedef enum {
    LRT_DRIVE_SERVO_CSP = 0,
    LRT_DRIVE_STEPPER_OPEN = 1,
    LRT_DRIVE_STEPPER_CLOSED = 2
} lrt_drive_type;

/* Kody bledow (ujemne) zwracane przez funkcje API. */
typedef enum {
    LRT_DRIVE_OK = 0,
    LRT_DRIVE_ERR_NULL = -1,
    LRT_DRIVE_ERR_TYPE = -2,       /* nieznany typ napedu */
    LRT_DRIVE_ERR_RESOLUTION = -3, /* counts_per_rev <= 0 albo za duze */
    LRT_DRIVE_ERR_TORQUE = -4,     /* moment znamionowy/szczytowy/limit niepoprawny */
    LRT_DRIVE_ERR_GAINS = -5,      /* wzmocnienia, filtry, FF poza zakresem */
    LRT_DRIVE_ERR_LIMITS = -6,     /* okno bledu, hamowanie, predkosci poza zakresem */
    LRT_DRIVE_ERR_STEPPER = -7,    /* liczba krokow na obrot, tlumienie */
    LRT_DRIVE_ERR_DT = -8,         /* dt <= 0, za duze albo nieskonczone */
    LRT_DRIVE_ERR_NUMERIC = -9,    /* NaN/inf w sprzezeniu albo wyniku */
    LRT_DRIVE_ERR_NO_OBJECT = -10, /* obiekt/podindeks nie istnieje */
    LRT_DRIVE_ERR_READ_ONLY = -11, /* zapis do obiektu tylko do odczytu */
    LRT_DRIVE_ERR_RANGE = -12,     /* wartosc poza zakresem obiektu */
    LRT_DRIVE_ERR_UNSUPPORTED = -13, /* poprawna wartosc, ale model jej nie obsluguje */
    LRT_DRIVE_ERR_LIVE = -14       /* nieznany parametr live, NaN/inf albo wartosc poza zakresem */
} lrt_drive_status;

/* Stany maszyny CiA 402. */
typedef enum {
    LRT_DRIVE_NOT_READY = 0,
    LRT_DRIVE_SWITCH_ON_DISABLED,
    LRT_DRIVE_READY_TO_SWITCH_ON,
    LRT_DRIVE_SWITCHED_ON,
    LRT_DRIVE_OPERATION_ENABLED,
    LRT_DRIVE_QUICK_STOP_ACTIVE,
    LRT_DRIVE_FAULT_REACTION_ACTIVE,
    LRT_DRIVE_FAULT
} lrt_drive_state;

/* Slowo sterujace 6040h: bity i typowe komendy. */
#define LRT_CW_SWITCH_ON 0x0001u
#define LRT_CW_ENABLE_VOLTAGE 0x0002u
#define LRT_CW_QUICK_STOP 0x0004u /* aktywny niski: 0 = quick stop */
#define LRT_CW_ENABLE_OPERATION 0x0008u
#define LRT_CW_FAULT_RESET 0x0080u /* zbocze narastajace */
#define LRT_CW_CMD_DISABLE_VOLTAGE 0x0000u
#define LRT_CW_CMD_QUICK_STOP 0x0002u
#define LRT_CW_CMD_SHUTDOWN 0x0006u
#define LRT_CW_CMD_SWITCH_ON 0x0007u
#define LRT_CW_CMD_ENABLE_OPERATION 0x000Fu

/* Slowo stanu 6041h: bity. Stany rozpoznaje sie maskami: 0x4F (NOT_READY=0x00,
 * SWITCH_ON_DISABLED=0x40, FAULT_REACTION=0x0F, FAULT=0x08) i 0x6F (READY=0x21,
 * SWITCHED_ON=0x23, OPERATION_ENABLED=0x27, QUICK_STOP_ACTIVE=0x07). */
#define LRT_SW_READY_TO_SWITCH_ON 0x0001u
#define LRT_SW_SWITCHED_ON 0x0002u
#define LRT_SW_OPERATION_ENABLED 0x0004u
#define LRT_SW_FAULT 0x0008u
#define LRT_SW_VOLTAGE_ENABLED 0x0010u
#define LRT_SW_QUICK_STOP 0x0020u /* 1 = quick stop NIEaktywny */
#define LRT_SW_SWITCH_ON_DISABLED 0x0040u
#define LRT_SW_WARNING 0x0080u
#define LRT_SW_REMOTE 0x0200u
#define LRT_SW_INTERNAL_LIMIT 0x0800u /* moment ograniczony */
#define LRT_SW_FOLLOWS_COMMAND 0x1000u /* CSP: naped podaza za pozycja zadana */
#define LRT_SW_FOLLOWING_ERROR 0x2000u /* CSP: blad nadazania ponad okno */

/* Awarie napedu. Kolumny: nazwa, numer, kod 603Fh, alarm w core/linumert/alarms/catalog.yaml.
 * Kody 603Fh wedlug powszechnej praktyki CiA 301/402 (0xFFxx = wlasne, zakres producenta);
 * wartosci nie byly porownywane z norma (niedostepna) - NIEZWERYFIKOWANE. Kazda awaria ma
 * odpowiednik w katalogu: E-42xx, a COMM_WATCHDOG (sesja 016, watchdog serwera LRT-NET) E-4003
 * (test w tests/test_plant_core.py). */
#define LRT_DRIVE_FAULT_LIST(X)                                                              \
    X(GENERIC, 1, 0xFF00, "E-4200")                                                          \
    X(FOLLOWING_ERROR, 2, 0x8611, "E-4201")                                                  \
    X(OVERLOAD, 3, 0x2350, "E-4202")                                                         \
    X(OVERCURRENT, 4, 0x2310, "E-4203")                                                      \
    X(OVERTEMP, 5, 0x4310, "E-4204")                                                         \
    X(DC_BUS, 6, 0x3200, "E-4205")                                                           \
    X(ENCODER_LOST, 7, 0x7305, "E-4206")                                                     \
    X(HW_LIMIT, 8, 0xFF01, "E-4207")                                                         \
    X(STO, 9, 0xFF02, "E-4208")                                                              \
    X(ENCODER_BATTERY, 10, 0xFF03, "E-4211")                                                 \
    X(COMM_WATCHDOG, 11, 0x8130, "E-4003")

typedef enum {
    LRT_DRIVE_FAULT_NONE = 0,
#define LRT_DRIVE_FAULT_ENUM(name, num, cia, alarm) LRT_DRIVE_FAULT_##name = (num),
    LRT_DRIVE_FAULT_LIST(LRT_DRIVE_FAULT_ENUM)
#undef LRT_DRIVE_FAULT_ENUM
    LRT_DRIVE_FAULT_COUNT /* nie jest awaria */
} lrt_drive_fault;

/* Parametry napedu (szablon). Wartosci domyslne: lrt_drive_params_default(). */
typedef struct {
    lrt_drive_type type;

    /* Przetwornik: impulsy na obrot walu silnika (enkoder albo mikrokroki). */
    double counts_per_rev;
    double enc_noise_counts; /* szum enkodera, odch. std. [impulsy], 0 = brak */
    uint32_t enc_noise_seed; /* ziarno generatora (0 = stala domyslna) */

    /* Momenty */
    double rated_torque; /* znamionowy [N*m]; dla krokowca moment trzymania */
    double peak_torque;  /* szczytowy [N*m]; <= rated => brak ochrony I2t */
    double peak_time_s;  /* czas dopuszczalnej pracy ze szczytem [s]; 0 = brak I2t */
    uint16_t torque_limit_permille; /* domyslna wartosc 6072h [promile znamionowego] */

    /* Regulatory (CSP i serwo krokowe) */
    double kp_pos;       /* wzmocnienie polozenia [1/s] */
    double kv;           /* wzmocnienie predkosci [N*m*s/rad] */
    double ti;           /* czas calkowania predkosci [s]; 0 = bez calki */
    double kff_vel;      /* udzial FF predkosci (0..2) */
    double kff_acc;      /* udzial FF przyspieszenia (0..2) */
    double inertia_est;  /* estymata J na wale silnika dla FF przyspieszenia [kg*m^2] */
    double vel_filter_hz;/* filtr predkosci mierzonej [Hz] */
    double ff_filter_hz; /* filtr pochodnych pozycji zadanej [Hz] */
    double max_speed;    /* ograniczenie predkosci zadanej [rad/s] */

    /* Limity i reakcje */
    uint32_t following_window;     /* okno bledu nadazania 6065h [impulsy] */
    uint16_t following_window_ms;  /* czas okna 6066h [ms] */
    uint32_t quick_stop_decel;     /* 6085h [impulsy/s^2] */
    int16_t quick_stop_option;     /* 605Ah: 1 = wylacz naped, 2 = rampa i wylaczenie */
    int16_t fault_reaction_option; /* 605Eh: 0 = wylacz naped, 2 = rampa quick stop */
    double standstill_speed;       /* prog zatrzymania [rad/s] */
    double boot_time_s;            /* czas z NOT_READY do SWITCH_ON_DISABLED [s] */

    /* Krokowiec */
    int full_steps_per_rev;      /* np. 200; wielokrotnosc 4 */
    double stepper_damping_ratio;/* wzgledne tlumienie wirnika wzgledem pola (0..2); moment
                                    tlumienia ograniczony do 20 % amplitudy */

    /* Bazowanie w napedzie (tryb 6, sesja 015) */
    int8_t homing_method;          /* 6098h */
    uint32_t homing_speed_switch;  /* 6099h:1 [impulsy/s] */
    uint32_t homing_speed_zero;    /* 6099h:2 [impulsy/s] */
    uint32_t homing_accel;         /* 609Ah [impulsy/s^2] */
    int32_t home_offset;           /* 607Ch [impulsy]: pozycja raportowana w punkcie bazy */
    double hardstop_time_s;        /* metody -1/-2: czas nasycenia momentu = zderzak [s] */

    /* Przetwornik polozenia (sesja 015, REQ-VM-07) */
    int encoder;                   /* lrt_drive_encoder */
} lrt_drive_params;

/* Rodzaj przetwornika polozenia (pole `encoder`).
 *  IDEAL       - pozycja raportowana = kat walu w impulsach (model bez bazowania, sesje 011-014);
 *  INCREMENTAL - enkoder przyrostowy: po wlaczeniu (pierwszy pomiar) pozycja raportowana = 0,
 *                polozenie walu nieznane do bazowania;
 *  ABSOLUTE    - enkoder absolutny wieloobrotowy z bateria: pozycja = kat walu - przesuniecie
 *                zapamietane miedzy uruchomieniami (lrt_drive_set_absolute). Utrata baterii przy
 *                wylaczonym zasilaniu kasuje licznik obrotow: zostaje pozycja w jednym obrocie i
 *                awaria ENCODER_BATTERY (E-4211) do ponownego ustawienia bazy.
 * Krokowiec bez sprzezenia nie ma enkodera: pozycja raportowana = pozycja zadana (pole). */
typedef enum {
    LRT_ENC_IDEAL = 0,
    LRT_ENC_INCREMENTAL = 1,
    LRT_ENC_ABSOLUTE = 2
} lrt_drive_encoder;

/* Wejscia cyfrowe napedu (lrt_drive_set_inputs): stan logiczny "aktywny" (po NC/NO). Impuls
 * indeksu enkodera dostarcza maszyna (zbocze w danym kroku). */
#define LRT_DIN_NEG_LIMIT 0x0001u
#define LRT_DIN_POS_LIMIT 0x0002u
#define LRT_DIN_HOME 0x0004u
#define LRT_DIN_INDEX 0x0008u

/* Slowo sterujace w trybie 6: bit 4 = start bazowania (zbocze), bit 8 = zatrzymanie.
 * Slowo stanu w trybie 6: bit 10 = cel osiagniety (stoi), bit 12 = baza ustalona,
 * bit 13 = blad bazowania (w CSP te bity maja inne znaczenie, patrz wyzej). */
#define LRT_CW_HOMING_START 0x0010u
#define LRT_CW_HALT 0x0100u
#define LRT_SW_TARGET_REACHED 0x0400u
#define LRT_SW_HOMING_ATTAINED 0x1000u
#define LRT_SW_HOMING_ERROR 0x2000u

#define LRT_MODE_HOMING 6
#define LRT_MODE_CSP 8

/* Fazy bazowania w napedzie. */
typedef enum {
    LRT_HM_IDLE = 0,
    LRT_HM_SEARCH,  /* szukanie sygnalu wyzwalajacego z predkoscia 6099h:1 */
    LRT_HM_BACKOFF, /* zjazd z sygnalu z predkoscia 6099h:2 do zbocza */
    LRT_HM_INDEX,   /* szukanie impulsu indeksu z predkoscia 6099h:2 */
    LRT_HM_PUSH,    /* metody -1/-2: dojazd do zderzaka z ograniczonym momentem */
    LRT_HM_STOP,    /* hamowanie po ustaleniu bazy albo bledzie */
    LRT_HM_DONE,
    LRT_HM_ERROR
} lrt_drive_homing_phase;

/* Sprzezenie zwrotne podawane co krok przez orkiestrator (z lrt_axis). */
typedef struct {
    double theta_m;       /* kat walu silnika [rad] */
    double omega_m;       /* predkosc walu silnika [rad/s] */
    double torque_avail;  /* moment dostepny z krzywej przy |omega_m| [N*m], >= 0 */
    double j_total;       /* bezwladnosc zastepcza na wale [kg*m^2], > 0 */
} lrt_drive_feedback;

typedef struct {
    lrt_drive_params p;

    /* Wielkosci pochodne */
    double rad_per_count;
    double counts_per_rad;
    double pole_pairs;     /* krokowiec: full_steps_per_rev / 4 */
    double i2t_limit;      /* [N^2*m^2*s]; 0 = ochrona wylaczona */

    /* Wejscia mastera */
    uint16_t controlword;
    int32_t target_counts;       /* 607Ah */
    int32_t velocity_offset;     /* 60B1h [impulsy/s] */
    int16_t torque_offset;       /* 60B2h [promile znamionowego] */
    int8_t mode_of_operation;    /* 6060h (tylko 8 = CSP) */

    /* Obiekty zapisywalne */
    uint32_t following_window;
    uint16_t following_window_ms;
    uint16_t torque_limit_permille; /* 6072h */
    uint32_t quick_stop_decel;
    int16_t quick_stop_option;
    int16_t fault_reaction_option;
    int8_t homing_method;
    uint32_t homing_speed_switch;
    uint32_t homing_speed_zero;
    uint32_t homing_accel;
    int32_t home_offset;          /* 607Ch */

    /* Przetwornik i bazowanie (sesja 015) */
    int32_t pos_offset;           /* kat walu [impulsy] - pozycja raportowana */
    int offset_known;             /* przesuniecie ustalone (pierwszy pomiar albo absolut) */
    int abs_restored;             /* ABSOLUTE: lrt_drive_set_absolute() przed pierwszym pomiarem */
    int abs_restore_valid;        /* ... z poprawnym licznikiem obrotow */
    int abs_valid;                /* ABSOLUTE: przesuniecie warte zapamietania */
    int abs_lost;                 /* ABSOLUTE: licznik obrotow utracony, awaria E-4211 czeka */
    int battery_ok;               /* ABSOLUTE: 0 = bateria rozladowana (strata po wylaczeniu) */
    unsigned inputs;              /* LRT_DIN_* */
    unsigned prev_inputs;
    int hm_phase;                 /* lrt_drive_homing_phase */
    int hm_attained;              /* baza ustalona od ostatniego startu bazowania */
    double hm_target;             /* pozycja zadana bazowania [impulsy, ramka raportowana] */
    double hm_vel;                /* predkosc zadana bazowania [impulsy/s] */
    double hm_vel_goal;
    int hm_dir;                   /* kierunek fazy SEARCH (-1/+1) */
    double hm_push_timer;         /* metody -1/-2: czas nasycenia momentu [s] */

    /* Stan maszyny i awarie */
    lrt_drive_state state;
    uint16_t prev_controlword;
    double boot_timer;
    uint16_t error_code;          /* 603Fh */
    int fault;                    /* ostatnia awaria (lrt_drive_fault) */
    unsigned fault_cause_mask;    /* bit (1 << fault): trwala przyczyna wstrzyknieta */
    int pending_fault;            /* wstrzyknieta, jeszcze nie obsluzona */
    int pending_sticky;
    unsigned warnings;            /* LRT_DRIVE_WARN_* */
    double follow_timer;          /* czas ciaglego przekroczenia okna [s] */
    int follow_exceeded;          /* chwilowe przekroczenie okna */
    double i2t_acc;
    int ramp_active;              /* 1 = trwa hamowanie quick stop / reakcja na awarie */
    double ramp_v;                /* predkosc zadana rampy [rad/s] */
    double ramp_time;

    /* Sprzezenie, filtry */
    uint32_t rng;
    int have_meas;
    int32_t pos_meas;             /* zmierzona pozycja [impulsy] */
    int32_t prev_pos_meas;
    double vel_meas;              /* filtrowana predkosc [rad/s] */
    int32_t prev_target;
    double tv_f;                  /* filtrowana predkosc pozycji zadanej [rad/s] */
    double ta_f;                  /* filtrowane przyspieszenie pozycji zadanej [rad/s^2] */
    double integ;                 /* calka regulatora predkosci [N*m] */

    /* Krokowiec bez sprzezenia */
    double field_theta;           /* kat pola [rad] (nieograniczony) */
    double prev_field_theta;
    double field_omega;           /* filtrowana predkosc pola [rad/s] */
    int32_t k0;                   /* okresy elektryczne wyrownane przy wlaczeniu */
    int lost_periods;             /* utracone okresy elektryczne (ze znakiem) */

    /* Wyjscia */
    int32_t pos_report;           /* 6064h */
    int32_t vel_report;           /* 606Ch [impulsy/s] */
    int16_t torque_report;        /* 6077h [promile] */
    double torque_cmd;            /* ostatni moment zadany [N*m] */
    int torque_limited;           /* moment ograniczony w ostatnim kroku */
    long slip_events;             /* licznik poslizgow krokowca (okresy) */
    double time;                  /* czas od lrt_drive_init() [s]; rosnie po udanym kroku */
} lrt_drive;

enum {
    LRT_DRIVE_WARN_OVERLOAD = 1u << 0 /* I2t powyzej 80 % */
};

/* Wypelnia parametry typowymi wartosciami dla danego typu napedu (nie zwraca bledu:
 * nieznany typ daje domyslne serwo). */
void lrt_drive_params_default(lrt_drive_params *p, lrt_drive_type type);

/* Dobiera kv, ti, kp_pos i inertia_est z bezwladnosci j_total i pasma petli predkosci
 * [rad/s]; pasmo jest ograniczane do 0.15/dt (stabilnosc przy kroku dt). */
void lrt_drive_tune_servo(lrt_drive_params *p, double j_total, double vel_bandwidth, double dt);

/* Sprawdza parametry; zwraca LRT_DRIVE_OK albo kod bledu (nic nie modyfikuje). */
int lrt_drive_params_check(const lrt_drive_params *p);

/* Komunikat po polsku dla kodu statusu. */
const char *lrt_drive_strerror(int status);

/* Alarm katalogu (np. "E-4201") i kod 603Fh dla awarii; NULL/0 dla nieznanej. */
const char *lrt_drive_fault_alarm(int fault);
uint16_t lrt_drive_fault_error_code(int fault);

/* Inicjalizacja: kopiuje parametry, stan NOT_READY, zerowanie wyjsc. */
int lrt_drive_init(lrt_drive *d, const lrt_drive_params *p);

/* Wejscia mastera (zwykle z PDO). */
void lrt_drive_set_controlword(lrt_drive *d, uint16_t controlword);
void lrt_drive_set_target_position(lrt_drive *d, int32_t counts);

/* Obiekty CiA 402 przez "SDO": 603Fh 6040h 6041h 605Ah 605Eh 6060h 6061h 6064h 6065h 6066h
 * 606Ch 6072h 6077h 607Ah 607Ch 6085h 6098h 6099h:0-2 609Ah 60B1h 60B2h. Zwraca LRT_DRIVE_OK albo
 * LRT_DRIVE_ERR_NO_OBJECT / _READ_ONLY / _RANGE / _UNSUPPORTED (nic nie zmienia przy bledzie). */
int lrt_drive_od_read(const lrt_drive *d, uint16_t index, uint8_t sub, int64_t *value);
int lrt_drive_od_write(lrt_drive *d, uint16_t index, uint8_t sub, int64_t value);

/* Jeden krok czasu dt [s]; zapisuje moment zadany na wale silnika [N*m].
 * Zwraca LRT_DRIVE_OK albo kod bledu (stan nie jest zmieniany przy bledzie). */
int lrt_drive_step(lrt_drive *d, const lrt_drive_feedback *fb, double dt, double *torque_cmd);

/* Wyjscia (TxPDO). */
uint16_t lrt_drive_statusword(const lrt_drive *d);
int32_t lrt_drive_position_actual(const lrt_drive *d);
int32_t lrt_drive_velocity_actual(const lrt_drive *d);
int16_t lrt_drive_torque_actual(const lrt_drive *d);
uint16_t lrt_drive_error_code(const lrt_drive *d);
lrt_drive_state lrt_drive_get_state(const lrt_drive *d);

/* Krokowiec bez sprzezenia: utracone pelne kroki od ostatniego wlaczenia (zawsze
 * wielokrotnosc 4) oraz licznik zdarzen poslizgu. Znak: dodatnie = wirnik zostal za polem
 * w kierunku dodatnim (pole - wirnik > 0). Dla innych typow zero. */
int lrt_drive_lost_steps(const lrt_drive *d);
long lrt_drive_slip_events(const lrt_drive *d);

/* Wstrzykiwanie awarii (panel awarii, scenariusze). sticky = 1: przyczyna trwa do
 * lrt_drive_clear_fault_cause(), a reset awarii jest odrzucany. sticky = 0: jednorazowa. */
int lrt_drive_inject_fault(lrt_drive *d, int fault, int sticky);
void lrt_drive_clear_fault_cause(lrt_drive *d, int fault);

/* Zmiana parametru napedu w locie (REQ-VD-04, sesja 013): LRT_LIVE_TORQUE_LIMIT (6072h,
 * promile znamionowego, 0..limit wynikajacy z momentu szczytowego) albo LRT_LIVE_INERTIA_EST
 * (estymata J dla FF przyspieszenia, np. po zmianie masy osi). Stan regulatora jest zachowany.
 * Kazda udana zmiana trafia do dziennika `log` (moze byc NULL) z czasem modelu napedu.
 * Przy bledzie nic nie zmienia i nie dopisuje. Zwraca LRT_DRIVE_OK, LRT_DRIVE_ERR_NULL albo
 * LRT_DRIVE_ERR_LIVE. Parametry osi (masa, J, tarcie, luz, napiecie): lrt_axis_set_live(). */
int lrt_drive_set_live(lrt_drive *d, int param, double value, lrt_live_log *log);
int lrt_drive_get_live(const lrt_drive *d, int param, double *value);

/* --- przetwornik i bazowanie (sesja 015, REQ-VM-07) ------------------------------------ */
/* Wejscia cyfrowe napedu (LRT_DIN_*), ustawiane przez maszyne przed kazdym krokiem. */
void lrt_drive_set_inputs(lrt_drive *d, unsigned inputs);
/* Kat walu [impulsy] minus pozycja raportowana; do przeliczen polozenia mechanicznego na
 * impulsy mastera (lrt_machine_counts_for). */
int32_t lrt_drive_position_offset(const lrt_drive *d);
/* ABSOLUTE: przywraca zapamietane przesuniecie przed pierwszym krokiem (stan z pliku).
 * valid = 0: licznik obrotow utracony (bateria) - po wlaczeniu zostaje pozycja w jednym
 * obrocie i trwala awaria ENCODER_BATTERY do ustalenia bazy (tryb 6, np. metoda 35/37).
 * Zwraca LRT_DRIVE_ERR_UNSUPPORTED dla innego przetwornika albo po pierwszym pomiarze. */
int lrt_drive_set_absolute(lrt_drive *d, int32_t offset, int valid);
/* ABSOLUTE: przesuniecie do zapisania w pliku stanu i czy jest wazne (bateria i baza). */
int lrt_drive_get_absolute(const lrt_drive *d, int32_t *offset, int *valid);
/* ABSOLUTE: stan baterii (0 = rozladowana; pozycja przepadnie po nastepnym wlaczeniu). */
int lrt_drive_set_battery(lrt_drive *d, int ok);
/* Faza bazowania w napedzie (lrt_drive_homing_phase). */
int lrt_drive_homing_state(const lrt_drive *d);

#ifdef __cplusplus
}
#endif

#endif /* LRT_PLANT_DRIVE_H */
