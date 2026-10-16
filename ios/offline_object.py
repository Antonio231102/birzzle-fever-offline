"""Link checked freestanding ARMv7 Thumb code into the iOS __OFFLINE segment.

Text and cstrings keep their object-relative positions under ASLR. Only local
Thumb branches, checked PC-relative section-difference pairs, and explicit
calls through pre-existing ARM-mode import stubs are allowed.
"""

import struct

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB


def _thumb_bl(source: int, target: int, *, link: bool = True) -> bytes:
    displacement = target - (source + 4)
    if displacement & 1 or not -(1 << 24) <= displacement < (1 << 24):
        raise ValueError("ARM backend import veneer is outside Thumb BL range")
    value = displacement & ((1 << 25) - 1)
    sign, i1, i2 = (value >> 24) & 1, (value >> 23) & 1, (value >> 22) & 1
    j1, j2 = 1 ^ i1 ^ sign, 1 ^ i2 ^ sign
    return struct.pack("<HH", 0xF000 | (sign << 10) | ((value >> 12) & 0x3FF),
                       (0xD000 if link else 0x9000) | (j1 << 13)
                       | (j2 << 11) | ((value >> 1) & 0x7FF))


def text_and_symbols(blob: bytes, exports: tuple[str, ...],
                     base_vm: int = 0, imports: dict[str, int] | None = None
                     ) -> tuple[bytes, dict[str, int]]:
    if struct.unpack_from("<IIII", blob) != (0xFEEDFACE, 12, 9, 1):
        raise ValueError("Not an ARMv7 Mach-O object")
    cursor = 28
    sections = {}
    symtab = None
    for _ in range(struct.unpack_from("<I", blob, 16)[0]):
        kind, size = struct.unpack_from("<II", blob, cursor)
        if kind == 1:
            for j in range(struct.unpack_from("<I", blob, cursor + 48)[0]):
                sect = struct.unpack_from("<16s16sIIIIIIIII", blob, cursor + 56 + 68 * j)
                name = sect[0].split(b"\0", 1)[0].decode("ascii")
                if name in ("__text", "__cstring", "__const"):
                    sections[name] = sect
                elif sect[3] and name != "__nl_symbol_ptr":
                    raise ValueError("On-device calculator has unsupported data section")
        elif kind == 2:
            symtab = struct.unpack_from("<IIII", blob, cursor + 8)
        cursor += size
    if "__text" not in sections or symtab is None or cursor > len(blob):
        raise ValueError("Incomplete ARMv7 object")
    text_sect = sections["__text"]
    text_length = text_sect[3]
    if text_sect[2] != 0 or not 0 < text_length <= 0x100000:
        raise ValueError("Unexpected backend text size or address")
    end = max(sect[2] + sect[3] for sect in sections.values())
    if end > 0x100000:
        raise ValueError("Backend section exceeds guarded segment size")
    code = bytearray(end)
    for sect in sections.values():
        if sect[4] + sect[3] > len(blob):
            raise ValueError("Backend section lies outside Mach-O object")
        code[sect[2]:sect[2] + sect[3]] = blob[sect[4]:sect[4] + sect[3]]
    symoff, count, stroff, strsize = symtab
    names = {}
    unresolved = {}
    for index in range(count):
        strx, _, section, _, value = struct.unpack_from("<IBBhI", blob, symoff + 12 * index)
        if (strx >= strsize or section not in (0, 1, 2, 3)
                or (section == 3 and "__const" not in sections)):
            raise ValueError("Unexpected backend symbol section")
        name = blob[stroff + strx:stroff + strsize].split(b"\0", 1)[0].decode("ascii")
        if section == 0:
            if name not in (imports or {}):
                raise ValueError("Unresolved backend import")
            unresolved[index] = name
        elif value >= end:
            raise ValueError("Out-of-section backend symbol")
        else:
            names[name] = value
    if set(exports) - names.keys():
        raise ValueError("Missing required native backend entrypoint")
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    start, total = text_sect[6], text_sect[7]
    veneers = {}
    index = 0
    while index < total:
        address, info = struct.unpack_from("<II", blob, start + 8 * index)
        if address & 0x80000000:
            # Paired ARM_RELOC_HALF_SECTDIFF / ARM_RELOC_PAIR. Both object
            # addresses translate by the same image slide and segment base,
            # so the already encoded PC difference stays exact.
            if index + 1 >= total:
                raise ValueError("Unpaired ARM section-difference relocation")
            pair_addr, pair_value = struct.unpack_from("<II", blob, start + 8 * (index + 1))
            if ((address >> 24 & 15) not in (2, 9)
                    or (pair_addr >> 24 & 15) != 1
                    or not pair_addr & 0x80000000
                    or (address & 0xFFFFFF) + 4 > text_length
                    or info >= end or pair_value >= end):
                raise ValueError("Unsafe backend PC-relative section relocation")
            if (address >> 24 & 15) == 9:
                insns = list(decoder.disasm(
                    code[address & 0xFFFFFF:(address & 0xFFFFFF) + 4], address & 0xFFFFFF))
                if len(insns) != 1 or insns[0].mnemonic not in ("movw", "movt"):
                    raise ValueError("ARM half-section-difference is not a Thumb address operand")
            index += 2
            continue
        if ((info >> 24 & 1) != 1 or (info >> 25 & 3) != 2
                or (info >> 28) != 6 or address + 4 > text_length):
            raise ValueError("Unsupported ARM backend relocation")
        insns = list(decoder.disasm(code[address:address + 4], address))
        if len(insns) != 1 or insns[0].mnemonic not in ("bl", "b.w"):
            raise ValueError("Relocated native instruction is not a Thumb branch")
        if info >> 27 & 1:
            symbol = unresolved.get(info & 0xFFFFFF)
            if symbol is None:
                raise ValueError("Unapproved external ARM helper")
            if symbol not in veneers:
                # Thumb MOVW/MOVT/ADD/BX; BX tail-calls the original ARM-mode
                # import stub without destroying the caller's return address.
                offset = (len(code) + 3) & ~3
                code.extend(b"\0" * (offset - len(code)))
                target = imports[symbol]
                delta = (target - base_vm - offset - 12) & 0xFFFFFFFF
                code.extend(struct.pack("<HHHHHH",
                                        0xF240 | (((delta >> 11) & 1) << 10) | ((delta >> 12) & 15),
                                        0x0C00 | ((delta >> 8) & 7) << 12 | (delta & 255),
                                        0xF2C0 | (((delta >> 27) & 1) << 10) | ((delta >> 28) & 15),
                                        0x0C00 | ((delta >> 24) & 7) << 12 | ((delta >> 16) & 255),
                                        0x44FC, 0x4760))
                veneers[symbol] = offset
            code[address:address + 4] = _thumb_bl(
                address, veneers[symbol], link=insns[0].mnemonic == "bl")
        else:
            if (info & 0xFFFFFF) != 1:
                raise ValueError("Local ARM branch does not target __text")
            target = int(insns[0].op_str.removeprefix("#"), 16)
            if not 0 <= target < text_length:
                raise ValueError("Native local branch escapes backend text")
        index += 1
    return bytes(code), {name: names[name] for name in exports}
