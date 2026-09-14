from __future__ import annotations

from typing import Callable, Optional


class TkDispatcher:
    """Marshal callbacks onto Tk's main/UI thread."""

    def __init__(self, root):
        self._root = root

    def call(self, callback: Callable, *args, **kwargs):
        """Schedule callback with Tk.after(0); never execute it on the caller thread."""
        return self._root.after(0, lambda: callback(*args, **kwargs))

    def call_later(self, delay_ms: int, callback: Callable, *args, **kwargs):
        delay_ms = max(0, int(delay_ms))
        return self._root.after(delay_ms, lambda: callback(*args, **kwargs))

    def cancel(self, after_id) -> None:
        if after_id is None:
            return
        try:
            self._root.after_cancel(after_id)
        except Exception:
            pass


def safe_after(root, callback: Callable, *args, delay_ms: int = 0, **kwargs):
    """Small functional helper for background workers that need to update Tk."""
    return root.after(max(0, int(delay_ms)), lambda: callback(*args, **kwargs))
