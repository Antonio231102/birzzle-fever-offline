import argparse
import base64
import copy
import hashlib
import io
import json
import re
import secrets
import tarfile
from pathlib import Path

from Crypto.Cipher import AES

from analyze_birzzle_save import CRYPT2_KEY, HISTORICAL_UID, decrypt2
from diagnose_response_index import diagnose_bytes
from reconstruct_response_pool import index_name, reconstruct


PACKAGE = "com.halfbrick.birzzlefever"


def repair_index(raw: bytes, mtime: int) -> bytes:
    """Repair only the writer's authenticated, empty-token envelope defect."""
    decoded = decrypt2(raw)
    if decoded is None or not decoded["digest_valid"]:
        raise ValueError("refusing to repair an unauthenticated or corrupt envelope")
    if not re.fullmatch(rb"KEY:\nDATA:[A-Za-z0-9+/]+={0,2}\nTIMESTAMP:[0-9]+", decoded["body"]):
        raise ValueError("index is not the exact empty-token writer format")
    if diagnose_bytes(raw, mtime).get("failure_reason") != "FIELD_MISSING_KEY":
        raise ValueError("index does not have the empty-token reader failure")
    token = base64.b64encode(secrets.token_bytes(16))
    body = b"KEY:" + token + decoded["body"][4:]
    plain = b"C+" + hashlib.md5(body).hexdigest().encode("ascii") + body
    padding = 16 - len(plain) % 16
    repaired = base64.b64encode(
        AES.new(CRYPT2_KEY, AES.MODE_ECB).encrypt(plain + bytes([padding]) * padding)
    )
    diagnostic = diagnose_bytes(repaired, mtime)
    if diagnostic.get("readcontent_result") != "ACCEPT":
        raise ValueError(f"index has another defect; refusing repair: {diagnostic['failure_reason']}")
    return repaired


def repair_archive(source: Path, output: Path, uid: str = HISTORICAL_UID):
    """Write a separate recovery archive; never change the source or a device."""
    if source.resolve() == output.resolve():
        raise ValueError("recovery output must differ from the original archive")
    report_path = output.with_name(output.name + ".repair.json")
    if output.exists() or report_path.exists():
        raise FileExistsError("refusing to overwrite a recovery archive or its report")
    pool = reconstruct(source, uid, 4095)
    if pool["classification"] != "INDEX_REJECTED" or pool["invalid_records"] or pool["semantic_warnings"]:
        raise ValueError("source has additional pool defects; manual investigation required")
    index_path = f"data/data/{PACKAGE}/files/{index_name(uid)}"
    with tarfile.open(source, "r:*") as archive:
        members = archive.getmembers()
        if len({m.name for m in members}) != len(members):
            raise ValueError("duplicate archive members make recovery ambiguous")
        member = archive.getmember(index_path)
        if not member.isfile():
            raise ValueError("response index is not a regular file")
        original = archive.extractfile(member).read()
        repaired = repair_index(original, int(member.mtime))
        diagnostic = diagnose_bytes(repaired, int(member.mtime))
        if diagnostic["last_index"] != pool["highest_valid"] or diagnostic["last_index"] != pool["contiguous_last"]:
            raise ValueError("index does not describe the complete preserved request history")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(output, "x:gz") as candidate:
            for entry in members:
                if entry.name == index_path:
                    replacement = copy.copy(entry)
                    replacement.size = len(repaired)
                    candidate.addfile(replacement, io.BytesIO(repaired))
                else:
                    candidate.addfile(entry, archive.extractfile(entry) if entry.isfile() else None)

    recovered_pool = reconstruct(output, uid, 4095)
    if recovered_pool["classification"] != "CONSISTENT":
        raise ValueError("recovery archive verification failed; do not deploy output")
    unchanged_files = 0
    with tarfile.open(source, "r:*") as original_tar, tarfile.open(output, "r:*") as recovered_tar:
        before = original_tar.getmembers()
        after = recovered_tar.getmembers()
        if len(before) != len(after):
            raise ValueError("recovery archive member count changed")
        for old, new in zip(before, after):
            old_info, new_info = old.get_info(), new.get_info()
            # Header checksums change with serialization, not filesystem state.
            old_info.pop("chksum")
            new_info.pop("chksum")
            if old.name == index_path:
                old_info.pop("size")
                new_info.pop("size")
            # PAX may encode long paths that the source encoded with GNU headers.
            # Their effective values are already checked in get_info().
            standard_pax = {"path", "linkpath", "size", "uid", "gid", "uname", "gname", "mtime"}
            old_extra = {k: v for k, v in old.pax_headers.items() if k not in standard_pax}
            new_extra = {k: v for k, v in new.pax_headers.items() if k not in standard_pax}
            if old_info != new_info or old_extra != new_extra:
                raise ValueError(f"recovery altered metadata: {old.name}")
            if old.isfile() and old.name != index_path:
                if original_tar.extractfile(old).read() != recovered_tar.extractfile(new).read():
                    raise ValueError(f"recovery altered unrelated data: {old.name}")
                unchanged_files += 1
    report = {
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output": str(output),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "changed_member": index_path,
        "index_before_sha256": hashlib.sha256(original).hexdigest(),
        "index_after_sha256": hashlib.sha256(repaired).hexdigest(),
        "preserved_index_text": diagnostic["index_text"],
        "preserved_timestamp": diagnostic["embedded_timestamp"],
        "preserved_mtime": int(member.mtime),
        "preserved_uid": member.uid,
        "preserved_gid": member.gid,
        "preserved_mode": oct(member.mode),
        "unchanged_other_files": unchanged_files,
        "preserved_record_count": recovered_pool["record_count"],
        "classification": recovered_pool["classification"],
        "device_applied": False,
        "warning": "Install the fixed candidate before deploying the repaired index; no claims have been awarded by this repair.",
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Stage an index-only empty-token repair in a separate app-data archive. No ADB access.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--uid", default=HISTORICAL_UID)
    args = parser.parse_args()
    print(json.dumps(repair_archive(args.source, args.output, args.uid), indent=2))


if __name__ == "__main__":
    main()
