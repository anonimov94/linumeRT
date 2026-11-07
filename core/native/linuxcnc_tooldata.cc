/* SPDX-License-Identifier: GPL-2.0-or-later
 * Model-Author: Codex
 *
 * LinuxCNC 2.9 tooldata -> a small C ABI for the isolated gcode.parse worker.
 * This optional bridge is separate from the dependency-free C11 math kernels.
 * Compile against the same LinuxCNC headers/libraries used by the worker.
 */
#include "tooldata.hh"

#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits.h>
#include <sys/stat.h>
#include <unistd.h>

static bool opened = false;
static bool used = false;

extern "C" int lrt_tooldata_bridge_abi() { return 1; }

extern "C" int lrt_tooldata_open(const char *table)
{
    if (used || !table)
        return -EINVAL;
    const char *home = std::getenv("HOME");
    char cwd[PATH_MAX];
    struct stat info;
    // A fresh, private worker only. Never initialize the live controller's mmap.
    if (!home || !getcwd(cwd, sizeof(cwd)) || std::strcmp(home, cwd) != 0
        || stat(cwd, &info) || !S_ISDIR(info.st_mode) || info.st_uid != geteuid()
        || (info.st_mode & 0077))
        return -EPERM;
    if (lstat(".tool.mmap", &info) == 0 || errno != ENOENT)
        return -EEXIST;
    used = true;
    if (tool_mmap_creator(nullptr, 0))
        return -EIO;
    opened = true;
    tooldata_init(false);
    if (tooldata_load(table, nullptr)) {
        tool_mmap_close();
        opened = false;
        return -EIO;
    }
    return 0;
}

extern "C" int lrt_tooldata_read(int32_t pocket, int32_t *number, double *values,
                                  int32_t *orientation)
{
    if (!opened || !number || !values || !orientation
        || pocket < 0 || pocket >= CANON_POCKETS_MAX)
        return -EINVAL;
    CANON_TOOL_TABLE row;
    if (tooldata_get(&row, pocket) != IDX_OK)
        return -ERANGE;
    *number = row.toolno;
    *orientation = row.orientation;
    const double offsets[] = {row.offset.tran.x, row.offset.tran.y, row.offset.tran.z,
                              row.offset.a, row.offset.b, row.offset.c,
                              row.offset.u, row.offset.v, row.offset.w,
                              row.diameter, row.frontangle, row.backangle};
    std::memcpy(values, offsets, sizeof(offsets));
    return 0;
}

extern "C" void lrt_tooldata_close()
{
    if (opened) {
        tool_mmap_close();
        opened = false;
    }
}
