from __future__ import annotations

import threading
from typing import Callable, Optional

try:
    import comtypes
    from pycaw.pycaw import AudioUtilities
except Exception:  # pragma: no cover - Windows runtime dependency
    comtypes = None
    AudioUtilities = None


class AudioDeviceMonitor:
    """Low-impact polling monitor for Windows audio device topology changes.

    The callback runs on the monitor thread. GUI callers should marshal it back
    to the Tk main thread with root.after().
    """

    def __init__(self, on_change: Callable[[], None], interval: float = 2.0):
        self._on_change = on_change
        self._interval = max(0.5, float(interval))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_signature = None

    @staticmethod
    def _signature():
        if AudioUtilities is None:
            return ()
        devices = AudioUtilities.GetAllDevices()
        return tuple(
            sorted(
                (
                    str(getattr(d, "id", "")),
                    str(getattr(d, "FriendlyName", "")),
                    str(getattr(d, "state", "")),
                )
                for d in devices
            )
        )

    def poll_once(self) -> bool:
        """Poll once and return True only when the device topology changed."""
        signature = self._signature()
        if self._last_signature is None:
            self._last_signature = signature
            return False
        if signature == self._last_signature:
            return False
        self._last_signature = signature
        try:
            self._on_change()
        except Exception:
            # The monitor must survive a callback failure and continue polling.
            pass
        return True

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="bm-audio-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._thread = None

    def _run(self) -> None:
        if comtypes is not None:
            try:
                comtypes.CoInitialize()
            except Exception:
                pass
        try:
            while not self._stop.is_set():
                try:
                    self.poll_once()
                except Exception:
                    # Device enumeration can temporarily fail during USB/Bluetooth changes.
                    pass
                self._stop.wait(self._interval)
        finally:
            if comtypes is not None:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass
