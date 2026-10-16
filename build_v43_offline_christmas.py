"""Build the offline Christmas challenge, active until both pets are claimed."""
import argparse
import hashlib
import io
import json
import re
import struct
import subprocess
import zipfile
from pathlib import Path

from native_arm_analysis import vaddr_to_offset
from elftools.elf.elffile import ELFFile

ROOT = Path(__file__).resolve().parent
SOURCE_APK = ROOT / "native-patches/v42-binary-safe-tokens/release-signed/BirzzleFever-1.1.2-v42-release-signed.apk"
OUTPUT_DIR = ROOT / "native-patches/v43-offline-christmas"
SOURCE_SHA256 = "766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4"
LIBRARY_SHA256 = "087f0742624d3e57ba4277adf16685193556bc02ff3a6adf4904726e51879d56"
LLVM = ROOT / "tools/llvm-mingw-20260826-ucrt-x86_64/bin"
GOALS = {"Rudy": [100000000, 25, 25000], "Eve": [200000000, 50, 50000]}
HOOKS = {
    0x11BB30: ("f0b55f46", "christmas_active"),
    0x0763F0: ("f0b55f46", "christmas_show_banner"),
    0x133CF8: ("10b5e8f7", "christmas_unload_images"),
    0x0F6D4C: ("f0b55f46", "christmas_load_background"),
    0x133008: ("10b50c48", "christmas_unload_winter"),
    0x141870: ("6bf176bb", "christmas_set_scene"),
    0x11B6E8: ("00200329", "christmas_objective"),
    0x11B700: ("002a04d1", "christmas_achievement"),
    0x11B7A8: ("0a318900", "christmas_pending"),
    0x11B724: ("f0b585b0", "christmas_complete"),
    0x11B6C0: ("002904d0", "christmas_has_pending"),
    0x11BC9C: ("f0b54746", "christmas_add"),
    0x0BA7DC: ("f0b55f46", "christmas_show_dialog"),
    0x0B7828: ("f0b54f46", "christmas_commit_progress"),
    0x111168: ("f0b55746", "eve_load_present"),
    0x1112E8: ("f0b55746", "eve_save_present"),
    0x1113E4: ("10b5e622", "eve_unlock_present"),
    0x1113F8: ("f8b5e823", "eve_received_present"),
    0x11143C: ("70b5061c", "eve_remaining"),
    0x0B0DE0: ("f0b55f46", "eve_receive_present"),
}
STAGE_TEXTURE_CALLS = {
    0x0F3B16: "7ff7e2ea",
    0x0F3B6C: "7ff7b6ea",
    0x0F3BC0: "7ff78cea",
    0x0F3C34: "7ff752ea",
    0x0F3CAC: "7ff716ea",
}
LINK_SYMBOLS = {
    "event_manager": 0x11BFA9,
    "save_missions": 0x11B7B5,
    "apply_missions": 0x11B9A9,
    "show_dialog_continue": 0x0BA7E1,
    "show_banner_continue": 0x0763F5,
    "pet_manager": 0x10F201,
    "get_pet": 0x10ED25,
    "load_background_continue": 0x0F6D51,
    "original_set_scene": 0x2ACF61,
    "load_winter_images": 0x134B35,
    "reload_stage_background": 0x0F3AC5,
    "create_texture": 0x730DC,
    "find_actor": 0x732D4,
    "set_label": 0x743B4,
    "get_rect": 0x748C4,
    "get_layer": 0x739F4,
    "copy_actor": 0x73658,
    "delete_actor": 0x73CF4,
    "set_actor_id": 0x74960,
    "set_position": 0x74678,
    "show_actor": 0x74A2C,
    "local_string": 0x171625,
    "format_text": 0x7376C,
    "string_create": 0x74978,
    "string_destroy": 0x73DCC,
    "string_commas": 0x73B74,
    "string_data": 0x73958,
    "__aeabi_fadd": 0x72F08,
    "__aeabi_fsub": 0x7457C,
    "receive_present_continue": 0x0B0DE5,
    "temp_path": 0x748E8,
    "file_create": 0x73FE8,
    "file_decrypt": 0x74198,
    "file_encrypt": 0x739AC,
    "file_close": 0x72F14,
    "stdio_open": 0x73AE4,
    "stdio_read": 0x73AB4,
    "stdio_close": 0x73A6C,
    "pet_owned": 0x1104FD,
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(command: list, output: Path) -> None:
    result = subprocess.run([str(x) for x in command], capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    with (output / "commands.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps({"command": [str(x) for x in command],
                              "exit_code": result.returncode,
                              "stdout": result.stdout, "stderr": result.stderr}) + "\n")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def thumb_jump(source: int, target: int) -> bytes:
    # Same signed 25-bit Thumb-2 branch encoding used by the V26 patcher.
    delta = (target & ~1) - (source + 4)
    if delta & 1 or not -(1 << 24) <= delta < (1 << 24):
        raise ValueError("Thumb branch is out of range")
    value = delta & 0x1FFFFFF
    sign = (value >> 24) & 1
    j1 = (~(((value >> 23) & 1) ^ sign)) & 1
    j2 = (~(((value >> 22) & 1) ^ sign)) & 1
    return struct.pack("<HH", 0xF000 | (sign << 10) | ((value >> 12) & 0x3FF),
                       0x9000 | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF))


def compile_helper(output: Path, address: int) -> tuple[bytes, dict[str, int]]:
    output.mkdir(parents=True, exist_ok=True)
    definitions = [f"-D{pet.upper()}_{kind}={value}" for pet, values in GOALS.items()
                   for kind, value in zip(("SCORE", "BOXES", "COINS"), values)]
    compiler = [LLVM / "clang.exe", "--target=armv7a-linux-androideabi", "-mthumb",
                "-mfloat-abi=soft", "-fPIC", "-fvisibility=hidden", "-Oz",
                "-ffreestanding", "-fno-builtin", "-fno-stack-protector",
                "-fno-unwind-tables", "-fno-asynchronous-unwind-tables"]
    run(compiler + ["-std=c11", "-Wall", "-Wextra", "-Werror", *definitions,
                    "-c", OUTPUT_DIR / "v43_christmas.c", "-o", output / "challenge.o"], output)
    run(compiler + ["-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-c", OUTPUT_DIR / "v43_eve.c", "-o", output / "eve.o"], output)
    run(compiler + ["-c", OUTPUT_DIR / "v43_entry.S", "-o", output / "entry.o"], output)
    # --defsym creates STT_NOTYPE symbols: LLD then leaves Thumb BL calls
    # targeting ARM PLT code instead of emitting interworking BLX calls.
    bindings = output / "bindings.inc"
    bindings.write_text(".syntax unified\n.arm\n" + "".join(
        f".global {name}\n.type {name}, %function\n"
        f"{'.thumb_set' if value & 1 else '.set'} {name}, {value:#x}\n"
        for name, value in LINK_SYMBOLS.items()), encoding="utf-8")
    run(compiler + ["-x", "assembler", "-c", bindings,
                    "-o", output / "bindings.o"], output)
    script = output / "helper.ld"
    script.write_text(f"SECTIONS {{ . = {address:#x}; .text : {{ *(.text*) *(.rodata*) }} "
                      "/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) } }\n", encoding="utf-8")
    linked = output / "challenge.elf"
    run([LLVM / "ld.lld.exe", "--no-undefined", "-T", script,
         output / "challenge.o", output / "eve.o", output / "entry.o", output / "bindings.o",
         "-o", linked], output)
    with linked.open("rb") as stream:
        elf = ELFFile(stream)
        # Every address must be PC-relative or a resolved relative call.
        for section in elf.iter_sections():
            if section["sh_size"] and (section["sh_type"] in {"SHT_REL", "SHT_RELA"}
                                       or section.name in {".got", ".got.plt", ".data", ".bss"}):
                raise ValueError(f"non-PIC helper section: {section.name}")
        code = elf.get_section_by_name(".text").data()
        symbols = {symbol.name: symbol["st_value"] for symbol in
                   elf.get_section_by_name(".symtab").iter_symbols() if symbol.name}
    return code, symbols


def patch_inventory_library(source: bytes, output: Path) -> tuple[bytes, dict]:
    expected_hash = "43558dd75a1fa5420decd9d2bc5cab405ab13c6056c04a5748890e34e3f2f8ae"
    if digest(source) != expected_hash:
        raise ValueError("unexpected frozen V42 inventory engine SHA-256")
    output.mkdir(parents=True, exist_ok=True)
    elf = ELFFile(io.BytesIO(source))
    segments = list(elf.iter_segments())
    if elf.elfclass != 32 or elf["e_phentsize"] != 32 or elf["e_phnum"] != 5:
        raise ValueError("unexpected inventory engine ELF layout")
    file_start = (len(source) + 4095) & ~4095
    virtual_start = (max(s["p_vaddr"] + s["p_memsz"] for s in segments
                         if s["p_type"] == "PT_LOAD") + 4095) & ~4095
    table_size = (len(segments) + 2) * 32
    address = virtual_start + table_size
    bindings = {
        "id_string_create": 0x9F8D5, "id_string_destroy": 0xA0889,
        "id_get_string": 0x11A51D, "id_update_string": 0x11B27D,
        "id_get_item": 0x119DD5, "id_update_item": 0x119D45,
        "id_message_destroy": 0x119E21,
        "inventory_use_continue": 0x134B6B,
        "inventory_count_continue": 0x13472D,
        "inventory_no_match": 0x134797, "inventory_match": 0x134935,
    }
    compiler = [LLVM / "clang.exe", "--target=armv7a-linux-androideabi", "-mthumb",
                "-mfloat-abi=soft", "-fPIC", "-fvisibility=hidden", "-Oz",
                "-ffreestanding", "-fno-builtin", "-fno-stack-protector",
                "-fno-unwind-tables", "-fno-asynchronous-unwind-tables"]
    run(compiler + ["-std=c11", "-Wall", "-Wextra", "-Werror", "-c",
                    OUTPUT_DIR / "v43_inventory.c", "-o", output / "inventory.o"], output)
    run(compiler + ["-c", OUTPUT_DIR / "v43_inventory.S",
                    "-o", output / "inventory-entry.o"], output)
    binding_source = output / "inventory-bindings.inc"
    binding_source.write_text(".syntax unified\n.thumb\n" + "".join(
        f".global {name}\n.type {name}, %function\n.thumb_set {name}, {value:#x}\n"
        for name, value in bindings.items()), encoding="utf-8")
    run(compiler + ["-x", "assembler", "-c", binding_source,
                    "-o", output / "inventory-bindings.o"], output)
    script = output / "inventory.ld"
    script.write_text(f"SECTIONS {{ . = {address:#x}; .text : {{ *(.text*) *(.rodata*) }} "
                      "/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) } }\n",
                      encoding="utf-8")
    linked = output / "inventory.elf"
    run([LLVM / "ld.lld.exe", "--no-undefined", "-T", script,
         output / "inventory.o", output / "inventory-entry.o",
         output / "inventory-bindings.o", "-o", linked], output)
    helper = ELFFile(io.BytesIO(linked.read_bytes()))
    for section in helper.iter_sections():
        if section["sh_size"] and (section["sh_type"] in {"SHT_REL", "SHT_RELA"}
                                   or section.name in {".got", ".got.plt", ".data", ".bss"}):
            raise ValueError(f"non-PIC inventory section: {section.name}")
    code = helper.get_section_by_name(".text").data()
    symbols = {s.name: s["st_value"] for s in
               helper.get_section_by_name(".symtab").iter_symbols() if s.name}
    library = bytearray(source)
    hooks = {
        0x134AEC: ("2849e7ad", "inventory_select_entry"),
        0x1346FA: ("87ad0c99", "inventory_request_entry"),
        0x13475E: ("0999069a", "inventory_compare_entry"),
    }
    for target, (expected, symbol) in hooks.items():
        offset = vaddr_to_offset(elf, target)
        if source[offset:offset + 4] != bytes.fromhex(expected):
            raise ValueError(f"unexpected inventory instructions at {target:#x}")
        library[offset:offset + 4] = thumb_jump(target, symbols[symbol])
    old_table = source[elf["e_phoff"]:elf["e_phoff"] + len(segments) * 32]
    load_size = table_size + len(code)
    # Without PT_PHDR Android assumes load_bias + e_phoff. The appended
    # file offset differs from its virtual address because of the old BSS.
    # Describe the table explicitly, before every PT_LOAD as ELF requires.
    phdr = struct.pack("<8I", 6, file_start, virtual_start, virtual_start,
                       table_size, table_size, 4, 4)
    new_header = struct.pack("<8I", 1, file_start, virtual_start, virtual_start,
                             load_size, load_size, 5, 4096)
    library.extend(bytes(file_start - len(library)))
    library.extend(phdr + old_table + new_header + code)
    struct.pack_into("<I", library, 28, file_start)
    struct.pack_into("<H", library, 44, len(segments) + 2)
    result = bytes(library)
    return result, {"source_sha256": expected_hash, "sha256": digest(result),
                    "transaction_ids": "opaque_strings",
                    "helper_symbols": symbols, "code_address": address,
                    "code_size": len(code), "save_migration_required": False}


def patch_library(source: bytes, output: Path) -> tuple[bytes, dict]:
    if digest(source) != LIBRARY_SHA256:
        raise ValueError("unexpected V42 gameplay library SHA-256")
    elf = ELFFile(io.BytesIO(source))
    segments = list(elf.iter_segments())
    if elf.elfclass != 32 or elf["e_phentsize"] != 32 or elf["e_phnum"] != 5:
        raise ValueError("unexpected V42 ELF program-header layout")
    file_start = (len(source) + 4095) & ~4095
    virtual_start = (max(s["p_vaddr"] + s["p_memsz"] for s in segments
                         if s["p_type"] == "PT_LOAD") + 4095) & ~4095
    table_size = (len(segments) + 1) * 32
    code_start = virtual_start + table_size
    code, symbols = compile_helper(output, code_start)
    library = bytearray(source)

    def replace(address: int, expected: bytes, replacement: bytes) -> None:
        offset = vaddr_to_offset(elf, address)
        if len(expected) != len(replacement) or library[offset:offset + len(expected)] != expected:
            raise ValueError(f"unexpected hook bytes at {address:#x}")
        library[offset:offset + len(expected)] = replacement

    for address, (expected, symbol) in HOOKS.items():
        replace(address, bytes.fromhex(expected), thumb_jump(address, symbols[symbol]))
    for address, expected in STAGE_TEXTURE_CALLS.items():
        first, second = struct.unpack("<HH", thumb_jump(address, symbols["christmas_stage_texture"]))
        replace(address, bytes.fromhex(expected), struct.pack("<HH", first, second | 0x4000))
    # The manager allocates 0x40 bytes, with one winter flag at 0x3c and three
    # padding bytes. Zero the word so the new transient theme byte starts unknown.
    replace(0x11BF9C, bytes.fromhex("8354"), bytes.fromhex("8350"))
    # The only setter caller is Eve's unlock callback. It used time(NULL)-60
    # to request an immediate first gift, mixing wall and offline server time.
    replace(0x168294, bytes.fromhex("00200bf7b0ec011c3c39"),
            bytes.fromhex("0021") + bytes.fromhex("00bf") * 4)
    # Keep the catalog's event ID/types stable for owned pets and claim routing.
    # Only activity/visibility changes with ownership, never pet classification.
    replace(0x17920C, bytes.fromhex("011c"), bytes.fromhex("0121"))
    replace(0x11B9DC, bytes.fromhex("10b55bf0"), bytes.fromhex("02207047"))
    # Keep all original RX/RW segments and section offsets unchanged. Place a
    # replacement PHDR table inside a separate, page-aligned, read/execute LOAD;
    # Android can locate the in-memory table through that LOAD's file range.
    old_table = source[elf["e_phoff"]:elf["e_phoff"] + len(segments) * 32]
    load_size = table_size + len(code)
    new_header = struct.pack("<8I", 1, file_start, virtual_start, virtual_start,
                             load_size, load_size, 5, 4096)
    library.extend(bytes(file_start - len(library)))
    library.extend(old_table + new_header + code)
    struct.pack_into("<I", library, 28, file_start)
    struct.pack_into("<H", library, 44, len(segments) + 1)
    result = bytes(library)
    checked = ELFFile(io.BytesIO(result))
    assert vaddr_to_offset(checked, code_start) == file_start + table_size
    assert checked.num_segments() == 6
    return result, {"goals": GOALS, "code_address": code_start, "code_size": len(code),
                    "helper_symbols": symbols, "library_sha256": digest(result),
                    "shared_progress": True, "claim_cost_coins": 0, "claim_cost_gems": 0,
                    "event_ends_when": "both_pets_owned",
                    "artwork_reconciliation": "main_menu_and_pet_inventory",
                    "eve_cooldown": {"seconds": 21600, "clock": "CLOCK_BOOTTIME",
                                     "first_gift": "immediately_available",
                                     "profile_version": "EVE1",
                                     "reboot_policy": "resume_saved_remaining",
                                     "checkpoint_seconds": 60}}


def patch_localization(data: bytes) -> bytes:
    text = data.decode("utf-8-sig")
    # Override only event-specific copy. Missing locale keys get the same
    # explicit fallback; ordinary friendship UI and pet abilities are untouched.
    for key, value in {"EVENT_DATE_DESC": "Until both claimed",
                       "EVENT_TITLE_DESC": "Collect both pets by completing their three goals.",
                       "EVENT_COLLECT_MYSTERYBOX": "Open Mystery Boxes"}.items():
        pattern = rf"(<key>{key}</key>\s*<string>).*?(</string>)"
        text, count = re.subn(pattern, lambda m: m[1] + value + m[2], text, flags=re.S)
        if count == 0:
            addition = f"\t<key>{key}</key>\n\t<string>{value}</string>\n"
            text, count = re.subn(r"(?=</dict>\s*</plist>\s*$)", lambda m: addition, text)
        if count != 1:
            raise ValueError(f"ambiguous localization key {key}")
    return text.encode("utf-8")


def build(source: Path, output: Path) -> dict:
    if digest(source.read_bytes()) != SOURCE_SHA256:
        raise ValueError("unexpected frozen V42 APK SHA-256")
    output.mkdir(parents=True, exist_ok=True)
    unsigned = output / "BirzzleFever-1.1.2-v43-offline-christmas-unsigned.apk"
    signed = output / "BirzzleFever-1.1.2-v43-offline-christmas-test.apk"
    with zipfile.ZipFile(source) as original:
        library, report = patch_library(original.read("lib/armeabi/libbirzzle.so"), output)
        (output / "libbirzzle-v43-offline-christmas.so").write_bytes(library)
        engine, inventory_report = patch_inventory_library(
            original.read("lib/armeabi/libef2d.so"), output)
        (output / "libef2d-v43-inventory-ids.so").write_bytes(engine)
        report["inventory_ids"] = inventory_report
        expected = {}
        changed = []
        with zipfile.ZipFile(unsigned, "w") as result:
            for entry in original.infolist():
                if entry.filename.upper().startswith("META-INF/"):
                    continue
                before = original.read(entry)
                after = before
                if entry.filename == "lib/armeabi/libbirzzle.so":
                    after = library
                elif entry.filename == "lib/armeabi/libef2d.so":
                    after = engine
                elif entry.filename.startswith("assets/Strings/Localization") and entry.filename.endswith(".plist"):
                    after = patch_localization(before)
                if after != before:
                    changed.append(entry.filename)
                expected[entry.filename] = digest(after)
                result.writestr(entry, after)
    keystore = ROOT / "xposed-birzzle-id-spoof/build/debug.keystore"
    run(["jarsigner", "-keystore", keystore, "-storepass", "android", "-keypass", "android",
         "-sigalg", "SHA256withRSA", "-digestalg", "SHA-256", "-signedjar", signed,
         unsigned, "androiddebugkey"], output)
    run(["jarsigner", "-verify", "-strict", "-keystore", keystore,
         "-storepass", "android", signed], output)
    with zipfile.ZipFile(signed) as result:
        actual = {entry.filename: digest(result.read(entry)) for entry in result.infolist()
                  if not entry.filename.upper().startswith("META-INF/")}
        if actual != expected:
            raise ValueError("signed APK payload mismatch")
    report.update({"source_apk_sha256": SOURCE_SHA256, "apk": str(signed),
                   "apk_sha256": digest(signed.read_bytes()), "changed_payloads": changed,
                   "all_other_payloads_unchanged": True, "debug_signed": True,
                   "strict_signature_verified": True, "device_qualified": False})
    (output / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_APK)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    report = build(args.source.resolve(), args.output.resolve())
    print(json.dumps({key: report[key] for key in
                     ("apk", "apk_sha256", "goals", "code_size", "changed_payloads", "strict_signature_verified")}, indent=2))
