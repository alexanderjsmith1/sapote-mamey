from pathlib import Path
import pytest
from types import SimpleNamespace
import zipfile
from tools.blastp_crawl import crawl_handoff as mod

@pytest.mark.parametrize("result_name", ["result.xml", "nested/_ledger.csv", "nested/_run.log", "nested/_runner.pid", "nested/_HANDOFF_OUT.txt"])
def test_conflicting_results_hold_ledger_and_marker_before_any_copy(tmp_path, monkeypatch, result_name):
    lane = "_STRAINGAP_SINGLE_CLNR_GAP_AS971"
    home = tmp_path / "workspace/Blastp RESULTS" / lane
    home.mkdir(parents=True)
    prior = b"file,status\nquery,submitted\n"
    (home / "_ledger.csv").write_bytes(prior)
    result_path = home / result_name
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text("home evidence")
    (home / "_HANDOFF_OUT.txt").write_text("held")
    archive = tmp_path / "return.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(mod.MANIFEST, "lane\tledger_sha256_at_handoff\n" + lane + "\t" + mod.sha256(prior) + "\n")
        z.writestr("Blastp RESULTS/" + lane + "/_ledger.csv", "file,status\nquery,fetched\n")
        z.writestr("Blastp RESULTS/" + lane + "/" + result_name, "returned evidence")
        z.writestr("Blastp RESULTS/" + lane + "/new.xml", "new evidence")
    monkeypatch.setattr(mod, "workspace", lambda: home.parents[1])
    monkeypatch.setattr(mod, "assert_output_outside_bundle", lambda *args, **kwargs: None)
    assert mod.cmd_merge(SimpleNamespace(zip=str(archive), execute=True)) == 1
    assert (home / "_ledger.csv").read_bytes() == prior
    assert (home / "_HANDOFF_OUT.txt").exists()
    assert not (home / "new.xml").exists()
