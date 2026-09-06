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
OUTPUT_DIR = Path("native-patches/v28-mtime-diagnostic")
ASSEMBLY = OUTPUT_DIR / "v28_mtime_diagnostic.S"
OBJECT = OUTPUT_DIR / "v28_mtime_diagnostic.o"
HELPER_ELF = OUTPUT_DIR / "v28_mtime_diagnostic.elf"
HELPER_BINARY = OUTPUT_DIR / "v28_mtime_diagnostic.bin"
OUTPUT_LIBRARY = OUTPUT_DIR / "libef2d-v28-mtime-diagnostic.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v28-mtime-diagnostic-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v28-mtime-diagnostic.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")
LLVM_BIN = Path("tools/llvm-mingw-20260826-ucrt-x86_64/bin")
CLANG = str(LLVM_BIN / "clang.exe")
LD_LLD = str(LLVM_BIN / "ld.lld.exe")
LLVM_OBJCOPY = str(LLVM_BIN / "llvm-objcopy.exe")
EXPECTED_APK_SHA256 = "cf34c8e640ee785cf34d1b75d55b5610b01357fda9315c2f380d7a6923260ee8"
EXPECTED_LIBRARY_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
HELPER_OFFSET = 0x264448
HELPER_LIMIT = 0x264538
MTIME_HOOK_OFFSET = 0x121BE4
V26_MTIME_HOOK = bytes.fromhex("42f193b9")
STRRCHR_PLT = 0x96498
STRCMP_PLT = 0x96C78
ANDROID_LOG_PRINT = 0x966A8
MTIME_ACCEPT_RETURN = 0x121E08
MTIME_REJECT_RETURN = 0x121BEA


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    second = 0x9000 | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF)
    return struct.pack("<HH", first, second)


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
    f"--defsym=strrchr_plt={STRRCHR_PLT:#x}",
    f"--defsym=strcmp_plt={STRCMP_PLT:#x}",
    f"--defsym=android_log_print={ANDROID_LOG_PRINT:#x}",
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
    raise SystemExit("diagnostic helper does not fit code cave")
with HELPER_ELF.open("rb") as stream:
    elf = ELFFile(stream)
    symbols = elf.get_section_by_name(".symtab")
    entry = next(
        (symbol["st_value"] & ~1 for symbol in symbols.iter_symbols()
         if symbol.name == "diagnostic_mtime_guard"),
        None,
    )
if entry is None:
    raise SystemExit("missing diagnostic_mtime_guard symbol")

library = bytearray(SOURCE_LIBRARY.read_bytes())
if any(library[HELPER_OFFSET:HELPER_LIMIT]):
    raise SystemExit("diagnostic code cave is not empty")
if bytes(library[MTIME_HOOK_OFFSET:MTIME_HOOK_OFFSET + 4]) != V26_MTIME_HOOK:
    raise SystemExit("unexpected V26 mtime hook")
library[HELPER_OFFSET:HELPER_OFFSET + len(helper)] = helper
library[MTIME_HOOK_OFFSET:MTIME_HOOK_OFFSET + 4] = thumb2_branch(
    MTIME_HOOK_OFFSET, entry
)
OUTPUT_LIBRARY.write_bytes(library)

with zipfile.ZipFile(SOURCE_APK, "r") as source:
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
    raise SystemExit("V26 APK does not contain lib/armeabi/libef2d.so")
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
print(f"helper_size={len(helper)}")
print(f"helper_sha256={hashlib.sha256(helper).hexdigest()}")
print(f"libef2d_sha256={sha256(OUTPUT_LIBRARY)}")
print(f"signed_apk_sha256={sha256(SIGNED_APK)}")
