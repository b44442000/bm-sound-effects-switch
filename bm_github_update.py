import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional, Tuple


@dataclass
class ReleaseUpdate:
    major: int
    minor: int
    patch: int
    download_url: str
    sha256: Optional[str] = None


# Keep compatibility with older main.py builds that still pass the upstream repo.
LEGACY_UPSTREAM_REPO = "BoringMan314/bm-sound-effects-switch"
DEFAULT_FORK_REPO = "b44442000/bm-sound-effects-switch"
_DOWNLOAD_DIGESTS: dict[str, str] = {}


def _normalize_repo(repo: str) -> str:
    repo = (repo or "").strip().strip("/")
    if repo == LEGACY_UPSTREAM_REPO:
        return DEFAULT_FORK_REPO
    return repo


def parse_version_tag(tag: str) -> Optional[Tuple[int, int, int]]:
    t = (tag or "").strip()
    if t.lower().startswith("v"):
        t = t[1:]
    parts = t.split(".")
    if len(parts) < 2:
        return None
    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) >= 3 else 0
        return major, minor, patch
    except ValueError:
        return None


def parse_title_version(suffix: str) -> Tuple[int, int, int]:
    m = re.search(r"V(\d+)\.(\d+)(?:\.(\d+))?", suffix or "", re.IGNORECASE)
    if not m:
        return 1, 0, 0
    patch = int(m.group(3)) if m.group(3) else 0
    return int(m.group(1)), int(m.group(2)), patch


def is_newer(remote: Tuple[int, int, int], current: Tuple[int, int, int]) -> bool:
    return remote > current


def version_label(major: int, minor: int, patch: int) -> str:
    return f"V{major}.{minor}.{patch}"


def make_pick_win10_exe(stem: str) -> Callable[[str], bool]:
    needle = stem.lower()

    def pick(name: str) -> bool:
        lower = name.lower()
        return needle in lower and lower.endswith(".exe") and "_win7" not in lower

    return pick


def _asset_sha256(asset: dict) -> Optional[str]:
    """Return GitHub's SHA-256 asset digest when available."""
    digest = asset.get("digest")
    if not isinstance(digest, str):
        return None
    digest = digest.strip().lower()
    if digest.startswith("sha256:"):
        digest = digest[7:]
    if re.fullmatch(r"[0-9a-f]{64}", digest):
        return digest
    return None


def fetch_latest_update(
    repo: str,
    user_agent: str,
    current: Tuple[int, int, int],
    pick_asset: Callable[[str], bool],
    timeout: float = 15,
) -> Optional[ReleaseUpdate]:
    repo = _normalize_repo(repo)
    if not repo or "/" not in repo:
        return None
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        return None

    tag = data.get("tag_name")
    parsed = parse_version_tag(tag) if isinstance(tag, str) else None
    if parsed is None or not is_newer(parsed, current):
        return None

    assets = data.get("assets")
    if not isinstance(assets, list):
        return None

    selected_asset = None
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        if isinstance(name, str) and pick_asset(name):
            browser_url = asset.get("browser_download_url")
            if isinstance(browser_url, str) and browser_url:
                selected_asset = asset
                break

    if selected_asset is None:
        return None

    download_url = selected_asset["browser_download_url"]
    sha256 = _asset_sha256(selected_asset)
    if sha256:
        _DOWNLOAD_DIGESTS[download_url] = sha256

    return ReleaseUpdate(
        major=parsed[0],
        minor=parsed[1],
        patch=parsed[2],
        download_url=download_url,
        sha256=sha256,
    )


def build_save_path(
    app_dir: str,
    file_stem: str,
    major: int,
    minor: int,
    patch: int,
    extension: str,
) -> str:
    label = version_label(major, minor, patch)
    return os.path.join(app_dir, f"{file_stem}-{label}{extension}")


def _sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as src:
        while True:
            chunk = src.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def download_release(
    url: str,
    dest_path: str,
    user_agent: str,
    timeout: float = 600,
    expected_sha256: Optional[str] = None,
) -> bool:
    """Download an update atomically and optionally verify its SHA-256."""
    expected = (expected_sha256 or _DOWNLOAD_DIGESTS.get(url) or "").strip().lower()
    if expected.startswith("sha256:"):
        expected = expected[7:]
    if expected and not re.fullmatch(r"[0-9a-f]{64}", expected):
        return False

    if os.path.isfile(dest_path) and expected:
        try:
            if _sha256_file(dest_path) == expected:
                return True
        except OSError:
            pass
        try:
            os.remove(dest_path)
        except OSError:
            return False

    # If no digest is available, do not trust an old cached file. Download a
    # fresh copy into a temporary file and replace the destination atomically.
    temp_path = dest_path + ".download"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/octet-stream"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            with open(temp_path, "wb") as out:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    out.write(chunk)

        if expected and _sha256_file(temp_path) != expected:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            return False

        os.replace(temp_path, dest_path)
        return True
    except (urllib.error.URLError, OSError):
        try:
            if os.path.isfile(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        return False
