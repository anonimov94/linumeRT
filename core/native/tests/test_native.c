/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - testy C natywnych przyspieszen (make -C core/native test, make test-c).
 * Model-Author: Claude · 2026-11-05
 *
 * Wartosci analityczne niezalezne od Pythona; zgodnosc z referencja w Pythonie sprawdza
 * tests/test_native.py na tych samych danych.
 */
#include "lrt_native.h"
#include "lrt_test.h"

#include <math.h>
#include <string.h>

#define PI 3.14159265358979323846

/* plaszczyzna z = a x + b y + c jako dwa trojkaty w kwadracie [-s, s]^2 */
static void plane(double *t, double a, double b, double c, double s)
{
    const double p[4][2] = {{-s, -s}, {s, -s}, {s, s}, {-s, s}};
    const int idx[6] = {0, 1, 2, 0, 2, 3};
    for (int k = 0; k < 6; k++) {
        t[3 * k] = p[idx[k]][0];
        t[3 * k + 1] = p[idx[k]][1];
        t[3 * k + 2] = a * p[idx[k]][0] + b * p[idx[k]][1] + c;
    }
}

static void test_relief_analytic_plane(void)
{
    const double slopes[4][2] = {{0, 0}, {0.25, 0}, {-0.5, 0.25}, {1, -2}};
    double t[18], out;
    int32_t work[2];
    const double xy[2] = {0, 0}, r = 0.5;
    for (int k = 0; k < 4; k++) {
        const double a = slopes[k][0], b = slopes[k][1];
        plane(t, a, b, 3, 4);
        LRT_CHECK(lrt_relief_heights(t, 2, xy, 1, r, r * r, work, &out) == LRT_NATIVE_OK);
        LRT_CHECK_ABS(out, 3 + r * (sqrt(1 + a * a + b * b) - 1), 1e-12);
    }
}

static void test_relief_wall_edge_and_miss(void)
{
    /* pionowa sciana: kontakt na krawedzi gornej */
    const double wall[9] = {0, -2, 0, 0, 2, 0, 0, 0, 3};
    double out[2];
    int32_t work[1];
    const double xy[4] = {0.5, 0, 10, 10};
    LRT_CHECK(lrt_relief_heights(wall, 1, xy, 2, 1, 1, work, out) == LRT_NATIVE_OK);
    LRT_CHECK_ABS(out[0], 3 + sqrt(1 - 0.25) - 1, 1e-12);
    LRT_CHECK(isinf(out[1]) && out[1] < 0);
    /* srodek pochylej krawedzi, nie wierzcholki i nie wnetrze */
    const double edge[9] = {0, -2, -2, 0, 2, 2, 0, -2, -3};
    LRT_CHECK(lrt_relief_heights(edge, 1, xy, 1, 1, 1, work, out) == LRT_NATIVE_OK);
    LRT_CHECK_ABS(out[0], sqrt(1.5) - 1, 1e-12);
}

static void test_relief_rejects_bad_radius(void)
{
    double t[18], out;
    int32_t work[2];
    const double xy[2] = {0, 0};
    plane(t, 0, 0, 0, 1);
    LRT_CHECK(lrt_relief_heights(t, 2, xy, 1, 0, 0, work, &out) == LRT_NATIVE_EINVAL);
    LRT_CHECK(lrt_relief_heights(t, 2, xy, 1, NAN, NAN, work, &out) == LRT_NATIVE_EINVAL);
    LRT_CHECK(lrt_relief_heights(t, 2, NULL, 1, 1, 1, work, &out) == LRT_NATIVE_EINVAL);
}

/* mapa 100 x 100 komorek 0,1 mm od (0, 0), wierzch 0, dno -10 */
#define N 100
static float map[N * N];
static double xs[N], ys[N];

static void flat_map(void)
{
    for (int i = 0; i < N; i++)
        xs[i] = ys[i] = (i + 0.5) * 0.1;
    for (int i = 0; i < N * N; i++)
        map[i] = 0.0f;
}

static lrt_cut_result plunge(const lrt_cutter *c, const double *pr, const double *pz, int np,
                             double depth)
{
    const double p0[3] = {5, 5, 1}, p1[3] = {5, 5, depth};
    lrt_cut_result res;
    memset(&res, 0, sizeof res);
    double reach = c->radius;
    for (int k = 0; k < np; k++)
        reach = pr[k] > reach ? pr[k] : reach;
    LRT_CHECK(lrt_zmap_cut(map, N, N, xs, ys, 0, 0, 0.1, -10, c, pr, pz, np, reach, p0, p1, 1,
                           40, 1e-3, &res) == LRT_NATIVE_OK);
    return res;
}

static void test_zmap_flat_plunge_volume(void)
{
    flat_map();
    const lrt_cutter c = {.radius = 2, .profile = LRT_PROFILE_FLAT};
    const lrt_cut_result res = plunge(&c, NULL, NULL, 0, -1);
    int cells = 0;
    for (int iy = 0; iy < N; iy++)
        for (int ix = 0; ix < N; ix++) {
            const double r = hypot(xs[ix] - 5, ys[iy] - 5);
            const float h = map[iy * N + ix];
            LRT_CHECK(r <= 2 ? h == -1.0f : h == 0.0f);
            cells += r <= 2;
        }
    LRT_CHECK_REL(res.removed, cells * 0.01, 1e-6);  /* roznice float32 w kolejnych probkach */
    LRT_CHECK_REL(res.removed, PI * 4.0, 0.01);   /* dyskretyzacja siatki 0,1 mm */
    LRT_CHECK(res.has_contact && res.parts == 0);
    LRT_CHECK_ABS(res.contact_at[2], -0.05, 1e-12);  /* pierwsza probka ponizej wierzchu */
}

static void test_zmap_ball_profile_and_bottom(void)
{
    flat_map();
    const lrt_cutter c = {.radius = 1, .profile = LRT_PROFILE_BALL};
    const lrt_cut_result res = plunge(&c, NULL, NULL, 0, -12);  /* ponizej dna -10 */
    const float centre = map[49 * N + 49];  /* komorka (4,95; 4,95), r = 0,0707 */
    const double r = hypot(0.05, 0.05);
    LRT_CHECK_ABS(centre, -12 + 1 - sqrt(1 - r * r), 1e-6);
    /* objetosc liczona tylko do dna: walec r = 1 x 10 mm (bez czaszy pod dnem) */
    LRT_CHECK_REL(res.removed, PI * 10.0, 0.02);
}

static void test_zmap_parts_contact_before_cut(void)
{
    flat_map();
    const lrt_cutter c = {.radius = 1, .profile = LRT_PROFILE_FLAT};
    const double pr[2] = {1, 4}, pz[2] = {5, 1.5};
    const lrt_cut_result res = plunge(&c, pr, pz, 2, -2);
    /* szyjka (bit 0) od 5 mm nad ostrzem nie siega wierzchu; oprawka (bit 1) od 1,5 mm tak */
    LRT_CHECK(res.parts == 2u);
    LRT_CHECK(res.has_contact);
}

static void test_zmap_above_material_and_invalid(void)
{
    flat_map();
    const lrt_cutter c = {.radius = 2, .profile = LRT_PROFILE_CONE, .cone_tan = 1};
    const double p0[3] = {5, 5, 3}, p1[3] = {8, 5, 0.0005};
    lrt_cut_result res;
    LRT_CHECK(lrt_zmap_cut(map, N, N, xs, ys, 0, 0, 0.1, -10, &c, NULL, NULL, 0, 2, p0, p1, 1,
                           20, 1e-3, &res) == LRT_NATIVE_OK);
    LRT_CHECK(res.removed == 0 && !res.has_contact);
    for (int i = 0; i < N * N; i++)
        LRT_CHECK(map[i] == 0.0f);
    const double bad[3] = {NAN, 0, 0};
    LRT_CHECK(lrt_zmap_cut(map, N, N, xs, ys, 0, 0, 0.1, -10, &c, NULL, NULL, 0, 2, bad, p1, 1,
                           20, 1e-3, &res) == LRT_NATIVE_EINVAL);
    LRT_CHECK(lrt_zmap_cut(map, N, N, xs, ys, 0, 0, 0.1, -10, &c, NULL, NULL, 33, 2, p0, p1, 1,
                           20, 1e-3, &res) == LRT_NATIVE_EINVAL);
    LRT_CHECK(lrt_native_abi() == LRT_NATIVE_ABI);
}

int main(void)
{
    LRT_RUN(test_relief_analytic_plane);
    LRT_RUN(test_relief_wall_edge_and_miss);
    LRT_RUN(test_relief_rejects_bad_radius);
    LRT_RUN(test_zmap_flat_plunge_volume);
    LRT_RUN(test_zmap_ball_profile_and_bottom);
    LRT_RUN(test_zmap_parts_contact_before_cut);
    LRT_RUN(test_zmap_above_material_and_invalid);
    return lrt_summary();
}
