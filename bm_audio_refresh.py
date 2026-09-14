from __future__ import annotations

import threading
from typing import Callable, Optional

from bm_audio_monitor import AudioDeviceMonitor


class AudioRefreshController:
    """Bridge audio-device monitoring to a GUI main-thread dispatcher.

    ``dispatch`` must schedule the supplied callback on the GUI thread. For
    Tkinter, pass ``root.after`` through a wrapper such as
    ``lambda fn: root.after(0, fn)``.

    Multiple device notifications that arrive before the GUI has refreshed are
    coalesced into one refresh. This prevents a burst of USB/Bluetooth
    notifications from queueing a large number of identical Tk callbacks.
    """

    def __init__(
        self,
        refresh_callback: Callable[[], None],
        dispatch: Callable[[Callable[[], None]], object],
        interval: float = 2.0,
    ) -> None:
        self._refresh_callback = refresh_callback
        self._dispatch = dispatch
        self._monitor = AudioDeviceMonitor(self._on_device_change, interval)
        self._started = False
        self._state_lock = threading.Lock()
        self._refresh_queued = False

    @property
    def monitor(self) -> AudioDeviceMonitor:
        return self._monitor

    @property
    def started(self) -> bool:
        with self._state_lock:
            return self._started

    def start(self) -> None:
        with self._state_lock:
            if self._started:
                return
            self._started = True
        try:
            self._monitor.start()
        except Exception:
            with self._state_lock:
                self._started = False
            raise

    def stop(self) -> None:
        with self._state_lock:
            if not self._started:
                return
            self._started = False
            self._refresh_queued = False
        self._monitor.stop()

    def _on_device_change(self) -> None:
        with self._state_lock:
            if not self._started or self._refresh_queued:
                return
            self._refresh_queued = True

        try:
            self._dispatch(self._run_refresh)
        except Exception:
            with self._state_lock:
                self._refresh_queued = False

    def _run_refresh(self) -> None:
        try:
            with self._state_lock:
                if not self._started:
                    return
            self._refresh_callback()
        finally:
            with self._state_lock:
                self._refresh_queued = False
