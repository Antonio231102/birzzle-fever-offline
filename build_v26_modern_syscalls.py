import argparse
import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path

from elftools.elf.elffile import ELFFile


SOURCE_DIR = Path("native-patches/v25-ranking-template")
SOURCE_APK = SOURCE_DIR / "BirzzleFever-1.1.2-v25-ranking-template.apk"
SOURCE_LIBRARY = SOURCE_DIR / "libef2d-v25-ranking-template.so"
OUTPUT_DIR = Path("native-patches/v26-modern-syscalls")
ASSEMBLY = OUTPUT_DIR / "v26_modern_syscalls.S"
OBJECT = OUTPUT_DIR / "v26_modern_syscalls.o"
HELPER_ELF = OUTPUT_DIR / "v26_modern_syscalls.elf"
HELPER_BINARY = OUTPUT_DIR / "v26_modern_syscalls.bin"
OUTPUT_LIBRARY = OUTPUT_DIR / "libef2d-v26-modern-syscalls.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v26-modern-syscalls-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v26-modern-syscalls.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")
LLVM_BIN = Path(__file__).resolve().parent / "tools/llvm-mingw-20260826-ucrt-x86_64/bin"
CLANG = str(LLVM_BIN / "clang.exe")
LD_LLD = str(LLVM_BIN / "ld.lld.exe")
LLVM_OBJCOPY = str(LLVM_BIN / "llvm-objcopy.exe")
EXPECTED_APK_SHA256 = "66006ed20a308d52660bea5154a513a64d07f4d7f8d725bd5f02077c70168b05"
EXPECTED_LIBRARY_SHA256 = "6f2b88586c798b924e612d14e26a18e0367101fdb29a8bd05c97b4131edaee9e"
EXPECTED_BIRZZLE_SHA256 = "bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"
HELPER_OFFSET = 0x263E5C
HELPER_LIMIT = 0x263F70
STRCPY_PLT = 0x96E7C
STRLEN_PLT = 0x96558
STRRCHR_PLT = 0x96498
STRCMP_PLT = 0x96C78
MTIME_ACCEPT_RETURN = 0x121E08
MTIME_REJECT_RETURN = 0x121BEA
NOP = bytes.fromhex("00bf")
PATCHES = {
    0x27BF70: (
        bytes.fromhex("fff776fe0021052700df"),
        "compat_open_temp",
        "temporary-index openat",
    ),
    0x27BF9C: (
        bytes.fromhex("fff760fe5146262700df"),
        "compat_rename_index",
        "atomic renameat",
    ),
    0x27BFAA: (
        bytes.fromhex("fff759fe2c3844f20001052700df"),
        "compat_open_directory",
        "parent-directory openat",
    ),
    0x27BFDC: (
        bytes.fromhex("fff740fe0a2700df"),
        "compat_unlink_temp",
        "temporary-index unlinkat",
    ),
}
MTIME_PATCH_OFFSET = 0x121BE4
MTIME_PATCH_EXPECTED = bytes.fromhex("5af17ab9")


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def thumb2_branch(source: int, target: int) -> bytes:
    offset = target - (source + 4)
    if offset & 1 or not -(1 << 24) <= offset < (1 << 24):
        raise ValueError(f"invalid Thumb-2 branch {source:#x} -> {target:#x}")
    value = offset & 0x1FFFFFF
    s = (value >> 24) & 1
    i1 = (value >> 23) & 1
    i2 = (value >> 22) & 1
    j1 = (~(i1 ^ s)) & 1
    j2 = (~(i2 ^ s)) & 1
    first = 0xF000 | (s << 10) | ((value >> 12) & 0x3FF)
    second = 0xD000 | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF)
    return struct.pack("<HH", first, second)


def thumb2_jump(source: int, target: int) -> bytes:
    linked = thumb2_branch(source, target)
    first, second = struct.unpack("<HH", linked)
    return struct.pack("<HH", first, (second & ~0x4000))


def helper_symbols() -> dict[str, int]:
    with HELPER_ELF.open("rb") as stream:
        elf = ELFFile(stream)
        table = elf.get_section_by_name(".symtab")
        return {
            symbol.name: symbol["st_value"] & ~1
            for symbol in table.iter_symbols()
            if symbol.name
        }


_parser = argparse.ArgumentParser(description="Apply the V26 syscall compatibility patch.")
_parser.add_argument("--native-only", action="store_true", help="Build only the native library; do not read, package, or sign an APK.")
_args = _parser.parse_args()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if not _args.native_only and sha256(SOURCE_APK) != EXPECTED_APK_SHA256:
    raise SystemExit("unexpected V25 APK SHA-256")
if sha256(SOURCE_LIBRARY) != EXPECTED_LIBRARY_SHA256:
    raise SystemExit("unexpected V25 libef2d SHA-256")

run(
    CLANG,
    "--target=armv7-none-linux-gnueabi",
    "-march=armv7-a",
    "-mthumb",
    "-c",
    str(ASSEMBLY),
    "-o",
    str(OBJECT),
)
run(
    LD_LLD,
    "-m",
    "armelf_linux_eabi",
    f"-Ttext={HELPER_OFFSET:#x}",
    f"--defsym=strcpy_plt={STRCPY_PLT:#x}",
    f"--defsym=strlen_plt={STRLEN_PLT:#x}",
    f"--defsym=strrchr_plt={STRRCHR_PLT:#x}",
    f"--defsym=strcmp_plt={STRCMP_PLT:#x}",
    f"--defsym=mtime_accept_return={MTIME_ACCEPT_RETURN:#x}",
    f"--defsym=mtime_reject_return={MTIME_REJECT_RETURN:#x}",
    str(OBJECT),
    "-o",
    str(HELPER_ELF),
)
run(
    LLVM_OBJCOPY,
    "-O",
    "binary",
    "--only-section=.text",
    str(HELPER_ELF),
    str(HELPER_BINARY),
)

helper = HELPER_BINARY.read_bytes()
if not helper or HELPER_OFFSET + len(helper) > HELPER_LIMIT:
    raise SystemExit(
        f"helper does not fit cave: {HELPER_OFFSET:#x}+{len(helper):#x}>{HELPER_LIMIT:#x}"
    )
symbols = helper_symbols()
required = {entry[1] for entry in PATCHES.values()} | {"compat_mtime_guard"}
if not required <= symbols.keys():
    raise SystemExit(f"missing helper symbols: {sorted(required - symbols.keys())}")

library = bytearray(SOURCE_LIBRARY.read_bytes())
if any(library[HELPER_OFFSET:HELPER_LIMIT]):
    raise SystemExit("V25 compatibility-helper cave is not empty")
library[HELPER_OFFSET:HELPER_OFFSET + len(helper)] = helper
for offset, (expected, symbol, label) in PATCHES.items():
    actual = bytes(library[offset:offset + len(expected)])
    if actual != expected:
        raise SystemExit(
            f"unexpected {label} bytes at {offset:#x}: {actual.hex()} != {expected.hex()}"
        )
    branch = thumb2_branch(offset, symbols[symbol])
    replacement = branch + NOP * ((len(expected) - len(branch)) // 2)
    if len(replacement) != len(expected):
        raise SystemExit(f"invalid replacement size for {label}")
    library[offset:offset + len(replacement)] = replacement
    print(f"{label}: {offset:#x} -> {symbols[symbol]:#x}")
actual_mtime = bytes(library[MTIME_PATCH_OFFSET:MTIME_PATCH_OFFSET + 4])
if actual_mtime != MTIME_PATCH_EXPECTED:
    raise SystemExit(
        f"unexpected mtime hook bytes: {actual_mtime.hex()} != {MTIME_PATCH_EXPECTED.hex()}"
    )
library[MTIME_PATCH_OFFSET:MTIME_PATCH_OFFSET + 4] = thumb2_jump(
    MTIME_PATCH_OFFSET, symbols["compat_mtime_guard"]
)
print(f"path-independent mtime guard: {MTIME_PATCH_OFFSET:#x} -> "
      f"{symbols['compat_mtime_guard']:#x}")
OUTPUT_LIBRARY.write_bytes(library)
if _args.native_only:
    print(f"native_sha256={hashlib.sha256(library).hexdigest()}")
    raise SystemExit(0)

with zipfile.ZipFile(SOURCE_APK, "r") as source:
    if sha256_bytes(source.read("lib/armeabi/libbirzzle.so")) != EXPECTED_BIRZZLE_SHA256:
        raise SystemExit("V25 libbirzzle mismatch")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("V25 seed mismatch")
    temporary = UNSIGNED_APK.with_suffix(".tmp.apk")
    with zipfile.ZipFile(temporary, "w") as output:
        found = False
        for item in source.infolist():
            if item.filename.upper().startswith("META-INF/"):
                continue
            payload = source.read(item.filename)
            if item.filename == "lib/armeabi/libef2d.so":
                payload = bytes(library)
                found = True
            output.writestr(item, payload)
if not found:
    raise SystemExit("V25 APK does not contain lib/armeabi/libef2d.so")
temporary.replace(UNSIGNED_APK)

shutil.copyfile(UNSIGNED_APK, SIGNED_APK)
run(
    "jarsigner",
    "-keystore",
    str(KEYSTORE),
    "-storepass",
    "android",
    "-keypass",
    "android",
    "-sigalg",
    "SHA256withRSA",
    "-digestalg",
    "SHA-256",
    str(SIGNED_APK),
    "androiddebugkey",
)
run("jarsigner", "-verify", str(SIGNED_APK))

with zipfile.ZipFile(SIGNED_APK, "r") as result:
    if result.read("lib/armeabi/libef2d.so") != bytes(library):
        raise SystemExit("signed APK libef2d mismatch")
    if sha256_bytes(result.read("lib/armeabi/libbirzzle.so")) != EXPECTED_BIRZZLE_SHA256:
        raise SystemExit("signed APK libbirzzle mismatch")
    if sha256_bytes(result.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("signed APK seed mismatch")

print(f"helper_size={len(helper)}")
print(f"helper_sha256={sha256(HELPER_BINARY)}")
print(f"libef2d_sha256={sha256(OUTPUT_LIBRARY)}")
print(f"unsigned_apk_sha256={sha256(UNSIGNED_APK)}")
print(f"signed_apk_sha256={sha256(SIGNED_APK)}")
