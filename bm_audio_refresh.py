from __future__ import annotations

from typing import Callable, Optional

from bm_audio_monitor import AudioDeviceMonitor


class AudioRefreshController:
    """Bridge audio-device monitoring to a GUI main-thread dispatcher.

    ``dispatch`` must schedule the supplied callback on the GUI thread. For
    Tkinter, pass ``root.after`` through a small wrapper such as
    ``lambda fn: root.after(0, fn)``.
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

    @property
    def monitor(self) -> AudioDeviceMonitor:
        return self._monitor

    @property
    def started(self) -> bool:
        return self._started

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._monitor.start()

    def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        self._monitor.stop()

    def _on_device_change(self) -> None:
        try:
            self._dispatch(self._refresh_callback)
        except Exception:
            # GUI shutdown/race conditions must not kill the monitor thread.
            pass
