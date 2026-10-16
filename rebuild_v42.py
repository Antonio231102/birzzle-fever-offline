"""Rebuild and deterministically re-sign V42 from the original APK and offline seed."""

import argparse
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from build_v42_binary_safe_tokens import patch_library as patch_binary_tokens

ROOT = Path(__file__).resolve().parent
ORIGINAL_SHA256 = "9bdfd11afd542265dbbc228a0205336806a77e59c739cbefd2b6f22e8741088c"
SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"
RELEASE_SHA256 = "766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4"
NATIVE_SHA256 = {
    "libbirzzle.so": "087f0742624d3e57ba4277adf16685193556bc02ff3a6adf4904726e51879d56",
    "libef2d.so": "43558dd75a1fa5420decd9d2bc5cab405ab13c6056c04a5748890e34e3f2f8ae",
}
EARLY_PATCHES = (
    "patch_ranking_inflight_v4.py",
    "patch_unlimited_lives_v6.py",
    "patch_ranking_generation_v7.py",
    "patch_ranking_menu_rearm_v8.py",
    "patch_ranking_postrestore_v9.py",
    "patch_ranking_reject_cleanup_v10.py",
    "patch_ranking_dispatch_a_v12.py",
    "patch_powerup_pending_v13.py",
    "patch_powerup_scene_pending_v14.py",
)
LATE_PATCHES = (
    "build_v31_ranking_lineage_correction.py",
    "build_v32_pet_tutorial_ranking_rearm.py",
    "build_v33_pet_tutorial_retryable_ranking.py",
    "build_v34_isolated_pet_tutorial_ranking.py",
    "build_v35_pet_tutorial_state41_marker.py",
    "build_v36_buypet_response_ranking.py",
    "build_v37_global_powerup_scene_marker.py",
    "build_v41_dual_powerup_scene_rearm.py",
)
# Recovered link recipe for the authored V22 assembly. No historical ELF or blob
# is read during a rebuild; the patcher checks both freshly assembled sections.
RECOVERY_SYMBOLS = {
    "request_highwater": 0x294624,
    "string_copy_ctor": 0xA08AC,
    "file_worker_instance": 0x1210D4,
    "read_content": 0x1215A8,
    "node_deallocate": 0x209FF4,
    "operator_delete": 0x1ED7B4,
    "access_plt": 0x966B4,
    "strcmp_plt": 0x96C78,
    "usleep_plt": 0x96300,
    "fopen_plt": 0x96780,
    "fwrite_plt": 0x962DC,
    "fflush_plt": 0x969FC,
    "fclose_plt": 0x96744,
    "suite_nonempty_return": 0x13107E,
    "suite_empty_return": 0x131300,
    "suite_compare_return": 0x1310C4,
    "all_nonempty_return": 0x1315A6,
    "all_empty_return": 0x131952,
    "all_valid_return": 0x1315E8,
    "set_nonempty_return": 0x131E58,
    "set_empty_return": 0x132104,
    "set_compute_return": 0x131E98,
    "suite_record_return": 0x13121C,
    "all_record_return": 0x1316EE,
    "mtime_accept_return": 0x121E08,
    "mtime_reject_return": 0x121BEA,
    "write_return": 0x1213DE,
}


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_hash(path: Path, expected: str) -> None:
    if file_sha256(path) != expected:
        raise ValueError(f"unexpected input SHA-256: {path.name}")


def run(command: list, cwd: Path, log: list, *, environment: dict[str, str] | None = None) -> None:
    result = subprocess.run(
        [str(arg) for arg in command], cwd=cwd, capture_output=True,
        text=True, encoding="utf-8", errors="replace", check=False, env=environment,
    )
    log.append({"command": [str(arg) for arg in command],
                "exit_code": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr})
    with (cwd / "commands.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(log[-1]) + "\n")
    if result.returncode:
        raise RuntimeError(f"build command failed: {result.stdout}\n{result.stderr}")


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError("source transform does not match exactly once")
    return text.replace(old, new, 1)


def replace_method(text: str, signature: str, body: str) -> str:
    pattern = r"(?ms)^\.method " + re.escape(signature) + r"\n.*?^\.end method$"
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError(f"expected one smali method: {signature}")
    match = matches[0]
    return text[:match.start()] + ".method " + signature + "\n" + body + ".end method" + text[match.end():]


def smali_specification(name: str) -> str:
    text = (ROOT / "reverse-engineering/smali" / name).read_text(encoding="utf-8")
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#")).strip("\n")


def patch_java(decoded: Path) -> None:
    package = decoded / "smali/com/halfbrick/birzzlefever"
    activity = package / "BirzzleFever.smali"
    text = activity.read_text(encoding="utf-8")
    for name, count in (("BirzzleFever.GetUniqueDeviceID.smali", 1), ("BirzzleFever.Network.smali", 2)):
        methods = re.findall(r"(?ms)^\.method ([^\n]+)\n(.*?)^\.end method$", smali_specification(name))
        if len(methods) != count:
            raise ValueError(f"unexpected method count in {name}")
        for signature, body in methods:
            text = replace_method(text, signature, body)
    anchor = "    invoke-direct {p0, v1}, Lcom/halfbrick/birzzlefever/BirzzleFever;->MakeContactJson(Ljava/util/ArrayList;)V"
    text = replace_once(text, anchor, anchor + "\n" + smali_specification("BirzzleFever.PostInitialize-gcm-bypass.snippet.smali") + "\n")
    activity.write_text(text, encoding="utf-8", newline="\n")
    application = package / "MyApplication.smali"
    text = application.read_text(encoding="utf-8")
    anchor = "    invoke-super {p0}, Landroid/app/Application;->onCreate()V"
    text = replace_once(text, anchor, anchor + "\n\n" + smali_specification("MyApplication.onCreate-bootstrap.snippet.smali"))
    application.write_text(text, encoding="utf-8", newline="\n")
    shutil.copyfile(ROOT / "native-patches/v24-connectivity-independent/apktool/smali/com/halfbrick/birzzlefever/SaveBootstrap.smali", package / "SaveBootstrap.smali")
    manifest = decoded / "AndroidManifest.xml"
    text = manifest.read_text(encoding="utf-8")
    pattern = r'(?ms)^        <receiver android:name="com\.google\.android\.gcm\.GCMBroadcastReceiver"[^>]*>.*?^        </receiver>\n'
    text, count = re.subn(pattern, "", text)
    if count != 1:
        raise ValueError("expected one Birzzle GCM receiver")
    text = replace_once(text, '        <service android:name=".GCMIntentService"/>\n', "")
    manifest.write_text(text, encoding="utf-8", newline="\n")


def rebuild_native(original: Path, work: Path, log: list) -> dict[str, Path]:
    with zipfile.ZipFile(original) as apk:
        for name, relative in {
            "libbirzzle.so": "original/libbirzzle.so",
            "libef2d.so": "native-patches/v20-request-index-retention/libef2d-source.so",
        }.items():
            destination = work / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(apk.read("lib/armeabi/" + name))
    run([sys.executable, ROOT / "patch_deduplicate_ranking.py", "original/libbirzzle.so",
         "native-patches/v2-deduplicate-ranking/libbirzzle.so"], work, log)
    for script in EARLY_PATCHES:
        run([sys.executable, ROOT / script], work, log)
    for script in LATE_PATCHES:
        run([sys.executable, ROOT / script, "--native-only"], work, log)
    llvm = ROOT / "tools/llvm-mingw-20260826-ucrt-x86_64/bin"
    recovery = work / "native-patches/v22-first-read-recovery"
    recovery.mkdir(parents=True, exist_ok=True)
    run([llvm / "clang.exe", "--target=armv7a-linux-androideabi", "-mthumb", "-c",
         ROOT / "native-patches/v22-first-read-recovery/v22_hardening.S",
         "-o", recovery / "v22_hardening.o"], work, log)
    run([llvm / "ld.lld.exe", "-Ttext=0x27bc50", "--section-start=.rodata=0x263d70",
         *[f"--defsym={name}={value:#x}" for name, value in RECOVERY_SYMBOLS.items()],
         recovery / "v22_hardening.o", "-o", recovery / "v22_hardening.elf"], work, log)
    for section, name in ((".text", "v22_hardening.bin"), (".rodata", "v22_hardening-rodata.bin")):
        run([llvm / "llvm-objcopy.exe", "-O", "binary", "--only-section=" + section,
             recovery / "v22_hardening.elf", recovery / name], work, log)
    run([sys.executable, ROOT / "patch_first_read_recovery_v22.py"], work, log)
    run([sys.executable, ROOT / "build_v23_request_first.py", "--native-only"], work, log)
    engine = bytearray((work / "native-patches/v23-request-first-index/libef2d.so").read_bytes())
    if engine[0x12B858:0x12B85C] != bytes.fromhex("10b5cef7"):
        raise ValueError("unexpected NetworkStatusSync instructions")
    engine[0x12B858:0x12B85C] = bytes.fromhex("00207047")
    engine_path = work / "native-patches/v25-ranking-template/libef2d-v25-ranking-template.so"
    engine_path.parent.mkdir(parents=True, exist_ok=True)
    engine_path.write_bytes(engine)
    relative = Path("native-patches/v26-modern-syscalls/v26_modern_syscalls.S")
    (work / relative).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / relative, work / relative)
    run([sys.executable, ROOT / "build_v26_modern_syscalls.py", "--native-only"], work, log)
    engine = (work / "native-patches/v26-modern-syscalls/libef2d-v26-modern-syscalls.so").read_bytes()
    engine_path = work / "libef2d-v42.so"
    engine_path.write_bytes(patch_binary_tokens(engine))
    outputs = {
        "libef2d.so": engine_path,
        "libbirzzle.so": work / "native-patches/v41-dual-powerup-scene-rearm/libbirzzle-v41-dual-powerup-scene-rearm.so",
    }
    for name, path in outputs.items():
        require_hash(path, NATIVE_SHA256[name])
    return outputs


def release_recipe() -> dict:
    recipe = json.loads((ROOT / "v42_rebuild_layout.json").read_text(encoding="utf-8"))
    if recipe["original_apk_sha256"] != ORIGINAL_SHA256 or recipe["release_apk_sha256"] != RELEASE_SHA256:
        raise ValueError("unexpected release recipe identity")
    return recipe


def verify_payload(payload: Path, recipe: dict) -> dict[str, str]:
    expected = {entry["name"]: entry["sha256"] for entry in recipe["entries"]}
    if len(expected) != len(recipe["entries"]):
        raise ValueError("duplicate release layout entry")
    with zipfile.ZipFile(payload) as apk:
        names = apk.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("rebuilt APK entry set differs from the release")
        actual = {name: hashlib.sha256(apk.read(name)).hexdigest() for name in names}
    changed = sorted(name for name in expected if actual[name] != expected[name])
    if changed:
        raise ValueError(f"rebuilt payload mismatch: {changed}")
    return actual


def prepare_signing(output: Path, java: str, recipe: dict) -> None:
    verify_payload(output / "v42-payload-unsigned.apk", recipe)
    layout = output / "release-layout.tsv"
    layout.write_text("".join(f"{entry['name']}\t{entry['method']}\t{entry['time']}\n"
                              for entry in recipe["entries"]), encoding="utf-8", newline="\n")
    run([java, ROOT / "V42Reproducible.java", "metadata", output / "v42-payload-unsigned.apk",
         layout, output / "signing", recipe["created_by"], recipe["signing_time_utc"]], output, [])
    for name, field in (("MANIFEST.MF", "manifest_sha256"), ("SIGNATURE.SF", "signature_file_sha256"),
                        ("signed-attributes.der", "signed_attributes_sha256")):
        require_hash(output / "signing" / name, recipe[field])


def build_payload(original: Path, seed: Path, output: Path, apktool: Path, java: str) -> dict:
    original, seed, output, apktool = (path.resolve() for path in (original, seed, output, apktool))
    require_hash(original, ORIGINAL_SHA256)
    require_hash(seed, SEED_SHA256)
    recipe = release_recipe()
    require_hash(apktool, recipe["apktool_sha256"])
    for name, expected in recipe["native_tool_sha256"].items():
        require_hash(ROOT / "tools/llvm-mingw-20260826-ucrt-x86_64/bin" / name, expected)
    output.mkdir(parents=True, exist_ok=False)
    log = []
    decoded = output / "decoded-original"
    normalized_apk = output / "original-roundtrip.apk"
    normalized = output / "decoded-normalized"
    framework = output / "framework"
    command = [java, "-jar", apktool]
    run(command + ["d", "-p", framework, original, "-o", decoded], output, log)
    # This clean roundtrip reproduces legacy aapt2 resource normalization, not
    # gameplay changes. No historical decoded tree or resource blob is copied.
    run(command + ["b", "-p", framework, decoded, "-o", normalized_apk], output, log)
    run(command + ["d", "-p", framework, normalized_apk, "-o", normalized], output, log)
    patch_java(normalized)
    shutil.copyfile(seed, normalized / "assets/birzzle_seed_v1.zip")
    native = rebuild_native(original, output, log)
    for name, path in native.items():
        shutil.copyfile(path, normalized / "lib/armeabi" / name)
    payload_apk = output / "v42-payload-unsigned.apk"
    run(command + ["b", "-p", framework, normalized, "-o", payload_apk], output, log)
    hashes = verify_payload(payload_apk, recipe)
    prepare_signing(output, java, recipe)
    report = {"original_apk_sha256": ORIGINAL_SHA256, "seed_sha256": SEED_SHA256,
              "historical_apk_inputs": [], "prebuilt_native_library_inputs": [],
              "apktool_sha256": file_sha256(apktool), "payload_apk": str(payload_apk),
              "payload_entry_sha256": hashes, "native_sha256": NATIVE_SHA256,
              "all_payloads_match_release": True, "signing_metadata_regenerated_exactly": True,
              "release_signature_regenerated": False}
    (output / "payload-build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def signing_environment(prompt: bool) -> dict[str, str]:
    environment = dict(os.environ)
    if prompt:
        if not environment.get("BIRZZLE_KEYSTORE"):
            environment["BIRZZLE_KEYSTORE"] = input("Private keystore path (not saved): ").strip()
        if not environment.get("BIRZZLE_KEY_ALIAS"):
            environment["BIRZZLE_KEY_ALIAS"] = getpass.getpass("Private key alias (not saved): ")
        if not environment.get("BIRZZLE_STORE_PASSWORD"):
            environment["BIRZZLE_STORE_PASSWORD"] = getpass.getpass("Keystore password: ")
        if "BIRZZLE_KEY_PASSWORD" not in environment:
            environment["BIRZZLE_KEY_PASSWORD"] = getpass.getpass("Key password (Enter to use keystore password): ") or environment["BIRZZLE_STORE_PASSWORD"]
    required = ("BIRZZLE_KEYSTORE", "BIRZZLE_KEY_ALIAS", "BIRZZLE_STORE_PASSWORD")
    if any(not environment.get(name) for name in required):
        raise ValueError("Original private signing credentials are required. Configure BIRZZLE_KEYSTORE, "
                         "BIRZZLE_KEY_ALIAS, and BIRZZLE_STORE_PASSWORD locally, or use --prompt-signing.")
    return environment


def sign_build(output: Path, java: str, prompt: bool, reference: Path | None) -> dict:
    output = output.resolve()
    recipe = release_recipe()
    # Credentials are never written to command logs, reports, or the source tree.
    prepare_signing(output, java, recipe)
    environment = signing_environment(prompt)
    signing = output / "signing"
    result = subprocess.run(
        [java, str(ROOT / "V42Reproducible.java"), "sign", str(signing),
         recipe["certificate_sha256"], recipe["signed_attributes_sha256"]],
        env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Private signing failed")
    require_hash(signing / "SIGNATURE.RSA", recipe["signature_block_sha256"])
    require_hash(signing / "signer-certificate.der", recipe["certificate_sha256"])
    candidate = output / "v42-signing-candidate.apk"
    pack_environment = {name: value for name, value in environment.items()
                        if name not in {"BIRZZLE_KEYSTORE", "BIRZZLE_STORE_PASSWORD", "BIRZZLE_KEY_PASSWORD"}}
    run([java, ROOT / "V42Reproducible.java", "pack", output / "v42-payload-unsigned.apk",
         output / "release-layout.tsv", signing, candidate, recipe["signature_zip_time"]],
        output, [], environment=pack_environment)
    require_hash(candidate, RELEASE_SHA256)
    comparison = None
    if reference is not None:
        require_hash(reference, RELEASE_SHA256)
        with candidate.open("rb") as actual, reference.open("rb") as expected:
            while block := actual.read(1024 * 1024):
                if block != expected.read(len(block)):
                    raise ValueError("reference byte comparison failed")
            if expected.read(1):
                raise ValueError("reference length differs")
        comparison = True
    with tempfile.TemporaryDirectory(prefix="birzzle-public-cert-") as temporary:
        truststore = Path(temporary) / "verification.p12"
        # This temporary store contains only a public certificate, not a private key.
        verification_log = []
        run(["keytool", "-importcert", "-noprompt", "-alias", "expected-release", "-file",
             signing / "signer-certificate.der", "-keystore", truststore, "-storetype", "PKCS12",
             "-storepass", "public-verification"], output, verification_log)
        run(["jarsigner", "-verify", "-strict", "-keystore", truststore,
             "-storepass", "public-verification", candidate], output, verification_log)
        (output / "signature-verification.json").write_text(
            json.dumps(verification_log, indent=2) + "\n", encoding="utf-8")
    final = output / "BirzzleFever-1.1.2-v42-release-signed.apk"
    if final.exists():
        raise ValueError("verified output APK already exists")
    candidate.rename(final)
    report = {"apk": str(final), "apk_sha256": RELEASE_SHA256,
              "signature_regenerated_with_private_key": True, "reference_byte_identical": comparison,
              "certificate_sha256": recipe["certificate_sha256"], "strict_signature_verified": True,
              "signature_block_reused": False, "historical_apk_payloads_reused": False}
    (output / "rebuild-verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, help="Untouched Birzzle Fever 1.1.2 APK")
    parser.add_argument("--seed", type=Path, help="The separately preserved sanitized offline seed ZIP")
    parser.add_argument("--output", type=Path, help="New, nonexistent build directory")
    parser.add_argument("--sign-build", type=Path, help="Sign an already completed clean payload build")
    parser.add_argument("--sign", action="store_true", help="Sign after rebuilding all payloads")
    parser.add_argument("--prompt-signing", action="store_true", help="Read private signing inputs locally without saving them")
    parser.add_argument("--reference", type=Path, help="Optional comparison-only signed APK; never supplies rebuilt bytes")
    parser.add_argument("--apktool", type=Path, default=ROOT / "tools/apktool_2.12.1.jar")
    parser.add_argument("--java", default="java")
    args = parser.parse_args()
    if (args.prompt_signing or args.reference is not None) and not (args.sign or args.sign_build is not None):
        parser.error("--prompt-signing and --reference require --sign or --sign-build")
    if args.sign_build is not None:
        if any(value is not None for value in (args.original, args.seed, args.output)) or args.sign:
            parser.error("--sign-build cannot be combined with build inputs or --sign")
        report = sign_build(args.sign_build, args.java, args.prompt_signing, args.reference)
    else:
        if any(value is None for value in (args.original, args.seed, args.output)):
            parser.error("--original, --seed, and --output are required for a clean build")
        built = build_payload(args.original, args.seed, args.output, args.apktool, args.java)
        report = {"payload_apk": built["payload_apk"], "payload_entries": len(built["payload_entry_sha256"]),
                  "all_payloads_match_release": True, "signing_metadata_regenerated_exactly": True}
        if args.sign:
            report = sign_build(args.output, args.java, args.prompt_signing, args.reference)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
