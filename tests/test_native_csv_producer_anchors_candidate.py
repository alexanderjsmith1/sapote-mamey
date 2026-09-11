"""Focused controls for native complete-locus anchors in auxiliary CSV producers."""
from types import SimpleNamespace

import pytest

from mamey.bgc_decomp import TWO_MODEL_DECOMP_HEADERS, run_bgc_decomp
from mamey.crosswalk import infer_node_id
from mamey.exact_identity import ExactLocusIdentityError
from mamey.lead_board import AXIS_LEAD_BOARD_HEADERS, axis_lead_board_rows


STRAIN = "TEST-STRAIN"
CONTIG_A = "NODE_1_length_1000_cov_1.5"
CONTIG_B = "NODE_1_length_1000_cov_1.9"


def _bgc(alias, contig, region, *, node_id=None):
    return SimpleNamespace(
        bgc_id=alias,
        contig=contig,
        node_id=infer_node_id(contig, "") if node_id is None else node_id,
        antismash_region=region,
        region_number=int(region[-3:]) if region else None,
        source_gbk="",
        start=0,
        end=1000,
        products=["NRPS"],
        kcb_top="",
        closest_candidate_kcb_product="",
    )


def _triage(alias):
    return SimpleNamespace(
        bgc_id=alias,
        ab_score=1.0,
        af_score=1.0,
        lead_tier="Medium",
        standing_rule_flag="",
        primary_metabolism_flag=False,
        mobile_element_flag="",
        corrected_rank=1,
    )


def test_auxiliary_producers_emit_complete_native_anchors_without_node_collision():
    first = _bgc("BGC101", CONTIG_A, "region001")
    second = _bgc("BGC102", CONTIG_B, "region002")
    assert first.node_id == second.node_id  # normalized join key, not physical identity

    decomp_rows = run_bgc_decomp([first, second], None, strain=STRAIN)["rows"]
    assert TWO_MODEL_DECOMP_HEADERS[-3:] == ("strain", "node_id", "antismash_region")
    assert [(r["strain"], r["contig"], r["node_id"], r["antismash_region"], r["bgc_id"])
            for r in decomp_rows] == [
        (STRAIN, CONTIG_A, first.node_id, "region001", "BGC101"),
        (STRAIN, CONTIG_B, second.node_id, "region002", "BGC102"),
    ]

    axis_rows = axis_lead_board_rows(
        [_triage("BGC101"), _triage("BGC102")],
        {first.bgc_id: first, second.bgc_id: second},
        "ab",
        strain=STRAIN,
    )
    assert AXIS_LEAD_BOARD_HEADERS[-2:] == ["Strain", "antiSMASH_Region"]
    assert [(r["Strain"], r["Contig"], r["Node_ID"], r["antiSMASH_Region"], r["BGC_ID"])
            for r in axis_rows] == [
        (STRAIN, CONTIG_A, first.node_id, "region001", "BGC101"),
        (STRAIN, CONTIG_B, second.node_id, "region002", "BGC102"),
    ]


@pytest.mark.parametrize(
    "bgc",
    [
        _bgc("BGC103", CONTIG_A, ""),
        _bgc("BGC104", CONTIG_A, "region001", node_id="unvalidated-node"),
    ],
)
def test_auxiliary_producers_refuse_missing_or_conflicting_native_identity_before_rows(bgc):
    with pytest.raises(ExactLocusIdentityError):
        run_bgc_decomp([bgc], None, strain=STRAIN)
    with pytest.raises(ExactLocusIdentityError):
        axis_lead_board_rows([_triage(bgc.bgc_id)], {bgc.bgc_id: bgc}, "ab", strain=STRAIN)


@pytest.mark.parametrize("kind",["ab","af","decomp"])
@pytest.mark.parametrize("duplicate",[False,True])
def test_parent_produced_csv_is_admitted_and_duplicates_refused(tmp_path,kind,duplicate):
    import csv,json
    from tools.determinism_fingerprint import _csv_cells
    bgc=_bgc("BGC101",CONTIG_A,"region001")
    if kind=="decomp":
        rows=run_bgc_decomp([bgc],None,strain=STRAIN)["rows"]
        headers=TWO_MODEL_DECOMP_HEADERS;suffix="_4B_two_model_decomp.csv"
    else:
        rows=axis_lead_board_rows([_triage(bgc.bgc_id)],{bgc.bgc_id:bgc},kind,strain=STRAIN)
        headers=AXIS_LEAD_BOARD_HEADERS;suffix=f"_4c_{kind.upper()}_lead_board.csv"
    package=tmp_path/f"{STRAIN}__{CONTIG_A}__region001__BGC101"
    package.mkdir();(package/"manifest.json").write_text(json.dumps({"strain_id":STRAIN}))
    with (package/("synthetic"+suffix)).open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=headers);writer.writeheader();writer.writerows(rows*(2 if duplicate else 1))
    cells,holds=_csv_cells(package)
    if duplicate:
        assert holds and not cells
    else:
        assert not holds and len(cells)==1
        assert next(iter(cells)).endswith(f"{STRAIN} / {CONTIG_A} / region001 / BGC101")


@pytest.mark.parametrize("stale",[False,True])
def test_axis_writer_withholds_both_boards_and_records_typed_identity_refusal(tmp_path,stale):
    import json
    from mamey.cli import _write_axis_lead_boards
    bgc=_bgc("BGC101",CONTIG_A,"")
    paths=[tmp_path/f"{STRAIN}_4c_{axis}_lead_board.csv" for axis in ["AB","AF"]]
    if stale:
        for path in paths:path.write_text("stale generated board")
    issues=[]
    _write_axis_lead_boards(tmp_path,STRAIN,[_triage(bgc.bgc_id)],{bgc.bgc_id:bgc},issues)
    assert not any(path.exists() for path in paths)
    assert issues==["EXACT_LOCUS_IDENTITY_UNAVAILABLE: axis lead boards omitted; complete source locus identity is required."]
    receipts=[json.loads(line) for line in (tmp_path/"run_phase_receipts.jsonl").read_text().splitlines()]
    assert receipts[-1]["phase"]=="axis_lead_boards" and receipts[-1]["status"]=="SKIP"
    assert receipts[-1]["reason"]=="EXACT_LOCUS_IDENTITY_UNAVAILABLE"

def test_axis_writer_preserves_unexpected_errors(tmp_path,monkeypatch):
    from mamey.cli import _write_axis_lead_boards
    import mamey.lead_board as board
    def unexpected(*args,**kwargs):raise RuntimeError("unexpected producer failure")
    monkeypatch.setattr(board,"axis_lead_board_rows",unexpected)
    with pytest.raises(RuntimeError,match="unexpected producer"):
        _write_axis_lead_boards(tmp_path,STRAIN,[],{},[])


def test_core_run_records_auxiliary_identity_refusals_and_retires_stale_sidecar(tmp_path,synthetic_single_contig_admitted_zip):
    import json
    from pathlib import Path
    from mamey.cli import run_one_strain
    strain="SYNTHETIC-REFUSAL"
    package=tmp_path/strain/"package";package.mkdir(parents=True)
    stale=package/f"{strain}_4B_two_model_decomp.csv";stale.write_text("stale generated sidecar")
    result=run_one_strain(strain_id=strain,display_name=strain,input_zip=str(synthetic_single_contig_admitted_zip),outdir=str(tmp_path),mode="full",taxonomy="",source="",bioactivity="",master_path=None,json_mode="off")
    assert result.get("package_zip") and Path(result["package_zip"]).is_file()
    assert not stale.exists()
    assert all(not (package/f"{strain}_4c_{axis}_lead_board.csv").exists() for axis in ["AB","AF"])
    assert any("EXACT_LOCUS_IDENTITY_UNAVAILABLE: two-model" in issue for issue in result["issues"])
    assert any("EXACT_LOCUS_IDENTITY_UNAVAILABLE: axis" in issue for issue in result["issues"])
    receipts=[json.loads(line) for line in (package/"run_phase_receipts.jsonl").read_text().splitlines()]
    assert any(r["phase"]=="bgc_two_model" and r["status"]=="SKIP" and r.get("reason")=="EXACT_LOCUS_IDENTITY_UNAVAILABLE" for r in receipts)


def test_axis_second_write_failure_retires_partial_pair_only(tmp_path,monkeypatch):
    from contextlib import contextmanager
    import mamey.cli as cli
    bgc=_bgc("BGC101",CONTIG_A,"region001")
    paths=[tmp_path/f"{STRAIN}_4c_{axis}_lead_board.csv" for axis in ["AB","AF"]]
    for path in paths:path.write_text("old generated board")
    unrelated=tmp_path/"preserved.txt";unrelated.write_text("keep")
    original=cli._atomic_open_pkg
    @contextmanager
    def fail_second(path,*args,**kwargs):
        if path==paths[1]:raise OSError("injected second write failure")
        with original(path,*args,**kwargs) as handle:yield handle
    monkeypatch.setattr(cli,"_atomic_open_pkg",fail_second)
    with pytest.raises(OSError,match="injected second write failure"):
        cli._write_axis_lead_boards(tmp_path,STRAIN,[_triage(bgc.bgc_id)],{bgc.bgc_id:bgc},[])
    assert not any(path.exists() for path in paths)
    assert unrelated.read_text()=="keep"
