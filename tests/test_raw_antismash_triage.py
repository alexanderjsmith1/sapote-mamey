"""test_raw_antismash_triage.py — tests for the pre-extraction genome triage mode (v9.7.233).

`mamey explore` chains kcb_frontpage, a new scanner-evidence census, rare_motif, and
split_detector, in the run order Sapote_Mamey_ROADMAP.md documents. These tests build
small synthetic antiSMASH-shaped fixtures (a regions.js + region GBKs) directly with
Biopython/JSON, rather than depending on a real antiSMASH ZIP not present in this repo.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
pytest.importorskip("Bio")
from Bio.Seq import Seq
from Bio.SeqFeature import FeatureLocation, SeqFeature
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _write_region_gbk(path: Path, seq_id: str, product: str, cds_domains: list[list[str]]):
    """Write a minimal but real, Biopython-parseable region GBK with the qualifiers
    kcb_frontpage/rare_motif/split_detector/scanner_evidence all actually read:
    region/product, and per-CDS locus_tag/translation/sec_met_domain."""
    seq = Seq("ATG" * 2000)
    rec = SeqRecord(seq, id=seq_id, name=seq_id[:16], description="synthetic test region",
                     annotations={"molecule_type": "DNA", "topology": "linear"})
    rec.features.append(SeqFeature(FeatureLocation(0, len(seq)), type="region",
                                    qualifiers={"product": [product]}))
    pos = 0
    for i, doms in enumerate(cds_domains):
        start, end = pos, pos + 300
        pos = end + 50
        rec.features.append(SeqFeature(
            FeatureLocation(start, end, strand=1), type="CDS",
            qualifiers={"locus_tag": [f"ctg_{i}"],
                        "translation": ["M" + "A" * 98],
                        "sec_met_domain": [f"{d} (E-value: 1e-30)" for d in doms]},
        ))
    with open(path, "w") as fh:
        SeqIO.write(rec, fh, "genbank")


def _write_regions_js(path: Path, records: list[dict]):
    """records: [{"seq_id": str, "regions": [{"idx": int, "anchor": "r1c1"}]}]"""
    record_data = [{"length": 6000, "seq_id": r["seq_id"], "regions": r["regions"]}
                   for r in records]
    results_data = {}
    for r in records:
        for reg in r["regions"]:
            results_data[reg["anchor"]] = {
                "orfs": [],
                "knownclusterblast": [{
                    "variant_name": "knownclusterblast",
                    "matches": reg.get("kcb_matches", []),
                }] if reg.get("kcb_matches") is not None else [],
            }
    js = ("var recordData = " + json.dumps(record_data) + ";\n"
          "var all_regions = [];\n"
          "var resultsData = " + json.dumps(results_data) + ";\n")
    path.write_text(js)


def _build_strain_dir(tmp_path: Path, name: str = "TEST") -> Path:
    """One strain, two regions: region001 carries a STRONG KCB hit + a watchlist motif
    (phosphonate PEP_mutase) so it should rank #1; region002 carries nothing notable."""
    d = tmp_path / name
    d.mkdir(parents=True)
    _write_regions_js(d / "regions.js", [
        {"seq_id": "NODE_1_length_6000_cov_10.0",
         "regions": [{"idx": 1, "anchor": "r1c1",
                      "kcb_matches": [{"label": "MIBiG: testomycin", "similarity": 90,
                                       "genes": list(range(12)), "product": "NRPS",
                                       "accession": "BGC0000001"}]}]},
        {"seq_id": "NODE_2_length_6000_cov_10.0",
         "regions": [{"idx": 1, "anchor": "r2c1", "kcb_matches": []}]},
    ])
    _write_region_gbk(d / "NODE_1_length_6000_cov_10.0.region001.gbk",
                       "NODE_1_length_6000_cov_10.0", "NRPS",
                       [["PEP_mutase", "AMP-binding"], ["Condensation"]])
    _write_region_gbk(d / "NODE_2_length_6000_cov_10.0.region001.gbk",
                       "NODE_2_length_6000_cov_10.0", "terpene",
                       [["Terpene_synth"]])
    return d


# ---------------------------------------------------------------------------
# stage_strain_dir / zip safety
# ---------------------------------------------------------------------------

def test_stage_strain_dir_extracts_and_locates_region_gbks(tmp_path):
    from mamey.raw_antismash_triage import stage_strain_dir

    src = _build_strain_dir(tmp_path / "src")
    zpath = tmp_path / "input.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for f in src.iterdir():
            z.write(f, f.name)

    out = stage_strain_dir(zpath, tmp_path / "staged")
    assert out.exists()
    assert list(out.glob("*region*.gbk"))


def test_stage_strain_dir_rejects_non_antismash_zip(tmp_path):
    from mamey.raw_antismash_triage import stage_strain_dir

    zpath = tmp_path / "not_antismash.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("readme.txt", "hello")
    with pytest.raises(ValueError, match="antiSMASH"):
        stage_strain_dir(zpath, tmp_path / "staged2")


def test_safe_extract_zip_rejects_path_traversal(tmp_path):
    from mamey.raw_antismash_triage import _safe_extract_zip

    zpath = tmp_path / "evil.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("../../etc/evil.txt", "pwned")
    dest = tmp_path / "dest"
    dest.mkdir()
    with zipfile.ZipFile(zpath) as z:
        with pytest.raises(ValueError, match="unsafe zip member path"):
            _safe_extract_zip(z, dest)


# ---------------------------------------------------------------------------
# _kcb_anchor_to_region_id
# ---------------------------------------------------------------------------

def test_kcb_anchor_to_region_id_maps_real_recordData_shape(tmp_path):
    from mamey.raw_antismash_triage import _kcb_anchor_to_region_id

    d = _build_strain_dir(tmp_path)
    m = _kcb_anchor_to_region_id(d)
    assert m == {
        "r1c1": "NODE_1_length_6000_cov_10.0.region001",
        "r2c1": "NODE_2_length_6000_cov_10.0.region001",
    }


def test_kcb_anchor_to_region_id_empty_when_no_regions_js(tmp_path):
    from mamey.raw_antismash_triage import _kcb_anchor_to_region_id

    d = tmp_path / "empty"
    d.mkdir()
    assert _kcb_anchor_to_region_id(d) == {}


# ---------------------------------------------------------------------------
# scanner_evidence
# ---------------------------------------------------------------------------

def _fake_bundle_root(tmp_path: Path, registry_scanners: list[dict]) -> Path:
    root = tmp_path / "fake_bundle"
    (root / "Wheelhouse" / "scanners").mkdir(parents=True)
    registry = {"registry_version": "0.99-test", "scanners": registry_scanners}
    (root / "Wheelhouse" / "scanners" / "scanner_registry_v0.99.json").write_text(
        json.dumps(registry))
    return root


def test_scanner_evidence_reports_gate_complete_only_when_all_gate_domains_present(tmp_path):
    from mamey.raw_antismash_triage import scanner_evidence

    strain_dir = _build_strain_dir(tmp_path / "strain")
    bundle_root = _fake_bundle_root(tmp_path, [
        {"id": "MD02", "name": "phosphonate", "cls": "misc",
         "gate": ["PEP_mutase"], "support": ["AMP-binding"],
         "rule": "PepM present", "trap": "", "test_status": "PASS"},
        {"id": "AB06", "name": "diterpene", "cls": "terpene",
         "gate": ["diterpene_synth_never_present"], "support": [],
         "rule": "gate only", "trap": "", "test_status": "PASS"},
    ])
    res = scanner_evidence(strain_dir, bundle_root=bundle_root)
    assert res["registry_version"] == "0.99-test"
    region1 = "NODE_1_length_6000_cov_10.0.region001"
    rows = res["regions"][region1]
    md02 = next(r for r in rows if r["scanner_id"] == "MD02")
    assert md02["gate_complete"] is True
    assert md02["gate_present"] == ["PEP_mutase"]
    assert md02["support_hits"] == ["AMP-binding"]
    # AB06's gate domain never occurs anywhere -> not even listed for this region
    assert not any(r["scanner_id"] == "AB06" for r in rows)


def test_scanner_evidence_never_auto_fires_a_multi_domain_gate_partially(tmp_path):
    """A scanner whose gate needs TWO domains, only one of which is present, must report
    gate_complete=False — the module must never claim a gate fired on partial evidence."""
    from mamey.raw_antismash_triage import scanner_evidence

    strain_dir = _build_strain_dir(tmp_path / "strain")
    bundle_root = _fake_bundle_root(tmp_path, [
        {"id": "AF01", "name": "aminocyclitol", "cls": "saccharide",
         "gate": ["PEP_mutase", "DHQ_synthase"], "support": [],
         "rule": "gate AND >=2 support", "trap": "", "test_status": "PASS"},
    ])
    res = scanner_evidence(strain_dir, bundle_root=bundle_root)
    region1 = "NODE_1_length_6000_cov_10.0.region001"
    rows = res["regions"][region1]
    af01 = next(r for r in rows if r["scanner_id"] == "AF01")
    assert af01["gate_complete"] is False
    assert af01["gate_present"] == ["PEP_mutase"]
    assert af01["gate_missing"] == ["DHQ_synthase"]


def test_scanner_evidence_missing_registry_reports_skipped_not_errored(tmp_path):
    from mamey.raw_antismash_triage import scanner_evidence

    strain_dir = _build_strain_dir(tmp_path / "strain")
    empty_bundle = tmp_path / "no_wheelhouse"
    (empty_bundle / "Wheelhouse" / "scanners").mkdir(parents=True)
    res = scanner_evidence(strain_dir, bundle_root=empty_bundle)
    assert res["registry_version"] is None
    assert res["regions"] == {}
    assert "note" in res


# ---------------------------------------------------------------------------
# rank_priority_regions
# ---------------------------------------------------------------------------

def test_rank_priority_regions_merges_kcb_and_rare_motif_signal_on_same_region():
    from mamey.raw_antismash_triage import rank_priority_regions

    rid = "NODE_1_length_6000_cov_10.0.region001"
    frontpage_hits = [{"region": rid, "compound": "testomycin", "tier": "STRONG",
                       "similarity": 90, "n_genes": 12}]
    rare_ranked = [{"region": f"TEST:{rid}", "product": "NRPS",
                    "rare_motifs": ["PEP_mutase"], "important_motifs": ["PEP_mutase"],
                    "score": 3}]
    scanner_ev = {"regions": {}}
    split_candidates = []

    ranked = rank_priority_regions(frontpage_hits, rare_ranked, scanner_ev, split_candidates)
    assert len(ranked) == 1
    b = ranked[0]
    assert b["region"] == rid
    assert b["kcb"]["tier"] == "STRONG"
    assert b["important_motifs"] == ["PEP_mutase"]
    assert any("KCB STRONG lead" in w for w in b["why"])
    assert any("high-value motif watchlist" in w for w in b["why"])


def test_rank_priority_regions_important_motif_outranks_bare_kcb_strong():
    from mamey.raw_antismash_triage import rank_priority_regions

    r_important = "NODE_A.region001"
    r_kcb_only = "NODE_B.region001"
    frontpage_hits = [
        {"region": r_important, "compound": "x", "tier": "LOW", "similarity": 5, "n_genes": 1},
        {"region": r_kcb_only, "compound": "y", "tier": "STRONG", "similarity": 90, "n_genes": 12},
    ]
    rare_ranked = [{"region": r_important, "product": "p",
                    "rare_motifs": [], "important_motifs": ["ene_KS"], "score": 2}]
    ranked = rank_priority_regions(frontpage_hits, rare_ranked, {"regions": {}}, [])
    assert ranked[0]["region"] == r_important


def test_rank_priority_regions_flags_both_sides_of_a_split_candidate():
    from mamey.raw_antismash_triage import rank_priority_regions

    split_candidates = [{"body": "NODE_A.region001", "fragment": "NODE_B.region001",
                          "confidence": "HIGH", "best_paralog_id": 55.0, "score": 8}]
    ranked = rank_priority_regions([], [], {"regions": {}}, split_candidates)
    regions = {b["region"]: b for b in ranked}
    assert regions["NODE_A.region001"]["split_candidate"] is True
    assert regions["NODE_B.region001"]["split_candidate"] is True


# ---------------------------------------------------------------------------
# explore_strain (integration, no bgc_walk — that needs pyhmmer + a real HMM db)
# ---------------------------------------------------------------------------

def test_explore_strain_end_to_end_on_synthetic_fixture(tmp_path):
    from mamey import raw_antismash_triage as genome_explore

    strain_dir = _build_strain_dir(tmp_path / "strain")
    bundle_root = _fake_bundle_root(tmp_path, [
        {"id": "MD02", "name": "phosphonate", "cls": "misc",
         "gate": ["PEP_mutase"], "support": [], "rule": "PepM present",
         "trap": "", "test_status": "PASS"},
    ])

    report = genome_explore.explore_strain(strain_dir, bundle_root=bundle_root,
                                            top_n=5, run_bgc_walk=False)
    for step in ("kcb_frontpage", "scanner_evidence", "rare_motif", "split_detector"):
        assert report["steps"][step]["status"] == "RAN", report["steps"][step]
    assert report["steps"]["bgc_walk"]["status"] == "SKIPPED"

    region1 = "NODE_1_length_6000_cov_10.0.region001"
    top = report["priority_regions"][0]
    assert top["region"] == region1
    assert top["kcb"]["tier"] == "STRONG"
    assert "PEP_mutase" in top["important_motifs"]
    assert "MD02" in top["scanner_gate_complete"]


def test_explore_strain_isolates_a_single_step_failure(tmp_path, monkeypatch):
    """One module raising must not prevent the other three from running (matches the
    render-all-figures precedent: best-effort, non-blocking per module)."""
    from mamey import raw_antismash_triage as genome_explore

    strain_dir = _build_strain_dir(tmp_path / "strain")

    def _boom(*a, **kw):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(genome_explore._rare_motif, "rare_motif_scan", _boom)
    report = genome_explore.explore_strain(strain_dir, top_n=5, run_bgc_walk=False)
    assert report["steps"]["rare_motif"]["status"] == "ERRORED"
    assert report["steps"]["kcb_frontpage"]["status"] == "RAN"
    assert report["steps"]["split_detector"]["status"] == "RAN"


def test_render_explore_report_md_is_nonempty_and_names_the_strain(tmp_path):
    from mamey import raw_antismash_triage as genome_explore

    strain_dir = _build_strain_dir(tmp_path / "strain")
    report = genome_explore.explore_strain(strain_dir, top_n=5, run_bgc_walk=False)
    md = genome_explore.render_explore_report_md(report, strain_name="TEST-001")
    assert "TEST-001" in md
    assert "Priority regions" in md


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------

def test_explore_subcommand_registered_in_cli():
    import subprocess, sys
    result = subprocess.run([sys.executable, "-m", "mamey", "triage-raw", "--help"],
                             capture_output=True, text=True, timeout=30)
    assert result.returncode == 0
    assert "--strain-dir" in result.stdout
    assert "--input-zip" in result.stdout


def test_explore_command_requires_one_input_source(tmp_path):
    import subprocess, sys
    result = subprocess.run([sys.executable, "-m", "mamey", "triage-raw"],
                             capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "required" in result.stderr.lower() or "one of the arguments" in result.stderr.lower()


def test_explore_command_writes_report_to_out(tmp_path):
    sdir = _build_strain_dir(tmp_path / "strain")
    out_path = tmp_path / "report.md"

    class _Args:
        strain_dir = str(sdir)
        input_zip = None
        strain = "TEST-001"
        top_n = 5
        no_walk = True
        out = str(out_path)
        json = False

    from mamey.raw_antismash_triage import explore_command
    rc = explore_command(_Args())
    assert rc == 0
    assert out_path.exists()
    assert "TEST-001" in out_path.read_text()
