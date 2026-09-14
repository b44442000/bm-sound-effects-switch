import bm_audio_monitor as monitor


class Device:
    def __init__(self, device_id, name, state):
        self.id = device_id
        self.FriendlyName = name
        self.state = state


def test_poll_once_only_notifies_on_change(monkeypatch):
    events = []
    snapshots = [
        [Device("a", "Speakers", "1")],
        [Device("a", "Speakers", "1")],
        [Device("b", "USB DAC", "1")],
    ]

    monkeypatch.setattr(
        monitor.AudioDeviceMonitor,
        "_signature",
        staticmethod(lambda: tuple(
            (d.id, d.FriendlyName, d.state) for d in snapshots.pop(0)
        )),
    )

    m = monitor.AudioDeviceMonitor(lambda: events.append("changed"))
    assert not m.poll_once()
    assert not m.poll_once()
    assert m.poll_once()
    assert events == ["changed"]


def test_interval_is_clamped():
    m = monitor.AudioDeviceMonitor(lambda: None, interval=0)
    assert m._interval == 0.5


def test_callback_failure_does_not_break_monitor(monkeypatch):
    snapshots = [
        [("a", "Speakers", "1")],
        [("b", "USB DAC", "1")],
    ]
    monkeypatch.setattr(
        monitor.AudioDeviceMonitor,
        "_signature",
        staticmethod(lambda: snapshots.pop(0)),
    )

    m = monitor.AudioDeviceMonitor(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert not m.poll_once()
    assert m.poll_once()
