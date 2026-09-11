"""DOMREF-01: the bundled domain functional-context dictionary (mamey/domain_reference.py) +
its per-package emitter (tools/build_domain_reference.py). Hermetic: synthetic package."""
import csv
import os
import pathlib
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from mamey import domain_reference as DR  # noqa: E402
import build_domain_reference as B  # noqa: E402


def test_curated_core_vocabulary():
    # aSDomains that ship with no antiSMASH text must resolve via CURATED
    cat, ctx = DR.categorize("PKS_KS")
    assert cat == "PKS-core" and "Ketosynthase" in ctx
    assert DR.is_curated("PKS_KS")
    assert DR.categorize("PCP")[0] == "carrier"
    assert DR.categorize("Thioesterase")[0] == "release"
    assert DR.categorize("Condensation")[0] == "NRPS-core"


def test_rule_and_fallback_categorization():
    # regex rules (first match wins), description used as context when present
    assert DR.categorize("some_halogenase")[0] == "tailoring-halogenation"
    assert DR.categorize("ABC_tran")[0] == "transport"
    assert DR.categorize("TetR", "TetR family transcriptional regulator")[0] == "regulatory"
    assert DR.categorize("YcaO")[0] == "RiPP-maturation"
    # unknown domain with a description falls through to "other", keeping the desc as context
    cat, ctx = DR.categorize("ZZZ_novel", "mystery protein of unknown function")
    assert cat == "other" and ctx == "mystery protein of unknown function"


def test_biosynthetic_category_set_is_coherent():
    # every biosynthetic category is a real category; transport/regulatory are NOT biosynthetic
    assert DR.BIOSYNTHETIC_CATEGORIES <= set(DR.CAT_ORDER)
    assert "transport" not in DR.BIOSYNTHETIC_CATEGORIES
    assert "regulatory" not in DR.BIOSYNTHETIC_CATEGORIES
    assert "PKS-core" in DR.BIOSYNTHETIC_CATEGORIES


def test_categorize_is_deterministic():
    a = DR.categorize("PKS_AT", "acyltransferase")
    b = DR.categorize("PKS_AT", "acyltransferase")
    assert a == b


def _pkg(root, sid, domain_rows, hmm_rows):
    d = os.path.join(root, sid, "package")
    os.makedirs(d)
    with open(os.path.join(d, f"{sid}_domains.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["bgc_id", "locus_tag", "domain", "pfam_acc"])
        w.writeheader()
        for bid, dom, acc in domain_rows:
            w.writerow({"bgc_id": bid, "locus_tag": "g", "domain": dom, "pfam_acc": acc})
    with open(os.path.join(d, f"{sid}_3_antismash_hmm.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["bgc_id", "domain_name", "accession", "description"])
        w.writeheader()
        for bid, dom, acc, desc in hmm_rows:
            w.writerow({"bgc_id": bid, "domain_name": dom, "accession": acc, "description": desc})
    return d


def test_build_reference_rows_from_package():
    with tempfile.TemporaryDirectory() as root:
        pkg = _pkg(root,
                   "AS-T",
                   [("BGC001", "PKS_KS", "PF00109"), ("BGC001", "ABC_tran", "PF00005"),
                    ("BGC002", "PKS_KS", "PF00109")],
                   [("BGC001", "ketoacyl-synt", "PF00109", "PKS ketosynthase")])
        rows = DR.build_reference_rows(pkg)
        by = {r["domain"]: r for r in rows}
        assert by["PKS_KS"]["category"] == "PKS-core"
        assert by["PKS_KS"]["n_bgcs"] == 2  # in BGC001 + BGC002
        assert by["ABC_tran"]["category"] == "transport"
        # description from the HMM table flows into the aSDomain vocab entry
        assert by["ketoacyl-synt"]["antismash_desc"] == "PKS ketosynthase"


def test_emitter_writes_tsv_and_md():
    with tempfile.TemporaryDirectory() as root:
        pkg = _pkg(root, "AS-T", [("BGC001", "PKS_KS", "PF00109")],
                   [("BGC001", "ketoacyl-synt", "PF00109", "PKS ketosynthase")])
        with tempfile.TemporaryDirectory() as out:
            rc = B.main(["--package", pkg, "--out", out])
            assert rc == 0
            tsv = os.path.join(out, "domain_reference.tsv")
            md = os.path.join(out, "domain_reference.md")
            assert os.path.exists(tsv) and os.path.exists(md)
            rows = list(csv.DictReader(open(tsv), delimiter="\t"))
            assert {"domain", "category", "context", "n_bgcs"} <= set(rows[0].keys())
            # claim-safety: the human-readable doc states function-only, never a product claim
            text = open(md).read().lower()
            assert "never a claim about the product" in text


def test_merge_across_packages_sums_counts():
    with tempfile.TemporaryDirectory() as root:
        p1 = _pkg(root, "AS-1", [("BGC001", "PKS_KS", "PF00109")], [])
        p2 = _pkg(root, "AS-2", [("BGC001", "PKS_KS", "PF00109"), ("BGC002", "PKS_KS", "PF00109")], [])
        rows = B._merge_packages([p1, p2])
        ks = {r["domain"]: r for r in rows}["PKS_KS"]
        assert ks["n_bgcs"] == 3 and ks["n_packages"] == 2
