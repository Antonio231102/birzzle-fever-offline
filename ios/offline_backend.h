#ifndef BIRZZLE_IOS_OFFLINE_BACKEND_H
#define BIRZZLE_IOS_OFFLINE_BACKEND_H

#include <stddef.h>
#include <stdint.h>

enum { BF_MAX_PETS = 10, BF_TRANSACTION_BYTES = 64, BF_JSON_BYTES = 4096,
       BF_WIRE_BYTES = 6144 };

typedef struct {
    uint32_t magic;
    uint32_t version;
    int32_t coin, gem, heart, exp, tropy, stage, playcount, playcount_stage;
    uint32_t owned_mask;
    uint8_t ability[BF_MAX_PETS];
    char transaction[BF_MAX_PETS][BF_TRANSACTION_BYTES];
    unsigned char seen_pocket_sets[16][16];
    uint32_t next_seen_slot;
    unsigned char digest[16];
} BFState;

typedef struct {
    unsigned char *(*md5)(const void *, unsigned long, unsigned char *);
    int (*crypt)(int, int, int, const void *, size_t, const void *,
                 const void *, size_t, void *, size_t, size_t *);
    void *(*fopen)(const char *, const char *);
    size_t (*fread)(void *, size_t, size_t, void *);
    size_t (*fwrite)(const void *, size_t, size_t, void *);
    int (*fflush)(void *);
    int (*fclose)(void *);
    void *(*dlsym)(void *, const char *);
    void *(*malloc)(size_t);
    void (*free)(void *);
} BFHost;

typedef struct {
    BFHost host;
    const char *state_path; /* App-private Documents path, not historical account. */
    const unsigned char *incoming_key;
    const char *buy_template;
    const char *set_template;
    const char *login_template;
    const char *inventory_template;
    const char *pocket_template;
    const char *ranking_template;
    BFState initial;
    BFState current;
    unsigned initialized;
    char *arena; /* One retained bounded allocation, freed on app shutdown. */
    char path[512]; /* Sandboxed mutable state; never an archived backup path. */
    char *queued[64]; /* Per-ID owned frames survive overlapping callbacks. */
} BFContext;

int bf_query_value(const char *query, size_t length, const char *key,
                   char *value, size_t capacity);
int bf_query_int(const char *query, size_t length, const char *key, int32_t *value);
const char *bf_mutation_response(BFContext *context, uint32_t request_id,
                                 const char *api, const char *params,
                                 size_t params_length);
const char *bf_read_response(BFContext *context, uint32_t request_id,
                             const char *api);
void bf_release(BFContext *context);

#endif
