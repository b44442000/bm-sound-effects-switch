from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Dict, Optional

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


@dataclass(frozen=True)
class Hotkey:
    hotkey_id: int
    modifiers: int
    vk: int


class HotkeyRegistry:
    """Thin, testable wrapper around the Windows RegisterHotKey API.

    Registration happens on the thread that owns the window/message loop.
    The application remains responsible for dispatching WM_HOTKEY messages.
    """

    def __init__(self, hwnd: int):
        self.hwnd = int(hwnd)
        self._items: Dict[int, Hotkey] = {}
        self._user32 = None
        if os.name == "nt":
            import ctypes
            self._user32 = ctypes.windll.user32

    @property
    def items(self) -> tuple[Hotkey, ...]:
        return tuple(self._items.values())

    def register(self, hotkey_id: int, modifiers: int, vk: int, *, no_repeat: bool = True) -> bool:
        if not self._user32:
            return False
        hotkey_id = int(hotkey_id)
        modifiers = int(modifiers) | (MOD_NOREPEAT if no_repeat else 0)
        vk = int(vk)
        if hotkey_id in self._items:
            self.unregister(hotkey_id)
        ok = bool(self._user32.RegisterHotKey(self.hwnd, hotkey_id, modifiers, vk))
        if ok:
            self._items[hotkey_id] = Hotkey(hotkey_id, modifiers, vk)
        return ok

    def unregister(self, hotkey_id: int) -> bool:
        hotkey_id = int(hotkey_id)
        self._items.pop(hotkey_id, None)
        if not self._user32:
            return False
        return bool(self._user32.UnregisterHotKey(self.hwnd, hotkey_id))

    def unregister_all(self) -> None:
        for hotkey_id in tuple(self._items):
            self.unregister(hotkey_id)

    def dispatch(self, wparam: int, callbacks: Dict[int, Callable[[], None]]) -> bool:
        """Dispatch a WM_HOTKEY wParam to an application callback."""
        hotkey_id = int(wparam)
        if hotkey_id not in self._items:
            return False
        callback = callbacks.get(hotkey_id)
        if callback is None:
            return False
        callback()
        return True
