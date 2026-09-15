from types import SimpleNamespace
import pytest
from mamey import timing

@pytest.mark.parametrize("platform,native,expected",[("darwin",2_097_152,2048),("linux",2048,2048)])
def test_peak_rss_uses_kib_on_supported_resource_platforms(monkeypatch,platform,native,expected):
    monkeypatch.setattr(timing.sys,"platform",platform)
    monkeypatch.setattr(timing,"_HAS_RESOURCE",True)
    monkeypatch.setattr(timing._resource,"getrusage",lambda _:SimpleNamespace(ru_utime=1,ru_stime=2,ru_maxrss=native))
    record=timing.TimingRecorder("DEMO", "gold", "test").finish()
    assert record["process"]["peak_rss_kb"] == expected
