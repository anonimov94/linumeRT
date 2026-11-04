/* SPDX-License-Identifier: GPL-2.0-or-later
 *
 * linumeRT - Plant: nazwy parametrow live i dziennik zmian (REQ-VD-04).
 * Model-Author: Claude · sesja 013
 */
#include "live.h"

#include <string.h>

static const char *const live_names[LRT_LIVE_COUNT] = {
    "load", "j_motor", "j_screw", "friction_coulomb", "friction_static", "friction_viscous",
    "backlash", "supply_scale", "torque_limit", "inertia_est"};

const char *lrt_live_param_name(int param)
{
    return (param >= 0 && param < LRT_LIVE_COUNT) ? live_names[param] : NULL;
}

void lrt_live_log_init(lrt_live_log *log)
{
    if (log != NULL) {
        memset(log, 0, sizeof(*log));
    }
}

void lrt_live_log_append(lrt_live_log *log, double t, int param, double old_value,
                         double new_value)
{
    lrt_live_entry *e;

    if (log == NULL) {
        return;
    }
    e = &log->entries[log->total % LRT_LIVE_LOG_SIZE];
    e->t = t;
    e->param = param;
    e->old_value = old_value;
    e->new_value = new_value;
    log->total++;
}

unsigned lrt_live_log_size(const lrt_live_log *log)
{
    if (log == NULL) {
        return 0u;
    }
    return (log->total < LRT_LIVE_LOG_SIZE) ? log->total : (unsigned)LRT_LIVE_LOG_SIZE;
}

unsigned lrt_live_log_dropped(const lrt_live_log *log)
{
    if (log == NULL || log->total <= LRT_LIVE_LOG_SIZE) {
        return 0u;
    }
    return log->total - (unsigned)LRT_LIVE_LOG_SIZE;
}

int lrt_live_log_get(const lrt_live_log *log, unsigned i, lrt_live_entry *out)
{
    if (log == NULL || out == NULL || i >= lrt_live_log_size(log)) {
        return -1;
    }
    *out = log->entries[(lrt_live_log_dropped(log) + i) % LRT_LIVE_LOG_SIZE];
    return 0;
}
