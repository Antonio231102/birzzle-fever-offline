/* Build-time checked placeholders are replaced only in ignored private output.
 * No historical identifiers, encryption keys, or account values live in Git.
 */
#include "offline_backend.c"

extern void *NSHomeDirectory(void);
extern unsigned char *CC_MD5(const void *, unsigned long, unsigned char *);
extern int CCCrypt(int, int, int, const void *, size_t, const void *,
                   const void *, size_t, void *, size_t, size_t *);
extern void *fopen(const char *, const char *);
extern size_t fread(void *, size_t, size_t, void *);
extern size_t fwrite(const void *, size_t, size_t, void *);
extern int fflush(void *);
extern int fclose(void *);
extern void *dlsym(void *, const char *);
extern void *malloc(size_t);
extern void free(void *);
extern void *objc_msgSend(void *, void *);
/* Local typed thunks keep host function pointers inside the ASLR-sliding
 * appended text. Direct external-function addresses require Mach-O nonlazy
 * symbol pointers that the original app does not bind for this new segment.
 */
static unsigned char *bf_ios_md5(const void *src, unsigned long n, unsigned char *out) {
    return CC_MD5(src, n, out);
}
static int bf_ios_crypt(int op, int alg, int flags, const void *key, size_t key_bytes,
                        const void *iv, const void *src, size_t n, void *out,
                        size_t capacity, size_t *moved) {
    return CCCrypt(op, alg, flags, key, key_bytes, iv, src, n, out, capacity, moved);
}
static void *bf_ios_open(const char *path, const char *mode) { return fopen(path, mode); }
static size_t bf_ios_read(void *p, size_t size, size_t count, void *file) {
    return fread(p, size, count, file);
}
static size_t bf_ios_write(const void *p, size_t size, size_t count, void *file) {
    return fwrite(p, size, count, file);
}
static int bf_ios_flush(void *file) { return fflush(file); }
static int bf_ios_close(void *file) { return fclose(file); }
static void *bf_ios_symbol(void *scope, const char *name) { return dlsym(scope, name); }
static void *bf_ios_alloc(size_t n) { return malloc(n); }
static void bf_ios_free(void *p) { free(p); }
#define BF_THUMB_HOST(field, function) \
    ((__typeof__(((BFContext *)0)->host.field))((uintptr_t)(function) | 1u))

static int bf_device_setup(BFContext *ctx, void *utf8_selector) {
    if (!ctx || !utf8_selector) return 0;
    if (ctx->host.md5) return 1;
    void *home = NSHomeDirectory();
    const char *directory = (const char *)objc_msgSend(home, utf8_selector);
    if (!directory || !bf_path(ctx->path, sizeof(ctx->path), directory,
                               "/Documents/birzzle-offline-v1.dat")) return 0;
    ctx->state_path = ctx->path;
    ctx->incoming_key = (const unsigned char *)"@BF_KEY@";
    ctx->buy_template = "@BF_BUY@";
    ctx->set_template = "@BF_SET@";
    ctx->login_template = "@BF_LOGIN@";
    ctx->inventory_template = "@BF_INVENTORY@";
    ctx->pocket_template = "@BF_POCKET@";
    ctx->ranking_template = "@BF_RANKING@";
    ctx->initial.magic = BF_MAGIC;
    ctx->initial.version = BF_VERSION;
    ctx->initial.coin = @BF_COIN@;
    ctx->initial.gem = @BF_GEM@;
    ctx->initial.heart = @BF_HEART@;
    ctx->initial.exp = @BF_EXP@;
    ctx->initial.tropy = @BF_TROPY@;
    ctx->host.crypt = BF_THUMB_HOST(crypt, bf_ios_crypt);
    ctx->host.fopen = BF_THUMB_HOST(fopen, bf_ios_open);
    ctx->host.fread = BF_THUMB_HOST(fread, bf_ios_read);
    ctx->host.fwrite = BF_THUMB_HOST(fwrite, bf_ios_write);
    ctx->host.fflush = BF_THUMB_HOST(fflush, bf_ios_flush);
    ctx->host.fclose = BF_THUMB_HOST(fclose, bf_ios_close);
    ctx->host.dlsym = BF_THUMB_HOST(dlsym, bf_ios_symbol);
    ctx->host.malloc = BF_THUMB_HOST(malloc, bf_ios_alloc);
    ctx->host.free = BF_THUMB_HOST(free, bf_ios_free);
    ctx->host.md5 = BF_THUMB_HOST(md5, bf_ios_md5);
    return 1;
}

/* Called before original remote request; never sends or changes archived data. */
void bf_ios_request(BFContext *ctx, uint32_t id, const char *api,
                    void *params_object, void *utf8_selector) {
    if (!ctx || !api || id < 2 || id >= 64
            || !bf_device_setup(ctx, utf8_selector)) return;
    const char *wire = bf_read_response(ctx, id, api);
    if (!wire && id >= 10) {
        const char *params = params_object
            ? (const char *)objc_msgSend(params_object, utf8_selector) : "";
        if (!params) return;
        size_t length = bf_length(params, 4097);
        if (length > 4096) return;
        wire = bf_mutation_response(ctx, id, api, params, length);
    }
    if (!wire) return;
    size_t count = bf_length(wire, BF_WIRE_BYTES);
    if (count == BF_WIRE_BYTES) return;
    char *copy = (char *)ctx->host.malloc(count + 1);
    if (!copy) return;
    if (!bf_copy(copy, count + 1, wire, count)) {
        ctx->host.free(copy);
        return;
    }
    if (ctx->queued[id]) ctx->host.free(ctx->queued[id]);
    ctx->queued[id] = copy;
}

const char *bf_ios_reply(BFContext *ctx, uint32_t id) {
    return ctx && id < 64 ? ctx->queued[id] : 0;
}

/* Only a frame allocated for a recognized offline request may use the
 * independently authenticated pre-/post-login archived token. Unknown live
 * responses keep the original app's strcmp result unchanged.
 */
int bf_ios_token_kind(const BFContext *ctx, const char *wire) {
    if (!ctx || !wire) return 0;
    for (uint32_t id = 2; id < 64; ++id) {
        if (ctx->queued[id] == wire) return id == 2 ? 1 : 2;
    }
    return 0;
}
