"""Build an iOS 6 ARMv7 privacy-filtered request, host and error tracer.

Only bounded uppercase dotted names or exact lowercase game API literals
may be printed. No full URLs, arbitrary API text, request bodies, account IDs
or tokens. The previously installed four-hook IPA remains a separate artifact.
"""

import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

import patch_startup_probe as base

IOS_DIR = Path(__file__).resolve().parent
ASSEMBLY = IOS_DIR / "request_trace_thumb.s"
CLANG = IOS_DIR.parent / "tools/llvm-mingw-20260826-ucrt-x86_64/bin/clang.exe"
CAVE_FILE_OFFSET = 0x1600
CAVE_VM_ADDRESS = CAVE_FILE_OFFSET + base.IMAGE_BASE
COMMAND = (0x206A2C, bytes.fromhex("6df1e6ea"), CAVE_VM_ADDRESS)
FAILURE = (0x1D60C8, bytes.fromhex("f0b503af"), CAVE_VM_ADDRESS + 0x80)
TRANSPORT_ERROR = (0x1D56C8, bytes.fromhex("f0b503af"), CAVE_VM_ADDRESS + 0x100)
REQUEST_MAP = (0x1D5E70, bytes.fromhex("f0b503af"), CAVE_VM_ADDRESS + 0x200)
HOOKS = (COMMAND, FAILURE, TRANSPORT_ERROR, REQUEST_MAP)
API_BASE_OFFSET = 0x316  # mov r3, pc -> 0x591a, including the Thumb PC bias
API_TABLE_OFFSET = 0x33C
ALLOWED_API_NAMES = (
    "pocket.login", "pocket.get", "pocket.set", "pocket.sync",
    "inventory.list", "inventory.use", "inventory.update",
    "inventory.buy", "inventory.sell", "custom.get", "custom.post",
    "global.get.name", "global.update.name", "gift.get.count",
    "gift.get.list", "gift.send", "gift.take", "score.ranking",
    "score.globalranking", "score.post", "profile.regist.platform",
    "profile.merge.platform", "profile.reset.friend", "profile.update",
    "profile.logout.platform", "friend.find", "friend.message",
    "quest.update.status", "purchase.validate", "server.init.2",
)
PC_TARGETS = (
    (0, 0x80, (("r0", 0x480050), ("r1", 0x477780), ("r4", 0x373DAC),
                ("ip", 0x373FFC), ("ip", 0x206A31))),
    (0x80, 0x100, (("r0", 0x480050), ("r1", 0x47F7C0),
                    ("r4", 0x373DAC), ("ip", 0x1D60CD))),
    (0x100, 0x200, (("r1", 0x46A7B4), ("r4", 0x373FFC),
                    ("r1", 0x46C6EC), ("r0", 0x480050),
                    ("r4", 0x373DAC), ("ip", 0x1D56CD))),
    (0x200, API_TABLE_OFFSET, (("r1", 0x46A45C), ("r4", 0x373FFC),
                    ("r1", 0x477780), ("r0", 0x480050),
                    ("r4", 0x373DAC), ("r0", 0x46F678),
                    ("r1", 0x46A2A8), ("r2", 0x4936E0),
                    ("r4", 0x373FFC), ("r0", 0x46F684),
                    ("r1", 0x46BC64), ("r1", 0x46A984),
                    ("r0", 0x480050), ("r4", 0x373DAC),
                    ("ip", 0x1D5E75))),
)


def validate_rebased_targets(text):
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    for beginning, ending, expected in PC_TARGETS:
        instructions = list(decoder.disasm(text[beginning:ending], CAVE_VM_ADDRESS + beginning))
        resolved = []
        for index, insn in enumerate(instructions):
            if insn.mnemonic != "add" or not insn.op_str.endswith(", pc"):
                continue
            reg = insn.op_str.split(",", 1)[0]
            low, high = instructions[index - 2:index]
            if (low.mnemonic, high.mnemonic) != ("movw", "movt"):
                raise ValueError("PC-relative diagnostic target lacks MOVW/MOVT")
            if any(not item.op_str.startswith(reg + ", #") for item in (low, high)):
                raise ValueError("PC-relative diagnostic target changed registers")
            immediate = (int(low.op_str.split("#", 1)[1], 0) |
                         int(high.op_str.split("#", 1)[1], 0) << 16)
            resolved.append((reg, (immediate + insn.address + 4) & 0xFFFFFFFF))
        if tuple(resolved) != expected:
            raise ValueError(f"Diagnostic PC targets are not ASLR-relative: {resolved}")
        if sum(insn.mnemonic == "movw" for insn in instructions) != len(expected):
            raise ValueError("Diagnostic contains an unverified absolute pointer")

def validate_known_apis(text, original):
    if text[API_BASE_OFFSET - 4:API_BASE_OFFSET + 2] != bytes.fromhex("0ff228017b46"):
        raise ValueError("Allowlist table pointer or rebased PC instruction moved")
    if API_TABLE_OFFSET + 4 * (len(ALLOWED_API_NAMES) + 1) != len(text):
        raise ValueError("Allowlist contains an unexpected entry")
    base_vm = CAVE_VM_ADDRESS + API_BASE_OFFSET + 4
    for index, name in enumerate(ALLOWED_API_NAMES):
        delta = struct.unpack_from("<I", text, API_TABLE_OFFSET + index * 4)[0]
        vm = (base_vm + delta) & 0xFFFFFFFF
        offset = vm - base.IMAGE_BASE
        expected = name.encode("ascii") + b"\0"
        if not 0 <= offset < len(original) - len(expected) or original[offset:offset + len(expected)] != expected:
            raise ValueError(f"Unsafe or mismatched exact API literal: {name}")
    if struct.unpack_from("<I", text, API_TABLE_OFFSET + 4 * len(ALLOWED_API_NAMES))[0]:
        raise ValueError("Allowlist has no zero terminator")


def assemble(original):
    if not CLANG.is_file():
        raise ValueError(f"ARMv7-capable clang unavailable: {CLANG}")
    cache = IOS_DIR / "captures"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="armv7-request-", dir=cache) as folder:
        object_file = Path(folder) / "trace.o"
        subprocess.run(
            (str(CLANG), "-target", "armv7-apple-ios6.0", "-c", str(ASSEMBLY), "-o", str(object_file)),
            check=True, capture_output=True, timeout=30,
        )
        binary = object_file.read_bytes()
    if struct.unpack_from("<IIII", binary) != (0xFEEDFACE, 12, 9, 1):
        raise ValueError("Assembler did not emit a 32-bit ARMv7 Mach-O object")
    text = None
    symbols = None
    offset = 28
    for _ in range(struct.unpack_from("<I", binary, 16)[0]):
        command, command_size = struct.unpack_from("<II", binary, offset)
        if command == 1:  # LC_SEGMENT
            sections = struct.unpack_from("<I", binary, offset + 48)[0]
            for index in range(sections):
                item = struct.unpack_from("<16s16sIIIIIIIII", binary, offset + 56 + 68 * index)
                if item[0].split(b"\0")[0] == b"__text":
                    if item[7]:
                        raise ValueError("Diagnostic text contains unresolved relocations")
                    text = binary[item[4] : item[4] + item[3]]
        elif command == 2:  # LC_SYMTAB
            symbols = struct.unpack_from("<IIII", binary, offset + 8)
        offset += command_size
    if text is None or symbols is None or not 0 < len(text) <= 0x400:
        raise ValueError("Missing or oversized ARMv7 diagnostic text")
    symbol_offset, count, string_offset, _ = symbols
    labels = {}
    for index in range(count):
        entry = symbol_offset + index * 12
        name_offset = struct.unpack_from("<I", binary, entry)[0]
        if name_offset:
            name = binary[string_offset + name_offset :].split(b"\0", 1)[0]
            if name in (b"_trace_command", b"_trace_fail", b"_trace_transport_error",
                        b"_trace_api_host", b"_trace_api_base", b"_trace_api_table"):
                labels[name] = struct.unpack_from("<I", binary, entry + 8)[0]
    if labels != {b"_trace_command": 0, b"_trace_fail": 0x80,
                  b"_trace_transport_error": 0x100, b"_trace_api_host": 0x200,
                  b"_trace_api_base": API_BASE_OFFSET, b"_trace_api_table": API_TABLE_OFFSET}:
        raise ValueError("Diagnostic entry points moved")
    validate_rebased_targets(text)
    validate_known_apis(text, original)
    return text


def thumb_branch(source, destination):
    """Encode a Thumb-2 unconditional B.W to a fixed image-relative address."""
    displacement = destination - (source + 4)
    if displacement & 1 or not -(1 << 24) <= displacement < (1 << 24):
        raise ValueError("Diagnostic trampoline is not within Thumb B.W reach")
    value = displacement & ((1 << 25) - 1)
    sign = (value >> 24) & 1
    i1 = (value >> 23) & 1
    i2 = (value >> 22) & 1
    j1, j2 = (1 ^ i1 ^ sign), (1 ^ i2 ^ sign)
    high = 0xF000 | (sign << 10) | ((value >> 12) & 0x3FF)
    low = 0x9000 | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF)
    return struct.pack("<HH", high, low)


def expected_executable(original, text):
    data = bytearray(base.patched_executable(original))
    if not (28 + struct.unpack_from("<I", original, 20)[0] <= CAVE_FILE_OFFSET < 0x5E80):
        raise ValueError("Diagnostic cave overlaps Mach-O commands or executable section")
    if any(original[CAVE_FILE_OFFSET : CAVE_FILE_OFFSET + 0x400]):
        raise ValueError("Diagnostic cave is not empty in the clean IPA")
    data[CAVE_FILE_OFFSET : CAVE_FILE_OFFSET + len(text)] = text
    for source, old, destination in HOOKS:
        file_offset = source - base.IMAGE_BASE
        if original[file_offset : file_offset + 4] != old:
            raise ValueError(f"Unknown original instruction at image address 0x{source:x}")
        data[file_offset : file_offset + 4] = thumb_branch(source, destination)
    return bytes(data)


def verify(path, diagnostic):
    with zipfile.ZipFile(base.ORIGINAL) as clean, zipfile.ZipFile(path) as candidate:
        names = clean.namelist()
        if candidate.namelist() != names:
            raise ValueError("IPA archive members changed")
        for name in names:
            expected = diagnostic if name == base.EXECUTABLE else clean.read(name)
            if candidate.read(name) != expected:
                raise ValueError(f"Unexpected IPA member change: {name}")
    print(f"Verified ARMv7 privacy-filtered API/host diagnostic IPA: {path}")


def build(path, diagnostic):
    with zipfile.ZipFile(base.ORIGINAL) as clean:
        stream = path.open("xb")
        try:
            with stream, zipfile.ZipFile(stream, "w") as candidate:
                candidate.comment = clean.comment
                for member in clean.infolist():
                    candidate.writestr(
                        member,
                        diagnostic if member.filename == base.EXECUTABLE else clean.read(member),
                    )
            verify(path, diagnostic)
        except BaseException:
            stream.close()
            path.unlink()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--build", type=Path, metavar="IOS_OUTPUT_IPA")
    operation.add_argument("--verify", type=Path, metavar="IOS_DIAGNOSTIC_IPA")
    args = parser.parse_args()
    original = base.original_executable()
    text = assemble(original)
    diagnostic = expected_executable(original, text)
    output = base.ensure_inside_ios(args.build if args.build is not None else args.verify)
    if args.build is not None:
        build(output, diagnostic)
    else:
        verify(output, diagnostic)


if __name__ == "__main__":
    main()
