/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - wysokosc frezu kulistego nad siatka STL (odpowiednik relief.ball_tip_height).
 * Model-Author: Claude · 2026-11-05
 *
 * Dokladny kontakt statyczny kuli: krawedzie (prosta + luk, maksimum analityczne) i wnetrza
 * trojkatow. Odniesienie to dolny wierzcholek kuli. Kolejnosc dzialan jak w numpy w
 * core/linumert/generators/relief.py, zeby wynik byl ten sam bitowo; przy zmianie wzoru
 * zmien oba miejsca i test tests/test_native.py. Poza RT, bez alokacji.
 */
#include "lrt_native.h"

#include <math.h>

/* np.maximum(0, v): pierwszy argument przy remisie (takze +0 wobec -0). */
static double max0(double v)
{
    return (0.0 >= v) ? 0.0 : v;
}

/* np.clip(v, 0, 1) = MIN(MAX(v, 0), 1) z makr numpy (_NPY_CLIP). */
static double clip01(double v)
{
    double m = (v > 0.0) ? v : 0.0;
    return (m < 1.0) ? m : 1.0;
}

static double min3(double a, double b, double c)
{
    double m = a < b ? a : b;
    return m < c ? m : c;
}

static double max3(double a, double b, double c)
{
    double m = a > b ? a : b;
    return m > c ? m : c;
}

static double point_height(const double *tris, size_t n_tris, double x, double y,
                           double radius, double radius_sq, int32_t *work)
{
    const double lo_x = (x - radius) - 1e-9, hi_x = (x + radius) + 1e-9;
    const double lo_y = (y - radius) - 1e-9, hi_y = (y + radius) + 1e-9;
    const double touch = -1e-10 * (1.0 >= radius_sq ? 1.0 : radius_sq);
    size_t m = 0;
    for (size_t k = 0; k < n_tris; k++) {
        const double *t = tris + 9 * k;
        if (min3(t[0], t[3], t[6]) <= hi_x && min3(t[1], t[4], t[7]) <= hi_y
            && max3(t[0], t[3], t[6]) >= lo_x && max3(t[1], t[4], t[7]) >= lo_y)
            work[m++] = (int32_t)k;
    }
    double best = -INFINITY;
    /* krawedzie: ograniczenie do odcinka to prosta i luk z maksimum analitycznym */
    for (size_t j = 0; j < m; j++) {
        const double *t = tris + 9 * (size_t)work[j];
        for (int e = 0; e < 3; e++) {
            const double *a = t + 3 * e, *b = t + 3 * ((e + 1) % 3);
            const double d0 = b[0] - a[0], d1 = b[1] - a[1], d2 = b[2] - a[2];
            const double length2 = d0 * d0 + d1 * d1;
            const int nonvertical = length2 > 0;
            const double den = nonvertical ? length2 : 1.0;
            const double proj = ((x - a[0]) * d0 + (y - a[1]) * d1) / den;
            const double e0 = (a[0] + proj * d0) - x, e1 = (a[1] + proj * d1) - y;
            const double avail = max0(radius_sq - (e0 * e0 + e1 * e1));
            const double off = d2 * sqrt(avail / (den + d2 * d2));
            double param = clip01(proj + off / sqrt(den));
            if (!nonvertical)
                param = d2 > 0 ? 1.0 : 0.0;
            const double c0 = a[0] + param * d0, c1 = a[1] + param * d1, c2 = a[2] + param * d2;
            const double q0 = c0 - x, q1 = c1 - y;
            const double inside = radius_sq - (q0 * q0 + q1 * q1);
            const double h = (c2 + sqrt(max0(inside))) - radius;
            if (inside >= touch && h > best)
                best = h;
        }
    }
    /* wnetrze: optimum z = ax + by + c pod czasza kuli */
    double best_in = -INFINITY;
    for (size_t j = 0; j < m; j++) {
        const double *t = tris + 9 * (size_t)work[j];
        const double u0 = t[3] - t[0], u1 = t[4] - t[1], u2 = t[5] - t[2];
        const double v0 = t[6] - t[0], v1 = t[7] - t[1], v2 = t[8] - t[2];
        const double nx = u1 * v2 - u2 * v1, ny = u2 * v0 - u0 * v2, nz = u0 * v1 - u1 * v0;
        if (nz == 0)
            continue;
        const double sgn = nz > 0 ? 1.0 : -1.0;
        const double nn = sqrt((nx * nx + ny * ny) + nz * nz);
        const double o0 = ((-radius * nx) * sgn) / nn, o1 = ((-radius * ny) * sgn) / nn;
        const double q0 = (x + o0) - t[0], q1 = (y + o1) - t[1];
        const double det = u0 * v1 - u1 * v0;
        const double u = (q0 * v1 - q1 * v0) / det;
        const double v = (u0 * q1 - u1 * q0) / det;
        if (!(u >= -1e-10 && v >= -1e-10 && u + v <= 1 + 1e-10))
            continue;
        const double surface = (t[2] + u * (t[5] - t[2])) + v * (t[8] - t[2]);
        const double h = surface + sqrt(max0(radius_sq - (o0 * o0 + o1 * o1)));
        if (h > best_in)
            best_in = h;
    }
    best_in = best_in - radius;
    return best_in > best ? best_in : best;
}

int lrt_relief_heights(const double *tris, size_t n_tris, const double *xy, size_t n_points,
                       double radius, double radius_sq, int32_t *work, double *out)
{
    if ((n_tris && (!tris || !work)) || (n_points && (!xy || !out)) || !(radius > 0)
        || !isfinite(radius) || !isfinite(radius_sq) || n_tris > (size_t)INT32_MAX)
        return LRT_NATIVE_EINVAL;
    for (size_t p = 0; p < n_points; p++)
        out[p] = n_tris ? point_height(tris, n_tris, xy[2 * p], xy[2 * p + 1], radius,
                                       radius_sq, work)
                        : -INFINITY;
    return LRT_NATIVE_OK;
}
