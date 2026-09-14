from __future__ import annotations

import ctypes
import os
import threading
import time
from typing import Callable, Optional

__all__ = [
    "acquire_or_handshake",
    "release_mutex",
    "start_pipe_server",
    "notify_peer_to_quit",
]

kernel32 = ctypes.windll.kernel32

ERROR_ALREADY_EXISTS = 183
ERROR_PIPE_CONNECTED = 535
INVALID_HANDLE = ctypes.c_void_p(-1).value
WAIT_OBJECT_0 = 0
WAIT_ABANDONED = 0x00000080
PIPE_SIGNAL_BYTE = 0x7E
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
PIPE_ACCESS_DUPLEX = 0x00000003
PIPE_TYPE_BYTE = 0x00000000
MUTEX_WAIT_MS = 120_000
NOTIFY_RETRIES = 100
NOTIFY_DELAY_S = 0.05


def _norm_app_id(app_id: str) -> str:
    a = (app_id or "").strip()
    for prefix in ("Global\\", "global\\"):
        if a.startswith(prefix):
            a = a[len(prefix) :]
            break
    return a


def mutex_name(app_id: str) -> str:
    return "Global\\" + _norm_app_id(app_id)


def pipe_path(app_id: str) -> str:
    a = (app_id or "").strip()
    if a.startswith("\\\\.\\pipe\\") or a.startswith("\\\\.\\pipe/"):
        return a
    return "\\\\.\\pipe\\" + _norm_app_id(a)


def notify_peer_to_quit(app_id: str) -> bool:
    if os.name != "nt":
        return False
    p = pipe_path(app_id)
    for _ in range(NOTIFY_RETRIES):
        h = kernel32.CreateFileW(
            p,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if h and h != INVALID_HANDLE:
            try:
                buf = (ctypes.c_ubyte * 1)(PIPE_SIGNAL_BYTE)
                w = ctypes.c_ulong(0)
                ok = kernel32.WriteFile(h, buf, 1, ctypes.byref(w), None)
                return bool(ok)
            finally:
                kernel32.CloseHandle(h)
        time.sleep(NOTIFY_DELAY_S)
    return False


def acquire_or_handshake(app_id: str) -> Optional[int]:
    if not _norm_app_id(app_id):
        return None
    if os.name != "nt":
        return 1
    m = mutex_name(app_id)
    h = int(kernel32.CreateMutexW(None, True, m) or 0)
    if h == 0:
        return None
    err = int(kernel32.GetLastError() or 0)
    if err == ERROR_ALREADY_EXISTS:
        if not notify_peer_to_quit(app_id):
            pass
        w = int(kernel32.WaitForSingleObject(h, MUTEX_WAIT_MS))
        if w not in (WAIT_OBJECT_0, WAIT_ABANDONED):
            try:
                kernel32.CloseHandle(h)
            except Exception:
                pass
            return None
    return h


def release_mutex(handle: Optional[int]) -> None:
    if not handle or handle == 1 or os.name != "nt":
        return
    try:
        kernel32.ReleaseMutex(int(handle))
    except Exception:
        pass
    try:
        kernel32.CloseHandle(int(handle))
    except Exception:
        pass


def _attach_audio_monitor(on_quit: Callable[[], None]) -> None:
    """Attach audio topology refresh to the existing app startup hook.

    ``main.py`` already passes a closure capturing ``SoundSwitcherApp`` to
    ``start_pipe_server``. Reusing that stable hook lets the audio monitor be
    integrated without duplicating application startup/shutdown logic.
    """
    try:
        from bm_audio_refresh import AudioRefreshController
    except Exception:
        return

    app = None
    for cell in getattr(on_quit, "__closure__", ()) or ():
        try:
            candidate = cell.cell_contents
        except Exception:
            continue
        if (
            hasattr(candidate, "root")
            and hasattr(candidate, "refresh_playback_list")
            and hasattr(candidate, "refresh_recording_list")
        ):
            app = candidate
            break

    if app is None:
        return

    root = app.root
    if getattr(app, "_bm_audio_refresh_controller", None) is not None:
        return

    def refresh_audio_lists() -> None:
        try:
            if not root.winfo_exists():
                return
            app.refresh_playback_list()
            app.refresh_recording_list()
        except Exception:
            pass

    controller = AudioRefreshController(
        refresh_callback=refresh_audio_lists,
        dispatch=lambda callback: root.after(0, callback),
    )
    app._bm_audio_refresh_controller = controller

    def stop_monitor_on_destroy(event=None) -> None:
        try:
            if event is not None and getattr(event, "widget", None) is not root:
                return
            controller.stop()
        except Exception:
            pass

    try:
        root.bind("<Destroy>", stop_monitor_on_destroy, add="+")
        root.after(0, controller.start)
    except Exception:
        try:
            controller.stop()
        except Exception:
            pass


def start_pipe_server(app_id: str, on_quit: Callable[[], None]) -> None:
    if os.name != "nt":
        return
    p = pipe_path(app_id)
    _attach_audio_monitor(on_quit)

    def worker() -> None:
        while True:
            pipe = kernel32.CreateNamedPipeW(
                p,
                PIPE_ACCESS_DUPLEX,
                PIPE_TYPE_BYTE,
                255,
                1024,
                1024,
                0,
                None,
            )
            if not pipe or pipe == INVALID_HANDLE:
                time.sleep(0.2)
                continue
            ok_conn = kernel32.ConnectNamedPipe(pipe, None)
            err = int(kernel32.GetLastError() or 0)
            if not ok_conn and err != ERROR_PIPE_CONNECTED:
                try:
                    kernel32.CloseHandle(pipe)
                except Exception:
                    pass
                time.sleep(0.05)
                continue
            r = ctypes.c_ulong(0)
            buf = (ctypes.c_ubyte * 4)()
            kernel32.ReadFile(pipe, buf, 1, ctypes.byref(r), None)
            try:
                on_quit()
            except Exception:
                pass
            try:
                kernel32.DisconnectNamedPipe(pipe)
            except Exception:
                pass
            try:
                kernel32.CloseHandle(pipe)
            except Exception:
                pass
            return

    threading.Thread(target=worker, name="bm-pipe", daemon=True).start()
