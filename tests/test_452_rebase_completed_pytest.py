from pathlib import Path
from types import SimpleNamespace
import pytest
from tools import cut_audit

@pytest.mark.parametrize("rc,out", [(2, "collection interrupted"), (3, "INTERNALERROR> broken"), (4, "usage error"), (5, "no tests ran in 0.01s"), (0, ""), (1, "1 failed in 0.01s\nInterrupted: broken")])
def test_incomplete_test_run_cannot_be_clean_delta(tmp_path, monkeypatch, rc, out):
    base = tmp_path / "base"
    base.mkdir()
    card = tmp_path / "card"
    card.mkdir()
    def run(cmd, **kwargs):
        return (rc, out) if "pytest" in cmd else (0, "")
    monkeypatch.setattr(cut_audit, "_run", run)
    args = SimpleNamespace(base=str(base), card=str(card), tests=["tests/example.py"], python="python3", timeout=1, keep=False)
    assert cut_audit.rebase_verify(args) == 2
