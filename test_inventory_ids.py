"""Run the real ARM inventory reducer; supply its unchanged JSON/STL boundaries."""
import copy
import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP

from build_v43_offline_christmas import SOURCE_APK, patch_inventory_library


class InventoryNative:
    BIAS = 0x1000000
    RAM = 0x4000000
    ROOT = RAM + 0x1000
    STOP = RAM + 0x100

    def __init__(self, library, inventory, requests):
        elf = ELFFile(io.BytesIO(library))
        self.machine = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        segments = [s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        end = max(s['p_vaddr'] + s['p_memsz'] for s in segments)
        self.machine.mem_map(self.BIAS, (end + 4095) & ~4095)
        for segment in segments:
            self.machine.mem_write(self.BIAS + segment['p_vaddr'], segment.data())
        self.machine.mem_map(self.RAM, 0x200000)
        self.next_heap = self.RAM + 0x10000
        self.messages = {self.ROOT: {'inven': copy.deepcopy(inventory)}}
        self.arrays = {}
        self.requests = requests
        self.allocations = set()
        self.vector_strings = []
        self.calls = []
        # The native calc object embeds its current request after the pool pointer.
        self.make_string(self.ROOT + 0x28, json.dumps({'extradata': 'UsePet'}))
        symbols = elf.get_section_by_name('.dynsym')
        for relocation in elf.get_section_by_name('.rel.dyn').iter_relocations():
            name = symbols.get_symbol(relocation['r_info_sym']).name
            if name == '__stack_chk_guard':
                self.put(self.BIAS + relocation['r_offset'], self.RAM + 0x200)
        self.put(self.RAM + 0x200, 0x76543210)
        self.machine.hook_add(UC_HOOK_CODE, self.boundary)

    def put(self, address, value):
        self.machine.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def word(self, address):
        return struct.unpack('<I', self.machine.mem_read(address, 4))[0]

    def allocate(self, size):
        address = self.next_heap
        self.next_heap += (size + 7) & ~7
        return address

    def cstring(self, address):
        result = bytearray()
        while (char := bytes(self.machine.mem_read(address + len(result), 1))) != b'\0':
            result.extend(char)
        return result.decode()

    def string(self, address):
        return self.cstring(self.word(address + 20))

    def make_string(self, address, value):
        encoded = str(value).encode() + b'\0'
        buffer = self.allocate(max(16, len(encoded)))
        self.machine.mem_write(buffer, encoded)
        self.machine.mem_write(address, bytes(24))
        self.put(address, buffer + max(16, len(encoded)))
        self.put(address + 16, buffer + len(encoded) - 1)
        self.put(address + 20, buffer)
        self.allocations.add(buffer)

    def boundary(self, machine, address, size, data):
        offset = address - self.BIAS
        r0, r1, r2, r3 = [machine.reg_read(r) for r in
                          (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
        result = None
        if offset == 0x9f8d4:  # string(char const*, allocator const&)
            self.make_string(r0, self.cstring(r1))
        elif offset == 0xa08ac:  # string copy
            self.make_string(r0, self.string(r1))
        elif offset in (0x209ff4, 0x1ed7b4):
            self.allocations.remove(r0)
        elif offset == 0x11acd0:  # GetArray, hidden result pointer
            self.arrays[r0] = copy.deepcopy(self.messages[r1][self.string(r2)])
        elif offset == 0x130f10:  # GetRequestSuite, vector<RequestInfo>
            base = self.allocate(56 * len(self.requests) + 8)
            for index, (command, fields) in enumerate(self.requests):
                record = base + 56 * index
                for slot, value in ((record + 4, command), (record + 28, json.dumps(fields))):
                    self.make_string(slot, value)
                    self.vector_strings.append(slot)
            self.put(r0, base)
            self.put(r0 + 4, base + 56 * len(self.requests))
            self.put(r0 + 8, base + 56 * len(self.requests))
        elif offset == 0x11aed4:  # MessageObject(string, format)
            self.messages[r0] = json.loads(self.string(r1))
        elif offset == 0x119d20:
            self.messages[r0] = {}
        elif offset == 0x11a6a0:  # Original ARM32 GetInt/atoi semantics
            value = int(self.messages[r0].get(self.string(r1), r2))
            result = min(2147483647, max(-2147483648, value))
        elif offset == 0x11a51c:  # GetString, hidden result pointer
            self.make_string(r0, self.messages[r1].get(self.string(r2), self.string(r3)))
        elif offset == 0x119d3c:
            result = len(self.arrays[r0])
        elif offset == 0x119dd4:
            self.messages[r0] = copy.deepcopy(self.arrays[r1][r2])
        elif offset == 0x11b420:
            self.messages[r0][self.string(r1)] = str(struct.unpack('<i', struct.pack('<I', r2))[0])
        elif offset == 0x11b27c:
            self.messages[r0][self.string(r1)] = self.string(r2)
        elif offset == 0x119d44:
            self.arrays[r0][r1] = copy.deepcopy(self.messages[r2])
        elif offset == 0x119d90:
            self.arrays[r0].append(copy.deepcopy(self.messages[r1]))
        elif offset == 0x119ed8:
            self.messages[r0][self.string(r1)] = copy.deepcopy(self.arrays[r2])
        elif offset == 0x119e20:
            del self.messages[r0]
        elif offset == 0x11a140:
            del self.arrays[r0]
        elif offset == 0x12ba14:
            for slot in self.vector_strings:
                self.allocations.remove(self.word(slot + 20))
            self.vector_strings.clear()
        elif offset == 0x96ae0:  # memcmp
            left, right = bytes(machine.mem_read(r0, r2)), bytes(machine.mem_read(r1, r2))
            result = (left > right) - (left < right)
        elif offset == 0x9678c:
            raise AssertionError('native stack canary failed')
        else:
            return
        self.calls.append(hex(offset))
        if result is not None:
            machine.reg_write(UC_ARM_REG_R0, result & 0xffffffff)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def replay(self):
        machine = self.machine
        machine.reg_write(UC_ARM_REG_R0, self.ROOT)
        machine.reg_write(UC_ARM_REG_SP, self.RAM + 0x1f0000)
        machine.reg_write(UC_ARM_REG_LR, self.STOP | 1)
        machine.emu_start(self.BIAS + 0x1345f5, self.STOP, count=100000)
        if machine.reg_read(UC_ARM_REG_PC) != self.STOP:
            raise AssertionError('native reducer did not return')
        # The calc object's input string remains owned by its enclosing object.
        if self.allocations != {self.word(self.ROOT + 0x28 + 20)}:
            raise AssertionError('reducer leaked temporary string storage')
        return self.messages[self.ROOT]['inven']


class InventoryIdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        with zipfile.ZipFile(SOURCE_APK) as apk:
            cls.original = apk.read('lib/armeabi/libef2d.so')
        cls.fixed, cls.report = patch_inventory_library(cls.original, Path(cls.work.name))

    def inventory(self):
        return [{'tid': '2147483647', 'itemid': '', 'ability': '0', 'odr': '0'},
                {'tid': '-2126748964', 'itemid': '0', 'ability': '30', 'odr': '1'},
                {'tid': '2147486133', 'itemid': '8', 'ability': '2', 'odr': '1'},
                {'tid': '2147486134', 'itemid': '9', 'ability': '1', 'odr': '1'}]

    def test_android_finds_file_backed_program_headers(self):
        elf = ELFFile(io.BytesIO(self.fixed))
        segments = list(elf.iter_segments())
        size = elf['e_phnum'] * elf['e_phentsize']
        explicit = next((s for s in segments if s['p_type'] == 'PT_PHDR'), None)
        if explicit is not None:
            address = explicit['p_vaddr']
        else:
            first = next(s for s in segments if s['p_type'] == 'PT_LOAD' and s['p_offset'] == 0)
            address = first['p_vaddr'] + elf['e_phoff']
        mapped = next((s for s in segments if s['p_type'] == 'PT_LOAD'
                       and s['p_vaddr'] <= address
                       and address + size <= s['p_vaddr'] + s['p_filesz']), None)
        self.assertIsNotNone(mapped, 'Android rejects a program-header table outside file-backed LOAD data')
        offset = mapped['p_offset'] + address - mapped['p_vaddr']
        self.assertEqual(self.fixed[offset:offset + size],
                         self.fixed[elf['e_phoff']:elf['e_phoff'] + size])

    def test_captured_rudy_equip_preserves_full_id_and_owned_inventory(self):
        inventory = self.inventory()
        requests = [('inventory.use', {'tid': '2147486133'})]
        before = InventoryNative(self.original, inventory, requests).replay()
        self.assertEqual(before[0]['tid'], '2147483647')
        after = InventoryNative(self.fixed, inventory, requests).replay()
        self.assertEqual(after[0]['tid'], '2147486133')
        self.assertEqual(after[1:], inventory[1:])

    def test_upgrade_does_not_alias_two_overflowing_ids(self):
        inventory = self.inventory()
        requests = [('inventory.update', {'tid': '2147486134', 'ability': '3'})]
        before = InventoryNative(self.original, inventory, requests).replay()
        self.assertEqual(before[2]['ability'], '3')
        after = InventoryNative(self.fixed, inventory, requests).replay()
        self.assertEqual(after[2], inventory[2])
        self.assertEqual(after[3]['ability'], '3')
        self.assertEqual(after[:2], inventory[:2])

    def test_replayed_selection_recovers_without_rewriting_owned_ids(self):
        inventory = self.inventory()
        requests = [('inventory.use', {'tid': tid}) for tid in
                    ('2147486133', '-2126748964', '2147486134')]
        after = InventoryNative(self.fixed, inventory, requests).replay()
        self.assertEqual(after[0]['tid'], '2147486134')
        self.assertEqual(after[1:], inventory[1:])

    def test_unknown_and_prefix_ids_do_not_modify_owned_pets(self):
        inventory = self.inventory()
        for tid in ('214748613', '21474861330', '9223372036854775807'):
            with self.subTest(tid=tid):
                requests = [('inventory.update', {'tid': tid, 'ability': '30'})]
                self.assertEqual(InventoryNative(self.fixed, inventory, requests).replay(), inventory)

    def test_new_purchase_full_width_id_survives_equip_and_upgrade(self):
        inventory = self.inventory()[:2]
        tid = '9223372036854775807'
        requests = [
            ('inventory.buy', {'tid': tid, 'itemid': '8', 'ability': '1', 'odr': '1'}),
            ('inventory.use', {'tid': tid}),
            ('inventory.update', {'tid': tid, 'ability': '2'}),
        ]
        after = InventoryNative(self.fixed, inventory, requests).replay()
        self.assertEqual(after[0]['tid'], tid)
        self.assertEqual(after[1], inventory[1])
        self.assertEqual(after[2], {'tid': tid, 'itemid': '8', 'ability': '2', 'odr': '1'})


if __name__ == '__main__':
    unittest.main()
