import io
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP
from elftools.elf.elffile import ELFFile

from build_v43_offline_christmas import SOURCE_APK, patch_library


class ChristmasNative:
    """Execute the packaged ARM32 code at a nonzero load bias.

    Disk saves and external engine arrays are supplied. Inventory lookup and
    ownership checks execute the original code, including ARM PLT transitions.
    """
    BIAS = 0x1000000
    RAM = 0x2000000
    EVENT = RAM + 0x1000
    STOP = RAM + 0x100
    MANAGER = RAM + 0x1400
    ARRAY = RAM + 0x1500
    RUDY = RAM + 0x2800
    EVE = RAM + 0x2000

    def __init__(self, library):
        elf = ELFFile(io.BytesIO(library))
        segments = [s for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        self.machine = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        end = max(s["p_vaddr"] + s["p_memsz"] for s in segments)
        self.machine.mem_map(self.BIAS, (end + 4095) & ~4095)
        for segment in segments:
            self.machine.mem_write(self.BIAS + segment["p_vaddr"], segment.data())
        self.machine.mem_map(self.RAM, 0x10000)
        self.machine.mem_write(self.BIAS + 0x2C6F50, struct.pack("<I", self.MANAGER))
        self.machine.mem_write(self.MANAGER, struct.pack("<I", self.ARRAY))
        self.array_services = {self.RAM + 0x400: "ARRAY_GetCount",
                               self.RAM + 0x404: "ARRAY_GetAt"}
        targets = {name: address | 1 for address, name in self.array_services.items()}
        dynsym = elf.get_section_by_name(".dynsym")
        for relocation in elf.get_section_by_name(".rel.plt").iter_relocations():
            name = dynsym.get_symbol(relocation["r_info_sym"]).name
            if name in targets:
                self.machine.mem_write(self.BIAS + relocation["r_offset"],
                                       struct.pack("<I", targets[name]))
        self.inventory()
        self.machine.hook_add(UC_HOOK_CODE, self.boundary)

    def boundary(self, machine, address, size, data):
        if address == self.BIAS + 0x11B7B4:
            pass
        elif address in self.array_services:
            if machine.reg_read(UC_ARM_REG_R0) != self.ARRAY:
                raise AssertionError("unexpected inventory array")
            if self.array_services[address] == "ARRAY_GetCount":
                value = len(self.pet_pointers)
            else:
                value = self.pet_pointers[machine.reg_read(UC_ARM_REG_R1)]
            machine.reg_write(UC_ARM_REG_R0, value)
        else:
            return
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def inventory(self, rudy=0, eve=0):
        self.pet_pointers = []
        for pet, pointer, level in ((8, self.RUDY, rudy), (9, self.EVE, eve)):
            if level is not None:
                self.machine.mem_write(pointer, struct.pack("<ii", pet, level))
                self.pet_pointers.append(pointer)

    def state(self, applied=(0, 0, 0), pending=(0, 0, 0), social=0):
        self.machine.mem_write(self.EVENT + 0x1C,
                               struct.pack("<8i", *applied, social, *pending, 0))

    def call(self, address, first=0, second=0, *, receiver=None):
        machine = self.machine
        machine.reg_write(UC_ARM_REG_R0, self.EVENT if receiver is None else receiver)
        machine.reg_write(UC_ARM_REG_R1, first)
        machine.reg_write(UC_ARM_REG_R2, second)
        machine.reg_write(UC_ARM_REG_SP, self.RAM + 0xF000)
        machine.reg_write(UC_ARM_REG_LR, self.STOP | 1)
        machine.emu_start(self.BIAS + address + 1, self.STOP, count=10000)
        if machine.reg_read(UC_ARM_REG_PC) != self.STOP:
            raise AssertionError("native call did not return")
        return machine.reg_read(UC_ARM_REG_R0)

    def complete(self, pet):
        return self.call(0x11B724, pet)

    def progress(self, mission, pending=True):
        return self.call(0x11B700, mission, int(pending))


class ChristmasDialogNative(ChristmasNative):
    """Run the UI adapter through real ARM PLT instructions and resolved GOT slots.

    Only the original dialog body and external engine services are supplied.
    Unlike intercepting PLT entry points, this exercises instruction-set changes.
    """
    DIALOG = ChristmasNative.RAM + 0x1800
    TRANSLATIONS = {
        "QUEST_PROGRESS_LEFT_BLOCK": "%s times left",
        "QUEST_PROGRESS_LEFT_SCORE": "%s points left",
        "QUEST_PROGRESS_LEFT_COIN": "%s Coins left",
        "QUEST_COMPLETE_TEXT": "Mission completed!",
    }

    def __init__(self, library, symbols):
        super().__init__(library)
        self.labels = {}
        self.strings = {}
        self.copies = []
        self.ids = {i: self.RAM + 0x4000 + (i - 0x640) * 32 for i in range(0x640, 0x66F)}
        self.ids.update({0x6900 + i: self.RAM + 0x6800 + i * 32 for i in range(4)})
        self.actors = {pointer: {"id": i, "rect": (184.0, 308.0, 194.0, 20.0),
                                 "visible": False} for i, pointer in self.ids.items()}
        self.machine.mem_write(self.DIALOG + 0x24, struct.pack("<8f", 50, 200, 250, 450,
                                                              325, 200, 250, 450))
        self.original_dialog = symbols["original_show_dialog"] & ~1
        names = ("ACTOR_FindWithID", "LABEL_SetString", "ACTOR_GetRect",
                 "ACTOR_GetLayer", "ACTOR_CreateWithActor", "ACTOR_Delete", "ACTION_Stop",
                 "ACTOR_SetID", "ACTOR_SetPosition", "ACTOR_Show", "snprintf",
                 "_ZN2EF7CStringC1Ev", "_ZN2EF7CStringD1Ev",
                 "_ZN2EF7CString14SetCommaStringEi", "_ZN2EF7CString6StringEv",
                 "__aeabi_fadd", "__aeabi_fsub")
        self.services = {self.RAM + 0x800 + i * 4: name for i, name in enumerate(names)}
        targets = {name: address | 1 for address, name in self.services.items()}
        elf = ELFFile(io.BytesIO(library))
        dynsym = elf.get_section_by_name(".dynsym")
        for relocation in elf.get_section_by_name(".rel.plt").iter_relocations():
            name = dynsym.get_symbol(relocation["r_info_sym"]).name
            if name in targets:
                self.machine.mem_write(self.BIAS + relocation["r_offset"],
                                       struct.pack("<I", targets[name]))
        self.machine.hook_add(UC_HOOK_CODE, self.engine_boundary)

    @staticmethod
    def text(machine, pointer):
        return bytes(machine.mem_read(pointer, 256)).split(b"\0", 1)[0].decode()

    def show(self, visible=True):
        return self.call(0xBA7DC, int(visible), receiver=self.DIALOG)

    def engine_boundary(self, machine, address, size, data):
        from unicorn.arm_const import UC_ARM_REG_R3

        r0, r1, r2, r3 = (machine.reg_read(reg) for reg in
                          (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
        relative = address - self.BIAS
        name = self.services.get(address)
        if relative == self.original_dialog:
            if r1:
                machine.mem_write(r0 + 0x44, b"\x01")
            for pointer in self.ids.values():
                self.actors[pointer]["visible"] = bool(r1)
        elif relative == 0x11BFA8:
            machine.reg_write(UC_ARM_REG_R0, self.EVENT)
        elif relative == 0x171624:
            text = self.TRANSLATIONS[self.text(machine, r0)]
            machine.mem_write(self.RAM + 0x7100, text.encode() + b"\0")
            machine.reg_write(UC_ARM_REG_R0, self.RAM + 0x7100)
        elif name == "ACTOR_FindWithID":
            machine.reg_write(UC_ARM_REG_R0, self.ids.get(r0, 0))
        elif name == "LABEL_SetString":
            self.labels[self.actors[r0]["id"]] = self.text(machine, r1)
        elif name == "ACTOR_GetRect":
            machine.mem_write(r0, struct.pack("<4f", *self.actors[r1]["rect"]))
        elif name == "ACTOR_GetLayer":
            machine.mem_write(r0, struct.pack("<2I", 0x4A, 3))
        elif name == "ACTOR_CreateWithActor":
            pointer = self.RAM + 0x6000 + len(self.copies) * 32
            self.actors[pointer] = dict(self.actors[r0], id=-1)
            self.copies.append(pointer)
            machine.reg_write(UC_ARM_REG_R0, pointer)
        elif name == "ACTION_Stop":
            pass
        elif name == "ACTOR_Delete":
            del self.ids[self.actors[r0]["id"]]
            del self.actors[r0]
        elif name == "ACTOR_SetID":
            self.actors[r0]["id"] = r1
            self.ids[r1] = r0
        elif name == "ACTOR_SetPosition":
            x, y = struct.unpack("<2f", struct.pack("<2I", r1, r2))
            self.actors[r0]["rect"] = (x, y, *self.actors[r0]["rect"][2:])
        elif name == "ACTOR_Show":
            self.actors[r0]["visible"] = bool(r1)
        elif name == "_ZN2EF7CStringC1Ev":
            self.strings[r0] = ""
        elif name == "_ZN2EF7CStringD1Ev":
            del self.strings[r0]
        elif name == "_ZN2EF7CString14SetCommaStringEi":
            self.strings[r0] = f"{r1:,}"
        elif name == "_ZN2EF7CString6StringEv":
            machine.mem_write(self.RAM + 0x7000, self.strings[r0].encode() + b"\0")
            machine.reg_write(UC_ARM_REG_R0, self.RAM + 0x7000)
        elif name in ("__aeabi_fadd", "__aeabi_fsub"):
            left, right = struct.unpack("<2f", struct.pack("<2I", r0, r1))
            value = left + right if name.endswith("fadd") else left - right
            machine.reg_write(UC_ARM_REG_R0, struct.unpack("<I", struct.pack("<f", value))[0])
        elif name == "snprintf":
            rendered = (self.text(machine, r2) % self.text(machine, r3)).encode()
            machine.mem_write(r0, rendered[:r1 - 1] + b"\0")
            machine.reg_write(UC_ARM_REG_R0, len(rendered))
        else:
            return
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))


class ChristmasArtworkNative(ChristmasDialogNative):
    """Execute scene handoff, background selection, and the native stage repaint.

    Background actor construction and external graphics services are supplied;
    the native repaint's texture selection, crop, and landscape branches execute.
    """
    STORY = ChristmasNative.RAM + 0x3000

    def __init__(self, library, symbols, landscape=False, screen=(1024, 768)):
        self.landscape = landscape
        self.screen = screen
        self.backgrounds = []
        self.textures = []
        self.images = {}
        self.tiles = []
        self.original_background = symbols.get("original_load_background", 0xF6D4C) & ~1
        super().__init__(library, symbols)
        names = ("GL_CreateTextureWithFilename", "GL_CreateTextureWithPlist",
                 "_ZN2EF5IMAGEC1Ev", "ACTOR_CreateWithImageInfo", "ACTOR_Resize",
                 "__aeabi_fdiv", "__aeabi_fcmpgt")
        extra = {self.RAM + 0xA00 + i * 4: name for i, name in enumerate(names)}
        self.services.update(extra)
        targets = {name: address | 1 for address, name in extra.items()}
        elf = ELFFile(io.BytesIO(library))
        dynsym = elf.get_section_by_name(".dynsym")
        for relocation in elf.get_section_by_name(".rel.plt").iter_relocations():
            name = dynsym.get_symbol(relocation["r_info_sym"]).name
            if name in targets:
                self.machine.mem_write(self.BIAS + relocation["r_offset"],
                                       struct.pack("<I", targets[name]))

    def create_actor(self, actor_id, path):
        pointer = self.RAM + 0x9000 + len(self.textures) * 0x100 + len(self.actors) * 32
        self.ids[actor_id] = pointer
        self.actors[pointer] = {"id": actor_id, "path": path,
                                "rect": (0, 0, 0, 0), "visible": True}
        return pointer

    def engine_boundary(self, machine, address, size, data):
        from unicorn.arm_const import UC_ARM_REG_R3

        r0, r1, r2, r3 = (machine.reg_read(reg) for reg in
                          (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
        relative = address - self.BIAS
        name = self.services.get(address)
        if relative == self.original_background:
            self.background_return = machine.reg_read(UC_ARM_REG_LR)
            selector = 0xF6DC8 if self.landscape else 0xF6EE0
            machine.reg_write(UC_ARM_REG_PC, self.BIAS + selector + 1)
            return
        if name == "GL_CreateTextureWithPlist":
            self.backgrounds.append(self.text(machine, r1))
            machine.reg_write(UC_ARM_REG_PC, self.background_return)
            return
        if name == "GL_CreateTextureWithFilename":
            stack = machine.reg_read(UC_ARM_REG_SP)
            height, image = struct.unpack("<II", machine.mem_read(stack, 8))
            path = self.text(machine, r0)
            crop = struct.unpack("<4f", struct.pack("<4I", r1, r2, r3, height))
            self.images[image] = path
            self.textures.append((path, crop))
            machine.reg_write(UC_ARM_REG_R0, 1)
        elif relative == 0x161D04:  # Position-helper singleton.
            machine.reg_write(UC_ARM_REG_R0, self.RAM + 0x1700)
        elif relative == 0x161D38:
            machine.reg_write(UC_ARM_REG_R0, int(self.landscape))
        elif relative == 0x162C04:
            machine.mem_write(r0, struct.pack("<2f", *self.screen))
        elif relative == 0x156548:  # Tiled-actor construction boundary.
            extent = struct.unpack("<2f", struct.pack("<2I", r1, r2))
            self.tiles.append((self.images[r0], extent))
            machine.reg_write(UC_ARM_REG_R0, self.create_actor(r3, self.images[r0]))
        elif relative == 0x134B34:  # Winter overlay bundle construction boundary.
            for actor_id in range(0xCFD0, 0xCFD4):
                self.create_actor(actor_id, "winter_images.png")
        elif name == "ACTOR_CreateWithImageInfo":
            machine.reg_write(UC_ARM_REG_R0, self.create_actor(r1, self.images[r0]))
        elif name in ("_ZN2EF5IMAGEC1Ev", "ACTOR_Resize"):
            pass
        elif name == "ACTOR_Delete" and not r0:
            pass
        elif name in ("__aeabi_fdiv", "__aeabi_fcmpgt"):
            left, right = struct.unpack("<2f", struct.pack("<2I", r0, r1))
            value = (struct.unpack("<I", struct.pack("<f", left / right))[0]
                     if name == "__aeabi_fdiv" else int(left > right))
            machine.reg_write(UC_ARM_REG_R0, value)
        else:
            return super().engine_boundary(machine, address, size, data)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def load_game_artwork(self):
        self.call(0xF6D4C, 1, receiver=self.STORY + 4)
        self.call(0xF3AC4, receiver=self.STORY + 4)

    def main_ready(self):
        from unicorn.arm_const import UC_ARM_REG_R4

        self.machine.reg_write(UC_ARM_REG_R4, self.STORY)
        self.machine.reg_write(UC_ARM_REG_SP, self.RAM + 0xF000)
        end = self.BIAS + 0x146F94
        self.machine.emu_start(self.BIAS + 0x146F7B, end, count=100000)
        if self.machine.reg_read(UC_ARM_REG_PC) != end:
            raise AssertionError("main-scene handoff did not finish")

    def visible_artwork(self):
        return [self.backgrounds[-1], *[actor["path"] for actor in self.actors.values()
                                      if "path" in actor]]


class OfflineChristmasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="birzzle-christmas-tests-")
        cls.addClassCleanup(temporary.cleanup)
        with zipfile.ZipFile(SOURCE_APK) as apk:
            original = apk.read("lib/armeabi/libbirzzle.so")
        cls.library, cls.report = patch_library(original, Path(temporary.name))

    def setUp(self):
        self.native = ChristmasNative(self.library)
        self.native.state()
    def test_loaded_owned_inventory_replaces_cold_start_winter_artwork(self):
        for landscape, screen in ((False, (768, 1024)), (True, (1024, 768)),
                                  (True, (1280, 720))):
            with self.subTest(landscape=landscape, screen=screen):
                native = ChristmasArtworkNative(self.library, self.report["helper_symbols"],
                                                landscape, screen)
                native.inventory(None, None)
                native.load_game_artwork()
                self.assertTrue(all("winter" in path for path in native.visible_artwork()))
                native.inventory(30, 1)
                native.main_ready()
                self.assertTrue(all("winter" not in path for path in native.visible_artwork()))
                expected = (678.0, 768.0) if landscape else (640.0, 872.0)
                self.assertEqual(native.tiles[-1][1], expected)
                self.assertEqual(native.textures[-(3 if landscape else 1)][1],
                                 (0.0, 0.0, *expected))
                before = (list(native.backgrounds), list(native.textures))
                native.call(0x141870, 0x16, receiver=native.STORY)
                native.call(0x141870, 0x3E, receiver=native.STORY)
                self.assertEqual((native.backgrounds, native.textures), before)

    def test_final_claim_removes_winter_artwork_and_overlays_in_either_order(self):
        for first in (8, 9):
            with self.subTest(first_claim=first):
                native = ChristmasArtworkNative(self.library, self.report["helper_symbols"])
                native.inventory(int(first == 8), int(first == 9))
                native.load_game_artwork()
                native.main_ready()
                self.assertTrue(all("winter" in path for path in native.visible_artwork()))
                native.inventory(1, 1)
                native.call(0x141870, 0x3E, receiver=native.STORY)
                self.assertTrue(all("winter" not in path for path in native.visible_artwork()))
                self.assertFalse(set(range(0xCFD0, 0xCFD4)) & native.ids.keys())


    def test_event_dialog_renders_progress_through_arm_engine_trampolines(self):
        native = ChristmasDialogNative(self.library, self.report["helper_symbols"])
        native.state((123456789, 20, 20000))
        native.show()
        self.assertEqual(native.labels[0x666], "30 times left")
        self.assertEqual(native.labels[0x669], "76,543,211 points left")
        self.assertEqual(native.labels[0x66C], "30,000 Coins left")

    def test_completed_eve_rows_follow_committed_progress_without_the_bar(self):
        native = ChristmasDialogNative(self.library, self.report["helper_symbols"])
        native.state((199999999, 49, 49999), (1, 1, 1))
        native.call(0xB7828)  # Original dialog's progress-commit entry.
        native.show()
        self.assertEqual([native.progress(i, False) for i in range(3)], [200000000, 50, 50000])
        self.assertEqual([native.labels[i] for i in (0x666, 0x669, 0x66C)],
                         [native.TRANSLATIONS["QUEST_COMPLETE_TEXT"]] * 3)

    def test_event_is_active_without_server_configuration_or_clock(self):
        self.assertEqual(self.native.call(0x11BB30), 1)
        self.assertEqual(self.native.call(0x11B9DC), 2)
        self.assertFalse(self.native.complete(0))
        self.assertFalse(self.native.complete(1))

    def test_completed_missions_wait_for_both_claims_in_either_order(self):
        for first in (8, 9):
            with self.subTest(first_claim=first):
                native = ChristmasNative(self.library)
                native.state((200000000, 50, 50000))
                self.assertTrue(native.complete(0))
                self.assertTrue(native.complete(1))
                self.assertEqual(native.call(0x11BB30), 1)
                native.inventory(rudy=int(first == 8), eve=int(first == 9))
                self.assertEqual(native.call(0x11BB30), 1)
                native.inventory(rudy=1, eve=1)
                self.assertEqual(native.call(0x11BB30), 0)

    def test_restored_owned_inventory_closes_event_without_mission_history(self):
        self.native.inventory(rudy=30, eve=1)
        self.assertEqual(self.native.call(0x11BB30), 0)
        self.native.call(0x11BC9C, 0, 1000)
        self.assertEqual(self.native.progress(0), 0)
        for pet in (8, 9):
            found = self.native.call(0x10ED24, pet, receiver=self.native.MANAGER)
            self.assertTrue(self.native.call(0x1104FC, receiver=found))

    def test_missing_inventory_keeps_claims_available(self):
        self.native.inventory(rudy=None, eve=None)
        self.assertEqual(self.native.call(0x11BB30), 1)
        self.native.inventory(rudy=30, eve=None)
        self.assertEqual(self.native.call(0x11BB30), 1)

    def test_final_claim_blocks_dialog_and_hides_existing_banner(self):
        native = ChristmasDialogNative(self.library, self.report["helper_symbols"])
        native.show()
        self.assertTrue(native.actors[native.ids[0x666]]["visible"])
        native.inventory(rudy=30, eve=1)
        native.show()  # A queued open must close, not reopen, the completed event.
        self.assertFalse(native.actors[native.ids[0x666]]["visible"])
        for actor_id in range(0x6900, 0x6904):
            native.actors[native.ids[actor_id]]["visible"] = True
        native.call(0x763F0, 1)  # Actual original banner body, not a stub.
        self.assertFalse(any(native.actors[native.ids[i]]["visible"]
                             for i in range(0x6900, 0x6904)))
        native.call(0x133CF8)  # Inactive must not skip loaded-image teardown.
        self.assertTrue(all(i not in native.ids for i in range(0x6900, 0x6904)))

    def test_each_pet_requires_all_three_exact_objectives(self):
        for pet, goals in enumerate(((100000000, 25, 25000), (200000000, 50, 50000))):
            self.native.state(goals)
            self.assertTrue(self.native.complete(pet))
            for mission in range(3):
                with self.subTest(pet=pet, missing_objective=mission):
                    short = list(goals)
                    short[mission] -= 1
                    self.native.state(short)
                    self.assertFalse(self.native.complete(pet))

    def test_rudy_completion_does_not_unlock_eve_or_stop_progress(self):
        self.native.state((100000000, 25, 25000))
        self.assertTrue(self.native.complete(0))
        self.assertFalse(self.native.complete(1))
        for mission, increment in enumerate((100000000, 25, 25000)):
            self.native.call(0x11BC9C, mission, increment)
        self.assertTrue(self.native.complete(1))
        self.assertEqual([self.native.progress(i) for i in range(3)], [200000000, 50, 50000])

    def test_pending_progress_and_original_apply_are_consistent(self):
        self.native.state((199999999, 49, 49999), (1, 1, 1))
        self.assertTrue(self.native.complete(1))
        self.assertEqual(self.native.progress(3, False), 0)
        self.assertEqual(self.native.progress(3, True), 3)
        self.assertEqual(self.native.call(0x11B7A8, 3), 3)
        self.assertTrue(self.native.call(0x11B6C0, 1))
        self.native.call(0x11B9A8)  # Actual original ApplieAchievementRate.
        self.native.call(0x11B9A8)  # Reapplying must not award progress twice.
        self.assertEqual([self.native.progress(i, False) for i in range(3)], [200000000, 50, 50000])
        self.assertEqual(self.native.progress(3, False), 3)
        self.assertEqual(self.native.call(0x11B7A8, 3), 0)
        self.assertFalse(self.native.call(0x11B6C0, 1))

    def test_large_awards_saturate_at_eve_goals_without_overflow(self):
        self.native.state((100000000, 25, 25000))
        for mission in range(3):
            self.native.call(0x11BC9C, mission, 2147483647)
            self.native.call(0x11BC9C, mission, 1)
        self.assertEqual([self.native.progress(i) for i in range(3)], [200000000, 50, 50000])
        self.assertTrue(self.native.complete(1))

    def test_friendship_points_cannot_replace_any_eve_objective(self):
        self.native.state((200000000, 50, 49999), social=1000000)
        self.native.call(0x11BC9C, 3, 1000000)
        self.assertFalse(self.native.complete(1))
        self.assertEqual(self.native.progress(3), 2)
        self.assertEqual(self.native.progress(2), 49999)


if __name__ == "__main__":
    unittest.main()
