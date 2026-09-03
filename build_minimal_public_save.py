import gzip
import io
import json
import tarfile
from pathlib import Path

from analyze_birzzle_save import decrypt2


SOURCE = Path("com.halfbrick.birzzlefever-20160501-111000.tar.gz")
OUTPUT_DIR = Path("minimal-public-save")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT = OUTPUT_DIR / "birzzle-2016-minimal-data.tar.gz"
MANIFEST = OUTPUT_DIR / "manifest.json"
REQUIRED_LOCAL = {
    "new2profile.dat",
    "bMarket.dat",
    "exp.dat",
    "tuto.dat_3c8bb7308c3fcb60c439224bd595c794d8f31501",
}


included = []
excluded = []
with (
    tarfile.open(SOURCE, "r:gz") as source,
    OUTPUT.open("wb") as compressed_stream,
    gzip.GzipFile(filename="", mode="wb", fileobj=compressed_stream, mtime=0) as gzip_stream,
    tarfile.open(fileobj=gzip_stream, mode="w") as output,
):
    for member in source.getmembers():
        if not member.isfile():
            continue
        stream = source.extractfile(member)
        if stream is None:
            continue
        raw = stream.read()
        name = Path(member.name).name
        role = None
        if "/files/" in member.name and decrypt2(raw) is not None:
            role = "ccrypt2_bootstrap"
        elif "/files/" in member.name and name in REQUIRED_LOCAL:
            role = "local_game_profile"
        if role is None:
            excluded.append({"path": member.name, "size": len(raw)})
            continue
        output.addfile(member, io.BytesIO(raw))
        included.append({
            "path": member.name,
            "name": name,
            "size": len(raw),
            "mtime": int(member.mtime),
            "role": role,
        })
    marker = tarfile.TarInfo("data/data/com.halfbrick.birzzlefever/.birzzle_seed_v1")
    marker.size = 0
    marker.mode = 0o600
    marker.mtime = 1462101029
    marker.uid = 10125
    marker.gid = 10125
    output.addfile(marker)
    included.append({
        "path": marker.name,
        "name": marker.name.rsplit("/", 1)[-1],
        "size": 0,
        "mtime": marker.mtime,
        "role": "portable_seed_marker",
    })

manifest = {
    "source": str(SOURCE),
    "output": OUTPUT.as_posix(),
    "policy": "All 22 original CCrypt2 bootstrap records, four gameplay-local profiles, and the portable seed marker; no analytics, databases, preferences, OLE workbooks, or journals.",
    "included_count": len(included),
    "excluded_count": len(excluded),
    "included": included,
    "excluded": excluded,
}
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps({"included": len(included), "excluded": len(excluded), "output": OUTPUT.as_posix()}))
