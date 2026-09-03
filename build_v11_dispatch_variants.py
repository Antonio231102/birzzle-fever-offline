import hashlib
import struct
import zipfile
from pathlib import Path


SOURCE_LIB = Path("native-patches/v10-rejected-ranking-cleanup/libbirzzle.so")
SOURCE_APK = Path(
    "native-patches/v10-rejected-ranking-cleanup/"
    "BirzzleFever-1.1.2-v10-rejected-ranking-cleanup.apk"
)
EXPECTED_SHA256 = "28435b4e4577b244e86b742df606fa77f4a0fc9bd4d9b3dcf8dbcb7963777442"
LIBRARY_ENTRY = "lib/armeabi/libbirzzle.so"

RESTORE_RANKING = 0x141A10
POSTRESTORE_STUB = 0x2ACE90
GET_RANKING = 0x163B78
REARM_REQUEST_STUB = 0x2ACE40


def thumb2_branch(source: int, target: int, link: bool) -> bytes:
    offset = target - (source + 4)
    value = offset & 0x1FFFFFF
    s = (value >> 24) & 1
    i1 = (value >> 23) & 1
    i2 = (value >> 22) & 1
    j1 = (~(i1 ^ s)) & 1
    j2 = (~(i2 ^ s)) & 1
    first = 0xF000 | (s << 10) | ((value >> 12) & 0x3FF)
    second = (0xD000 if link else 0x9000) | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF)
    return struct.pack("<HH", first, second)


source = SOURCE_LIB.read_bytes()
if hashlib.sha256(source).hexdigest() != EXPECTED_SHA256:
    raise SystemExit("unexpected v10 source library")

common = [
    (0x145938, POSTRESTORE_STUB, RESTORE_RANKING),
    (0x145A74, POSTRESTORE_STUB, RESTORE_RANKING),
]

for label, dispatch in (("a", 0x147848), ("b", 0x148E38)):
    data = bytearray(source)
    for address, old_target, new_target in common:
        expected = thumb2_branch(address, old_target, True)
        replacement = thumb2_branch(address, new_target, True)
        if data[address : address + 4] != expected:
            raise SystemExit(f"unexpected common bytes at {address:#x}")
        data[address : address + 4] = replacement

    expected = thumb2_branch(dispatch, GET_RANKING, True)
    replacement = thumb2_branch(dispatch, REARM_REQUEST_STUB, True)
    if data[dispatch : dispatch + 4] != expected:
        raise SystemExit(f"unexpected dispatch bytes at {dispatch:#x}")
    data[dispatch : dispatch + 4] = replacement

    output_dir = Path(f"native-patches/v11-diagnostic-dispatch-{label}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_lib = output_dir / "libbirzzle.so"
    output_apk = output_dir / f"BirzzleFever-1.1.2-v11-dispatch-{label}-unsigned.apk"
    output_lib.write_bytes(data)

    temporary = output_apk.with_suffix(".tmp.apk")
    with zipfile.ZipFile(SOURCE_APK, "r") as apk_in, zipfile.ZipFile(temporary, "w") as apk_out:
        for item in apk_in.infolist():
            if item.filename.upper().startswith("META-INF/"):
                continue
            payload = data if item.filename == LIBRARY_ENTRY else apk_in.read(item.filename)
            apk_out.writestr(item, payload)
    temporary.replace(output_apk)
    print(label, hashlib.sha256(data).hexdigest(), hashlib.sha256(output_apk.read_bytes()).hexdigest())
