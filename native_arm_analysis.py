import argparse
import re
import sys

sys.path.insert(0, ".analysis-tools")

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from capstone.arm import ARM_OP_IMM
from elftools.elf.elffile import ELFFile


def load_symbols(elf):
    result = {}
    for section_name in (".dynsym", ".symtab"):
        section = elf.get_section_by_name(section_name)
        if not section:
            continue
        for symbol in section.iter_symbols():
            if not symbol.name or not symbol["st_value"]:
                continue
            previous = result.get(symbol.name)
            current = (symbol["st_value"], symbol["st_size"], section_name)
            if previous is None or current[1] > previous[1]:
                result[symbol.name] = current
    return result


def vaddr_to_offset(elf, address):
    for segment in elf.iter_segments():
        if segment["p_type"] != "PT_LOAD":
            continue
        start = segment["p_vaddr"]
        end = start + segment["p_filesz"]
        if start <= address < end:
            return segment["p_offset"] + address - start
    raise ValueError(f"address {address:#x} is not file-backed")


def symbol_for_address(symbols, address):
    best = None
    for name, (value, size, _) in symbols.items():
        start = value & ~1
        end = start + max(size, 1)
        if start <= address < end:
            candidate = (start, name, address - start)
            if best is None or candidate[0] > best[0]:
                best = candidate
    if best:
        return f"{best[1]}+{best[2]:#x}"
    return ""


def disassemble(stream, elf, symbols, name, before=0, after=0):
    raw_address, size, source = symbols[name]
    thumb = bool(raw_address & 1)
    start = (raw_address & ~1) - before
    amount = before + (size or 512) + after
    offset = vaddr_to_offset(elf, start)
    stream.seek(offset)
    code = stream.read(amount)
    engine = Cs(CS_ARCH_ARM, CS_MODE_THUMB if thumb else CS_MODE_ARM)
    engine.detail = True
    print(
        f"\n{name}\n"
        f"  address={raw_address:#x} size={size:#x} file_offset={vaddr_to_offset(elf, raw_address & ~1):#x} "
        f"mode={'thumb' if thumb else 'arm'} source={source}"
    )
    for instruction in engine.disasm(code, start):
        annotation = ""
        if instruction.mnemonic in {"bl", "blx", "b", "beq", "bne", "cbz", "cbnz"}:
            if instruction.operands and instruction.operands[0].type == ARM_OP_IMM:
                target = instruction.operands[0].imm
                label = symbol_for_address(symbols, target)
                if label:
                    annotation = f" ; {label}"
        raw = code[instruction.address - start : instruction.address - start + instruction.size]
        print(
            f"  {instruction.address:08x}  {raw.hex():<10}  "
            f"{instruction.mnemonic:<8} {instruction.op_str}{annotation}"
        )


def disassemble_range(stream, elf, symbols, raw_address, size, thumb):
    address = raw_address & ~1
    offset = vaddr_to_offset(elf, address)
    stream.seek(offset)
    code = stream.read(size)
    engine = Cs(CS_ARCH_ARM, CS_MODE_THUMB if thumb else CS_MODE_ARM)
    engine.detail = True
    print(
        f"\nrange address={raw_address:#x} size={size:#x} "
        f"file_offset={offset:#x} mode={'thumb' if thumb else 'arm'}"
    )
    for instruction in engine.disasm(code, address):
        annotation = ""
        if instruction.mnemonic in {"bl", "blx", "b", "beq", "bne", "cbz", "cbnz"}:
            if instruction.operands and instruction.operands[0].type == ARM_OP_IMM:
                target = instruction.operands[0].imm
                label = symbol_for_address(symbols, target)
                if label:
                    annotation = f" ; {label}"
        raw = code[instruction.address - address : instruction.address - address + instruction.size]
        print(
            f"  {instruction.address:08x}  {raw.hex():<10}  "
            f"{instruction.mnemonic:<8} {instruction.op_str}{annotation}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("library")
    parser.add_argument("--list", metavar="REGEX")
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--before", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--after", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--address", type=lambda value: int(value, 0))
    parser.add_argument("--length", type=lambda value: int(value, 0), default=0x100)
    parser.add_argument("--arm", action="store_true")
    parser.add_argument("--xrefs", action="append", default=[])
    parser.add_argument("--xrefs-address", action="append", default=[], type=lambda value: int(value, 0))
    args = parser.parse_args()

    with open(args.library, "rb") as stream:
        elf = ELFFile(stream)
        symbols = load_symbols(elf)
        if args.list:
            pattern = re.compile(args.list, re.IGNORECASE)
            for name, (address, size, source) in sorted(
                symbols.items(), key=lambda item: item[1][0]
            ):
                if pattern.search(name):
                    print(
                        f"{address:#010x} size={size:#08x} offset="
                        f"{vaddr_to_offset(elf, address & ~1):#010x} {source} {name}"
                    )
        for name in args.symbol:
            if name not in symbols:
                print(f"missing symbol: {name}", file=sys.stderr)
                continue
            disassemble(stream, elf, symbols, name, args.before, args.after)
        if args.address is not None:
            disassemble_range(stream, elf, symbols, args.address, args.length, not args.arm)
        for target_name in args.xrefs:
            if target_name not in symbols:
                print(f"missing symbol: {target_name}", file=sys.stderr)
                continue
            target = symbols[target_name][0] & ~1
            print(f"\nxrefs to {target_name} ({target:#x})")
            for section in elf.iter_sections():
                if not (section["sh_flags"] & 0x4) or section["sh_type"] != "SHT_PROGBITS":
                    continue
                data = section.data()
                base = section["sh_addr"]
                for mode in (CS_MODE_THUMB, CS_MODE_ARM):
                    engine = Cs(CS_ARCH_ARM, mode)
                    engine.detail = True
                    for instruction in engine.disasm(data, base):
                        if instruction.mnemonic not in {"bl", "blx"}:
                            continue
                        if not instruction.operands or instruction.operands[0].type != ARM_OP_IMM:
                            continue
                        if (instruction.operands[0].imm & ~1) == target:
                            owner = symbol_for_address(symbols, instruction.address)
                            print(
                                f"  {instruction.address:#010x} "
                                f"{instruction.mnemonic} {instruction.op_str} {owner}"
                            )
        for raw_target in args.xrefs_address:
            target = raw_target & ~1
            print(f"\nxrefs to address {target:#x}")
            for section in elf.iter_sections():
                if not (section["sh_flags"] & 0x4) or section["sh_type"] != "SHT_PROGBITS":
                    continue
                data = section.data()
                base = section["sh_addr"]
                for mode in (CS_MODE_THUMB, CS_MODE_ARM):
                    engine = Cs(CS_ARCH_ARM, mode)
                    engine.detail = True
                    for instruction in engine.disasm(data, base):
                        if instruction.mnemonic not in {"bl", "blx"}:
                            continue
                        if not instruction.operands or instruction.operands[0].type != ARM_OP_IMM:
                            continue
                        if (instruction.operands[0].imm & ~1) == target:
                            owner = symbol_for_address(symbols, instruction.address)
                            print(
                                f"  {instruction.address:#010x} "
                                f"{instruction.mnemonic} {instruction.op_str} {owner}"
                            )


if __name__ == "__main__":
    main()
