"""run --strains survives a refused or short result, and a [BLOCKING] issue fails the exit code."""
from argparse import Namespace

from mamey import cli


def _args(**overrides):
    d = dict(chatgpt_safe=True, chatgpt_followup=True, mode="gold", brief="standard",
             json_evidence="bounded", require_workbook=False, locus_maps="auto", heartbeat_seconds=20,
             strains=None, strain="TEST", input_zip="missing.zip", outdir="out", master=None,
             taxonomy=None, source=None, bioactivity=None, bioactivity_json=None,
             antismash_profile="unknown", release=None, metadata_csv=None, token_budget="standard",
             display_name=None)
    d.update(overrides)
    return Namespace(**d)


def test_blocking_issue_exits_one(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "run_one_strain", lambda **kw: {
        "strain_id": "TEST", "status": "MAMEY_COMPLETE_WITH_ISSUES", "validator_status": "PASS",
        "issues": ["[BLOCKING] sealed-internal gate_validation.json differs from the external final receipt"]})
    assert cli.run_command(_args(outdir=str(tmp_path))) == 1


def test_advisory_issue_still_exits_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "run_one_strain", lambda **kw: {
        "strain_id": "TEST", "status": "MAMEY_COMPLETE_WITH_ISSUES", "validator_status": "PASS",
        "issues": ["[WARN] enrichment files missing before seal"]})
    assert cli.run_command(_args(outdir=str(tmp_path))) == 0


def test_batch_keeps_going_after_a_short_result(monkeypatch, tmp_path):
    rows = iter([{"status": "PACKAGE_LOCKED", "written": False},
                 {"strain_id": "B", "status": "MAMEY_COMPLETE", "raw_bgcs": 3, "assembly_tier": "GOOD",
                  "issues": []}])
    monkeypatch.setattr(cli, "run_one_strain", lambda **kw: next(rows))
    results = cli.run_batch(input_zips=["A.zip", "B.zip"], outdir=str(tmp_path), mode="gold",
                            master_path=None, taxonomy_list=[], source_list=[])
    assert [r["status"] for r in results] == ["PACKAGE_LOCKED", "MAMEY_COMPLETE"]


def test_batch_refusal_is_a_result_row_not_an_int(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_refuse_unsafe_strain_id", lambda sid: sid.startswith("BAD"))
    monkeypatch.setattr(cli, "run_one_strain", lambda **kw: {
        "strain_id": kw["strain_id"], "status": "MAMEY_COMPLETE", "raw_bgcs": 1,
        "assembly_tier": "GOOD", "issues": []})
    results = cli.run_batch(input_zips=["BAD_one.zip", "GOOD_two.zip"], outdir=str(tmp_path), mode="gold",
                            master_path=None, taxonomy_list=[], source_list=[])
    assert isinstance(results, list)
    assert results[0]["status"] == "REFUSED_UNSAFE_ID_OR_OUTDIR"
    assert results[1]["status"] == "MAMEY_COMPLETE"
