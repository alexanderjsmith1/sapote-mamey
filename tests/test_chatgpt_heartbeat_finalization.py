import io
import time

from mamey.timing import HeartbeatThread, heartbeat_context


def test_heartbeat_thread_emits_during_slow_block():
    stream = io.StringIO()
    with heartbeat_context("slow_finalization", enabled=True, seconds=1, stream=stream):
        time.sleep(1.25)
    text = stream.getvalue()
    assert "[heartbeat] slow_finalization still running" in text


def test_heartbeat_disabled_is_silent():
    stream = io.StringIO()
    with heartbeat_context("silent", enabled=False, seconds=1, stream=stream):
        time.sleep(0.05)
    assert stream.getvalue() == ""


def test_heartbeat_seconds_floor():
    hb = HeartbeatThread("floor", enabled=True, seconds=0)
    assert hb.seconds == 1
