/* SPDX-License-Identifier: GPL-2.0-or-later */
/* linumeRT - narzedzie testowe dla hal/lrt_net_proto.h (porownanie z lrtnet.py w pytest).
 * Model-Author: Claude · sesja 017
 *   cmd <seq> <time_ns> <n> <cw> <mode> <target> [...x n] <dout> <spindle>  -> hex ramki
 *   reply <hex>                                                             -> pola odpowiedzi
 *   crc <hex>                                                               -> crc32
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../lrt_net_proto.h"

static int unhex(const char *s, uint8_t *out, int max)
{
    int n = 0;
    while (s[0] && s[1] && n < max) {
        unsigned v;
        if (sscanf(s, "%2x", &v) != 1) {
            return -1;
        }
        out[n++] = (uint8_t)v;
        s += 2;
    }
    return n;
}

int main(int argc, char **argv)
{
    uint8_t buf[1024];
    int i, len;

    if (argc >= 2 && strcmp(argv[1], "cmd") == 0 && argc >= 5) {
        lrt_net_command c;
        memset(&c, 0, sizeof c);
        c.seq = (uint32_t)strtoul(argv[2], NULL, 0);
        c.time_ns = strtoull(argv[3], NULL, 0);
        c.n_axes = (uint8_t)atoi(argv[4]);
        if (argc != 7 + 3 * c.n_axes) {
            return 2;
        }
        for (i = 0; i < c.n_axes; i++) {
            c.axes[i].controlword = (uint16_t)strtoul(argv[5 + 3 * i], NULL, 0);
            c.axes[i].mode = (int8_t)atoi(argv[6 + 3 * i]);
            c.axes[i].target_pos = (int32_t)strtol(argv[7 + 3 * i], NULL, 0);
        }
        c.digital_out = (uint32_t)strtoul(argv[5 + 3 * c.n_axes], NULL, 0);
        c.spindle_cmd = strtof(argv[6 + 3 * c.n_axes], NULL);
        len = lrt_net_encode_command(&c, buf);
        if (len < 0) {
            printf("ERR %d\n", len);
            return 1;
        }
        for (i = 0; i < len; i++) {
            printf("%02x", buf[i]);
        }
        printf("\n");
        return 0;
    }
    if (argc == 3 && strcmp(argv[1], "reply") == 0) {
        lrt_net_reply r;
        int rc;
        len = unhex(argv[2], buf, (int)sizeof buf);
        rc = lrt_net_decode_reply(buf, len, 0, &r);
        if (rc != LRT_NET_OK) {
            printf("ERR %d\n", rc);
            return 0;
        }
        printf("seq=%u time=%llu flags=%u din=%u spindle=%.3f lost=%u late=%u jitter=%u\n", r.seq,
               (unsigned long long)r.time_ns, r.flags, r.digital_in, r.spindle_actual,
               r.frames_lost, r.frames_late, r.jitter_us);
        for (i = 0; i < r.n_axes; i++) {
            printf("axis sw=%u mode=%d pos=%d ferr=%d torque=%d err=%u\n", r.axes[i].statusword,
                   r.axes[i].mode_display, r.axes[i].actual_pos, r.axes[i].following_error,
                   r.axes[i].torque, r.axes[i].error_code);
        }
        return 0;
    }
    if (argc == 3 && strcmp(argv[1], "crc") == 0) {
        len = unhex(argv[2], buf, (int)sizeof buf);
        printf("%u\n", lrt_net_crc32(buf, len));
        return 0;
    }
    return 2;
}
