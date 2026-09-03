import sys

sys.path.insert(0, ".analysis-tools")

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from capstone.arm import ARM_OP_IMM
from elftools.elf.elffile import ELFFile


library = sys.argv[1]
targets = {int(value, 0) & ~1 for value in sys.argv[2:]}

with open(library, "rb") as stream:
    elf = ELFFile(stream)
    symbols = elf.get_section_by_name(".dynsym")
    for symbol in symbols.iter_symbols():
        raw_address = symbol["st_value"]
        size = symbol["st_size"]
        if not raw_address or not size or symbol["st_info"]["type"] != "STT_FUNC":
            continue
        address = raw_address & ~1
        for segment in elf.iter_segments():
            if segment["p_type"] != "PT_LOAD":
                continue
            if segment["p_vaddr"] <= address < segment["p_vaddr"] + segment["p_filesz"]:
                offset = segment["p_offset"] + address - segment["p_vaddr"]
                break
        else:
            continue
        stream.seek(offset)
        code = stream.read(size)
        engine = Cs(CS_ARCH_ARM, CS_MODE_THUMB if raw_address & 1 else CS_MODE_ARM)
        engine.detail = True
        for instruction in engine.disasm(code, address):
            if instruction.mnemonic not in {"bl", "blx"} or not instruction.operands:
                continue
            operand = instruction.operands[0]
            if operand.type == ARM_OP_IMM and (operand.imm & ~1) in targets:
                print(
                    f"{instruction.address:#010x} -> {operand.imm:#010x} "
                    f"{symbol.name}+{instruction.address - address:#x}"
                )
