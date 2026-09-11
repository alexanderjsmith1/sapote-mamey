"""Tests for scope_cluster — synthetic over-merged region, no network.

Builds a region GBK with two merged protoclusters (nucleoside + saccharide) and checks that
scoping to 'nucleoside' keeps the nucleoside genes and excludes the saccharide ones — the exact
over-merge failure this tool prevents.
"""
import importlib.util
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "scope_cluster.py"


def _load():
    pytest.importorskip("Bio")
    spec = importlib.util.spec_from_file_location("sc", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _merged_region():
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    rec = SeqRecord(Seq("N" * 40000), id="reg", name="reg", description="")
    rec.annotations["molecule_type"] = "DNA"
    # cand_cluster nucleoside [0:20000]; cand_cluster saccharide [20000:40000]
    for kind, cat, s, e, cs, ce in [
        ("cand_cluster", "nucleoside", 0, 20000, None, None),
        ("protocluster", "nucleoside", 0, 20000, 8000, 12000),
        ("cand_cluster", "saccharide", 20000, 40000, None, None),
        ("protocluster", "saccharide", 20000, 40000, 28000, 32000),
    ]:
        f = SeqFeature(FeatureLocation(s, e, strand=1), type=kind)
        f.qualifiers["category"] = [cat]
        if cs is not None:
            f.qualifiers["core_location"] = [f"[{cs}:{ce}]"]
        rec.features.append(f)
    # nucleoside genes at 9000, 11000; saccharide genes at 29000, 31000
    for lt, pos, dom in [("nuc_A", 9000, "nikJ"), ("nuc_B", 11000, "truD"),
                          ("sac_A", 29000, "Glycos_transf_2"), ("sac_B", 31000, "Epimerase_2")]:
        f = SeqFeature(FeatureLocation(pos, pos + 800, strand=1), type="CDS")
        f.qualifiers["locus_tag"] = [lt]; f.qualifiers["sec_met_domain"] = [dom]
        f.qualifiers["translation"] = ["M" + "A" * 100]
        rec.features.append(f)
    return rec


def test_scope_keeps_target_excludes_neighbour():
    m = _load()
    rec = _merged_region()
    report, kept, span = m.scope(rec, "nucleoside")
    assert report["boundary"] == [0, 20000]
    kept_tags = [f.qualifiers["locus_tag"][0] for f in kept]
    assert "nuc_A" in kept_tags and "nuc_B" in kept_tags
    assert "sac_A" not in kept_tags and "sac_B" not in kept_tags   # saccharide excluded
    assert report["n_excluded"] == 2


def test_reports_merged_protoclusters():
    m = _load()
    rec = _merged_region()
    report, kept, span = m.scope(rec, "nucleoside")
    cats = {p["category"] for p in report["all_protoclusters"] if p["kind"] == "protocluster"}
    assert cats == {"nucleoside", "saccharide"}


def test_missing_category_raises():
    m = _load()
    rec = _merged_region()
    with pytest.raises(KeyError):
        m.scope(rec, "terpene")
