import io
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_HOOK_CODE, UC_HOOK_INTR
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R7,
)

from build_v43_offline_christmas import SOURCE_APK, patch_library
from decode_birzzle_profiles import seed_crypt
from test_offline_christmas import ChristmasNative


class EveNative(ChristmasNative):
    """Actual ARM helper, PLT/GOT transitions and clock syscall; external file
    services use the game's SEED format. The unchanged payout is a boundary."""
    PET = ChristmasNative.RAM + 0x2000
    BOOT = "11111111-2222-3333-4444-555555555555"
    PATH = "/test/petPresent.dat_9"

    def __init__(self, library, symbols, *, files=None, now=1000, boot=BOOT):
        super().__init__(library)
        self.files = files if files is not None else {}
        self.now = now
        self.boot = boot
        self.server_time = 0
        self.clock_failure = False
        self.boot_failure = False
        self.write_failure = False
        self.owned = True
        self.payouts = 0
        self.handles = {}
        self.original_payout = symbols["original_receive_present"] & ~1
        self.machine.mem_write(self.PET, struct.pack("<i", 9))
        self.machine.mem_write(self.PET + 0x394, struct.pack("<i", 21600))
        self.machine.mem_write(self.PET + 0x3A0, struct.pack("<i", -1))
        names = ("GetTempPath", "snprintf", "FILE_Create", "FILE_EncryptRead",
                 "FILE_EncryptWrite", "FILE_Close", "fopen", "fread", "fclose")
        self.services = {self.RAM + 0x800 + i * 4: name for i, name in enumerate(names)}
        targets = {name: address | 1 for address, name in self.services.items()}
        elf = ELFFile(io.BytesIO(library))
        dynsym = elf.get_section_by_name(".dynsym")
        for relocation in elf.get_section_by_name(".rel.plt").iter_relocations():
            name = dynsym.get_symbol(relocation["r_info_sym"]).name
            if name in targets:
                self.machine.mem_write(self.BIAS + relocation["r_offset"],
                                       struct.pack("<I", targets[name]))
        self.machine.hook_add(UC_HOOK_CODE, self.service)
        self.machine.hook_add(UC_HOOK_INTR, self.syscall)

    @property
    def owned(self):
        return struct.unpack("<i", self.machine.mem_read(self.PET + 4, 4))[0] > 0

    @owned.setter
    def owned(self, value):
        self.machine.mem_write(self.PET + 4, struct.pack("<i", int(value)))

    def syscall(self, machine, interrupt, data):
        if machine.reg_read(UC_ARM_REG_R7) != 263 or machine.reg_read(UC_ARM_REG_R0) != 7:
            raise AssertionError("cooldown must use CLOCK_BOOTTIME")
        pointer = machine.reg_read(UC_ARM_REG_R1)
        machine.mem_write(pointer, struct.pack("<ii", self.now, 0))
        machine.reg_write(UC_ARM_REG_R0, 0xFFFFFFFF if self.clock_failure else 0)

    @staticmethod
    def text(machine, pointer):
        return bytes(machine.mem_read(pointer, 512)).split(b"\0", 1)[0].decode()

    @staticmethod
    def encrypted(plain):
        return seed_crypt(plain + bytes(16 - len(plain) % 16), decrypt=False)

    def service(self, machine, address, size, data):
        regs = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
        r0, r1, r2, r3 = (machine.reg_read(reg) for reg in regs)
        relative = address - self.BIAS
        name = self.services.get(address)
        result = 0
        if relative == self.original_payout:
            self.payouts += 1
            # Follow the original payout's final ReceivedPresent transition.
            machine.reg_write(UC_ARM_REG_R0, r1)
            machine.reg_write(UC_ARM_REG_PC, self.BIAS + 0x1113F9)
            return
        if relative == 0x169DC4:
            result = self.RAM + 0x3000
        elif relative == 0x16394C:
            result = self.server_time & 0xFFFFFFFF
            machine.reg_write(UC_ARM_REG_R1, (self.server_time >> 32) & 0xFFFFFFFF)
        elif name == "GetTempPath":
            if self.text(machine, r0) != "petPresent.dat":
                raise AssertionError("unexpected profile")
            result = self.RAM + 0x6000
            machine.mem_write(result, b"/test/petPresent.dat\0")
        elif name == "snprintf":
            rendered = (self.text(machine, r2) % (self.text(machine, r3), 9)).encode()
            machine.mem_write(r0, rendered[:r1 - 1] + b"\0")
            result = len(rendered)
        elif name == "FILE_Create":
            path = self.text(machine, r0)
            if path != self.PATH:
                raise AssertionError(path)
            machine.mem_write(r1, struct.pack("<I", len(self.files.get(path, b""))))
            if r3 or path in self.files:
                result = 1
                self.handles[result] = path
                if r3:
                    self.files[path] = b""
        elif name == "FILE_EncryptRead":
            raw = self.files[self.handles[r0]]
            if raw and len(raw) % 16 == 0:
                plain = seed_crypt(raw, decrypt=True)
                machine.mem_write(r1, plain[:r3])
                result = r3
        elif name == "FILE_EncryptWrite":
            raw = self.encrypted(bytes(machine.mem_read(r1, r3)))
            self.files[self.handles[r0]] = raw[:16] if self.write_failure else raw
            result = r3  # Engine does not propagate fwrite's short count.
        elif name == "FILE_Close":
            del self.handles[r0]
        elif name == "fopen":
            if self.text(machine, r0) != "/proc/sys/kernel/random/boot_id":
                raise AssertionError("unexpected clock source")
            result = 0 if self.boot_failure else 2
        elif name == "fread":
            raw = self.boot.encode()
            machine.mem_write(r0, raw)
            result = len(raw)
        elif name == "fclose":
            pass
        else:
            return
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def unlock(self):
        self.call(0x1113E4, 1790215200, receiver=self.PET)

    def remaining(self):
        return self.call(0x11143C, receiver=self.PET)

    def claim(self):
        self.call(0xB0DE0, self.PET, receiver=self.RAM + 0x4000)


class EveCooldownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="birzzle-eve-tests-")
        cls.addClassCleanup(temporary.cleanup)
        with zipfile.ZipFile(SOURCE_APK) as apk:
            original = apk.read("lib/armeabi/libbirzzle.so")
        cls.library, cls.report = patch_library(original, Path(temporary.name))

    def native(self, **kwargs):
        return EveNative(self.library, self.report["helper_symbols"], **kwargs)

    def test_first_gift_then_exact_six_hour_repeated_claim_boundary(self):
        native = self.native()
        native.unlock()
        self.assertEqual(native.remaining(), 0)
        native.claim()
        self.assertEqual(native.payouts, 1)
        self.assertEqual(native.remaining(), 21600)
        native.now += 21599
        self.assertEqual(native.remaining(), 1)
        native.claim()
        self.assertEqual(native.payouts, 1)
        native.now += 1
        native.claim()
        native.claim()
        self.assertEqual(native.payouts, 2)
        self.assertEqual(native.remaining(), 21600)

    def test_event_closure_preserves_cooldown_and_future_gifts(self):
        native = self.native()
        native.unlock()
        native.claim()
        native.now += 600
        native.inventory(rudy=1, eve=1)  # Rudy claimed last, during Eve's cooldown.
        self.assertEqual(native.call(0x11BB30), 0)
        self.assertEqual(native.remaining(), 21000)
        native.now += 21000
        native.claim()
        self.assertEqual(native.payouts, 2)
        resumed = self.native(files=native.files, now=native.now + 60)
        resumed.inventory(rudy=1, eve=1)
        self.assertEqual(resumed.call(0x11BB30), 0)
        self.assertEqual(resumed.remaining(), 21540)

    def test_app_restart_counts_closed_and_suspended_time(self):
        native = self.native()
        native.unlock()
        native.claim()
        resumed = self.native(files=native.files, now=native.now + 7200)
        self.assertEqual(resumed.remaining(), 14400)
        resumed.now += 14400
        self.assertEqual(resumed.remaining(), 0)
        resumed.claim()
        cold = self.native(files=resumed.files, now=resumed.now)
        self.assertEqual(cold.remaining(), 21600)

    def test_calendar_or_server_clock_changes_do_not_shorten_cooldown(self):
        native = self.native()
        native.unlock()
        native.claim()
        native.server_time = 4102444800
        self.assertEqual(native.remaining(), 21600)
        native.server_time = -2208988800
        native.now += 30
        self.assertEqual(native.remaining(), 21570)
        cold = self.native(files=native.files, now=native.now)
        cold.server_time = 4102444800
        self.assertEqual(cold.remaining(), 21570)

    def test_phone_reboot_preserves_checkpoint_even_with_larger_new_uptime(self):
        native = self.native()
        native.unlock()
        native.claim()
        native.now += 3600
        self.assertEqual(native.remaining(), 18000)
        rebooted = self.native(files=native.files, now=50000,
                              boot="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        self.assertEqual(rebooted.remaining(), 18000)
        rebooted.now += 60
        self.assertEqual(rebooted.remaining(), 17940)

    def test_broken_legacy_first_gift_migrates_without_calendar_arithmetic(self):
        plain = struct.pack("<8sIIQ", b"Birzzle\0", 1790215260, 0, 1790215200)
        native = self.native(files={EveNative.PATH: EveNative.encrypted(plain)})
        self.assertEqual(native.remaining(), 0)
        native.claim()
        cold = self.native(files=native.files, now=native.now)
        self.assertEqual(cold.remaining(), 21600)

    def test_legacy_claimed_timer_and_damaged_state_do_not_grant_extra_gifts(self):
        claimed = struct.pack("<8sIIQ", b"Birzzle\0", 1790215260, 0, 21600)
        native = self.native(files={EveNative.PATH: EveNative.encrypted(claimed)})
        self.assertEqual(native.remaining(), 21600)
        damaged = bytearray(native.files[EveNative.PATH])
        damaged[32] ^= 1
        cold = self.native(files={EveNative.PATH: bytes(damaged)}, now=native.now)
        self.assertEqual(cold.remaining(), 21600)
        cold.claim()
        self.assertEqual(cold.payouts, 0)

    def test_short_encrypted_write_blocks_payout_even_when_engine_reports_success(self):
        native = self.native()
        native.unlock()
        native.write_failure = True
        native.claim()
        self.assertEqual(native.payouts, 0)
        native.write_failure = False
        cold = self.native(files=native.files, now=native.now)
        self.assertEqual(cold.remaining(), 21600)

    def test_unavailable_trusted_clock_or_boot_identity_blocks_payout(self):
        native = self.native()
        native.unlock()
        native.clock_failure = True
        native.claim()
        self.assertEqual(native.payouts, 0)
        native.clock_failure = False
        native.boot_failure = True
        native.claim()
        self.assertEqual(native.payouts, 0)

    def test_unowned_eve_cannot_start_or_claim_a_reward(self):
        native = self.native()
        native.owned = False
        native.claim()
        self.assertEqual(native.payouts, 0)
        self.assertEqual(native.files, {})

    def test_ordinary_pets_keep_no_present_timer(self):
        native = self.native()
        native.machine.mem_write(native.PET, struct.pack("<i", 4))
        self.assertEqual(native.remaining(), 0)
        native.claim()
        self.assertEqual(native.payouts, 0)
        self.assertEqual(native.files, {})


if __name__ == "__main__":
    unittest.main()
