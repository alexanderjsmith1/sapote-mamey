import json
import zipfile
from types import SimpleNamespace

from mamey import registry_detector


def _bgc(source="x.region001.gbk"):
    return SimpleNamespace(
        bgc_id="BGC001", contig="NODE_1", node_id="NODE_1",
        antismash_region="region001", source_gbk=source,
    )


def test_missing_hmm_database_is_named_degradation(monkeypatch, tmp_path):
    archive = tmp_path / "input.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("x.region001.gbk", "LOCUS       x 1 bp DNA\n//\n")
    import mamey.hmm_blastp_adjudicate as owner
    monkeypatch.setattr(owner, "resolve_hmm_db", lambda: None)
    receipt = registry_detector.run_hmm_scan(str(archive), [_bgc()], "TEST-STRAIN")
    assert receipt["status"] == "HMM_SCAN_UNAVAILABLE"
    assert receipt["rows"] == []


def test_existing_owner_runs_and_emits_complete_identity(monkeypatch, tmp_path):
    archive = tmp_path / "input.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("x.region001.gbk", "LOCUS       x 1 bp DNA\n//\n")
    import mamey.hmm_blastp_adjudicate as owner
    monkeypatch.setattr(owner, "resolve_hmm_db", lambda: {"path": str(tmp_path / "scanner.hmm")})
    monkeypatch.setattr(owner, "walk_domains", lambda path, hmm_file=None: ({"gene1": [(1, "KS", 42.0)]}, ["gene1"], ""))
    receipt = registry_detector.run_hmm_scan(str(archive), [_bgc()], "TEST-STRAIN")
    row = receipt["rows"][0]
    assert receipt["status"] == "PASS"
    assert [row[k] for k in ("strain", "node_or_contig", "region", "bgc_alias")] == [
        "TEST-STRAIN", "NODE_1", "region001", "BGC001"
    ]
    assert row["domain_hit_count"] == 1


def test_cli_declares_hmm_scan_flag():
    from mamey.cli import build_parser
    args = build_parser().parse_args(["run", "--input-zip", "x.zip", "--hmm-scan"])
    assert args.hmm_scan is True
