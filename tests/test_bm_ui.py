from bm_ui import TkDispatcher


class _FakeRoot:
    def __init__(self):
        self.calls = []

    def after(self, delay, callback):
        self.calls.append((delay, callback))
        return len(self.calls)

    def after_cancel(self, after_id):
        self.calls.pop(after_id - 1)


def test_dispatcher_always_uses_after_zero():
    root = _FakeRoot()
    dispatcher = TkDispatcher(root)
    result = dispatcher.call(lambda: None)
    assert result == 1
    assert root.calls[0][0] == 0


def test_dispatcher_can_schedule_delay():
    root = _FakeRoot()
    dispatcher = TkDispatcher(root)
    dispatcher.call_later(-10, lambda: None)
    assert root.calls[0][0] == 0
    dispatcher.call_later(250, lambda: None)
    assert root.calls[1][0] == 250
