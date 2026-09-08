"""Genome exploration mode — the correctness property that matters: divergence is only
trustworthy from nr. ClusterBlast LOW identity must be UNCONFIRMED_CHECK_NR, not DIVERGENT
(the BGC043 trap: 62% ClusterBlast vs 100% nr). ClusterBlast HIGH identity is trustworthy."""
import json, pathlib, tempfile, sys
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.genome_explore import scan_divergence, scan_co_capture


def _pkg(tmp, bgcs, nr=None):
    p = pathlib.Path(tmp)
    (p / "manifest.json").write_text(json.dumps({
        "strain_id": "SYNTHETIC-001",
        "bgcs": [{"bgc_id": b, "contig": f"NODE_{i}_length_1000_cov_1",
                  "node_id": f"NODE_{i}_length_1000_cov_1", "region_number": i,
                  "antismash_region": f"region{i:03d}", "products": ["x"],
                  "ab_score": 40, "af_score": 30} for i, b in enumerate(bgcs, 1)],
        "source_scans": {"clusterblast_genes": {"per_gene_best_hit": {
            b: [{"query_gene": f"g{k}", "pct_identity": v} for k, v in enumerate(vals)]
            for b, vals in (nr or {}).get("cb", {}).items()}}},
        "resistance_gene_summary": {"bgc_coupling": {}},
    }))
    (p / "blastp_online").mkdir(exist_ok=True)
    for b, rows in (nr or {}).get("nr", {}).items():
        with (p / "blastp_online" / f"{b}_online_blastp.csv").open("w") as f:
            f.write("locus_tag,pct_identity,blastp_organism,channel,source_channel\n")
            for k, (pid, org) in enumerate(rows):
                f.write(f"g{k},{pid},{org},nr,nr\n")
    return str(p)


def test_clusterblast_low_identity_is_unconfirmed_not_divergent():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, ["BGC043"], nr={"cb": {"BGC043": [55, 62, 70, 60]}})  # ClusterBlast only, low
        d = {r["bgc_id"]: r for r in scan_divergence(pkg)}["BGC043"]
        assert d["source"] == "clusterblast"
        assert d["divergence_tier"] == "UNCONFIRMED_CHECK_NR"   # NOT "DIVERGENT" (the BGC043 trap)


def test_nr_low_identity_is_confirmed_divergent():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, ["BGC014"], nr={"nr": {"BGC014": [(57, "Micromonospora sp."), (67, "Micromonospora sp.")]}})
        d = {r["bgc_id"]: r for r in scan_divergence(pkg)}["BGC014"]
        assert d["source"] == "nr"
        assert d["divergence_tier"] == "DIVERGENT"              # nr-backed divergence is trustworthy


def test_high_identity_is_genus_conserved_either_source():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, ["BGC020"], nr={"cb": {"BGC020": [100, 98, 95]}})
        d = {r["bgc_id"]: r for r in scan_divergence(pkg)}["BGC020"]
        assert d["divergence_tier"] == "GENUS_CONSERVED"        # ClusterBlast HIGH id is trustworthy


def test_explore_command_json_respects_top(capsys):
    """explore_command's --json path must cap exploration_board at --top, same as the text
    renderer does (confirmed bug, 2026-07-08: --json previously always dumped the full board
    regardless of --top). divergence/co_capture stay uncapped in both modes -- only the ranked
    board is subject to --top, matching render_explore's own behavior."""
    import argparse
    from mamey.genome_explore import explore_command
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [f"BGC{i:03d}" for i in range(5)])
        args = argparse.Namespace(package=pkg, top=2, json=True)
        rc = explore_command(args)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert len(out["exploration_board"]) == 2


_STRAIN = "SYNTHETIC-001"
_NODE = "NODE_1_length_1000_cov_1"
_REGION = "region001"
_LOCUS_KEY = "opaque_locus_key"


def _admission_package(tmp_path, *, nr_rows=None, clusterblast_rows=None):
    package = tmp_path / "package"
    package.mkdir()
    manifest = {
        "strain_id": _STRAIN,
        "bgcs": [{
            "bgc_id": _LOCUS_KEY,
            "contig": _NODE,
            "node_id": _NODE,
            "region_number": 1,
            "antismash_region": _REGION,
        }],
        "source_scans": {"clusterblast_genes": {"per_gene_best_hit": {
            _LOCUS_KEY: [{"pct_identity": value} for value in (clusterblast_rows or [])]
        }}},
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if nr_rows is not None:
        overlay = package / "blastp_online"
        overlay.mkdir()
        rows = ["locus_tag,pct_identity,blastp_organism,channel,source_channel"]
        rows.extend(f"gene_{i},{value},Synthetic organism,nr,nr" for i, value in enumerate(nr_rows))
        (overlay / f"{_LOCUS_KEY}_online_blastp.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return package, manifest


@pytest.mark.parametrize("bad", ["NaN", "inf", "-inf", "-1", "101", "not-a-number"])
def test_invalid_nr_percentage_cannot_derive_a_tier_or_fallback(tmp_path, bad):
    package, _ = _admission_package(tmp_path, nr_rows=[bad], clusterblast_rows=[65])
    row = scan_divergence(package)[0]
    assert row["median_id"] is None
    assert row["n_genes"] == 0
    assert row["divergence_tier"] == "NO_EVIDENCE"
    assert row["source"] == "none"
    assert row["source_status"] == "INVALID"


def test_mixed_valid_and_invalid_nr_rows_invalidate_the_whole_observation(tmp_path):
    package, _ = _admission_package(tmp_path, nr_rows=[75, "NaN"], clusterblast_rows=[65])
    row = scan_divergence(package)[0]
    assert (row["median_id"], row["n_genes"], row["source"], row["source_status"]) == (
        None, 0, "none", "INVALID")


@pytest.mark.parametrize("nr_rows", [[], ["NO_HIT"]])
def test_unavailable_nr_uses_clusterblast_and_reports_actual_source(tmp_path, nr_rows):
    package, _ = _admission_package(tmp_path, nr_rows=nr_rows, clusterblast_rows=[65])
    row = scan_divergence(package)[0]
    assert row["median_id"] == 65.0
    assert row["divergence_tier"] == "UNCONFIRMED_CHECK_NR"
    assert row["source"] == "clusterblast"
    assert row["source_status"] == "ADMITTED"


@pytest.mark.parametrize("value,tier", [(0, "DIVERGENT"), (75, "VARIABLE"), (100, "GENUS_CONSERVED")])
def test_valid_nr_boundary_and_control_percentages_are_admitted(tmp_path, value, tier):
    package, _ = _admission_package(tmp_path, nr_rows=[value], clusterblast_rows=[65])
    row = scan_divergence(package)[0]
    assert row["median_id"] == float(value)
    assert row["n_genes"] == 1
    assert row["divergence_tier"] == tier
    assert row["source"] == "nr"
    assert row["source_status"] == "ADMITTED"


def test_invalid_clusterblast_percentage_cannot_derive_a_tier(tmp_path):
    package, _ = _admission_package(tmp_path, clusterblast_rows=["NaN"])
    row = scan_divergence(package)[0]
    assert (row["median_id"], row["source"], row["source_status"]) == (None, "none", "INVALID")


def test_conservation_background_uses_same_numeric_admission(tmp_path):
    from mamey.genome_explore import conservation_background

    package, _ = _admission_package(tmp_path, nr_rows=[0, "NO_HIT", 100])
    assert conservation_background(package) == (50.0, 2)
    (package / "blastp_online" / f"{_LOCUS_KEY}_online_blastp.csv").write_text(
        "locus_tag,pct_identity,blastp_organism\ngene_0,75,Synthetic organism\ngene_1,NaN,Synthetic organism\n",
        encoding="utf-8",
    )
    assert conservation_background(package) == (None, 0)


def test_authored_verifier_uses_shared_invalid_observation_without_fallback(tmp_path):
    from mamey.authored_verify import _bgc_context_from_package

    package, _ = _admission_package(tmp_path, nr_rows=["NaN"], clusterblast_rows=[65])
    context = _bgc_context_from_package(str(package), _LOCUS_KEY) or {}
    assert "conservation_median_id" not in context
    assert context["conservation_source"] == "none"
    assert context["conservation_source_status"] == "INVALID"


def test_authored_verifier_reports_clusterblast_after_unavailable_nr(tmp_path):
    from mamey.authored_verify import _bgc_context_from_package

    package, _ = _admission_package(tmp_path, nr_rows=["NO_HIT"], clusterblast_rows=[65])
    context = _bgc_context_from_package(str(package), _LOCUS_KEY) or {}
    assert context["conservation_median_id"] == 65.0
    assert context["conservation_source"] == "clusterblast"
    assert context["conservation_source_status"] == "ADMITTED"


@pytest.mark.parametrize("channel", ["clustered_nr", "swissprot", "ebi"])
def test_explicit_non_nr_channel_cannot_be_admitted_as_full_nr(tmp_path, channel):
    package, _ = _admission_package(tmp_path, nr_rows=[65], clusterblast_rows=[99])
    overlay = package / "blastp_online" / f"{_LOCUS_KEY}_online_blastp.csv"
    overlay.write_text(f"pct_identity,channel,source_channel\n65,{channel},{channel}\n", encoding="utf-8")
    row = scan_divergence(package)[0]
    assert (row["median_id"], row["source"], row["source_status"]) == (None, "none", "INVALID")


def test_mixed_or_conflicting_or_legacy_channels_are_invalid(tmp_path):
    package, _ = _admission_package(tmp_path, nr_rows=[65], clusterblast_rows=[99])
    overlay = package / "blastp_online" / f"{_LOCUS_KEY}_online_blastp.csv"
    for payload in (
        "pct_identity,channel,source_channel\n97,nr,nr\n20,swissprot,swissprot\n",
        "pct_identity,channel,source_channel\n65,nr,swissprot\n",
        "pct_identity\n65\n",
    ):
        overlay.write_text(payload, encoding="utf-8")
        row = scan_divergence(package)[0]
        assert (row["median_id"], row["source"], row["source_status"]) == (None, "none", "INVALID")
