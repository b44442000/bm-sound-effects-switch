import os

from bm_hotkeys import HotkeyRegistry, MOD_CONTROL, MOD_NOREPEAT


def test_registry_starts_empty():
    registry = HotkeyRegistry(0)
    assert registry.items == ()


def test_non_windows_registration_fails_cleanly():
    registry = HotkeyRegistry(0)
    if os.name != "nt":
        assert not registry.register(1, MOD_CONTROL, ord("A"))
        assert registry.items == ()


def test_constants_are_stable():
    assert MOD_CONTROL == 0x0002
    assert MOD_NOREPEAT == 0x4000
