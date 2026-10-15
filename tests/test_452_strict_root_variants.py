"""Strict root variants use synthetic tips and keep diagnostic acceptance separate."""
import shutil
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytest.importorskip("Bio.Phylo")
from tools import placement_root_variants as variants
from tools import tree_sanity_check as sanity

ROOT = Path(__file__).resolve().parents[1]
OG = "SYN-OUTGROUP"
TREE = f"(((SYN-970:0.05,SYN-971:0.05):0.06,(SYN-972:0.05,SYN-973:0.05):0.06):0.20,{OG}:0.0);"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(tmp_path, text=TREE):
    source = tmp_path / "input.newick"
    source.write_text(text)
    split, receipt, record = variants.prepare(source, tmp_path / "tree", [OG])
    return source, split, receipt, record


def test_original_strict_fail_split_pass_source_immutable_and_distances_preserved(tmp_path):
    from Bio import Phylo
    source, split, receipt, record = prepare(tmp_path)
    assert source.read_text() == TREE
    assert not sanity.check(source, outgroup=[OG])[0]
    assert sanity.check(split, outgroup=[OG])[0]
    assert record["long_root_branch"] is True
    assert record["accepted_variant"] == "display_rooted_split"
    original = receipt.parent / record["variants"]["root_as_built"]["tree"]["path"]
    assert original.read_bytes() == source.read_bytes()
    variants.verify_diagnostic(receipt, sha(receipt), original)
    a, b = Phylo.read(source, "newick"), Phylo.read(split, "newick")
    names = [tip.name for tip in a.get_terminals()]
    assert {t.name for t in b.get_terminals()} == set(names)
    for x in names:
        for y in names:
            assert a.distance(x, y) == pytest.approx(b.distance(x, y), abs=1e-12)
    assert a.total_branch_length() == pytest.approx(b.total_branch_length(), abs=1e-12)


@pytest.mark.parametrize("target", ["source", "split", "receipt"])
def test_diagnostic_refuses_changed_bindings(tmp_path, target):
    source, split, receipt, record = prepare(tmp_path)
    original = receipt.parent / record["variants"]["root_as_built"]["tree"]["path"]
    expected = sha(receipt)
    changed = {"source": source, "split": split, "receipt": receipt}[target]
    changed.write_bytes(changed.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="CHANGED|HASH_MISMATCH"):
        variants.verify_diagnostic(receipt, expected, original)


def test_diagnostic_refuses_rehashed_false_report(tmp_path):
    source, split, receipt, record = prepare(tmp_path)
    original = receipt.parent / record["variants"]["root_as_built"]["tree"]["path"]
    record["variants"]["root_as_built"]["gate_report"] = "PASS"
    receipt.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="VERDICT_MISMATCH"):
        variants.verify_diagnostic(receipt, sha(receipt), original)


def test_split_failure_cannot_authorize_diagnostic(tmp_path):
    source, split, receipt, record = prepare(tmp_path, TREE.replace("SYN-970:0.05", "SYN-970:0.9"))
    assert not sanity.check(split, outgroup=[OG])[0]
    assert record["accepted_variant"] is None
    original = receipt.parent / record["variants"]["root_as_built"]["tree"]["path"]
    with pytest.raises(ValueError, match="NOT_ELIGIBLE"):
        variants.verify_diagnostic(receipt, sha(receipt), original)


def test_root_as_built_cannot_be_rendered_as_accepted_display(tmp_path):
    source, split, receipt, record = prepare(tmp_path)
    from tools import gate_stem_aware as gate
    ok, report = gate.gate(source, outgroup=[OG])
    assert not ok and "DOMINATING_BRANCH" in report
    assert "stem-exemption" not in report


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_rect02_writes_bound_split_and_original_diagnostic_figures(tmp_path):
    """Actual approved renderer; no alternate plotting implementation."""
    source, split, receipt, record = prepare(tmp_path)
    original = receipt.parent / record["variants"]["root_as_built"]["tree"]["path"]
    alignment = tmp_path / "alignment.fasta"
    tips = [f"SYN-{i}" for i in range(970, 974)] + [OG]
    alignment.write_text("".join(f">{tip}\n" + "ACGT" * 150 + "\n" for tip in tips))
    metadata = tmp_path / "metadata.tsv"
    with metadata.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["tip", "label", "role", "taxon", "category", "source"], delimiter="\t")
        writer.writeheader()
        for tip in tips:
            writer.writerow(dict(tip=tip, label=tip, role="outgroup" if tip == OG else "query",
                                 taxon="Synthetic", category="", source=""))
    output_receipts = {}
    for variant, parent in [("split", split), ("root_as_built_GATE_FAIL_diagnostic", original)]:
        prefix = tmp_path / variant
        collapse = subprocess.run([sys.executable, str(ROOT / "tools/collapse_near_identical.py"),
                                   str(alignment), str(parent), str(metadata), "--out-prefix", str(prefix),
                                   "--max-nt", "0", "--min-cols", "600", "--group-label", "representative"],
                                  text=True, capture_output=True)
        assert collapse.returncode == 0, collapse.stdout + collapse.stderr
        display_receipt = Path(str(prefix) + "_display_receipt.json")
        env = dict(os.environ, SAPOTE_PYTHON=sys.executable, GG_PRINT_WIDTH="7.2", GG_STRIPS="0",
                   GG_DISPLAY_RECEIPT=str(display_receipt), GG_DISPLAY_RECEIPT_SHA256=sha(display_receipt),
                   GG_GATE_TREE=str(parent), GG_ROOT_POLICY="display_rooted_split" if variant == "split" else "root_as_built",
                   GG_DIAGNOSTIC_ROOTING_RECEIPT="", GG_DIAGNOSTIC_ROOTING_SHA256="")
        if variant != "split":
            env.update(GG_DIAGNOSTIC_ROOTING_RECEIPT=str(receipt), GG_DIAGNOSTIC_ROOTING_SHA256=sha(receipt))
        render_prefix = str(prefix) + "_rect02"
        command = ["Rscript", str(ROOT / "tools/ggtree_rect_heatmap.R"), str(prefix) + "_display.nwk",
                   str(prefix) + "_display_meta.tsv", render_prefix]
        rendered = subprocess.run(command, env=env, capture_output=True, text=True)
        assert rendered.returncode == 0, rendered.stdout + rendered.stderr
        output_receipts[variant] = json.loads(Path(render_prefix + ".render_receipt.json").read_text())
        from tools.check_figure_provenance import stamp
        for suffix in (".png", ".pdf"):
            assert stamp(Path(render_prefix + suffix))[0] == "PASS"
        if variant != "split":
            # The same failing parent cannot enter the ordinary accepted route.
            env.update(GG_DIAGNOSTIC_ROOTING_RECEIPT="", GG_DIAGNOSTIC_ROOTING_SHA256="")
            command[-1] += "_refused"
            refused = subprocess.run(command, env=env, capture_output=True, text=True)
            assert refused.returncode != 0
            assert not Path(command[-1] + ".pdf").exists()
    assert output_receipts["split"]["gate_pass"] is True
    diagnostic = output_receipts["root_as_built_GATE_FAIL_diagnostic"]
    assert diagnostic["gate_pass"] is False and diagnostic["accepted"] is False
    assert diagnostic["authority"] == "DIAGNOSTIC_ONLY_GATE_FAIL"
