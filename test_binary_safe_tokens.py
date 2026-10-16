import base64
import hashlib
import unittest
import zipfile

from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R8, UC_ARM_REG_SP, UC_ARM_REG_PC

from build_v42_binary_safe_tokens import SOURCE_APK, patch_library


def encode_native_digest(library: bytes, digest: bytes) -> bytes:
    """Execute GenerateToken's real Thumb call site with libc/encoder hooks."""
    machine = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    bias = 0x1000000
    machine.mem_map(bias, (len(library) + 4095) & ~4095)
    machine.mem_write(bias, library)
    buffer = 0x2000000
    machine.mem_map(buffer, 4096)
    machine.mem_write(buffer, digest + b"\0")
    machine.reg_write(UC_ARM_REG_R8, buffer)
    machine.reg_write(UC_ARM_REG_SP, buffer + 512)
    result = []

    def call_boundary(uc, address, size, user_data):
        if address == bias + 0x96558:  # strlen PLT
            pointer = uc.reg_read(UC_ARM_REG_R0)
            uc.reg_write(UC_ARM_REG_R0, bytes(uc.mem_read(pointer, 17)).index(0))
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        elif address == bias + 0x122A1C:  # base64EncodeData
            pointer = uc.reg_read(UC_ARM_REG_R1)
            length = uc.reg_read(UC_ARM_REG_R2)
            result.append(base64.b64encode(bytes(uc.mem_read(pointer, length))))
            uc.emu_stop()

    machine.hook_add(UC_HOOK_CODE, call_boundary)
    machine.emu_start(bias + 0x122CA4 + 1, bias + 0x122CB6, count=100)
    if len(result) != 1:
        raise AssertionError("native encoder call was not reached")
    return result[0]


class BinarySafeTokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(SOURCE_APK) as apk:
            cls.original = apk.read("lib/armeabi/libef2d.so")
        cls.fixed = patch_library(cls.original)

    def test_leading_zero_digest_no_longer_produces_empty_key(self):
        digest = hashlib.md5(b"168").digest()
        self.assertEqual(encode_native_digest(self.original, digest), b"")
        self.assertEqual(base64.b64decode(encode_native_digest(self.fixed, digest)), digest)

    def test_embedded_zero_digest_is_not_truncated(self):
        digest = next(hashlib.md5(str(i).encode()).digest() for i in range(1000)
                      if b"\0" in hashlib.md5(str(i).encode()).digest()[1:])
        self.assertNotEqual(base64.b64decode(encode_native_digest(self.original, digest)), digest)
        self.assertEqual(base64.b64decode(encode_native_digest(self.fixed, digest)), digest)

    def test_nonzero_legacy_digest_encoding_is_unchanged(self):
        digest = hashlib.md5(b"1").digest()
        self.assertEqual(encode_native_digest(self.original, digest), encode_native_digest(self.fixed, digest))
        self.assertEqual(base64.b64decode(encode_native_digest(self.fixed, digest)), digest)


if __name__ == "__main__":
    unittest.main()
