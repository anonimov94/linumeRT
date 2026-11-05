/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - natywne przyspieszenia rdzenia i symulacji (C11, tylko libc/libm).
 * Model-Author: Claude · 2026-11-05
 *
 * Biblioteka liczy poza RT (CLAUDE.md §5) dwie petle, ktorych numpy nie przyspiesza:
 *  - lrt_zmap_cut: przejazd narzedzia po mapie wysokosci przygotowki (simulation/linumert_sim/
 *    zmap.py, StockMap.cut). Kolejne probki zaleza od siebie (kazda obniza mape przed nastepna),
 *    wiec petli nie da sie zwektoryzowac.
 *  - lrt_relief_heights: wysokosc wierzcholka frezu kulistego nad siatka STL dla wielu punktow
 *    (core/linumert/generators/relief.py, ball_tip_height).
 * Kazda funkcja ma odpowiednik w Pythonie, ktory pozostaje sciezka zapasowa i referencyjna;
 * test tests/test_native.py porownuje wyniki. Operacje zmiennoprzecinkowe sa w tej samej
 * kolejnosci co w numpy (kompilacja z -ffp-contract=off), zeby wynik byl identyczny bitowo.
 * Funkcje nie alokuja pamieci i nie wykonuja I/O.
 */
#ifndef LRT_NATIVE_H
#define LRT_NATIVE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define LRT_NATIVE_ABI 1

#define LRT_NATIVE_OK 0
#define LRT_NATIVE_EINVAL (-1)

/* Profil czesci tnacej (simulation/linumert_sim/cutter.py, Cutter.lower). */
enum {
    LRT_PROFILE_FLAT = 0,  /* plaski: 0 w calym promieniu */
    LRT_PROFILE_BALL = 1,  /* kula: R - sqrt(R^2 - r^2) */
    LRT_PROFILE_BULL = 2,  /* torus: naroze `corner` */
    LRT_PROFILE_CONE = 3   /* stozek: r / cone_tan */
};

typedef struct {
    double radius;    /* promien tnacy [mm] */
    double corner;    /* promien naroza (BULL) [mm] */
    double corner_sq; /* corner ** 2 policzone w Pythonie (ta sama wartosc co tam) */
    double cone_tan;  /* tan(polowy kata wierzcholkowego) (CONE) */
    int32_t profile;  /* LRT_PROFILE_* */
    int32_t reserved;
} lrt_cutter;

/* Wynik przejazdu: jak CutResult w zmap.py. */
typedef struct {
    double removed;       /* [mm^3] */
    double contact_at[3]; /* pierwsza probka z kontaktem (gdy has_contact) */
    uint32_t parts;       /* bit i = czesc nietnaca i w materiale */
    int32_t has_contact;
} lrt_cut_result;

/* Wersja ABI (zgodnosc wiazania ctypes w core/linumert/native.py). */
int lrt_native_abi(void);

/*
 * Przejazd wierzcholka p0 -> p1 w `n` krokach, probki od i = `first` do n (t = i / n).
 *  h        - mapa [ny][nx] float32, zmieniana w miejscu
 *  xs, ys   - srodki komorek [nx], [ny] (StockMap.xs/ys)
 *  part_r, part_z - czesci nietnace: promien i dolna krawedz nad wierzcholkiem, n_parts <= 32
 *  reach    - zasieg okna (max promienia tnacego i czesci)
 *  eps      - zaglebienie uznawane za kontakt (zmap.EPS)
 * Zwraca LRT_NATIVE_OK albo LRT_NATIVE_EINVAL (zle argumenty, mapa nie zmieniona).
 */
int lrt_zmap_cut(float *h, int32_t nx, int32_t ny, const double *xs, const double *ys,
                 double x0, double y0, double cell, double z_bottom, const lrt_cutter *cutter,
                 const double *part_r, const double *part_z, int32_t n_parts, double reach,
                 const double *p0, const double *p1, int32_t first, int32_t n, double eps,
                 lrt_cut_result *out);

/*
 * Wysokosc wierzcholka frezu kulistego (relief.ball_tip_height) dla `n_points` punktow XY.
 *  tris     - trojkaty [n_tris][3][3] (x, y, z), skonczone
 *  xy       - punkty [n_points][2]
 *  radius, radius_sq - promien i radius ** 2 z Pythona
 *  work     - bufor roboczy int32 [n_tris] (indeksy kandydatow), wypelniany przez funkcje
 *  out      - [n_points]; -INFINITY, gdy kula nie siega siatki
 * Wybor kandydatow i obliczenia jak w Pythonie; kolejnosc punktow dowolna.
 */
int lrt_relief_heights(const double *tris, size_t n_tris, const double *xy, size_t n_points,
                       double radius, double radius_sq, int32_t *work, double *out);

#ifdef __cplusplus
}
#endif

#endif /* LRT_NATIVE_H */
