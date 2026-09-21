"""Integrity and incomplete-input regression tests; no network access."""

import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_sherlock import audit
from probe_sherlock import complete_members


class AcquisitionTests(unittest.TestCase):
    def fixture(self, root, member="01-Basic/ipal/train/events.json"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr(member, "[]")
        payload = buffer.getvalue()
        raw = root / "data/raw/sherlock/v3"
        manifests = root / "data/manifests"
        raw.mkdir(parents=True)
        manifests.mkdir(parents=True)
        part = raw / "01-Basic.zip.part"
        part.write_bytes(payload)
        metadata = {"id": 18467070, "metadata": {"doi": "10.5281/zenodo.18467070"},
                    "files": [{"key": "01-Basic.zip", "size": len(payload),
                               "checksum": "md5:" + hashlib.md5(payload).hexdigest(),
                               "links": {"self": "https://example.invalid/unused"}}]}
        (manifests / "zenodo_18467070.json").write_text(json.dumps(metadata))
        return part, payload

    def test_complete_archive_verified_and_renamed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            part, payload = self.fixture(root)
            result = audit(root)
            self.assertTrue(result["acquisition_complete"])
            self.assertFalse(result["phase1_complete"])
            self.assertFalse(part.exists())
            self.assertEqual(result["archives"][0]["sha256"], hashlib.sha256(payload).hexdigest())

    def test_incomplete_archive_is_not_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            part, payload = self.fixture(root)
            part.write_bytes(payload[:20])
            result = audit(root)
            self.assertFalse(result["acquisition_complete"])
            self.assertEqual(result["archives"][0]["status"], "incomplete")
            self.assertNotIn("sha256", result["archives"][0])
            self.assertTrue(part.exists())

    def test_same_size_corruption_fails_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            part, payload = self.fixture(root)
            part.write_bytes(payload[:-1] + bytes([payload[-1] ^ 1]))
            result = audit(root)
            self.assertEqual(result["archives"][0]["status"], "checksum_mismatch")
            self.assertTrue(part.exists())

    def test_unsafe_member_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, "../outside.json")
            with self.assertRaisesRegex(ValueError, "Unsafe archive path"):
                audit(root)

    def test_probe_ignores_incomplete_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            part, payload = self.fixture(Path(tmp))
            boundary = payload.index(b"[]")
            part.write_bytes(payload[:boundary+1])
            self.assertEqual(list(complete_members(part)), [])

    def test_probe_rejects_corrupt_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            part, payload = self.fixture(Path(tmp))
            part.write_bytes(payload.replace(b"[]", b"{}", 1))
            with self.assertRaisesRegex(ValueError, "CRC mismatch"):
                list(complete_members(part))

    def test_probe_accepts_complete_member_before_archive_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            part, payload = self.fixture(Path(tmp))
            part.write_bytes(payload[:payload.index(b"PK\x01\x02")])
            members = list(complete_members(part))
            self.assertEqual(len(members), 1)
            self.assertEqual(members[0][1], b"[]")


if __name__ == "__main__":
    unittest.main()
