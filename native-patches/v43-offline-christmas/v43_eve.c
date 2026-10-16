/* Eve's original first gift is immediately due; subsequent gifts take six
 * hours. Never mix the device calendar with Hangame's offline server clock.
 * CLOCK_BOOTTIME includes suspend and cannot be advanced by setting the date.
 * A boot UUID disambiguates uptime across restarts of the phone. */
typedef unsigned U32;
typedef struct {
    int id;
    unsigned char prefix[0x394 - sizeof(int)];
    int interval;
    U32 deadline;
    U32 checkpoint; /* Last persisted boot second + 1; zero means not loaded. */
    int reward;
    int amount;
} Pet;
typedef struct { int seconds, nanoseconds; } BootTime;
typedef struct {
    U32 magic;
    U32 sampled;
    U32 remaining;
    char boot[36];
    U32 checksum;
} PresentSave;
_Static_assert(__builtin_offsetof(Pet, deadline) == 0x398, "Original pet ABI");
_Static_assert(__builtin_offsetof(Pet, reward) == 0x3a0, "Original reward ABI");
_Static_assert(sizeof(PresentSave) == 52, "Versioned cooldown profile");

#define EXTERN __attribute__((visibility("hidden"))) extern
#define INTERVAL 21600u
#define MAGIC 0x31455645u /* EVE1 */
EXTERN int eve_clock(BootTime *time);
EXTERN const char *temp_path(const char *name);
EXTERN int format_text(char *buffer, unsigned size, const char *format, ...);
EXTERN void *file_create(const char *path, int *size, int absolute, int write);
EXTERN int file_decrypt(void *file, void *data, const char *key, int size);
EXTERN int file_encrypt(void *file, const void *data, const char *key, int size);
EXTERN void file_close(void *file);
EXTERN void *stdio_open(const char *path, const char *mode);
EXTERN unsigned stdio_read(void *data, unsigned size, unsigned count, void *file);
EXTERN int stdio_close(void *file);
EXTERN signed char pet_owned(Pet *pet);
EXTERN void original_receive_present(void *dialog, Pet *pet);

static int boot_seconds(U32 *now) {
    BootTime time;
    if (eve_clock(&time) || time.seconds < 0) return 0;
    *now = (U32)time.seconds;
    return 1;
}

static int boot_id(char id[36]) {
    void *file = stdio_open("/proc/sys/kernel/random/boot_id", "rb");
    if (!file) return 0;
    unsigned size = stdio_read(id, 1, 36, file);
    int closed = stdio_close(file);
    if (size != 36 || closed) return 0;
    for (unsigned i = 0; i < 36; ++i) {
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            if (id[i] != '-') return 0;
        } else if (!((id[i] >= '0' && id[i] <= '9') ||
                     (id[i] >= 'a' && id[i] <= 'f'))) return 0;
    }
    return 1;
}

static int equal(const void *a, const void *b, unsigned count) {
    const unsigned char *left = a, *right = b;
    for (unsigned i = 0; i < count; ++i)
        if (left[i] != right[i]) return 0;
    return 1;
}

static U32 checksum(const PresentSave *save) {
    const unsigned char *bytes = (const unsigned char *)save;
    U32 hash = 2166136261u;
    for (unsigned i = 0; i < __builtin_offsetof(PresentSave, checksum); ++i)
        hash = (hash ^ bytes[i]) * 16777619u;
    return hash;
}

static int present_path(Pet *pet, char path[512]) {
    int size = format_text(path, 512, "%s_%d", temp_path("petPresent.dat"), pet->id);
    return size > 0 && size < 512;
}

static int read_present(const char *path, PresentSave *save) {
    int size = 0;
    void *file = file_create(path, &size, 1, 0);
    if (!file) return 0;
    /* The engine reader does not reject short ciphertext itself. */
    int plain_size = size == 64 ? (int)sizeof(*save) : size == 32 ? 24 : 0;
    int read = plain_size ? file_decrypt(file, save, "1234567890ABCDEF", plain_size) : 0;
    file_close(file);
    return read == plain_size ? plain_size : 0;
}

static unsigned remaining(Pet *pet, U32 now) {
    return pet->deadline > now ? pet->deadline - now : 0;
}

static int store_present(Pet *pet, U32 now) {
    PresentSave save;
    char path[512];
    if (!present_path(pet, path) || !boot_id(save.boot)) return 0;
    save.magic = MAGIC;
    save.sampled = now;
    save.remaining = remaining(pet, now);
    if (save.remaining > INTERVAL) return 0;
    save.checksum = checksum(&save);
    int size = 0;
    void *file = file_create(path, &size, 1, 1);
    if (!file) return 0;
    int written = file_encrypt(file, &save, "1234567890ABCDEF", sizeof(save));
    file_close(file);
    /* FILE_EncryptWrite discards fwrite's return value. Verify the encrypted
     * round trip before allowing a reward; a short write must not grant it. */
    PresentSave verified;
    if (written != sizeof(save) || read_present(path, &verified) != sizeof(verified) ||
        !equal(&save, &verified, sizeof(save))) return 0;
    pet->checkpoint = now + 1;
    return 1;
}

static int load_present(Pet *pet, U32 now) {
    PresentSave save;
    char path[512], boot[36];
    if (!present_path(pet, path) || !boot_id(boot)) return 0;
    int size = read_present(path, &save);
    unsigned left = INTERVAL;
    if (size == sizeof(save) && save.magic == MAGIC && save.remaining <= INTERVAL &&
        save.checksum == checksum(&save)) {
        left = save.remaining;
        if (equal(save.boot, boot, sizeof(boot))) {
            if (now >= save.sampled) {
                U32 elapsed = now - save.sampled;
                left = elapsed < left ? left - elapsed : 0;
            }
        }
        /* A different boot cannot prove the elapsed time since the last
         * checkpoint. Keep the saved remainder; never consult wall time. */
    } else if (size == 24 && equal(&save, "Birzzle", 8)) {
        /* Original unlock writes wall_time - 60 and saves the wall timestamp.
         * Recognize that unclaimed first gift without using today's clock.
         * Other old deadlines have an untrustworthy server-clock domain and
         * migrate conservatively to one bounded six-hour interval. */
        const U32 *legacy = (const U32 *)&save;
        if (!legacy[5] && legacy[4] <= legacy[2] &&
            legacy[2] - legacy[4] >= 60 && legacy[2] - legacy[4] <= 70)
            left = 0;
    }
    pet->deadline = now + left;
    pet->checkpoint = 0;
    return store_present(pet, now);
}

int eve_load_present(Pet *pet) {
    U32 now;
    return boot_seconds(&now) && load_present(pet, now);
}

int eve_save_present(Pet *pet) {
    U32 now;
    return boot_seconds(&now) && pet->checkpoint && store_present(pet, now);
}

void eve_unlock_present(Pet *pet, int unused) {
    (void)unused;
    U32 now;
    pet->checkpoint = 0;
    if (!boot_seconds(&now)) return;
    pet->deadline = now; /* Preserve the original immediately available gift. */
    store_present(pet, now);
}

int eve_remaining(Pet *pet) {
    if (pet->id != 9) return 0;
    if (!pet_owned(pet)) return INTERVAL;
    U32 now;
    if (!boot_seconds(&now)) return INTERVAL;
    if (!pet->checkpoint && !load_present(pet, now)) return INTERVAL;
    if (now < pet->checkpoint - 1) return INTERVAL;
    unsigned left = remaining(pet, now);
    if (left > INTERVAL) return INTERVAL;
    if (now - (pet->checkpoint - 1) >= 60 && !store_present(pet, now))
        return INTERVAL;
    return (int)left;
}

void eve_received_present(Pet *pet) {
    /* The guarded claim commits its cooldown before invoking the original
     * payout. Keep the original reward-cache invalidation, not its clock. */
    pet->reward = -1;
    pet->amount = 0;
}

void eve_receive_present(void *dialog, Pet *pet) {
    if (pet->id != 9 || eve_remaining(pet)) return;
    U32 now;
    if (!boot_seconds(&now)) return;
    pet->deadline = now + INTERVAL;
    pet->checkpoint = 0;
    if (!store_present(pet, now)) return;
    original_receive_present(dialog, pet);
}
