from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from safeio import IoError, read_bytes, read_json, write_bytes, write_json  # noqa: E402


class SafeIoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_write_then_read_roundtrip(self) -> None:
        path = self.dir / "state.json"
        write_json(path, {"ok": True})
        st = path.stat()
        self.assertEqual(stat.S_IMODE(st.st_mode), 0o600)
        self.assertEqual(read_json(path), {"ok": True})

    def test_write_replaces_symlink_instead_of_following(self) -> None:
        victim = self.dir / "victim"
        victim.write_bytes(b"must survive\n")
        dest = self.dir / "cache.json"
        dest.symlink_to(victim)
        write_json(dest, {"n": 1})
        self.assertEqual(victim.read_bytes(), b"must survive\n")
        self.assertFalse(dest.is_symlink())
        self.assertEqual(json.loads(dest.read_text()), {"n": 1})

    def test_read_refuses_symlink(self) -> None:
        dest = self.dir / "cache.json"
        dest.symlink_to("/etc/passwd")
        with self.assertRaises(IoError):
            read_bytes(dest, 1024)

    def test_read_refuses_oversize(self) -> None:
        path = self.dir / "big.json"
        write_bytes(path, b"x" * 50)
        with self.assertRaises(IoError):
            read_bytes(path, 16)


if __name__ == "__main__":
    unittest.main()
