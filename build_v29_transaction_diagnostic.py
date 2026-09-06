import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path

from elftools.elf.elffile import ELFFile


SOURCE_DIR = Path("native-patches/v26-modern-syscalls")
SOURCE_APK = SOURCE_DIR / "BirzzleFever-1.1.2-v26-modern-syscalls.apk"
SOURCE_LIBRARY = SOURCE_DIR / "libef2d-v26-modern-syscalls.so"
OUTPUT_DIR = Path("native-patches/v29-v26-transaction-diagnostic")
ASSEMBLY = OUTPUT_DIR / "v29_transaction_diagnostic.S"
OBJECT = OUTPUT_DIR / "v29_transaction_diagnostic.o"
HELPER_ELF = OUTPUT_DIR / "v29_transaction_diagnostic.elf"
HELPER_BINARY = OUTPUT_DIR / "v29_transaction_diagnostic.bin"
OUTPUT_LIBRARY = OUTPUT_DIR / "libef2d-v29-transaction-diagnostic.so"
DECODED = OUTPUT_DIR / "apktool"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v29-transaction-diagnostic-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v29-transaction-diagnostic.apk"
VERIFY_DECODED = OUTPUT_DIR / "verification-decode"
APKTOOL = Path("tools/apktool_2.12.1.jar")
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")
LLVM_BIN = Path("tools/llvm-mingw-20260826-ucrt-x86_64/bin")
CLANG = str(LLVM_BIN / "clang.exe")
LD_LLD = str(LLVM_BIN / "ld.lld.exe")
LLVM_OBJCOPY = str(LLVM_BIN / "llvm-objcopy.exe")

EXPECTED_APK_SHA256 = "cf34c8e640ee785cf34d1b75d55b5610b01357fda9315c2f380d7a6923260ee8"
EXPECTED_LIBRARY_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_BIRZZLE_SHA256 = "bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

HELPER_OFFSET = 0x264448
HELPER_LIMIT = 0x264538
ANDROID_LOG_PRINT = 0x966A8
COMPAT_OPEN_TEMP = 0x263E7C
COMPAT_RENAME_INDEX = 0x263E9C
COMPAT_OPEN_DIRECTORY = 0x263EBE
COMPAT_UNLINK_TEMP = 0x263EEE

# Each existing V26 hook is replaced with a call to a logging wrapper. The
# wrappers call the original V26 helper and return its result unchanged.
HOOKS = {
    0x27BF70: (bytes.fromhex("e7f784ff"), "diagnostic_open_temp"),
    0x27BF80: (bytes.fromhex("762700df"), "diagnostic_fsync_temp"),
    0x27BF9C: (bytes.fromhex("e7f77eff"), "diagnostic_rename_index"),
    0x27BFAA: (bytes.fromhex("e7f788ff"), "diagnostic_open_directory"),
    0x27BFBE: (bytes.fromhex("762700df"), "diagnostic_fsync_directory"),
    0x27BFDC: (bytes.fromhex("e7f787ff"), "diagnostic_unlink_temp"),
}


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


def symbols(path: Path) -> dict[str, int]:
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        table = elf.get_section_by_name(".symtab")
        return {
            symbol.name: symbol["st_value"] & ~1
            for symbol in table.iter_symbols()
            if symbol.name
        }


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if sha256(SOURCE_APK) != EXPECTED_APK_SHA256:
    raise SystemExit("unexpected V26 APK SHA-256")
if sha256(SOURCE_LIBRARY) != EXPECTED_LIBRARY_SHA256:
    raise SystemExit("unexpected V26 libef2d SHA-256")

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
    f"--defsym=compat_open_temp={COMPAT_OPEN_TEMP:#x}",
    f"--defsym=compat_rename_index={COMPAT_RENAME_INDEX:#x}",
    f"--defsym=compat_open_directory={COMPAT_OPEN_DIRECTORY:#x}",
    f"--defsym=compat_unlink_temp={COMPAT_UNLINK_TEMP:#x}",
    f"--defsym=android_log_print={ANDROID_LOG_PRINT:#x}",
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
        f"diagnostic helper does not fit: {HELPER_OFFSET:#x}+{len(helper):#x}>{HELPER_LIMIT:#x}"
    )
helper_symbols = symbols(HELPER_ELF)
required = {symbol for _, symbol in HOOKS.values()}
if not required <= helper_symbols.keys():
    raise SystemExit(f"missing helper symbols: {sorted(required - helper_symbols.keys())}")

library = bytearray(SOURCE_LIBRARY.read_bytes())
if any(library[HELPER_OFFSET:HELPER_LIMIT]):
    raise SystemExit("V26 diagnostic code cave is not empty")
library[HELPER_OFFSET:HELPER_OFFSET + len(helper)] = helper
for offset, (expected, symbol) in HOOKS.items():
    actual = bytes(library[offset:offset + 4])
    if actual != expected:
        raise SystemExit(
            f"unexpected hook bytes at {offset:#x}: {actual.hex()} != {expected.hex()}"
        )
    target = helper_symbols[symbol]
    library[offset:offset + 4] = thumb2_branch(offset, target)
    print(f"{symbol}: {offset:#x} -> {target:#x}")
OUTPUT_LIBRARY.write_bytes(library)

with zipfile.ZipFile(SOURCE_APK, "r") as source:
    if sha256_bytes(source.read("lib/armeabi/libbirzzle.so")) != EXPECTED_BIRZZLE_SHA256:
        raise SystemExit("unexpected V26 libbirzzle SHA-256")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("unexpected V26 embedded seed SHA-256")

if DECODED.exists():
    shutil.rmtree(DECODED)
run("java", "-jar", str(APKTOOL), "d", "-f", str(SOURCE_APK), "-o", str(DECODED))
manifest_path = DECODED / "AndroidManifest.xml"
manifest = manifest_path.read_text(encoding="utf-8")
if "android:debuggable=" in manifest:
    raise SystemExit("source manifest unexpectedly already declares android:debuggable")
needle = "<application "
if manifest.count(needle) != 1:
    raise SystemExit("unable to identify application element")
manifest = manifest.replace(needle, '<application android:debuggable="true" ', 1)
manifest_path.write_text(manifest, encoding="utf-8", newline="\n")
shutil.copyfile(OUTPUT_LIBRARY, DECODED / "lib/armeabi/libef2d.so")

if UNSIGNED_APK.exists():
    UNSIGNED_APK.unlink()
run("java", "-jar", str(APKTOOL), "b", str(DECODED), "-o", str(UNSIGNED_APK))
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
        raise SystemExit("signed APK embedded seed mismatch")

if VERIFY_DECODED.exists():
    shutil.rmtree(VERIFY_DECODED)
run("java", "-jar", str(APKTOOL), "d", "-f", str(SIGNED_APK), "-o", str(VERIFY_DECODED))
verified_manifest = (VERIFY_DECODED / "AndroidManifest.xml").read_text(encoding="utf-8")
if 'android:debuggable="true"' not in verified_manifest:
    raise SystemExit("rebuilt APK is not debuggable")

print(f"helper_size={len(helper)}")
print(f"helper_sha256={sha256(HELPER_BINARY)}")
print(f"libef2d_sha256={sha256(OUTPUT_LIBRARY)}")
print(f"unsigned_apk_sha256={sha256(UNSIGNED_APK)}")
print(f"signed_apk_sha256={sha256(SIGNED_APK)}")
