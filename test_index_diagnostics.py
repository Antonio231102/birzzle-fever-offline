import base64
import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from Crypto.Cipher import AES

from diagnose_response_index import AES_KEY, diagnose_bytes, diagnose_path


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


if __name__ == "__main__":
    unittest.main()
