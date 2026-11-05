/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - usuwanie materialu z mapy wysokosci przygotowki (odpowiednik StockMap.cut).
 * Model-Author: Claude · 2026-11-05
 *
 * Ten sam algorytm co simulation/linumert_sim/zmap.py: przejazd p0 -> p1 probkowany w n krokach;
 * na kazdej probce czesci nietnace zglaszaja kontakt (przed cieciem), potem czesc tnaca obniza
 * mape do profilu narzedzia. Mapa float32 i obliczenia w double jak w numpy, wiec mapa po
 * przejezdzie jest ta sama bitowo; objetosc sumowana w double (numpy: suma float32), stad
 * tolerancja wzgledna objetosci w tests/test_native.py. Poza RT, bez alokacji i I/O.
 */
#include "lrt_native.h"

#include <math.h>

#define MAX_PARTS 32

/* int() Pythona na liczbie skonczonej: obciecie w strone zera, z ograniczeniem zakresu. */
static long itrunc(double v)
{
    if (v > 1e15)
        return 1000000000000000L;
    if (v < -1e15)
        return -1000000000000000L;
    return (long)v;
}

/* Komorki, ktorych srodek moze lezec w odleglosci <= rho od v (zapas 0,5 komorki z kazdej
 * strony, wiele rzedow wiekszy niz bledy zaokraglen), przyciete do okna [lo, hi). */
static void box(double v, double rho, double origin, double cell, long lo, long hi, long *a,
                long *b)
{
    const double fa = floor((v - rho - origin) / cell) - 1, fb = floor((v + rho - origin) / cell) + 2;
    *a = !(fa > (double)lo) ? lo : (fa >= (double)hi ? hi : (long)fa);
    *b = !(fb < (double)hi) ? hi : (fb <= (double)lo ? lo : (long)fb);
    if (*b < *a)
        *b = *a;
}

/* Cutter.lower(r): wysokosc powierzchni tnacej nad wierzcholkiem; +inf poza promieniem. */
static double lower(const lrt_cutter *c, double r)
{
    const double R = c->radius;
    if (!(r <= R))
        return INFINITY;
    switch (c->profile) {
    case LRT_PROFILE_BALL: {
        const double s = R * R - r * r;
        return R - sqrt(s > 0.0 ? s : 0.0); /* np.maximum(s, 0.0) */
    }
    case LRT_PROFILE_BULL: {
        const double flat = R - c->corner;
        const double dd = r - flat;
        const double d = dd > 0.0 ? dd : 0.0;
        const double s = c->corner_sq - d * d;
        return c->corner - sqrt(s > 0.0 ? s : 0.0);
    }
    case LRT_PROFILE_CONE:
        return r / c->cone_tan;
    default:
        return 0.0;
    }
}

static void stamp(float *h, long nx, long ny, const double *xs, const double *ys, double x0,
                  double y0, double cell, float zb, const lrt_cutter *cutter,
                  const double *part_r, const double *part_z, int n_parts, double reach,
                  double x, double y, double z, double eps, int scan_top, lrt_cut_result *out)
{
    long ix0 = itrunc((x - reach - x0) / cell), ix1 = itrunc((x + reach - x0) / cell) + 1;
    long iy0 = itrunc((y - reach - y0) / cell), iy1 = itrunc((y + reach - y0) / cell) + 1;
    ix0 = ix0 > 0 ? ix0 : 0;
    iy0 = iy0 > 0 ? iy0 : 0;
    ix1 = ix1 < nx ? ix1 : nx;
    iy1 = iy1 < ny ? iy1 : ny;
    if (ix0 >= ix1 || iy0 >= iy1)
        return;
    /* Python wychodzi, gdy okno nie siega ponad z + eps. Przy czesciach od z >= 0 nad ostrzem
     * wyjscie niczego nie zmienia (kontakt i ciecie wymagaja komorki ponad z + eps), wiec
     * przegladamy okno tylko, gdy jakas czesc zaczyna sie ponizej ostrza. */
    if (scan_top) {
        float top = -INFINITY;
        for (long iy = iy0; iy < iy1; iy++)
            for (long ix = ix0; ix < ix1; ix++)
                if (h[iy * nx + ix] > top)
                    top = h[iy * nx + ix];
        if ((double)top <= z + eps)
            return;
    }
    int contact = 0;
    /* czesci nietnace najpierw: material nad ostrzem w ich promieniu = kontakt. Najpierw warunek
     * wysokosci (tani), potem odleglosc; pudelko promienia z zapasem komorki, wynik jak w oknie. */
    for (int p = 0; p < n_parts; p++) {
        const double level = z + part_z[p] + eps;
        long bx0, bx1, by0, by1;
        box(x, part_r[p], x0, cell, ix0, ix1, &bx0, &bx1);
        box(y, part_r[p], y0, cell, iy0, iy1, &by0, &by1);
        int hit = 0;
        for (long iy = by0; iy < by1 && !hit; iy++) {
            const double dy = ys[iy] - y;
            for (long ix = bx0; ix < bx1; ix++) {
                if (!((double)h[iy * nx + ix] > level))
                    continue;
                const double dx = xs[ix] - x;
                if (sqrt(dx * dx + dy * dy) <= part_r[p]) {
                    hit = 1;
                    break;
                }
            }
        }
        if (hit) {
            out->parts |= (uint32_t)1 << p;
            contact = 1;
        }
    }
    /* czesc tnaca: powierzchnia >= z, wiec komorka nie wyzsza niz z + eps nie jest cieta */
    const double floor_z = z + eps;
    long bx0, bx1, by0, by1;
    box(x, cutter->radius, x0, cell, ix0, ix1, &bx0, &bx1);
    box(y, cutter->radius, y0, cell, iy0, iy1, &by0, &by1);
    double removed = 0.0;
    int any = 0;
    for (long iy = by0; iy < by1; iy++) {
        const double dy = ys[iy] - y;
        for (long ix = bx0; ix < bx1; ix++) {
            float *cellp = &h[iy * nx + ix];
            if (!((double)*cellp > floor_z))
                continue;
            const double dx = xs[ix] - x;
            const double surface = z + lower(cutter, sqrt(dx * dx + dy * dy));
            if (!((double)*cellp > surface + eps))
                continue;
            /* np.clip(x, z_bottom, None) = x > z_bottom ? x : z_bottom (makro _NPY_MAX) */
            const float old = *cellp > zb ? *cellp : zb;
            const float nh = (float)surface;
            const float nc = nh > zb ? nh : zb;
            *cellp = nh;
            removed += (double)(float)(old - nc);
            any = 1;
        }
    }
    if (any) {
        out->removed += removed * cell * cell;
        contact = 1;
    }
    if (contact && !out->has_contact) {
        out->has_contact = 1;
        out->contact_at[0] = x;
        out->contact_at[1] = y;
        out->contact_at[2] = z;
    }
}

int lrt_native_abi(void)
{
    return LRT_NATIVE_ABI;
}

int lrt_zmap_cut(float *h, int32_t nx, int32_t ny, const double *xs, const double *ys,
                 double x0, double y0, double cell, double z_bottom, const lrt_cutter *cutter,
                 const double *part_r, const double *part_z, int32_t n_parts, double reach,
                 const double *p0, const double *p1, int32_t first, int32_t n, double eps,
                 lrt_cut_result *out)
{
    if (!h || !xs || !ys || !cutter || !p0 || !p1 || !out || nx < 1 || ny < 1 || n < 1
        || first < 0 || first > n || n_parts < 0 || n_parts > MAX_PARTS
        || (n_parts && (!part_r || !part_z)) || !(cell > 0) || !isfinite(reach)
        || !isfinite(x0) || !isfinite(y0))
        return LRT_NATIVE_EINVAL;
    for (int k = 0; k < 3; k++)
        if (!isfinite(p0[k]) || !isfinite(p1[k]))
            return LRT_NATIVE_EINVAL;
    for (int k = 0; k < n_parts; k++)
        if (!isfinite(part_r[k]) || !isfinite(part_z[k]))
            return LRT_NATIVE_EINVAL;
    if (!isfinite(cutter->radius) || !isfinite(z_bottom) || !isfinite(eps))
        return LRT_NATIVE_EINVAL;
    out->removed = 0.0;
    out->parts = 0;
    out->has_contact = 0;
    out->contact_at[0] = out->contact_at[1] = out->contact_at[2] = 0.0;
    const float zb = (float)z_bottom;
    int scan_top = 0;
    for (int k = 0; k < n_parts; k++)
        scan_top |= !(part_z[k] >= 0);
    /* Caly przejazd nad materialem: maksimum w obwiedni wszystkich okien (z zapasem komorki)
     * ponizej najnizszej probki minus 1e-9 mm -> kazda probka wyszlaby wczesnie jak w Pythonie. */
    {
        const double lo_x = fmin(p0[0], p1[0]) - reach, hi_x = fmax(p0[0], p1[0]) + reach;
        const double lo_y = fmin(p0[1], p1[1]) - reach, hi_y = fmax(p0[1], p1[1]) + reach;
        long ax0, ax1, ay0, ay1;
        box(0.5 * (lo_x + hi_x), 0.5 * (hi_x - lo_x), x0, cell, 0, nx, &ax0, &ax1);
        box(0.5 * (lo_y + hi_y), 0.5 * (hi_y - lo_y), y0, cell, 0, ny, &ay0, &ay1);
        float top = -INFINITY;
        for (long iy = ay0; iy < ay1; iy++)
            for (long ix = ax0; ix < ax1; ix++)
                if (h[iy * nx + ix] > top)
                    top = h[iy * nx + ix];
        if ((double)top <= fmin(p0[2], p1[2]) + eps - 1e-9)
            return LRT_NATIVE_OK;
    }
    for (int32_t i = first; i <= n; i++) {
        const double t = (double)i / (double)n;
        const double x = p0[0] + (p1[0] - p0[0]) * t;
        const double y = p0[1] + (p1[1] - p0[1]) * t;
        const double z = p0[2] + (p1[2] - p0[2]) * t;
        stamp(h, nx, ny, xs, ys, x0, y0, cell, zb, cutter, part_r, part_z, n_parts, reach, x, y,
              z, eps, scan_top, out);
    }
    return LRT_NATIVE_OK;
}
