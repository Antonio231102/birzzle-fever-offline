import base64
import hashlib
import os
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from Crypto.Cipher import AES

from diagnose_response_index import AES_KEY, diagnose_bytes, diagnose_path
from analyze_birzzle_save import HISTORICAL_UID
from reconstruct_response_pool import index_name, parse_request, reconstruct, request_name
from repair_empty_index_token import repair_archive, repair_index


def encrypt_plain(plain: bytes):
    padding = 16 - len(plain) % 16
    return base64.b64encode(AES.new(AES_KEY, AES.MODE_ECB).encrypt(plain + bytes([padding]) * padding))


def envelope(body: bytes):
    return encrypt_plain(b"C+" + hashlib.md5(body).hexdigest().encode() + body)


def body(key=b"AAAAAAAAAAAAAAAAAAAAAA==", data=b"LTEsMTAy", timestamp=b"1788060200"):
    return b"KEY:" + key + b"\nDATA:" + data + b"\nTIMESTAMP:" + timestamp


class IndexDiagnosticsTests(unittest.TestCase):
    def assert_reason(self, name, raw, expected, mtime=1788060200):
        result = diagnose_bytes(raw, mtime)
        actual = result.get("failure_reason") or result.get("readcontent_result")
        self.assertEqual(actual, expected, f"{name}: {result}")

    def test_bytes_classifications(self):
        cases = (
            ("valid", envelope(body()), "ACCEPT", 1788060200),
            ("empty", b"", "EMPTY_FILE", 1788060200),
            ("outer", b"not base64!", "OUTER_BASE64_INVALID", 1788060200),
            ("block", base64.b64encode(b"123"), "AES_BLOCK_SIZE_INVALID", 1788060200),
            ("padding", base64.b64encode(bytes(16)), "PKCS7_PADDING_INVALID", 1788060200),
            ("prefix", encrypt_plain(b"X+" + b"0" * 32 + b"x"), "PREFIX_INVALID", 1788060200),
            ("md5", encrypt_plain(b"C+" + b"0" * 32 + body()), "ENVELOPE_MD5_MISMATCH", 1788060200),
            ("missing_key", envelope(b"DATA:LTEsMTAy\nTIMESTAMP:1788060200"), "FIELD_MISSING_KEY", 1788060200),
            ("empty_key", envelope(body(key=b"")), "FIELD_MISSING_KEY", 1788060200),
            ("legacy_short_key", envelope(body(key=b"AQ==")), "ACCEPT", 1788060200),
            ("key_extra_colon", envelope(body(key=b"AQ==:ignored")), "FIELD_MISSING_KEY", 1788060200),
            ("empty_data", envelope(body(data=b"")), "FIELD_MISSING_DATA", 1788060200),
            ("missing_data", envelope(b"KEY:AAAAAAAAAAAAAAAAAAAAAA==\nTIMESTAMP:1788060200"), "FIELD_MISSING_DATA", 1788060200),
            ("missing_timestamp", envelope(b"KEY:AAAAAAAAAAAAAAAAAAAAAA==\nDATA:LTEsMTAy"), "FIELD_MISSING_TIMESTAMP", 1788060200),
            ("key_base64", envelope(body(key=b"!")), "KEY_BASE64_INVALID", 1788060200),
            ("data_base64", envelope(body(data=b"!")), "DATA_BASE64_INVALID", 1788060200),
            ("timestamp", envelope(body(timestamp=b"x")), "TIMESTAMP_INVALID", 1788060200),
            ("mtime", envelope(body()), "MTIME_MISMATCH", 1788060260),
            ("payload", envelope(body(data=base64.b64encode(b"broken"))), "INDEX_PAYLOAD_INVALID", 1788060200),
            ("range", envelope(body(data=base64.b64encode(b"5,2"))), "INDEX_RANGE_INVALID", 1788060200),
        )
        for name, raw, expected, mtime in cases:
            with self.subTest(name=name):
                self.assert_reason(name, raw, expected, mtime)

    def test_path_classifications(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            self.assertEqual(diagnose_path(missing)["failure_reason"], "ACCESS_NOT_FOUND")

            valid = Path(directory) / "index"
            valid.write_bytes(envelope(body()))
            os.utime(valid, (1788060200, 1788060200))
            self.assertEqual(diagnose_path(valid)["readcontent_result"], "ACCEPT")

    def test_first_duplicate_field_wins_like_native_map_insert(self):
        raw = envelope(body() + b"\nDATA:" + base64.b64encode(b"5,2"))
        self.assertEqual(diagnose_bytes(raw, 1788060200)["index_text"], "-1,102")

    def test_empty_token_request_is_not_valid_history(self):
        data = base64.b64encode(b"quest.update.status,questid=50&queststatus=2")
        rejected = parse_request(envelope(body(key=b"", data=data)), 1788060200)
        self.assertFalse(rejected["valid"])
        self.assertEqual(rejected["failure_reason"], "FIELD_MISSING_KEY")
        self.assertTrue(parse_request(envelope(body(key=b"AQ==", data=data)), 1788060200)["valid"])

    def test_repair_preserves_progression_and_archive_metadata(self):
        timestamp = 1788060200
        broken_index = envelope(body(key=b"", data=base64.b64encode(b"-1,0")))
        request = envelope(body(data=base64.b64encode(b"quest.update.status,questid=50&queststatus=2")))
        prefix = "data/data/com.halfbrick.birzzlefever/files/"
        contents = {
            prefix + index_name(HISTORICAL_UID): broken_index,
            prefix + request_name(0, HISTORICAL_UID): request,
            prefix + "quest_progress.dat_" + HISTORICAL_UID: b"progression-must-not-change",
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "original.tar.gz"
            output = Path(directory) / "recovered.tar.gz"
            with tarfile.open(source, "w:gz", format=tarfile.GNU_FORMAT) as archive:
                for name, raw in contents.items():
                    info = tarfile.TarInfo(name)
                    info.size, info.mtime = len(raw), timestamp
                    info.uid, info.gid, info.mode = 10269, 10269, 0o600
                    archive.addfile(info, io.BytesIO(raw))
            original_archive = source.read_bytes()
            self.assertEqual(reconstruct(source, HISTORICAL_UID, 4)["classification"], "INDEX_REJECTED")
            report = repair_archive(source, output)
            self.assertEqual(source.read_bytes(), original_archive)
            recovered = reconstruct(output, HISTORICAL_UID, 4)
            self.assertEqual(recovered["classification"], "CONSISTENT")
            self.assertEqual(recovered["index_state"]["index_text"], "-1,0")
            self.assertEqual(recovered["records"][0]["text"], "quest.update.status,questid=50&queststatus=2")
            with tarfile.open(output) as archive:
                for name, raw in contents.items():
                    member = archive.getmember(name)
                    self.assertEqual((member.mtime, member.uid, member.gid, member.mode), (timestamp, 10269, 10269, 0o600))
                    if name != report["changed_member"]:
                        self.assertEqual(archive.extractfile(member).read(), raw)
            with self.assertRaises(FileExistsError):
                repair_archive(source, output)

    def test_repair_refuses_other_defects(self):
        for raw, mtime in (
            (envelope(body()), 1788060200),
            (envelope(body(key=b"", data=base64.b64encode(b"5,2"))), 1788060200),
            (envelope(body(key=b"")), 1788060260),
            (encrypt_plain(b"C+" + b"0" * 32 + body(key=b"")), 1788060200),
        ):
            with self.subTest(mtime=mtime, raw=raw):
                with self.assertRaises(ValueError):
                    repair_index(raw, mtime)


if __name__ == "__main__":
    unittest.main()
