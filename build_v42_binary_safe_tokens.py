import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v41-dual-powerup-scene-rearm/"
    "BirzzleFever-1.1.2-v41-dual-powerup-scene-rearm.apk"
)
OUTPUT_DIR = Path("native-patches/v42-binary-safe-tokens")
OUTPUT_LIBRARY = OUTPUT_DIR / "libef2d-v42-binary-safe-tokens.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v42-binary-safe-tokens-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v42-binary-safe-tokens.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")
EXPECTED_SOURCE_APK_SHA256 = "5a1ed5e21b5709c305251eb7b83340d7beb941f27f97ac9db1070fc13146cf88"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
TOKEN_LENGTH_OFFSET = 0x122CA6
# GenerateToken: strlen(binary_md5) -> constant digest length. The following
# mov r2,r0 passes that length to base64EncodeData; no calling-convention change.
EXPECTED_INSTRUCTIONS = bytes.fromhex("73f758ec")
REPLACEMENT_INSTRUCTIONS = bytes.fromhex("102000bf")  # movs r0,#16; nop


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_library(source: bytes) -> bytes:
    if sha256(source) != EXPECTED_EF2D_SHA256:
        raise ValueError("unexpected V41 libef2d SHA-256")
    end = TOKEN_LENGTH_OFFSET + len(EXPECTED_INSTRUCTIONS)
    if source[TOKEN_LENGTH_OFFSET:end] != EXPECTED_INSTRUCTIONS:
        raise ValueError("unexpected GenerateToken strlen instructions")
    library = bytearray(source)
    library[TOKEN_LENGTH_OFFSET:end] = REPLACEMENT_INSTRUCTIONS
    return bytes(library)


def main():
    if sha256(SOURCE_APK.read_bytes()) != EXPECTED_SOURCE_APK_SHA256:
        raise SystemExit("unexpected V41 source APK SHA-256")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE_APK) as source:
        library = patch_library(source.read("lib/armeabi/libef2d.so"))
        OUTPUT_LIBRARY.write_bytes(library)
        temporary = UNSIGNED_APK.with_suffix(".tmp.apk")
        with zipfile.ZipFile(temporary, "w") as output:
            for item in source.infolist():
                if item.filename.upper().startswith("META-INF/"):
                    continue
                payload = source.read(item.filename)
                if item.filename == "lib/armeabi/libef2d.so":
                    payload = library
                output.writestr(item, payload)
        temporary.replace(UNSIGNED_APK)

    shutil.copyfile(UNSIGNED_APK, SIGNED_APK)
    subprocess.run(
        ["jarsigner", "-keystore", str(KEYSTORE), "-storepass", "android",
         "-keypass", "android", "-sigalg", "SHA256withRSA", "-digestalg",
         "SHA-256", str(SIGNED_APK), "androiddebugkey"],
        check=True,
    )
    subprocess.run(["jarsigner", "-verify", str(SIGNED_APK)], check=True)
    with zipfile.ZipFile(SOURCE_APK) as source, zipfile.ZipFile(SIGNED_APK) as result:
        payload_names = {
            name for name in source.namelist() if not name.upper().startswith("META-INF/")
        }
        if payload_names != {
            name for name in result.namelist() if not name.upper().startswith("META-INF/")
        }:
            raise SystemExit("signed APK payload inventory changed")
        for name in payload_names:
            expected = library if name == "lib/armeabi/libef2d.so" else source.read(name)
            if result.read(name) != expected:
                raise SystemExit(f"signed APK payload mismatch: {name}")

    report = {
        "candidate": "V42 binary-safe tokens",
        "source_apk_sha256": EXPECTED_SOURCE_APK_SHA256,
        "source_libef2d_sha256": EXPECTED_EF2D_SHA256,
        "libef2d_sha256": sha256(library),
        "unsigned_apk_sha256": sha256(UNSIGNED_APK.read_bytes()),
        "signed_apk_sha256": sha256(SIGNED_APK.read_bytes()),
        "patch": {
            "function": "Enfeel::MathUtility::GenerateToken()",
            "offset": hex(TOKEN_LENGTH_OFFSET),
            "before": EXPECTED_INSTRUCTIONS.hex(),
            "after": REPLACEMENT_INSTRUCTIONS.hex(),
            "effect": "Base64-encode all 16 binary MD5 bytes, including zero bytes",
        },
        "all_other_apk_payloads_unchanged": True,
        "existing_fail_closed_pool_guards_unchanged": True,
        "device_qualified": False,
    }
    (OUTPUT_DIR / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
