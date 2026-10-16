"""Build the private iOS 6 offline gameplay trial from verified historical assets.

Generated source and IPA contain credentials; keep them under ignored ios/captures
or ios/*.ipa. Original iOS IPA and Android backup remain read-only inputs.
"""
import argparse
import json
import struct
from pathlib import Path
import subprocess
import tempfile
import zipfile

import macho_append_segment as segment
import offline_object as arm
import patch_offline_state as offline
import patch_startup_probe as original
import prepare_offline_history as history
import trace_request_ids as trace

ROOT = Path(__file__).resolve().parent
IMPORTS = {
    "_NSHomeDirectory": 0x373D8C, "_objc_msgSend": 0x373FFC,
    "_CCCrypt": 0x37418C, "_CC_MD5": 0x3741FC,
    "___udivsi3": 0x37447C, "_dlsym": 0x37472C,
    "_fclose": 0x37478C, "_fflush": 0x3747AC,
    "_fopen": 0x3747FC, "_fread": 0x37481C,
    "_free": 0x37482C, "_fwrite": 0x37488C,
    "_malloc": 0x374A6C, "_memcpy": 0x374A8C, "_memset": 0x374AAC,
}
EXPORTS = ("_bf_ios_request", "_bf_ios_reply", "_bf_ios_token_kind")


def literal(data: bytes) -> str:
    return "".join(f"\\x{byte:02x}" for byte in data)
def verified_imports(image: bytes) -> dict[str, int]:
    cursor = 28
    stubs = symbols = indirect = None
    for _ in range(struct.unpack_from("<I", image, 16)[0]):
        kind, size = struct.unpack_from("<II", image, cursor)
        if kind == 1:
            for index in range(struct.unpack_from("<I", image, cursor + 48)[0]):
                section = struct.unpack_from("<16s16sIIIIIIIII", image,
                                             cursor + 56 + 68 * index)
                if section[0].split(b"\0", 1)[0] == b"__picsymbolstub4":
                    stubs = section
        elif kind == 2:
            symbols = struct.unpack_from("<IIII", image, cursor + 8)
        elif kind == 11:
            indirect = struct.unpack_from("<II", image, cursor + 56)
        cursor += size
    if not stubs or not symbols or not indirect or stubs[10] != 16:
        raise ValueError("Original ARM import metadata changed")
    symoff, count, stroff, string_bytes = symbols
    matches = set()
    for slot in range(stubs[3] // stubs[10]):
        entry = struct.unpack_from("<I", image, indirect[0] + 4 * (stubs[9] + slot))[0]
        if entry >= count:
            continue
        string_index = struct.unpack_from("<I", image, symoff + 12 * entry)[0]
        if string_index >= string_bytes:
            raise ValueError("Invalid original ARM import name")
        name = image[stroff + string_index:stroff + string_bytes].split(b"\0", 1)[0].decode("ascii")
        if name in IMPORTS:
            if IMPORTS[name] != stubs[2] + slot * stubs[10]:
                raise ValueError("Original ARM import stub address changed")
            matches.add(name)
    if matches != IMPORTS.keys():
        raise ValueError("Original ARM app lacks a required native backend import")
    return IMPORTS


def private_source(image: bytes, package: dict) -> str:
    key = history.incoming_key(image)
    if len(key) != 16:
        raise ValueError("Authenticated incoming key size changed")
    cached = package["incoming_replies"]
    mutations = {}
    token = offline.post_login_access_token(image, package).decode("ascii")
    for name, expected_id, list_key in (("INVENTORY.BUY", "3", "inven"),
                                        ("POCKET.SET", "7", "pocket")):
        value = json.loads(history.decode_incoming_reply(cached[name], key))
        if (value.get("commandid") != expected_id or value.get("result") != "1"
                or value.get("accesstoken") != token
                or not isinstance(value.get(list_key), list) or len(value[list_key]) != 1):
            raise ValueError("Authenticated historical mutation template changed")
        mutations[name] = json.dumps(value, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")
    wallet = json.loads(history.decode_incoming_reply(cached["POCKET.GET"], key))["pocket"][0]
    replacements = {"KEY": key, "BUY": mutations["INVENTORY.BUY"],
                    "SET": mutations["POCKET.SET"]}
    for command, label in (("POCKET.LOGIN", "LOGIN"), ("INVENTORY.LIST", "INVENTORY"),
                           ("POCKET.GET", "POCKET"), ("SCORE.RANKING", "RANKING")):
        reply = offline.ios_offline_wire(image, package, command)
        adapted = history.decode_incoming_reply(reply, key)
        replacements[label] = adapted
    source = (ROOT / "offline_device.c").read_text(encoding="utf-8")
    for label, value in replacements.items():
        if len(value) >= 4096 or source.count("@BF_" + label + "@") != 1:
            raise ValueError("Missing or oversized historical iOS backend asset")
        source = source.replace("@BF_" + label + "@", literal(value))
    for name in ("COIN", "GEM", "HEART", "EXP", "TROPY"):
        number = int(wallet[name.lower()])
        if not 0 <= number <= 2147483647 or source.count("@BF_" + name + "@") != 1:
            raise ValueError("Invalid archived initial wallet field")
        source = source.replace("@BF_" + name + "@", str(number))
    if "@BF_" in source:
        raise ValueError("Unfilled private backend placeholder")
    return source


def executable(image: bytes, package: dict) -> bytes:
    vm, _ = segment.layout(image)
    with tempfile.TemporaryDirectory(prefix="ios-mutable-arm-", dir=ROOT / "captures") as temp:
        source = Path(temp) / "offline_device.c"
        object_file = Path(temp) / "offline_device.o"
        source.write_text(private_source(image, package), encoding="ascii")
        result = subprocess.run((str(trace.CLANG), "-target", "armv7-apple-ios6.0",
                                 "-Os", "-ffreestanding", "-fno-stack-protector",
                                 "-fno-builtin", "-mfpu=vfpv3", "-mfloat-abi=softfp",
                                 "-I", str(ROOT), "-c", str(source),
                                 "-o", str(object_file)), capture_output=True, timeout=45)
        if result.returncode:
            # Generated source contains account data: never emit compiler output.
            raise ValueError("Private ARMv7 backend did not compile")
        code, symbols = arm.text_and_symbols(
            object_file.read_bytes(), EXPORTS, base_vm=vm,
            imports=verified_imports(image))
    header = offline.assemble(image, package, backend_vm=vm, backend_exports=symbols)
    candidate = offline.expected_executable(image, header)
    amended, appended_vm = segment.append(candidate, code)
    if appended_vm != vm or amended[segment.align(len(image)):segment.align(len(image)) + len(code)] != code:
        raise ValueError("Backend segment address or code bytes changed")
    return amended


def verify(path: Path, binary: bytes):
    with zipfile.ZipFile(original.ORIGINAL) as archive, zipfile.ZipFile(path) as trial:
        if archive.namelist() != trial.namelist():
            raise ValueError("Original iOS IPA member list changed")
        for member in archive.namelist():
            expected = binary if member == original.EXECUTABLE else archive.read(member)
            if trial.read(member) != expected:
                raise ValueError("Private iOS IPA differs from exact guarded offline build")
    print("Verified original iOS resources and guarded native offline mutation image:", path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    image = original.original_executable()
    package = offline.private_package(image)
    binary = executable(image, package)
    if args.verify:
        verify(args.verify, binary)
    else:
        with zipfile.ZipFile(original.ORIGINAL) as source, zipfile.ZipFile(args.build.open("xb"), "w") as dest:
            dest.comment = source.comment
            for member in source.infolist():
                dest.writestr(member, binary if member.filename == original.EXECUTABLE
                              else source.read(member))
        verify(args.build, binary)


if __name__ == "__main__":
    main()
