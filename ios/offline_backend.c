/* Original iOS 6 gameplay mutations: no remote service and no archive writes.
 * The caller supplies checked historical reply JSON, the original inbound AES
 * key, sandboxed state path and pointers to the app's already-imported APIs.
 */
#include "offline_backend.h"
#include "offline_request.c"

#define BF_MAGIC 0x4246494fu
#define BF_VERSION 1u
#define BF_PLAIN_BYTES (BF_JSON_BYTES + 48u)
#define BF_ARENA_BYTES (BF_PLAIN_BYTES + BF_WIRE_BYTES)

static size_t bf_length(const char *s, size_t bound) {
    size_t n = 0;
    if (!s) return bound;
    while (n < bound && s[n]) ++n;
    return n;
}

static int bf_equal(const char *a, const char *b) {
    if (!a || !b) return 0;
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}

static int bf_copy(char *dst, size_t capacity, const char *src, size_t count) {
    if (count >= capacity) return 0;
    for (size_t i = 0; i < count; ++i) dst[i] = src[i];
    dst[count] = 0;
    return 1;
}

static int bf_decimal(char *dst, size_t capacity, int32_t number) {
    char reversed[12];
    uint32_t magnitude = number < 0 ? (uint32_t)(-(int64_t)number) : (uint32_t)number;
    size_t n = 0;
    do {
        uint32_t quotient = magnitude / 10u;
        reversed[n++] = (char)('0' + magnitude - quotient * 10u);
        magnitude = quotient;
    } while (magnitude);
    if (number < 0) reversed[n++] = '-';
    if (n >= capacity) return 0;
    for (size_t i = 0; i < n; ++i) dst[i] = reversed[n - i - 1];
    dst[n] = 0;
    return 1;
}

static int bf_patch(char *json, size_t capacity, const char *key,
                    const char *value) {
    size_t length = bf_length(json, capacity);
    size_t key_length = bf_length(key, 64);
    size_t value_length = bf_length(value, 128);
    if (length == capacity || !key_length || key_length == 64 || value_length == 128)
        return 0;
    size_t start = capacity;
    for (size_t pos = 0; pos + key_length + 4 < length; ++pos) {
        if (json[pos] != '"') continue;
        size_t j = 0;
        while (j < key_length && json[pos + 1 + j] == key[j]) ++j;
        if (j != key_length || json[pos + j + 1] != '"'
                || json[pos + j + 2] != ':') continue;
        if (json[pos + j + 3] != '"') return 0;
        if (start != capacity) return 0; /* ambiguous duplicated mutable key */
        start = pos + j + 4;
    }
    if (start == capacity) return 0;
    size_t end = start;
    for (; end < length; ++end) {
        if (json[end] == '\\') { ++end; continue; }
        if (json[end] == '"') break;
    }
    if (end == length) return 0;
    char escaped[256];
    size_t encoded = 0;
    for (size_t i = 0; i < value_length; ++i) {
        unsigned char c = (unsigned char)value[i];
        if (c < 32) return 0;
        if (c == '\\' || c == '"') {
            if (encoded + 2 >= sizeof(escaped)) return 0;
            escaped[encoded++] = '\\';
        } else if (encoded + 1 >= sizeof(escaped)) return 0;
        escaped[encoded++] = (char)c;
    }
    size_t tail = length - end + 1; /* includes closing quote and NUL */
    if (start + encoded + tail > capacity) return 0;
    if (encoded > end - start) {
        for (size_t i = tail; i-- > 0;) json[start + encoded + i] = json[end + i];
    } else {
        for (size_t i = 0; i < tail; ++i) json[start + encoded + i] = json[end + i];
    }
    for (size_t i = 0; i < encoded; ++i) json[start + i] = escaped[i];
    return 1;
}

static int bf_patch_number(char *json, const char *key, int32_t number) {
    char decimal[16];
    return bf_decimal(decimal, sizeof(decimal), number)
        && bf_patch(json, BF_JSON_BYTES, key, decimal);
}

static int bf_path(char *dest, size_t cap, const char *base, const char *suffix) {
    size_t a = bf_length(base, cap), b = bf_length(suffix, cap);
    if (a >= cap || b >= cap || a + b >= cap) return 0;
    for (size_t i = 0; i < a; ++i) dest[i] = base[i];
    for (size_t i = 0; i < b; ++i) dest[a + i] = suffix[i];
    dest[a + b] = 0;
    return 1;
}

static int bf_state_valid(BFContext *ctx, BFState *state) {
    unsigned char digest[16];
    if (state->magic != BF_MAGIC || state->version != BF_VERSION
            || !ctx->host.md5(state, offsetof(BFState, digest), digest)) return 0;
    for (unsigned i = 0; i < sizeof(digest); ++i)
        if (digest[i] != state->digest[i]) return 0;
    return 1;
}

static int bf_load(BFContext *ctx) {
    if (ctx->initialized) return ctx->initialized == 1;
    if (!ctx->state_path || !ctx->host.fopen || !ctx->host.fread
            || !ctx->host.fclose || !ctx->host.md5 || !ctx->host.dlsym)
        return 0;
    void *file = ctx->host.fopen(ctx->state_path, "rb");
    if (!file) {
        int *(*last_error)(void) = (int *(*)(void))ctx->host.dlsym((void *)-2, "__error");
        if (!last_error || *last_error() != 2 || ctx->initial.magic != BF_MAGIC
                || ctx->initial.version != BF_VERSION) return 0;
        ctx->current = ctx->initial;
    } else {
        BFState loaded;
        size_t read_count = ctx->host.fread(&loaded, sizeof(loaded), 1, file);
        int closed = ctx->host.fclose(file);
        if (read_count != 1 || closed || !bf_state_valid(ctx, &loaded)) return 0;
        ctx->current = loaded;
    }
    ctx->initialized = 1;
    return 1;
}

static int bf_save(BFContext *ctx, BFState *next) {
    char temporary[512];
    if (!bf_path(temporary, sizeof(temporary), ctx->state_path, ".tmp")
            || !ctx->host.fopen || !ctx->host.fwrite || !ctx->host.fflush
            || !ctx->host.fclose || !ctx->host.dlsym) return 0;
    if (!ctx->host.md5(next, offsetof(BFState, digest), next->digest)) return 0;
    void *file = ctx->host.fopen(temporary, "wb");
    if (!file) return 0;
    int success = ctx->host.fwrite(next, sizeof(*next), 1, file) == 1;
    if (ctx->host.fflush(file)) success = 0;
    int (*fileno_fn)(void *) = (int (*)(void *))ctx->host.dlsym((void *)-2, "fileno");
    int (*fsync_fn)(int) = (int (*)(int))ctx->host.dlsym((void *)-2, "fsync");
    if (!fileno_fn || !fsync_fn || fsync_fn(fileno_fn(file))) success = 0;
    if (ctx->host.fclose(file)) success = 0;
    int (*rename_fn)(const char *, const char *) =
        (int (*)(const char *, const char *))ctx->host.dlsym((void *)-2, "rename");
    if (!success || !rename_fn || rename_fn(temporary, ctx->state_path)) return 0;
    ctx->current = *next;
    return 1;
}

static int bf_render_buy(BFState *next, const char *params, size_t length, uint32_t id,
                         char *json) {
    int32_t pet, ability;
    char transaction[BF_TRANSACTION_BYTES], number[16];
    if (bf_query_int(params, length, "itemid", &pet) || pet < 0 || pet >= BF_MAX_PETS
            || bf_query_int(params, length, "ability", &ability)
            || ability < 0 || ability > 100
            || bf_query_value(params, length, "tid", transaction,
                              sizeof(transaction)) <= 0) return 0;
    /* The game can repeat a purchase after a restored session with a new
     * transaction ID. Ownership, not a transport-generated ID, defines the
     * idempotent item; retain the first purchase in app-private state.
     */
    if ((next->owned_mask & (1u << pet))
            && next->ability[pet] != (uint8_t)ability) return 0;
    size_t transaction_length = bf_length(transaction, sizeof(transaction));
    for (size_t i = 0; i < transaction_length; ++i) {
        unsigned char c = (unsigned char)transaction[i];
        if (!(c >= '0' && c <= '9') && !(c >= 'A' && c <= 'Z')
                && !(c >= 'a' && c <= 'z') && c != '-' && c != '_' && c != '.') return 0;
    }
    if (!(next->owned_mask & (1u << pet))) {
        if (!bf_copy(next->transaction[pet], BF_TRANSACTION_BYTES,
                     transaction, transaction_length)) return 0;
        next->ability[pet] = (uint8_t)ability;
        next->owned_mask |= 1u << pet;
    }
    if (!bf_decimal(number, sizeof(number), (int32_t)id)
            || !bf_patch(json, BF_JSON_BYTES, "commandid", number)
            || !bf_patch_number(json, "itemid", pet)
            || !bf_patch_number(json, "ability", ability)
            || !bf_patch(json, BF_JSON_BYTES, "tid", transaction)) return 0;
    return 1;
}

static int bf_add(int32_t *number, int32_t delta) {
    int64_t result = (int64_t)*number + delta;
    if (result < 0 || result > 2147483647ll) return 0;
    *number = (int32_t)result;
    return 1;
}

static int bf_render_set(BFContext *ctx, BFState *next,
                         const char *params, size_t length, uint32_t id,
                         char *json) {
    int32_t coin, gem, heart, exp, score, stage;
    char extra[128], decimal[16];
    if (bf_query_int(params, length, "coin", &coin)
            || bf_query_int(params, length, "gem", &gem)
            || bf_query_int(params, length, "heart", &heart)
            || bf_query_int(params, length, "exp", &exp)
            || bf_query_int(params, length, "tropy", &score)
            || bf_query_int(params, length, "stage", &stage)
            || bf_query_value(params, length, "extradata", extra, sizeof(extra)) < 0
            || stage < -1 || score < 0) return 0;
    unsigned char request_digest[16];
    if (!ctx->host.md5(params, (unsigned long)length, request_digest)) return 0;
    int seen = 0;
    for (unsigned slot = 0; slot < 16; ++slot) {
        unsigned matches = 1;
        for (unsigned byte = 0; byte < 16; ++byte)
            matches &= next->seen_pocket_sets[slot][byte] == request_digest[byte];
        seen |= matches;
    }
    if (!seen) {
        if (!bf_add(&next->coin, coin) || !bf_add(&next->gem, gem)
                || !bf_add(&next->heart, heart) || !bf_add(&next->exp, exp))
            return 0;
        if (score > next->tropy) next->tropy = score;
        if (stage > next->stage) next->stage = stage;
        if (bf_equal(extra, "GameStart")) {
            if (next->playcount == 2147483647) return 0;
            ++next->playcount;
        }
        unsigned slot = next->next_seen_slot % 16;
        for (unsigned byte = 0; byte < 16; ++byte)
            next->seen_pocket_sets[slot][byte] = request_digest[byte];
        ++next->next_seen_slot;
    }
    if (!bf_decimal(decimal, sizeof(decimal), (int32_t)id)
            || !bf_patch(json, BF_JSON_BYTES, "commandid", decimal)
            || !bf_patch(json, BF_JSON_BYTES, "extradata", extra)
            || !bf_patch_number(json, "coin", next->coin)
            || !bf_patch_number(json, "gem", next->gem)
            || !bf_patch_number(json, "heart", next->heart)
            || !bf_patch_number(json, "exp", next->exp)
            || !bf_patch_number(json, "tropy", next->tropy)
            || !bf_patch_number(json, "playcount", next->playcount)) return 0;
    return 1;
}
static char *bf_encode(BFContext *ctx, char *json) {
    static const char hex[] = "0123456789abcdef";
    static const char base64[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    unsigned char digest[16];
    size_t length = bf_length(json, BF_JSON_BYTES);
    if (!length || length == BF_JSON_BYTES
            || !ctx->host.md5(json, length, digest) || !ctx->host.crypt
            || !ctx->incoming_key) return 0;
    unsigned char *plain = (unsigned char *)json - 32;
    for (size_t i = 0; i < 16; ++i) {
        plain[i * 2] = hex[digest[i] >> 4];
        plain[i * 2 + 1] = hex[digest[i] & 15];
    }
    size_t encrypted = 0;
    size_t body = 32 + length;
    unsigned char pad = (unsigned char)(16 - body % 16);
    if (body + pad > BF_PLAIN_BYTES) return 0;
    for (size_t i = 0; i < pad; ++i) plain[body + i] = pad;
    if (ctx->host.crypt(0, 0, 2, ctx->incoming_key, 16, 0, plain,
                        body + pad, plain, BF_PLAIN_BYTES, &encrypted)
            || !encrypted || encrypted % 16 || (encrypted + 2) / 3 * 4 + 2 > BF_WIRE_BYTES)
        return 0;
    char *wire = ctx->arena + BF_PLAIN_BYTES;
    size_t out = 0;
    wire[out++] = '0'; /* original C++ receiver strips exactly one byte */
    for (size_t i = 0; i < encrypted; i += 3) {
        uint32_t value = (uint32_t)plain[i] << 16;
        if (i + 1 < encrypted) value |= (uint32_t)plain[i + 1] << 8;
        if (i + 2 < encrypted) value |= plain[i + 2];
        wire[out++] = base64[(value >> 18) & 63];
        wire[out++] = base64[(value >> 12) & 63];
        wire[out++] = i + 1 < encrypted ? base64[(value >> 6) & 63] : '=';
        wire[out++] = i + 2 < encrypted ? base64[value & 63] : '=';
    }
    wire[out] = 0;
    return wire;
}
static int bf_append(char *dst, size_t capacity, size_t *used, const char *value) {
    size_t n = bf_length(value, capacity);
    if (n == capacity || n >= capacity - *used) return 0;
    for (size_t i = 0; i < n; ++i) dst[*used + i] = value[i];
    *used += n;
    dst[*used] = 0;
    return 1;
}

static int bf_render_inventory(BFContext *ctx, char *json, const char *field) {
    if (!ctx->current.owned_mask) return 1;
    char marker[32] = "\"";
    size_t used = 1;
    if (!bf_append(marker, sizeof(marker), &used, field)
            || !bf_append(marker, sizeof(marker), &used, "\":[")) return 0;
    size_t length = bf_length(json, BF_JSON_BYTES);
    size_t marker_length = bf_length(marker, sizeof(marker));
    size_t start = length;
    for (size_t i = 0; i + marker_length < length; ++i) {
        size_t n = 0;
        while (n < marker_length && json[i + n] == marker[n]) ++n;
        if (n == marker_length) {
            if (start != length) return 0;
            start = i + marker_length;
        }
    }
    if (start == length || json[start] != '{') return 0;
    size_t end = start;
    while (end < length && json[end] != ']') ++end;
    if (end >= length || end - start > 256) return 0;
    char original[257];
    if (!bf_copy(original, sizeof(original), json + start, end - start)
            || !bf_equal(original, "{\"ability\":\"0\",\"itemid\":\"\",\"odr\":\"0\",\"tid\":\"0\"}"))
        return 0;
    char entries[1200] = "";
    size_t count = 0, size = 0;
    for (unsigned pet = 0; pet < BF_MAX_PETS; ++pet) {
        if (!(ctx->current.owned_mask & (1u << pet))) continue;
        char number[16];
        if ((count && !bf_append(entries, sizeof(entries), &size, ","))
                || !bf_append(entries, sizeof(entries), &size, "{\"ability\":\"")
                || !bf_decimal(number, sizeof(number), ctx->current.ability[pet])
                || !bf_append(entries, sizeof(entries), &size, number)
                || !bf_append(entries, sizeof(entries), &size, "\",\"itemid\":\"")
                || !bf_decimal(number, sizeof(number), (int32_t)pet)
                || !bf_append(entries, sizeof(entries), &size, number)
                || !bf_append(entries, sizeof(entries), &size, "\",\"odr\":\"")
                || !bf_decimal(number, sizeof(number), (int32_t)count)
                || !bf_append(entries, sizeof(entries), &size, number)
                || !bf_append(entries, sizeof(entries), &size, "\",\"tid\":\"")
                || !bf_append(entries, sizeof(entries), &size, ctx->current.transaction[pet])
                || !bf_append(entries, sizeof(entries), &size, "\"}")) return 0;
        ++count;
    }
    size_t tail = length - end + 1;
    if (start + size + tail > BF_JSON_BYTES) return 0;
    if (size > end - start) {
        for (size_t i = tail; i-- > 0;) json[start + size + i] = json[end + i];
    } else {
        for (size_t i = 0; i < tail; ++i) json[start + size + i] = json[end + i];
    }
    for (size_t i = 0; i < size; ++i) json[start + i] = entries[i];
    return 1;
}

const char *bf_read_response(BFContext *ctx, uint32_t id, const char *api) {
    if (!ctx || !api || !bf_load(ctx) || !ctx->host.malloc) return 0;
    const char *source = 0, *inventory_field = 0;
    if (bf_equal(api, "pocket.login") && id == 2) {
        source = ctx->login_template;
        inventory_field = "inventory";
    } else if (bf_equal(api, "inventory.list") && id == 3) {
        source = ctx->inventory_template;
        inventory_field = "inven";
    } else if (bf_equal(api, "pocket.get") && (id == 5 || id == 7)) {
        source = ctx->pocket_template;
    } else if (bf_equal(api, "score.ranking") && id == 9) {
        source = ctx->ranking_template;
    } else {
        return 0;
    }
    if (!ctx->arena) ctx->arena = (char *)ctx->host.malloc(BF_ARENA_BYTES);
    if (!ctx->arena) return 0;
    size_t length = bf_length(source, BF_JSON_BYTES);
    char *json = ctx->arena + 32;
    if (length == BF_JSON_BYTES || !bf_copy(json, BF_JSON_BYTES, source, length)
            || !bf_patch_number(json, "commandid", (int32_t)id)
            || (inventory_field && !bf_render_inventory(ctx, json, inventory_field)))
        return 0;
    if (bf_equal(api, "pocket.get")) {
        if (!bf_patch_number(json, "coin", ctx->current.coin)
                || !bf_patch_number(json, "gem", ctx->current.gem)
                || !bf_patch_number(json, "heart", ctx->current.heart)
                || !bf_patch_number(json, "exp", ctx->current.exp)
                || !bf_patch_number(json, "tropy", ctx->current.tropy)
                || !bf_patch_number(json, "playcount", ctx->current.playcount))
            return 0;
    }
    return bf_encode(ctx, json);
}

const char *bf_mutation_response(BFContext *ctx, uint32_t id,
                                 const char *api, const char *params,
                                 size_t params_length) {
    if (!ctx || id < 10 || id > 9999 || !params || params_length > 4096
            || !bf_load(ctx) || !ctx->host.malloc || !ctx->host.free) return 0;
    if (!ctx->arena) ctx->arena = (char *)ctx->host.malloc(BF_ARENA_BYTES);
    if (!ctx->arena) return 0;
    int buy = bf_equal(api, "inventory.buy");
    int set = bf_equal(api, "pocket.set");
    if (!buy && !set) return 0;
    const char *template = buy ? ctx->buy_template : ctx->set_template;
    size_t original_size = bf_length(template, BF_JSON_BYTES);
    char *json = ctx->arena + 32;
    if (original_size == BF_JSON_BYTES
            || !bf_copy(json, BF_JSON_BYTES, template, original_size)
            || !bf_patch(json, BF_JSON_BYTES, "timeout", "0")) return 0;
    BFState next = ctx->current;
    if (!(buy ? bf_render_buy(&next, params, params_length, id, json)
              : bf_render_set(ctx, &next, params, params_length, id, json))) return 0;
    char *wire = bf_encode(ctx, json);
    if (!wire || !bf_save(ctx, &next)) return 0;
    return wire;
}

void bf_release(BFContext *ctx) {
    if (ctx && ctx->arena && ctx->host.free) ctx->host.free(ctx->arena);
    if (ctx) ctx->arena = 0;
}
