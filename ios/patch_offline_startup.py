"""Build an in-process iOS 6 startup experiment from a private historical reply.

Only request ID 1 with the exact original `server.init.2` API receives the
historical SERVER.INIT payload. Unmatched requests retain the original error
path. This is not a complete playable offline save or an installer.
"""

import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

import patch_startup_probe as base
import trace_request_ids as trace

ROOT = Path(__file__).resolve().parent
CLANG = trace.CLANG
CAVE_VM = 0x5600
CAVE_OFFSET = CAVE_VM - base.IMAGE_BASE
STATE_VM = 0x494D00  # Unused zero-filled __DATA segment tail, beyond __common.
REQUEST_VM = 0x1D5E70
FAIL_CALL_VM = 0x1D6126
CALLBACK_VM = 0x206C60
SOURCE_API = 0x38C658
COMMAND = b"server.init.2\0"


ASM = r""".syntax unified
.thumb
.text
.p2align 2
.globl _offline_request
.thumb_func
_offline_request:
    // Objective-C method entry: r2=request ID, [sp]=API NSString.
    push.w {r0-r8, lr}
    mov r6, r2
    ldr r5, [sp, #40]
    cbz r5, .Lrequest_done
    mov r0, r5
    movw r1, #@REQUEST_SELECTOR_LO@
    movt r1, #@REQUEST_SELECTOR_HI@
.globl _pc_request_selector
_pc_request_selector:
    add r1, pc
    ldr r1, [r1]
    movw r4, #@REQUEST_SEND_LO@
    movt r4, #@REQUEST_SEND_HI@
.globl _pc_request_send
_pc_request_send:
    add r4, pc
    blx r4
    cbz r0, .Lrequest_done
    adr.w r1, _offline_command
.Lapi_byte:
    ldrb r2, [r0], #1
    ldrb r3, [r1], #1
    cmp r2, r3
    bne .Lrequest_done
    cmp r2, #0
    bne .Lapi_byte
    movw r8, #@REQUEST_STATE_LO@
    movt r8, #@REQUEST_STATE_HI@
.globl _pc_request_state
_pc_request_state:
    add r8, pc
    str r6, [r8]
.Lrequest_done:
    pop.w {r0-r8, lr}
    push {r4-r7, lr}       // original two-instruction prologue
    add r7, sp, #0xc
    movw r12, #@REQUEST_RETURN_LO@
    movt r12, #@REQUEST_RETURN_HI@
.globl _pc_request_return
_pc_request_return:
    add r12, pc
    bx r12
.p2align 2
_offline_command:
    .asciz "server.init.2"
.p2align 2
.space 0x100 - (. - _offline_request), 0

.globl _offline_failure
.thumb_func
_offline_failure:
    // Replaces only the C++ parser BL in ConnectorProxy failure callback.
    // Original registers r0=queue, r1=-1, r2=handle, r3=error; r6=self.
    push.w {r0-r3, r6, r8, lr}
    ldr r12, [r6, #8]
    cmp r12, #1
    bne .Loriginal_failure
    movw r8, #@FAIL_STATE_LO@
    movt r8, #@FAIL_STATE_HI@
.globl _pc_fail_state
_pc_fail_state:
    add r8, pc
    ldr r8, [r8]
    cmp r12, r8
    bne .Loriginal_failure
    pop.w {r0-r3, r6, r8, lr}
    ldr r1, [r6, #8]
    adr.w r3, _offline_wire
    b .Ldispatch
.Loriginal_failure:
    pop.w {r0-r3, r6, r8, lr}
.Ldispatch:
    movw r12, #@CALLBACK_LO@
    movt r12, #@CALLBACK_HI@
.globl _pc_callback
_pc_callback:
    add r12, pc
    blx r12
    movw r12, #@FAIL_RETURN_LO@
    movt r12, #@FAIL_RETURN_HI@
.globl _pc_fail_return
_pc_fail_return:
    add r12, pc
    bx r12
.p2align 2
.globl _offline_wire
_offline_wire:
    .asciz "@WIRE@"
"""
TARGETS = {
    "REQUEST_SELECTOR": ("_pc_request_selector", 0x46A45C),
    "REQUEST_SEND": ("_pc_request_send", 0x373FFC),
    "REQUEST_STATE": ("_pc_request_state", STATE_VM),
    "REQUEST_RETURN": ("_pc_request_return", REQUEST_VM + 5),
    "FAIL_STATE": ("_pc_fail_state", STATE_VM),
    "CALLBACK": ("_pc_callback", CALLBACK_VM + 1),
    "FAIL_RETURN": ("_pc_fail_return", FAIL_CALL_VM + 5),
}
LABELS = {b"_offline_request", b"_offline_failure", b"_offline_wire"} | {
    name.encode("ascii") for name, _ in TARGETS.values()
}


def object_text(blob: bytes):
    if struct.unpack_from("<IIII", blob) != (0xFEEDFACE, 12, 9, 1):
        raise ValueError("Not an ARMv7 Mach-O object")
    code = None
    symtab = None
    offset = 28
    for _ in range(struct.unpack_from("<I", blob, 16)[0]):
        command, size = struct.unpack_from("<II", blob, offset)
        if command == 1:
            for n in range(struct.unpack_from("<I", blob, offset + 48)[0]):
                section = struct.unpack_from("<16s16sIIIIIIIII", blob, offset + 56 + 68 * n)
                if section[0].split(b"\0")[0] == b"__text":
                    if section[7]:
                        raise ValueError("Offline hook contains unresolved relocations")
                    code = blob[section[4]:section[4] + section[3]]
        elif command == 2:
            symtab = struct.unpack_from("<IIII", blob, offset + 8)
        offset += size
    if code is None or symtab is None:
        raise ValueError("Missing ARMv7 code or symbols")
    symoff, count, stroff, _ = symtab
    labels = {}
    for n in range(count):
        entry = symoff + n * 12
        index = struct.unpack_from("<I", blob, entry)[0]
        if index:
            name = blob[stroff + index:].split(b"\0", 1)[0]
            if name in LABELS:
                labels[name.decode("ascii")] = struct.unpack_from("<I", blob, entry + 8)[0]
    if labels.keys() != {name.decode("ascii") for name in LABELS}:
        raise ValueError("Offline assembly label set changed")
    return code, labels


def compile_hook(reply: str):
    replacements = {key + part: "0" for key in TARGETS for part in ("_LO", "_HI")}
    replacements["WIRE"] = reply
    with tempfile.TemporaryDirectory(prefix="ios-offline-arm-", dir=ROOT / "captures") as temp:
        source = Path(temp) / "offline.s"
        output = Path(temp) / "offline.o"
        def assemble():
            code = ASM
            for name, value in replacements.items():
                code = code.replace("@" + name + "@", value)
            source.write_text(code, encoding="ascii")
            subprocess.run((str(CLANG), "-target", "armv7-apple-ios6.0", "-c", str(source), "-o", str(output)),
                           check=True, capture_output=True, timeout=30)
            return object_text(output.read_bytes())
        _, labels = assemble()
        if labels["_offline_request"] != 0 or labels["_offline_failure"] != 0x100:
            raise ValueError("Offline code entrypoints moved")
        for key, (label, target) in TARGETS.items():
            delta = (target - (CAVE_VM + labels[label] + 4)) & 0xFFFFFFFF
            replacements[key + "_LO"] = str(delta & 0xFFFF)
            replacements[key + "_HI"] = str(delta >> 16)
        code, revised = assemble()
    if revised != labels or len(code) > 0x800 or len(reply) + 1 > len(code) - labels["_offline_wire"]:
        raise ValueError("Offline cave overflow or moved labels")
    instructions = list(Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(code[:labels["_offline_wire"]], CAVE_VM))
    for label, target in TARGETS.values():
        addr = CAVE_VM + labels[label]
        matched = next((i for i in instructions if i.address == addr), None)
        if matched is None or matched.mnemonic != "add" or not matched.op_str.endswith(", pc"):
            raise ValueError("Offline PC-relative target changed")
        reg = matched.op_str.split(",", 1)[0]
        previous = [i for i in instructions if i.address < addr][-2:]
        if [i.mnemonic for i in previous] != ["movw", "movt"] or any(not i.op_str.startswith(reg + ", #") for i in previous):
            raise ValueError("Unverified ASLR-sensitive address")
        immediate = int(previous[0].op_str.split("#", 1)[1], 0) | int(previous[1].op_str.split("#", 1)[1], 0) << 16
        if (immediate + addr + 4) & 0xFFFFFFFF != target:
            raise ValueError("Offline PC-relative target mismatch")
    if code[labels["_offline_wire"]:labels["_offline_wire"] + len(reply) + 1] != reply.encode("ascii") + b"\0":
        raise ValueError("Offline reply bytes changed during assembly")
    return code


def original_reply():
    private = ROOT / "captures" / "offline-history.json"
    if not private.is_file():
        raise ValueError("Run prepare_offline_history.py into ios/captures/offline-history.json first")
    payload = json.loads(private.read_text(encoding="utf-8"))
    return payload["incoming_replies"]["SERVER.INIT"]


def patched(image: bytes, hook: bytes) -> bytes:
    if image[SOURCE_API - base.IMAGE_BASE:SOURCE_API - base.IMAGE_BASE + len(COMMAND)] != COMMAND:
        raise ValueError("Original iOS startup API differs from guarded literal")
    if any(image[CAVE_OFFSET:CAVE_OFFSET + 0x800]):
        raise ValueError("Original executable has no empty offline cave")
    result = bytearray(base.patched_executable(image))
    result[CAVE_OFFSET:CAVE_OFFSET + len(hook)] = hook
    for vm, expected, destination in (
        (REQUEST_VM, bytes.fromhex("f0b503af"), CAVE_VM),
        (FAIL_CALL_VM, bytes.fromhex("30f09bfd"), CAVE_VM + 0x100),
    ):
        offset = vm - base.IMAGE_BASE
        if image[offset:offset + 4] != expected:
            raise ValueError(f"Unexpected original offline hook instruction at {vm:x}")
        result[offset:offset + 4] = trace.thumb_branch(vm, destination)
    return bytes(result)


def verify(archive: Path, modified: bytes) -> None:
    with zipfile.ZipFile(base.ORIGINAL) as original, zipfile.ZipFile(archive) as built:
        if original.namelist() != built.namelist():
            raise ValueError("iOS archive member list changed")
        for member in original.namelist():
            expected = modified if member == base.EXECUTABLE else original.read(member)
            if built.read(member) != expected:
                raise ValueError("Unexpected iOS archive member change")
    print("Verified guarded offline startup experiment archive (not playable offline):", archive)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    image = base.original_executable()
    hook = compile_hook(original_reply())
    binary = patched(image, hook)
    if args.verify:
        verify(args.verify, binary)
    else:
        with zipfile.ZipFile(base.ORIGINAL) as original, zipfile.ZipFile(args.build.open("xb"), "w") as target:
            target.comment = original.comment
            for member in original.infolist():
                target.writestr(member, binary if member.filename == base.EXECUTABLE else original.read(member))
        verify(args.build, binary)


if __name__ == "__main__":
    main()
