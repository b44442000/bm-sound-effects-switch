import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
RELEASE_DIR = PROJECT_ROOT / "release"
APP_NAME = "bm-sound-effects-switch"
VERSION_INFO = PROJECT_ROOT / "version_info.txt"
ICON_FILE = PROJECT_ROOT / "icons" / "icon.ico"
HIDDEN_IMPORTS = [
    "pystray",
    "keyboard",
    "bm_single_instance",
    "bm_github_update",
    "bm_audio_monitor",
    "bm_audio_refresh",
    "bm_config",
    "bm_hotkeys",
    "bm_ui",
    "pycaw",
    "comtypes",
]


def clear_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def add_data_arg(source: Path, target: str) -> str:
    return str(source) + os.pathsep + target


def check_python(mode: str) -> None:
    v = sys.version_info
    if mode == "win7" and not (v.major == 3 and v.minor == 8):
        raise SystemExit("Win7 build requires Python 3.8.x.")
    if mode == "win10" and not (v.major == 3 and v.minor >= 10):
        raise SystemExit("Win10/11 build requires Python 3.10+.")


def require_version_info() -> Path:
    if not VERSION_INFO.is_file():
        raise SystemExit(
            "Missing version_info.txt at project root. "
            "Edit that file (Exe.txt Windows file version) then rebuild."
        )
    return VERSION_INFO


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksum(exe: Path) -> Path:
    checksum = sha256_file(exe)
    checksum_file = exe.with_suffix(exe.suffix + ".sha256")
    checksum_file.write_text(
        f"{checksum}  {exe.name}\n",
        encoding="utf-8",
    )
    return checksum_file


def build(mode: str) -> Path:
    check_python(mode)
    vinfo = require_version_info()

    clear_dir(BUILD_DIR)
    clear_dir(DIST_DIR)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    exe_name = APP_NAME if mode == "win10" else f"{APP_NAME}_win7"
    command: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        exe_name,
        "--icon",
        str(ICON_FILE),
        "--version-file",
        str(vinfo),
        "--workpath",
        str(BUILD_DIR),
        "--distpath",
        str(DIST_DIR),
        "--specpath",
        str(BUILD_DIR),
        "--add-data",
        add_data_arg(PROJECT_ROOT / "icons", "icons"),
        "--add-data",
        add_data_arg(PROJECT_ROOT / "wav", "wav"),
    ]
    for hidden_import in HIDDEN_IMPORTS:
        command.extend(["--hidden-import", hidden_import])
    command.append(str(PROJECT_ROOT / "main.py"))

    print("==> Building Windows EXE")
    subprocess.check_call(command, cwd=str(PROJECT_ROOT))

    built = DIST_DIR / f"{exe_name}.exe"
    if not built.is_file():
        raise SystemExit(f"PyInstaller completed but EXE was not found: {built}")

    final = RELEASE_DIR / built.name
    if final.exists():
        final.unlink()
    shutil.copy2(built, final)
    checksum_file = write_checksum(final)

    clear_dir(BUILD_DIR)
    clear_dir(DIST_DIR)

    print()
    print("Build completed successfully.")
    print(f"EXE    : {final}")
    print(f"SHA256 : {checksum_file}")
    print(f"HASH   : {sha256_file(final)}")
    return final


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the Windows EXE and generate its SHA-256 checksum."
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["win10", "win7"],
        default="win10",
        help="Build target (default: win10; compatible with Windows 10/11).",
    )
    args = parser.parse_args()
    build(args.mode)


if __name__ == "__main__":
    main()
