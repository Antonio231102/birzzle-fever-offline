/* V43: preserve the original event profile and inventory claim mechanism.
 * Counters 0..2 are shared lifetime event totals. Slot 3 is now a derived
 * completed-objective count, never earned Friendship Points. */
typedef struct {
    unsigned char prefix[0x1c];
    int applied[4];
    int pending[4];
    unsigned char winter_images_loaded;
    unsigned char artwork_theme; /* Former padding: 0 unknown, 1 ordinary, 2 winter. */
} Event;
typedef struct { float x, y, width, height; } Rect;
typedef struct {
    unsigned char prefix[0x24];
    Rect rudy_panel;
    Rect eve_panel;
    unsigned char images_loaded;
} EventDialog;
typedef struct { unsigned words[7]; } GameString; /* Original EF::CString ABI. */
_Static_assert(sizeof(int) == 4, "ARM32 counter ABI");
_Static_assert(__builtin_offsetof(Event, pending) == 0x2c, "Original profile ABI");
_Static_assert(__builtin_offsetof(Event, winter_images_loaded) == 0x3c, "Original winter flag");
_Static_assert(sizeof(Event) == 0x40, "Original event-manager allocation");
_Static_assert(__builtin_offsetof(EventDialog, images_loaded) == 0x44, "Original dialog ABI");

#define EXTERN __attribute__((visibility("hidden"))) extern
EXTERN Event *event_manager(void);
EXTERN void save_missions(Event *event);
EXTERN void apply_missions(Event *event);
EXTERN void original_show_dialog(void *dialog, signed char show);
EXTERN void original_show_banner(void *ranking, signed char show);
EXTERN void *pet_manager(void);
EXTERN void *get_pet(void *manager, unsigned type);
EXTERN signed char pet_owned(void *pet);
EXTERN void original_load_background(void *handler, signed char show);
EXTERN void original_set_scene(void *story, int scene);
EXTERN void load_winter_images(void *handler);
EXTERN void reload_stage_background(void *handler);
EXTERN int create_texture(const char *path, float x, float y, float width,
                          float height, void *image);
EXTERN void *find_actor(int id);
EXTERN void set_label(void *actor, const char *text);
EXTERN void get_rect(Rect *rect, void *actor);
EXTERN void get_layer(int layer[2], void *actor);
EXTERN void *copy_actor(void *actor, int layer, int depth);
EXTERN void delete_actor(void *actor, signed char children);
EXTERN void set_actor_id(void *actor, int id);
EXTERN void set_position(void *actor, float x, float y);
EXTERN void show_actor(void *actor, signed char show);
EXTERN const char *local_string(const char *key);
EXTERN int format_text(char *buffer, unsigned size, const char *format, ...);
EXTERN void string_create(GameString *string);
EXTERN void string_destroy(GameString *string);
EXTERN void string_commas(GameString *string, int number);
EXTERN const char *string_data(GameString *string);

static const int goals[2][3] = {
    {RUDY_SCORE, RUDY_BOXES, RUDY_COINS},
    {EVE_SCORE, EVE_BOXES, EVE_COINS}
};

/* Mission completion only enables a claim. The inventory's positive level,
 * queried by the original IsMyPet, is the committed ownership authority.
 * Missing/loading inventory must leave the remaining claims accessible. */
signed char christmas_active(void) {
    void *manager = pet_manager();
    if (!manager) return 1;
    void *rudy = get_pet(manager, 8);
    if (!rudy || !pet_owned(rudy)) return 1;
    void *eve = get_pet(manager, 9);
    return !eve || !pet_owned(eve);
}

void christmas_show_banner(void *ranking, signed char show) {
    /* The original inactive/show path returns without hiding old actors. */
    original_show_banner(ranking, show && christmas_active());
}

void christmas_unload_images(void *handler) {
    (void)handler;
    /* Loaded actors still need teardown after the final claim ends the event. */
    for (int i = 0; i < 4; ++i) {
        void *actor = find_actor(0x6900 + i);
        if (actor) delete_actor(actor, i != 3);
    }
}
void christmas_load_background(void *handler, signed char show) {
    original_load_background(handler, show);
    event_manager()->artwork_theme = christmas_active() ? 2 : 1;
}

void christmas_unload_winter(void *handler) {
    (void)handler;
    for (int i = 0; i < 4; ++i) {
        void *actor = find_actor(0xcfd0 + i);
        if (actor) delete_actor(actor, 1);
    }
    event_manager()->winter_images_loaded = 0;
}

static int same_path(const char *left, const char *right) {
    while (*left && *left == *right) {
        ++left;
        ++right;
    }
    return *left == *right;
}

/* The native background-only repaint hardcodes winter texture filenames.
 * Ordinary and winter paths use the same original crop/tile geometry.
 * Scope substitution to its five texture calls, not the global image loader.
 * Disable the Thumb-to-ARM tail-call, which would need an absolute veneer. */
__attribute__((disable_tail_calls))
int christmas_stage_texture(const char *path, float x, float y, float width,
                            float height, void *image) {
    if (!christmas_active()) {
        if (same_path(path, "assets/Images/stage_bg_winter.png"))
            path = "assets/Images/stage_bg.png";
        else if (same_path(path, "assets/Images/stage_bg_landscape_winter_RGB.png"))
            path = "assets/Images/stage_bg_landscape_RGB.png";
        else if (same_path(path, "assets/Images/Background_landscape_left_winter.png"))
            path = "assets/Images/Background_landscape_left.png";
        else if (same_path(path, "assets/Images/Background_landscape_right_winter.png"))
            path = "assets/Images/Background_landscape_right.png";
    }
    return create_texture(path, x, y, width, height, image);
}

static void reconcile_artwork(void *handler) {
    Event *event = event_manager();
    unsigned theme = christmas_active() ? 2 : 1;
    /* Do not create graphics before LoadGame, or rebuild them on every visit. */
    if (!event->artwork_theme ||
        (event->artwork_theme == theme &&
         !!event->winter_images_loaded == (theme == 2))) return;
    if (event->artwork_theme != theme) christmas_load_background(handler, 1);
    if (theme == 2) {
        if (!event->winter_images_loaded) load_winter_images(handler);
        event->winter_images_loaded = 1;
    } else {
        christmas_unload_winter(handler);
    }
    /* Repaint only background actors; never reconstruct gameplay/UI controls. */
    reload_stage_background(handler);
}

void christmas_set_scene(void *story, int scene) {
    original_set_scene(story, scene); /* Preserve V41's scene-10/26 rearm hook. */
    /* Main menu after inventory readiness, or inventory after a pet claim. */
    if (scene == 0x16 || scene == 0x3e)
        reconcile_artwork((unsigned char *)story + 4);
}


static int total(Event *event, unsigned mission, int include_pending) {
    return event->applied[mission] + (include_pending ? event->pending[mission] : 0);
}

int christmas_objective(Event *event, unsigned mission) {
    (void)event;
    if (mission < 3) return goals[0][mission];
    return mission == 3 ? 3 : 0;
}

int christmas_achievement(Event *event, unsigned mission, signed char include_pending) {
    if (mission < 3) return total(event, mission, include_pending);
    if (mission != 3) return 0;
    int completed = 0;
    for (unsigned i = 0; i < 3; ++i)
        completed += total(event, i, include_pending) >= goals[1][i];
    return completed;
}

int christmas_pending(Event *event, unsigned mission) {
    if (mission < 3) return event->pending[mission];
    if (mission != 3) return 0;
    return christmas_achievement(event, 3, 1) - christmas_achievement(event, 3, 0);
}

signed char christmas_has_pending(Event *event, unsigned pet) {
    if (pet > 1) return 0;
    return event->pending[0] > 0 || event->pending[1] > 0 || event->pending[2] > 0;
}

signed char christmas_complete(Event *event, unsigned pet) {
    if (pet > 1) return 0;
    for (unsigned i = 0; i < 3; ++i)
        if (total(event, i, 1) < goals[pet][i]) return 0;
    return 1;
}

void christmas_add(Event *event, unsigned mission, int amount) {
    /* Social actions must not advance Eve. Cap at her goals, not Rudy's.
     * Limit before adding so even a large positive award cannot overflow. */
    if (mission >= 3 || amount <= 0 || !christmas_active()) return;
    int remaining = goals[1][mission] - total(event, mission, 1);
    if (remaining <= 0) return;
    event->pending[mission] += amount < remaining ? amount : remaining;
    save_missions(event);
}

/* Reuse the engine's complete actor copy, including fonts, colors, alignment,
 * images, and row separators. Keep the existing IDs and dialog ownership. */
static void mirror_actor(int source_id, int target_id, float offset) {
    void *source = find_actor(source_id);
    if (!source) return;
    Rect rect;
    int layer[2];
    get_rect(&rect, source);
    get_layer(layer, source);
    void *copy = copy_actor(source, layer[0], layer[1]);
    if (!copy) return;
    delete_actor(find_actor(target_id), 1);
    set_actor_id(copy, target_id);
    set_position(copy, rect.x + offset, rect.y);
    show_actor(copy, 1);
}

/* The old bar animated these same actor IDs. Commit progress using the original
 * save routine, but no longer schedule bar resize/move actions on mission rows. */
void christmas_commit_progress(void *dialog) {
    (void)dialog;
    Event *event = event_manager();
    if (christmas_has_pending(event, 0)) apply_missions(event);
}

void christmas_show_dialog(void *dialog, signed char show) {
    if (show && !christmas_active()) show = 0;
    EventDialog *view = dialog;
    int first_load = !view->images_loaded;
    original_show_dialog(dialog, show);
    if (!show) return;
    if (first_load) {
        float offset = view->eve_panel.x - view->rudy_panel.x;
        mirror_actor(0x64c, 0x65f, offset); /* Missions heading. */
        for (int row = 0; row < 3; ++row) {
            mirror_actor(0x656 + row, 0x660 + row, offset);
            for (int part = 0; part < 3; ++part)
                mirror_actor(0x64d + row * 3 + part, 0x664 + row * 3 + part, offset);
        }
    }
    show_actor(find_actor(0x663), 0); /* Retired completed-goal bar counter. */
    Event *event = event_manager();
    GameString number;
    char buffer[64];
    string_create(&number);
    for (unsigned row = 0; row < 3; ++row) {
        unsigned mission = row == 0 ? 1 : row == 1 ? 0 : 2;
        int remaining = goals[1][mission] - total(event, mission, 1);
        const char *text;
        if (remaining > 0) {
            const char *key = mission == 1 ? "QUEST_PROGRESS_LEFT_BLOCK" :
                              mission == 0 ? "QUEST_PROGRESS_LEFT_SCORE" : "QUEST_PROGRESS_LEFT_COIN";
            string_commas(&number, remaining);
            format_text(buffer, sizeof(buffer), local_string(key), string_data(&number));
            text = buffer;
        } else {
            text = local_string("QUEST_COMPLETE_TEXT");
        }
        set_label(find_actor(0x666 + (int)row * 3), text);
    }
    string_destroy(&number);
}
