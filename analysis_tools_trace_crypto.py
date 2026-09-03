import sys

sys.path.insert(0, ".analysis-tools")

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile


TARGETS = {
    "_Z7DecryptSs",
    "_Z7EncryptRSs",
    "_ZN6Enfeel7Private13SetPrivateKeyESs",
    "_ZN6Enfeel7PrivateC1Ev",
    "_ZN6Enfeel7PrivateC2Ev",
}


def vaddr_to_offset(elf, address):
    for segment in elf.iter_segments():
        if segment["p_type"] != "PT_LOAD":
            continue
        start = segment["p_vaddr"]
        end = start + segment["p_filesz"]
        if start <= address < end:
            return segment["p_offset"] + address - start
    raise ValueError(hex(address))


with open(sys.argv[1], "rb") as stream:
    elf = ELFFile(stream)
    symbols = {}
    for section_name in (".dynsym", ".symtab"):
        section = elf.get_section_by_name(section_name)
        if not section:
            continue
        for symbol in section.iter_symbols():
            if symbol.name in TARGETS:
                symbols[symbol.name] = (symbol["st_value"], symbol["st_size"])

    for name, (raw_address, size) in symbols.items():
        thumb = bool(raw_address & 1)
        address = raw_address & ~1
        offset = vaddr_to_offset(elf, address)
        stream.seek(offset)
        code = stream.read(size or 512)
        engine = Cs(CS_ARCH_ARM, CS_MODE_THUMB if thumb else CS_MODE_ARM)
        print(f"\n{name} address={raw_address:#x} size={size} thumb={thumb}")
        for instruction in engine.disasm(code, address):
            print(f"{instruction.address:08x}: {instruction.mnemonic:8} {instruction.op_str}")
