from pathlib import Path
from types import SimpleNamespace
import zipfile
import pytest
from tools.blastp_crawl import crawl_handoff as mod

@pytest.mark.parametrize("member", ["Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_GAP_AS971/../../outside.txt", "Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_GAP_AS971/../_STRAINGAP_SINGLE_CLNR_GAP_AS972/out.txt", "Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_GAP_AS971/out.txt"])
def test_archive_and_existing_symlink_escape_are_refused(tmp_path, monkeypatch, member):
    results = tmp_path / "workspace/Blastp RESULTS"
    results.mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    if ".." not in member:
        (results / "_STRAINGAP_SINGLE_CLNR_GAP_AS971").symlink_to(external)
    archive = tmp_path / "return.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(mod.MANIFEST, "lane\tledger_sha256_at_handoff\n")
        z.writestr(member, "data")
    monkeypatch.setattr(mod, "workspace", lambda: results.parent)
    with pytest.raises(ValueError):
        mod.cmd_merge(SimpleNamespace(zip=str(archive), execute=False))
    assert list(external.iterdir()) == []

@pytest.mark.parametrize("alias", ["lane_symlink", "ledger_symlink", "log_symlink", "ledger_hardlink", "log_hardlink", "unlisted_log_symlink"])
def test_control_destination_aliases_are_refused_before_any_write(tmp_path, monkeypatch, alias):
    lane = "_STRAINGAP_SINGLE_CLNR_GAP_AS971"
    results = tmp_path / "workspace/Blastp RESULTS"
    home = results / lane
    home.mkdir(parents=True)
    other = results / "_STRAINGAP_SINGLE_CLNR_GAP_AS972"
    other.mkdir()
    prior = b"file,status\nquery,submitted\n"
    protected = other / "evidence.txt"
    protected.write_bytes(prior if "ledger" in alias else b"other evidence")
    if alias == "lane_symlink":
        home.rmdir()
        home.symlink_to(other, target_is_directory=True)
        (other / "_ledger.csv").write_bytes(prior)
    else:
        target = home / ("_ledger.csv" if "ledger" in alias else "_run.log")
        if "hardlink" in alias:
            __import__("os").link(protected, target)
        else:
            target.symlink_to(protected)
        if "ledger" not in alias:
            (home / "_ledger.csv").write_bytes(prior)
    (home / "_HANDOFF_OUT.txt").write_text("held")
    before = {p: p.read_bytes() for p in results.rglob("*") if p.is_file()}
    archive = tmp_path / "return.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(mod.MANIFEST, "lane\tledger_sha256_at_handoff\n" + lane + "\t" + mod.sha256(prior) + "\n")
        z.writestr("Blastp RESULTS/" + lane + "/_ledger.csv", "file,status\nquery,fetched\n")
        z.writestr("Blastp RESULTS/" + lane + "/new.xml", "returned evidence")
        if alias != "unlisted_log_symlink":
            z.writestr("Blastp RESULTS/" + lane + "/_run.log", "returned log")
    monkeypatch.setattr(mod, "workspace", lambda: results.parent)
    monkeypatch.setattr(mod, "assert_output_outside_bundle", lambda *args, **kwargs: None)
    with pytest.raises(ValueError):
        mod.cmd_merge(SimpleNamespace(zip=str(archive), execute=True))
    assert all(p.read_bytes() == data for p, data in before.items())
    assert not (home / "new.xml").exists()

def test_valid_archive_directory_entries_and_normal_merge_are_preserved(tmp_path, monkeypatch):
    lane = "_STRAINGAP_SINGLE_CLNR_GAP_AS971"
    home = tmp_path / "workspace/Blastp RESULTS" / lane
    home.mkdir(parents=True)
    prior = b"file,status\nquery,submitted\n"
    (home / "_ledger.csv").write_bytes(prior)
    (home / "_HANDOFF_OUT.txt").write_text("held")
    archive = tmp_path / "return.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(mod.MANIFEST, "lane\tledger_sha256_at_handoff\n" + lane + "\t" + mod.sha256(prior) + "\n")
        z.writestr("Blastp RESULTS/", "")
        z.writestr("Blastp RESULTS/" + lane + "/", "")
        z.writestr("Blastp RESULTS/" + lane + "/_ledger.csv", "file,status\nquery,fetched\n")
        z.writestr("Blastp RESULTS/" + lane + "/new.xml", "returned evidence")
    monkeypatch.setattr(mod, "workspace", lambda: home.parents[1])
    monkeypatch.setattr(mod, "assert_output_outside_bundle", lambda *args, **kwargs: None)
    assert mod.cmd_merge(SimpleNamespace(zip=str(archive), execute=True)) == 0
    assert (home / "new.xml").read_text() == "returned evidence"
    assert not (home / "_HANDOFF_OUT.txt").exists()
