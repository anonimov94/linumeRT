/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - minimalny framework testow C (jeden plik naglowkowy, bez zaleznosci).
 * Model-Author: Claude
 *
 * Uzycie: zdefiniuj `static void test_xxx(void)`, w main() wywolaj LRT_RUN(test_xxx),
 * na koniec `return lrt_summary();`. Wynik w formacie zblizonym do TAP:
 *   ok 1 - test_xxx
 *   not ok 2 - test_yyy
 * Plik wlaczany z dokladnie jednego pliku .c (funkcje static).
 */
#ifndef LRT_TEST_H
#define LRT_TEST_H

#include <math.h>
#include <stdio.h>

static int lrt_checks_failed;
static int lrt_tests_run;
static int lrt_tests_failed;

#define LRT_CHECK(cond)                                                                      \
    do {                                                                                     \
        if (!(cond)) {                                                                       \
            printf("#   %s:%d: warunek nie spelniony: %s\n", __FILE__, __LINE__, #cond);     \
            lrt_checks_failed++;                                                             \
        }                                                                                    \
    } while (0)

#define LRT_CHECK_ABS(actual, expected, tol)                                                 \
    do {                                                                                     \
        double a_ = (actual);                                                                \
        double e_ = (expected);                                                              \
        if (!(fabs(a_ - e_) <= (tol))) {                                                     \
            printf("#   %s:%d: %s = %.9g, oczekiwano %.9g (tol. bezwzgl. %.3g)\n", __FILE__,  \
                   __LINE__, #actual, a_, e_, (double)(tol));                                \
            lrt_checks_failed++;                                                             \
        }                                                                                    \
    } while (0)

/* Blad wzgledny wobec wartosci oczekiwanej (expected != 0). */
#define LRT_CHECK_REL(actual, expected, tol)                                                 \
    do {                                                                                     \
        double a_ = (actual);                                                                \
        double e_ = (expected);                                                              \
        double err_ = fabs(a_ - e_) / fabs(e_);                                              \
        if (!(err_ <= (tol))) {                                                              \
            printf("#   %s:%d: %s = %.9g, oczekiwano %.9g (blad wzgl. %.3g > %.3g)\n",        \
                   __FILE__, __LINE__, #actual, a_, e_, err_, (double)(tol));                \
            lrt_checks_failed++;                                                             \
        }                                                                                    \
    } while (0)

static void lrt_run_test(const char *name, void (*fn)(void))
{
    lrt_checks_failed = 0;
    fn();
    lrt_tests_run++;
    if (lrt_checks_failed == 0) {
        printf("ok %d - %s\n", lrt_tests_run, name);
    } else {
        printf("not ok %d - %s (%d nieudanych sprawdzen)\n", lrt_tests_run, name,
               lrt_checks_failed);
        lrt_tests_failed++;
    }
}

#define LRT_RUN(fn) lrt_run_test(#fn, fn)

static int lrt_summary(void)
{
    printf("# testy: %d, nieudane: %d\n", lrt_tests_run, lrt_tests_failed);
    return (lrt_tests_failed == 0 && lrt_tests_run > 0) ? 0 : 1;
}

#endif /* LRT_TEST_H */
