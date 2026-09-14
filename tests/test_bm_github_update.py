import hashlib
from pathlib import Path

import bm_github_update as updater


def test_parse_version_tag():
    assert updater.parse_version_tag("v1.2") == (1, 2, 0)
    assert updater.parse_version_tag("V2.3.4") == (2, 3, 4)
    assert updater.parse_version_tag("bad") is None


def test_version_comparison():
    assert updater.is_newer((1, 2, 0), (1, 1, 9))
    assert not updater.is_newer((1, 2, 0), (1, 2, 0))
    assert not updater.is_newer((1, 1, 9), (1, 2, 0))


def test_legacy_repo_redirect():
    assert (
        updater._normalize_repo("BoringMan314/bm-sound-effects-switch")
        == "b44442000/bm-sound-effects-switch"
    )
    assert updater._normalize_repo("owner/project") == "owner/project"


def test_asset_sha256():
    digest = "a" * 64
    assert updater._asset_sha256({"digest": f"sha256:{digest}"}) == digest
    assert updater._asset_sha256({"digest": "sha1:abc"}) is None


def test_download_release_verifies_sha256(tmp_path, monkeypatch):
    payload = b"test update payload"
    source = tmp_path / "source.bin"
    dest = tmp_path / "update.exe"
    source.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size=-1):
            return payload if size != 0 else b""

    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *a, **k: Response())
    assert updater.download_release(
        "https://example.invalid/update.exe",
        str(dest),
        "test",
        expected_sha256=expected,
    )
    assert dest.read_bytes() == payload


def test_download_release_rejects_bad_sha256(tmp_path, monkeypatch):
    payload = b"test update payload"
    dest = tmp_path / "update.exe"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size=-1):
            return payload if size != 0 else b""

    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *a, **k: Response())
    assert not updater.download_release(
        "https://example.invalid/update.exe",
        str(dest),
        "test",
        expected_sha256="b" * 64,
    )
    assert not dest.exists()
