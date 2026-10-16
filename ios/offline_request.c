/* Query-string parameters used by RankingCore -api:paramWithString:.
 * Distinguish absent, empty, malformed and overlong values. No allocation or
 * logging: account fields and full request strings must remain on-device. */
#include <stddef.h>
#include <stdint.h>

static int hex_digit(unsigned char c) {
    if (c >= '0' && c <= '9') return (int)(c - '0');
    if (c >= 'a' && c <= 'f') return (int)(c - 'a') + 10;
    if (c >= 'A' && c <= 'F') return (int)(c - 'A') + 10;
    return -1;
}

/* Nonnegative length on success, -1 if key absent, -2 if malformed or full.
 * Caller supplies the validated bounded length of the whole original request. */
int bf_query_value(const char *query, size_t length, const char *key,
                   char *value, size_t capacity) {
    if (!query || !key || !value || !capacity || length > 4096) return -2;
    for (size_t pos = 0; pos < length;) {
        size_t begin = pos;
        while (pos < length && query[pos] != '&' && query[pos] != '=') ++pos;
        size_t name_end = pos;
        if (pos == length || query[pos] != '=') {
            while (pos < length && query[pos] != '&') ++pos;
            if (pos < length) ++pos;
            continue;
        }
        ++pos;
        size_t start = pos;
        while (pos < length && query[pos] != '&') ++pos;
        size_t end = pos;
        if (pos < length) ++pos;
        size_t i = begin;
        while (i < name_end && *key && query[i] == *key) { ++i; ++key; }
        int matches = i == name_end && !*key;
        key -= i - begin;
        if (!matches) continue;
        size_t written = 0;
        for (i = start; i < end; ++i) {
            unsigned char c = (unsigned char)query[i];
            if (c == '%') {
                if (i + 2 >= end) return -2;
                int hi = hex_digit((unsigned char)query[++i]);
                int lo = hex_digit((unsigned char)query[++i]);
                if (hi < 0 || lo < 0) return -2;
                c = (unsigned char)(hi * 16 + lo);
            } else if (c == '+') {
                c = ' ';
            }
            if (!c || written + 1 >= capacity) return -2;
            value[written++] = (char)c;
        }
        value[written] = 0;
        return (int)written;
    }
    return -1;
}

/* Returns zero only for a complete signed 32-bit decimal value. */
int bf_query_int(const char *query, size_t length, const char *key, int32_t *value) {
    char text[16];
    if (!value) return -2;
    int size = bf_query_value(query, length, key, text, sizeof(text));
    if (size <= 0) return size == -1 ? -1 : -2;
    unsigned index = 0;
    int negative = text[0] == '-';
    if (negative) ++index;
    if (index == (unsigned)size) return -2;
    uint32_t acc = 0;
    const uint32_t tens = 214748364u;
    uint32_t units = negative ? 8u : 7u;
    for (; index < (unsigned)size; ++index) {
        unsigned char c = (unsigned char)text[index];
        if (c < '0' || c > '9') return -2;
        uint32_t digit = (uint32_t)(c - '0');
        if (acc > tens || (acc == tens && digit > units)) return -2;
        acc = acc * 10u + digit;
    }
    *value = negative ? (int32_t)(-(int64_t)acc) : (int32_t)acc;
    return 0;
}
