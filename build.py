import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
APP_NAME = "bm-sound-effects-switch"
VERSION_INFO = PROJECT_ROOT / "version_info.txt"
HIDDEN_IMPORTS = [
    "pystray",
    "keyboard",
    "bm_single_instance",
    "bm_github_update",
    "bm_audio_monitor",
    "bm_config",
    "bm_hotkeys",
    "bm_ui",
    "pycaw",
    "comtypes",
]


def clear_dir(path: Path) -> None:
    path.mkdir(exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def add_data_arg(source: Path, target: str) -> str:
    return str(source) + os.pathsep + target


def replace_exe(built: Path, final: Path) -> None:
    if final.exists():
        final.unlink()
    shutil.move(str(built), str(final))


def check_python(mode: str) -> None:
    v = sys.version_info
    if mode == "win7" and not (v.major == 3 and v.minor == 8):
        raise SystemExit("Win7 build requires Python 3.8.x.")
    if mode == "win10" and not (v.major == 3 and v.minor >= 10):
        raise SystemExit("Win10 build requires Python 3.10+.")


def require_version_info() -> Path:
    if not VERSION_INFO.is_file():
        raise SystemExit(
            "Missing version_info.txt at project root. "
            "Edit that file (Exe.txt Windows file version) then rebuild."
        )
    return VERSION_INFO


def build(mode: str) -> None:
    check_python(mode)
    vinfo = require_version_info()
    clear_dir(BUILD_DIR)
    clear_dir(DIST_DIR)

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
        str(PROJECT_ROOT / "icons" / "icon.ico"),
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
    for h in HIDDEN_IMPORTS:
        command.extend(["--hidden-import", h])
    command.append(str(PROJECT_ROOT / "main.py"))
    subprocess.check_call(command, cwd=str(PROJECT_ROOT))

    built = DIST_DIR / f"{exe_name}.exe"
    final = PROJECT_ROOT / f"{exe_name}.exe"
    replace_exe(built, final)

    clear_dir(BUILD_DIR)
    clear_dir(DIST_DIR)
    print("Built " + final.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["win10", "win7"])
    build(parser.parse_args().mode)


if __name__ == "__main__":
    main()
