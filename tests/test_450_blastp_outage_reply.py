"""An NCBI outage page is not an answer about a search: status() must raise, not return UNKNOWN."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/blastp_crawl/nr_rid_runner.py"


@pytest.fixture
def runner():
    spec = importlib.util.spec_from_file_location("rid_runner_450_outage", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("reply", ["Temporarily unavailable", "", "<html>Service busy</html>"])
def test_reply_without_status_raises(runner, monkeypatch, reply):
    monkeypatch.setattr(runner, "_curl", lambda args, timeout: reply)
    with pytest.raises(runner.TransportUnverified):
        runner.status("RID0001")


@pytest.mark.parametrize("word", ["UNKNOWN", "READY", "WAITING", "FAILED"])
def test_real_status_lines_pass_through(runner, monkeypatch, word):
    monkeypatch.setattr(runner, "_curl", lambda args, timeout: f"QBlastInfoBegin\n\tStatus={word}\nQBlastInfoEnd\n")
    assert runner.status("RID0001") == word
