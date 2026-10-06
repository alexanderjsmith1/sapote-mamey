"""Public synthetic receipt fixtures; no sequence search or private result fixture."""
import csv
import json
from pathlib import Path

import pytest

from mamey import modeb_template_emitter as emitter
from mamey.modeb_current50_v2 import load_contract

CORE = "PUBLIC-1 / CONTIG_A_length_1000 / region001 / BGC001"
PARTNER = "PUBLIC-1 / CONTIG_B_length_1000 / region002 / BGC002"


def source(tmp_path):
    d = tmp_path / "rescue"
    d.mkdir()
    receipt = dict(core=CORE, reference="BGC0000001.gbk", reference_name="synthetic comparator",
                   reference_source="synthetic fixture", reference_genes=2, present_in_core=1,
                   missing_found_clear=1, missing_found_ambiguous=0, missing_not_found=0,
                   split_gene_check="run", partners=[])
    (d / "gap_rescue_receipt.json").write_text(json.dumps(receipt))
    rows = [dict(reference_gene="1", name="enzyme", reference_gene_kind="biosynthetic",
                 status="PRESENT_IN_CORE", best_locus="a_1", best_protein="q1", best_len_aa="3",
                 best_region_identity=CORE, best_identity_pct="80", best_coverage_pct="100",
                 partner_verdict=""),
            dict(reference_gene="2", name="tailor", reference_gene_kind="biosynthetic-additional",
                 status="MISSING_FOUND_CLEAR", best_locus="b_1", best_protein="q2", best_len_aa="3",
                 best_region_identity=PARTNER, best_identity_pct="70", best_coverage_pct="100",
                 partner_verdict="SUPPORTED")]
    write_table(d / "gap_rescue.tsv", rows)
    write_table(d / "gap_rescue_split_genes.tsv", [], ["split_call", "piece1_region_identity",
                                                      "piece2_region_identity"])
    (d / "gap_rescue_proteins.faa").write_text(">q1\nACD\n>q2\nEFG\n")
    return d, rows


def write_table(path, rows, fields=None):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)


def emitted(tmp_path, monkeypatch, root, contract="current50_v2"):
    monkeypatch.setattr(emitter, "_bgc_facts", lambda *_: dict(
        strain_id="PUBLIC-1", contig="CONTIG_A_length_1000", node="CONTIG_A_length_1000",
        region="region001", bgc_id="BGC001", gene_rows=[]))
    return emitter.emit_card_template(tmp_path, "BGC001", contract=load_contract(contract),
                                      sources={"gap_rescue_dir": str(root)})


def test_emitter_populates_exact_rescue_evidence(tmp_path, monkeypatch):
    d, _ = source(tmp_path)
    md = emitted(tmp_path, monkeypatch, d)
    section = md.split("## §26 ")[1].split("## §27 ")[0]
    assert "BGC0000001.gbk" in section and "SUPPORTED" in section
    assert PARTNER in section and "Source-bound reference proteins" in section
    assert "1 of 2" in section and "Physical contig joins inferred: **0**" in section
    assert "1 supported external reference-gene assignment" in md.split("## §19 ")[1].split("## §20 ")[0]


def test_adjudication_demotes_find_without_rewriting_search_status(tmp_path):
    from mamey.modeb_gap_rescue import load_gap_rescue
    d, _ = source(tmp_path)
    write_table(d.parent / (d.name + "_ADJUDICATION.tsv"), [dict(
        reference_gene="tailor", candidate_locus="b_1", verdict="PARALOG_FAMILY")])
    r = load_gap_rescue(d, CORE)
    assert r["state"] == "BOUND" and r["counts"]["MISSING_FOUND_CLEAR"] == 1
    assert r["supported_external"] == 0
    assert r["rows"][1]["run_partner_verdict"] == "SUPPORTED"
    assert r["rows"][1]["effective_partner_verdict"] == "PARALOG_FAMILY"
    assert len(r["sources"]) == 5


def test_wrong_identity_is_a_hold_not_zero_rescue(tmp_path, monkeypatch):
    d, _ = source(tmp_path)
    p = d / "gap_rescue_receipt.json"
    r = json.loads(p.read_text()); r["core"] = PARTNER; p.write_text(json.dumps(r))
    md = emitted(tmp_path, monkeypatch, d)
    section = md.split("## §26 ")[1].split("## §27 ")[0]
    assert "RESCUE_EVIDENCE_HOLD" in section and "supported external reference-gene assignments: **0**" not in section


def test_root_duplicate_identity_is_not_arbitrarily_selected(tmp_path):
    import shutil
    from mamey.modeb_gap_rescue import load_gap_rescue
    d, _ = source(tmp_path)
    shutil.copytree(d, tmp_path / "duplicate")
    assert load_gap_rescue(tmp_path, CORE)["state"] == "HOLD"


@pytest.mark.parametrize("fault", ["counts", "duplicate_gene", "protein_length", "missing_fasta",
                                  "wrong_core_location", "bad_percent"])
def test_invalid_source_cannot_become_a_negative(tmp_path, fault):
    from mamey.modeb_gap_rescue import load_gap_rescue
    d, rows = source(tmp_path)
    if fault == "counts":
        p = d / "gap_rescue_receipt.json"; r = json.loads(p.read_text()); r["present_in_core"] = 2
        p.write_text(json.dumps(r))
    elif fault == "duplicate_gene":
        rows[1]["reference_gene"] = "1"
    elif fault == "protein_length":
        rows[1]["best_len_aa"] = "9"
    elif fault == "missing_fasta":
        (d / "gap_rescue_proteins.faa").unlink()
    elif fault == "wrong_core_location":
        rows[0]["best_region_identity"] = PARTNER
    elif fault == "bad_percent":
        rows[1]["best_identity_pct"] = "101"
    if fault not in ("counts", "missing_fasta"):
        write_table(d / "gap_rescue.tsv", rows)
    assert load_gap_rescue(d, CORE)["state"] == "HOLD"


def test_unrelated_clear_split_is_separate_from_focal_split(tmp_path):
    from mamey.modeb_gap_rescue import load_gap_rescue
    d, _ = source(tmp_path)
    write_table(d / "gap_rescue_split_genes.tsv", [dict(split_call="CLEAR",
        piece1_region_identity=PARTNER, piece2_region_identity="PUBLIC-1 / OTHER / region001 / BGC003")])
    r = load_gap_rescue(d, CORE)
    assert r["focal_clear_splits"] == 0 and r["other_clear_splits"] == 1


def test_new_source_flag_survives_route_handoffs():
    assert emitter.source_argv({"gap_rescue_dir": "/tmp/example"}) == ["--gap-rescue-dir", "/tmp/example"]


def test_legacy_profile_does_not_consume_v2_source(tmp_path, monkeypatch):
    d, _ = source(tmp_path)
    assert emitted(tmp_path, monkeypatch, d, "full48") == emitted(tmp_path, monkeypatch, "/absent", "full48")


def test_supported_gene_does_not_override_unresolved_pair_review(tmp_path):
    from mamey.modeb_gap_rescue import load_gap_rescue, render_section
    d, _ = source(tmp_path)
    p = tmp_path / "pairs.tsv"
    write_table(p, [{"strain": "PUBLIC-1", "core identity": CORE, "partner contig": "CONTIG_B_length_1000",
                     "partner region": PARTNER, "verdict": "UNRESOLVED", "rule": "competing locus",
                     "source": "synthetic review"}])
    r = load_gap_rescue(d, CORE, p)
    assert r["supported_external"] == 1 and r["pair_verdicts"][0]["verdict"] == "UNRESOLVED"
    assert "UNRESOLVED" in render_section(r) and "Gene-level support" in render_section(r)


def test_missing_pair_source_is_a_hold_when_explicitly_requested(tmp_path):
    from mamey.modeb_gap_rescue import load_gap_rescue
    d, _ = source(tmp_path)
    assert load_gap_rescue(d, CORE, tmp_path / "absent.tsv")["state"] == "HOLD"


def test_unperformed_split_check_does_not_become_a_zero_split_conclusion(tmp_path):
    from mamey.modeb_gap_rescue import load_gap_rescue, render_impact
    d, _ = source(tmp_path)
    p = d / "gap_rescue_receipt.json"
    r = json.loads(p.read_text()); r["split_gene_check"] = "not run: missing coordinates"
    p.write_text(json.dumps(r))
    text = render_impact(load_gap_rescue(d, CORE))
    assert "limited" in text and "0 CLEAR split" not in text


@pytest.mark.parametrize("route", ["emit-modeb-template", "modeb-round", "deliverable-queue"])
def test_all_routes_accept_the_two_new_sources(route):
    from mamey import cli
    args = cli.build_parser().parse_args([route, "--gap-rescue-dir", "existing", "--rescue-verdicts-tsv", "pairs"] +
        (["--runs-dir", "runs", "--out-root", "out"] if route == "deliverable-queue" else ["--package", "pkg"]))
    assert args.gap_rescue_dir == "existing" and args.rescue_verdicts_tsv == "pairs"
