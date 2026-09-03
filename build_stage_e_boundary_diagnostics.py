import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path


BASE_DIR = Path("native-patches/v23-request-first-index")
OUTPUT = BASE_DIR / "stage-e-interrupted-writes" / "diagnostics"
OUTPUT.mkdir(parents=True, exist_ok=True)
BASE_LIBRARY = BASE_DIR / "libef2d.so"
BASE_UNSIGNED_APK = BASE_DIR / "BirzzleFever-1.1.2-v23-request-first-index-unsigned.apk"
KEYSTORE = OUTPUT / "stage-e-test.keystore"
STOREPASS = "stageetest"
ALIAS = "stagee"
LLVM_BIN = Path("tools/llvm-mingw-20260826-ucrt-x86_64/bin")
CLANG = str(LLVM_BIN / "clang.exe")
LD_LLD = str(LLVM_BIN / "ld.lld.exe")
LLVM_OBJCOPY = str(LLVM_BIN / "llvm-objcopy.exe")
EXPECTED_BASE_SHA256 = "a66f91a1e498c325d4f9ef8e78df5bd4f71d4fce44b6fbcb5d51425eb3e83145"
STUB_OFFSET = 0x27BFEE
STUB_LIMIT = 0x27C000
RX_FILE_SIZE_OFFSET = 52 + 32 + 16
RX_MEMORY_SIZE_OFFSET = 52 + 32 + 20

VARIANTS = {
    "after-numbered-before-index": {
        "hook": 0x132018,
        "expected": bytes.fromhex("eff75cf8"),
        "resume": 0x132018,
        "pop_writer_frame": False,
    },
    "after-temp-before-rename": {
        "hook": 0x27BF9C,
        "expected": bytes.fromhex("fff760fe"),
        "resume": 0x27BF9C,
        "pop_writer_frame": False,
    },
    "immediately-after-rename": {
        "hook": 0x27BFAA,
        "expected": bytes.fromhex("fff759fe"),
        "resume": 0x27BFAA,
        "pop_writer_frame": False,
    },
}


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


def build_pause_stub(name: str, resume: int, pop_writer_frame: bool) -> bytes:
    directory = OUTPUT / name
    directory.mkdir(exist_ok=True)
    source = directory / "pause.S"
    object_file = directory / "pause.o"
    elf_file = directory / "pause.elf"
    binary_file = directory / "pause.bin"
    source.write_text(
        ".syntax unified\n"
        ".thumb\n"
        ".section .text\n"
        ".global pause_stub\n"
        ".thumb_func\n"
        "pause_stub:\n"
        "    movs    r7, #29\n"
        "    svc     #0\n"
        "    b       pause_stub\n",
        encoding="ascii",
    )
    run(
        CLANG, "--target=armv7-none-linux-gnueabi", "-march=armv7-a",
        "-mthumb", "-c", str(source), "-o", str(object_file),
    )
    run(
        LD_LLD, "-m", "armelf_linux_eabi", f"-Ttext={STUB_OFFSET:#x}",
        f"--defsym=resume={resume:#x}",
        str(object_file), "-o", str(elf_file),
    )
    run(
        LLVM_OBJCOPY, "-O", "binary", "--only-section=.text",
        str(elf_file), str(binary_file),
    )
    stub = binary_file.read_bytes()
    if len(stub) > STUB_LIMIT - STUB_OFFSET:
        raise SystemExit(f"{name}: pause stub is too large: {len(stub)}")
    return stub


def build_library(name: str, config: dict) -> Path:
    data = bytearray(BASE_LIBRARY.read_bytes())
    hook = config["hook"]
    expected = config["expected"]
    if bytes(data[hook : hook + 4]) != expected:
        raise SystemExit(f"{name}: unexpected hook bytes")
    if any(data[STUB_OFFSET:STUB_LIMIT]):
        raise SystemExit(f"{name}: diagnostic cave is not empty")
    stub = build_pause_stub(name, config["resume"], config["pop_writer_frame"])
    data[hook : hook + 4] = thumb2_branch(hook, STUB_OFFSET)
    data[STUB_OFFSET : STUB_OFFSET + len(stub)] = stub
    data[RX_FILE_SIZE_OFFSET : RX_FILE_SIZE_OFFSET + 4] = struct.pack("<I", STUB_LIMIT)
    data[RX_MEMORY_SIZE_OFFSET : RX_MEMORY_SIZE_OFFSET + 4] = struct.pack("<I", STUB_LIMIT)
    library = OUTPUT / name / "libef2d.so"
    library.write_bytes(data)
    return library


def build_apk(name: str, library: Path) -> Path:
    directory = OUTPUT / name
    unsigned = directory / f"BirzzleFever-1.1.2-v23-stage-e-{name}-unsigned.apk"
    signed = directory / f"BirzzleFever-1.1.2-v23-stage-e-{name}.apk"
    with zipfile.ZipFile(BASE_UNSIGNED_APK, "r") as source, zipfile.ZipFile(unsigned, "w") as target:
        for item in source.infolist():
            payload = (
                library.read_bytes()
                if item.filename == "lib/armeabi/libef2d.so"
                else source.read(item.filename)
            )
            target.writestr(item, payload)
    shutil.copyfile(unsigned, signed)
    run(
        "jarsigner", "-keystore", str(KEYSTORE), "-storepass", STOREPASS,
        "-keypass", STOREPASS, "-sigalg", "SHA256withRSA", "-digestalg", "SHA-256",
        str(signed), ALIAS,
    )
    run("jarsigner", "-verify", str(signed))
    with zipfile.ZipFile(signed, "r") as archive:
        if archive.read("lib/armeabi/libef2d.so") != library.read_bytes():
            raise SystemExit(f"{name}: signed APK library mismatch")
    return signed


if sha256(BASE_LIBRARY) != EXPECTED_BASE_SHA256:
    raise SystemExit("unexpected v22 base library")
if not KEYSTORE.exists():
    run(
        "keytool", "-genkeypair", "-keystore", str(KEYSTORE),
        "-storepass", STOREPASS, "-keypass", STOREPASS, "-alias", ALIAS,
        "-dname", "CN=Birzzle Stage E Diagnostic,O=Local Test,C=CA",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650",
    )

manifest = {}
for variant_name, variant_config in VARIANTS.items():
    diagnostic_library = build_library(variant_name, variant_config)
    diagnostic_apk = build_apk(variant_name, diagnostic_library)
    manifest[variant_name] = {
        "hook": f"{variant_config['hook']:#x}",
        "resume": f"{variant_config['resume']:#x}",
        "pause_loop": "blocking direct pause syscall",
        "stub_offset": f"{STUB_OFFSET:#x}",
        "stub_sha256": sha256(OUTPUT / variant_name / "pause.bin"),
        "libef2d_sha256": sha256(diagnostic_library),
        "apk_sha256": sha256(diagnostic_apk),
        "apk": str(diagnostic_apk),
    }

(OUTPUT / "manifest.json").write_text(
    __import__("json").dumps(manifest, indent=2) + "\n", encoding="utf-8"
)
print(__import__("json").dumps(manifest, indent=2))
