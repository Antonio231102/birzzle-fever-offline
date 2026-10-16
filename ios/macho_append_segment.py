"""Append an ASLR-sliding executable segment to the verified iOS 6 ARMv7 app.

Only a new LC_SEGMENT load command is inserted into original header padding;
original code, data, load commands and linkedit keep their existing offsets.
The caller supplies relocations resolved for the returned ``vmaddr``.
"""

import struct

import patch_startup_probe as original

PAGE = 0x1000
SEGMENT = b"__OFFLINE"
SECTION = b"__text"
COMMAND_BYTES = 56 + 68
SECTION_FLAGS = 0x80000400  # S_REGULAR | S_ATTR_PURE_INSTRUCTIONS | S_ATTR_SOME_INSTRUCTIONS


def align(value: int) -> int:
    return (value + PAGE - 1) & ~(PAGE - 1)


def layout(image: bytes) -> tuple[int, int]:
    if struct.unpack_from("<IIII", image) != (0xFEEDFACE, 12, 9, 2):
        raise ValueError("Not the verified ARMv7 iOS executable")
    commands, command_bytes = struct.unpack_from("<II", image, 16)
    end = 28 + command_bytes
    cursor = 28
    last_vm = 0
    if not 0 < commands < 256 or end > len(image):
        raise ValueError("Invalid original Mach-O load commands")
    for _ in range(commands):
        kind, size = struct.unpack_from("<II", image, cursor)
        if size < 8 or cursor + size > end:
            raise ValueError("Invalid original Mach-O load command size")
        if kind == 1:
            name, vm, vm_size, file_offset, file_size = struct.unpack_from("<16sIIII", image, cursor + 8)
            if name.rstrip(b"\0") == SEGMENT or file_offset + file_size > len(image):
                raise ValueError("Conflicting or invalid Mach-O segment")
            last_vm = max(last_vm, vm + vm_size)
        cursor += size
    if cursor != end or end + COMMAND_BYTES > 0x5600 - original.IMAGE_BASE:
        raise ValueError("No safe original header padding for new load command")
    if any(image[end:end + COMMAND_BYTES]):
        raise ValueError("Original header padding changed")
    return align(last_vm), align(len(image))


def append(image: bytes, code: bytes) -> tuple[bytes, int]:
    vm, file_offset = layout(image)
    if not code or len(code) > 1024 * 1024 or len(image) > file_offset:
        raise ValueError("Invalid on-device backend code or file placement")
    ncmds, command_bytes = struct.unpack_from("<II", image, 16)
    end = 28 + command_bytes
    padded = align(len(code))
    result = bytearray(image)
    struct.pack_into("<II", result, 16, ncmds + 1, command_bytes + COMMAND_BYTES)
    struct.pack_into("<II16sIIIIIIII", result, end, 1, COMMAND_BYTES,
                     SEGMENT.ljust(16, b"\0"), vm, padded, file_offset, padded,
                     5, 5, 1, 0)  # read+execute; never writable
    struct.pack_into("<16s16sIIIIIIIII", result, end + 56,
                     SECTION.ljust(16, b"\0"), SEGMENT.ljust(16, b"\0"),
                     vm, len(code), file_offset, 2, 0, 0, SECTION_FLAGS, 0, 0)
    result.extend(b"\0" * (file_offset - len(result)))
    result.extend(code)
    result.extend(b"\0" * (padded - len(code)))
    return bytes(result), vm
