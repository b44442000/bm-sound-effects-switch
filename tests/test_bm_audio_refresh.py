from bm_audio_refresh import AudioRefreshController


class FakeMonitor:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1


class ControllerUnderTest(AudioRefreshController):
    def __init__(self, refresh, dispatch):
        super().__init__(refresh, dispatch)
        self._monitor = FakeMonitor()


def test_start_and_stop_are_idempotent():
    c = ControllerUnderTest(lambda: None, lambda fn: fn())
    c.start()
    c.start()
    assert c.started
    assert c.monitor.started == 1

    c.stop()
    c.stop()
    assert not c.started
    assert c.monitor.stopped == 1


def test_device_change_is_dispatched_to_gui():
    events = []
    queued = []
    c = ControllerUnderTest(lambda: events.append("refresh"), queued.append)

    c._on_device_change()
    assert events == []
    assert len(queued) == 1

    queued[0]()
    assert events == ["refresh"]


def test_dispatch_failure_is_ignored():
    c = ControllerUnderTest(lambda: None, lambda fn: (_ for _ in ()).throw(RuntimeError("closed")))
    c._on_device_change()
