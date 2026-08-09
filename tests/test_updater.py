from __future__ import annotations

import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.updater import UpdateClient, UpdateError, parse_release, version_tuple


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False


def release_payload(*, version: str, content: bytes = b"installer") -> dict[str, object]:
    digest = hashlib.sha256(content).hexdigest()
    return {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/QCYTSN/ds-local-pet/releases/tag/v{version}",
        "assets": [
            {
                "name": f"DS-Local-Pet-Setup-v{version}.exe",
                "browser_download_url": (
                    "https://github.com/QCYTSN/ds-local-pet/releases/download/"
                    f"v{version}/DS-Local-Pet-Setup-v{version}.exe"
                ),
                "digest": f"sha256:{digest}",
                "size": len(content),
            }
        ],
    }


class UpdaterTests(unittest.TestCase):
    def test_semantic_version_comparison_is_numeric(self) -> None:
        self.assertGreater(version_tuple("v0.10.0"), version_tuple("0.2.9"))

    def test_same_or_older_release_is_ignored(self) -> None:
        self.assertIsNone(parse_release(release_payload(version="0.2.0"), current_version="0.2.0"))
        self.assertIsNone(parse_release(release_payload(version="0.1.9"), current_version="0.2.0"))

    def test_new_release_requires_github_sha256_digest(self) -> None:
        payload = release_payload(version="0.3.0")
        payload["assets"][0]["digest"] = None  # type: ignore[index]
        with self.assertRaises(UpdateError):
            parse_release(payload, current_version="0.2.0")

    def test_verified_download_is_atomically_promoted(self) -> None:
        content = b"verified installer bytes"
        info = parse_release(release_payload(version="0.3.0", content=content), current_version="0.2.0")
        self.assertIsNotNone(info)
        with tempfile.TemporaryDirectory() as temporary:
            client = UpdateClient(current_version="0.2.0", updates_dir=Path(temporary))
            with patch("urllib.request.urlopen", return_value=_Response(content)):
                target = client.download(info)
            self.assertEqual(target.read_bytes(), content)
            self.assertFalse(target.with_suffix(".exe.part").exists())

    def test_bad_download_hash_is_deleted(self) -> None:
        info = parse_release(release_payload(version="0.3.0", content=b"expected"), current_version="0.2.0")
        self.assertIsNotNone(info)
        with tempfile.TemporaryDirectory() as temporary:
            client = UpdateClient(current_version="0.2.0", updates_dir=Path(temporary))
            with patch("urllib.request.urlopen", return_value=_Response(b"tampered")):
                with self.assertRaises(UpdateError):
                    client.download(info)
            self.assertEqual(list(Path(temporary).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
