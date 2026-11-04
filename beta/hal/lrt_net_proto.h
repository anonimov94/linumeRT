/* SPDX-License-Identifier: GPL-2.0-or-later */
/* linumeRT - protokol LRT-NET v1 (docs/PLANT.md §3): CRC32 i pakowanie ramek.
 * Model-Author: Claude · sesja 017
 *
 * Wspolny dla komponentu hal/lrt_net.comp i testow bez LinuxCNC (hal/tests/test_lrt_net_proto.c).
 * Tylko funkcje statyczne na buforach wywolujacego: bez alokacji, bez I/O, bez libc poza
 * typami calkowitymi i memcpy (dozwolone w RT, CLAUDE.md §5). Little-endian jawnie, bajt po bajcie.
 */
#ifndef LRT_NET_PROTO_H
#define LRT_NET_PROTO_H

#include <stdint.h>
#include <string.h>

#define LRT_NET_MAGIC 0x524Cu
#define LRT_NET_VERSION 1u
#define LRT_NET_TYPE_COMMAND 1u
#define LRT_NET_TYPE_REPLY 2u
#define LRT_NET_PORT 47700
#define LRT_NET_MAX_AXES 8
#define LRT_NET_HEADER 20
#define LRT_NET_CMD_SIZE(n) (32 + 8 * (n))
#define LRT_NET_REPLY_SIZE(n) (44 + 16 * (n))
#define LRT_NET_MAX_FRAME LRT_NET_REPLY_SIZE(LRT_NET_MAX_AXES)

/* flagi naglowka */
#define LRT_NET_FLAG_RESET_STATS 0x01u   /* master: zeruj statystyki Plant */
#define LRT_NET_FLAG_DRIVE_FAULT 0x01u   /* plant: fault ktoregos napedu */
#define LRT_NET_FLAG_ESTOP_OPEN 0x02u    /* plant: petla E-STOP otwarta */

/* bledy dekodowania */
#define LRT_NET_OK 0
#define LRT_NET_ERR_SIZE -1
#define LRT_NET_ERR_MAGIC -2
#define LRT_NET_ERR_VERSION -3
#define LRT_NET_ERR_TYPE -4
#define LRT_NET_ERR_AXES -5
#define LRT_NET_ERR_CRC -6

typedef struct {
    uint16_t controlword;
    int8_t mode;
    int32_t target_pos;
} lrt_net_cmd_axis;

typedef struct {
    uint32_t seq;
    uint64_t time_ns;
    uint8_t n_axes;
    uint8_t flags;
    lrt_net_cmd_axis axes[LRT_NET_MAX_AXES];
    uint32_t digital_out;
    float spindle_cmd;
} lrt_net_command;

typedef struct {
    uint16_t statusword;
    int8_t mode_display;
    int32_t actual_pos;
    int32_t following_error;
    int16_t torque;
    uint16_t error_code;
} lrt_net_reply_axis;

typedef struct {
    uint32_t seq;
    uint64_t time_ns;
    uint8_t n_axes;
    uint8_t flags;
    lrt_net_reply_axis axes[LRT_NET_MAX_AXES];
    uint32_t digital_in;
    float spindle_actual;
    uint32_t frames_lost;
    uint32_t frames_late;
    uint32_t jitter_us;
} lrt_net_reply;

/* CRC32 IEEE 802.3 (jak zlib.crc32), bitowo: bez tablicy i bez inicjalizacji. */
static inline uint32_t lrt_net_crc32(const uint8_t *p, int n)
{
    uint32_t crc = 0xFFFFFFFFu;
    int i, k;

    for (i = 0; i < n; i++) {
        crc ^= p[i];
        for (k = 0; k < 8; k++) {
            crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
        }
    }
    return ~crc;
}

static inline void lrt_net_put16(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}

static inline void lrt_net_put32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static inline void lrt_net_put64(uint8_t *p, uint64_t v)
{
    lrt_net_put32(p, (uint32_t)v);
    lrt_net_put32(p + 4, (uint32_t)(v >> 32));
}

static inline uint16_t lrt_net_get16(const uint8_t *p)
{
    return (uint16_t)(p[0] | (p[1] << 8));
}

static inline uint32_t lrt_net_get32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static inline uint64_t lrt_net_get64(const uint8_t *p)
{
    return (uint64_t)lrt_net_get32(p) | ((uint64_t)lrt_net_get32(p + 4) << 32);
}

static inline uint32_t lrt_net_float_bits(float f)
{
    uint32_t u;
    memcpy(&u, &f, sizeof u);
    return u;
}

static inline float lrt_net_bits_float(uint32_t u)
{
    float f;
    memcpy(&f, &u, sizeof f);
    return f;
}

static inline void lrt_net_put_header(uint8_t *p, uint8_t type, uint32_t seq, uint64_t time_ns,
                                      uint8_t n_axes, uint8_t flags)
{
    lrt_net_put16(p, LRT_NET_MAGIC);
    p[2] = LRT_NET_VERSION;
    p[3] = type;
    lrt_net_put32(p + 4, seq);
    lrt_net_put64(p + 8, time_ns);
    p[16] = n_axes;
    p[17] = flags;
    lrt_net_put16(p + 18, 0);
}

/* Ramka master->plant do `buf` (>= LRT_NET_CMD_SIZE(n_axes)). Zwraca dlugosc albo blad < 0. */
static inline int lrt_net_encode_command(const lrt_net_command *c, uint8_t *buf)
{
    int i, off = LRT_NET_HEADER, n = c->n_axes;

    if (n < 1 || n > LRT_NET_MAX_AXES) {
        return LRT_NET_ERR_AXES;
    }
    lrt_net_put_header(buf, LRT_NET_TYPE_COMMAND, c->seq, c->time_ns, (uint8_t)n, c->flags);
    for (i = 0; i < n; i++, off += 8) {
        lrt_net_put16(buf + off, c->axes[i].controlword);
        buf[off + 2] = (uint8_t)c->axes[i].mode;
        buf[off + 3] = 0;
        lrt_net_put32(buf + off + 4, (uint32_t)c->axes[i].target_pos);
    }
    lrt_net_put32(buf + off, c->digital_out);
    lrt_net_put32(buf + off + 4, lrt_net_float_bits(c->spindle_cmd));
    off += 8;
    lrt_net_put32(buf + off, lrt_net_crc32(buf, off));
    return off + 4;
}

/* Ramka plant->master do `buf` (dla testow i atrap Plant w C). */
static inline int lrt_net_encode_reply(const lrt_net_reply *r, uint8_t *buf)
{
    int i, off = LRT_NET_HEADER, n = r->n_axes;

    if (n < 1 || n > LRT_NET_MAX_AXES) {
        return LRT_NET_ERR_AXES;
    }
    lrt_net_put_header(buf, LRT_NET_TYPE_REPLY, r->seq, r->time_ns, (uint8_t)n, r->flags);
    for (i = 0; i < n; i++, off += 16) {
        const lrt_net_reply_axis *a = &r->axes[i];
        lrt_net_put16(buf + off, a->statusword);
        buf[off + 2] = (uint8_t)a->mode_display;
        buf[off + 3] = 0;
        lrt_net_put32(buf + off + 4, (uint32_t)a->actual_pos);
        lrt_net_put32(buf + off + 8, (uint32_t)a->following_error);
        lrt_net_put16(buf + off + 12, (uint16_t)a->torque);
        lrt_net_put16(buf + off + 14, a->error_code);
    }
    lrt_net_put32(buf + off, r->digital_in);
    lrt_net_put32(buf + off + 4, lrt_net_float_bits(r->spindle_actual));
    lrt_net_put32(buf + off + 8, r->frames_lost);
    lrt_net_put32(buf + off + 12, r->frames_late);
    lrt_net_put32(buf + off + 16, r->jitter_us);
    off += 20;
    lrt_net_put32(buf + off, lrt_net_crc32(buf, off));
    return off + 4;
}

/* Wspolna kontrola naglowka, dlugosci i CRC. */
static inline int lrt_net_check(const uint8_t *buf, int len, uint8_t type, int expect_axes)
{
    int n;

    if (len < LRT_NET_HEADER + 4) {
        return LRT_NET_ERR_SIZE;
    }
    if (lrt_net_get16(buf) != LRT_NET_MAGIC) {
        return LRT_NET_ERR_MAGIC;
    }
    if (buf[2] != LRT_NET_VERSION) {
        return LRT_NET_ERR_VERSION;
    }
    if (buf[3] != type) {
        return LRT_NET_ERR_TYPE;
    }
    n = buf[16];
    if (n < 1 || n > LRT_NET_MAX_AXES || (expect_axes > 0 && n != expect_axes)) {
        return LRT_NET_ERR_AXES;
    }
    if (len != (type == LRT_NET_TYPE_REPLY ? LRT_NET_REPLY_SIZE(n) : LRT_NET_CMD_SIZE(n))) {
        return LRT_NET_ERR_SIZE;
    }
    if (lrt_net_get32(buf + len - 4) != lrt_net_crc32(buf, len - 4)) {
        return LRT_NET_ERR_CRC;
    }
    return n;
}

/* Dekoduje odpowiedz plant->master. expect_axes > 0: inna liczba osi = blad. */
static inline int lrt_net_decode_reply(const uint8_t *buf, int len, int expect_axes,
                                       lrt_net_reply *r)
{
    int i, off = LRT_NET_HEADER;
    int n = lrt_net_check(buf, len, LRT_NET_TYPE_REPLY, expect_axes);

    if (n < 0) {
        return n;
    }
    r->seq = lrt_net_get32(buf + 4);
    r->time_ns = lrt_net_get64(buf + 8);
    r->n_axes = (uint8_t)n;
    r->flags = buf[17];
    for (i = 0; i < n; i++, off += 16) {
        lrt_net_reply_axis *a = &r->axes[i];
        a->statusword = lrt_net_get16(buf + off);
        a->mode_display = (int8_t)buf[off + 2];
        a->actual_pos = (int32_t)lrt_net_get32(buf + off + 4);
        a->following_error = (int32_t)lrt_net_get32(buf + off + 8);
        a->torque = (int16_t)lrt_net_get16(buf + off + 12);
        a->error_code = lrt_net_get16(buf + off + 14);
    }
    r->digital_in = lrt_net_get32(buf + off);
    r->spindle_actual = lrt_net_bits_float(lrt_net_get32(buf + off + 4));
    r->frames_lost = lrt_net_get32(buf + off + 8);
    r->frames_late = lrt_net_get32(buf + off + 12);
    r->jitter_us = lrt_net_get32(buf + off + 16);
    return LRT_NET_OK;
}

/* Dekoduje ramke master->plant (testy, atrapy). */
static inline int lrt_net_decode_command(const uint8_t *buf, int len, lrt_net_command *c)
{
    int i, off = LRT_NET_HEADER;
    int n = lrt_net_check(buf, len, LRT_NET_TYPE_COMMAND, 0);

    if (n < 0) {
        return n;
    }
    c->seq = lrt_net_get32(buf + 4);
    c->time_ns = lrt_net_get64(buf + 8);
    c->n_axes = (uint8_t)n;
    c->flags = buf[17];
    for (i = 0; i < n; i++, off += 8) {
        c->axes[i].controlword = lrt_net_get16(buf + off);
        c->axes[i].mode = (int8_t)buf[off + 2];
        c->axes[i].target_pos = (int32_t)lrt_net_get32(buf + off + 4);
    }
    c->digital_out = lrt_net_get32(buf + off);
    c->spindle_cmd = lrt_net_bits_float(lrt_net_get32(buf + off + 4));
    return LRT_NET_OK;
}

/* Roznica numerow ramek z zawinieciem u32: > 0 nowsza, <= 0 starsza lub ta sama. */
static inline int32_t lrt_net_seq_delta(uint32_t now, uint32_t last)
{
    return (int32_t)(now - last);
}

#endif /* LRT_NET_PROTO_H */
