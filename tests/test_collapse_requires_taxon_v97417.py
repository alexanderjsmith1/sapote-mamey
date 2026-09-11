"""v9.7.417 — a display collapse with no `taxon` column must REFUSE, not quietly do nothing.

`tools/collapse_near_identical.py` states its own contract in its docstring: "Only explicitly
designated reference clades with a shared recorded taxon can collapse." The eligibility test reads
`metadata[n].get("taxon", "")` and skips any clade whose taxa set contains "". With the column
absent that is every clade — so the run finishes with **exit 0, a signed receipt, and a ledger of
nothing but RETAINED**, indistinguishable from a run where the sequences were genuinely too
divergent to group.

Measured on the v9.7.416 UNSEALED_01 candidate with ONE alignment, ONE tree and ONE set of
parameters, changing only the metadata:

    with a taxon column     -> REF_A/REF_B/REF_C collapse to one representative
    without a taxon column  -> 0 collapsed, exit 0, no warning anywhere

`--max-nt` is a required CLI argument, so every invocation is asking for collapsing; there is no
call that legitimately omits the column. The failure mode is the one this project has already been
bitten by once — the one-per-species dedup that silently no-op'd on an accession key (AMBER_396) —
and it is worse here because the output is a *published display tree*: a panel that should have
shown one representative per near-identical clade instead shows every isolate, and nothing in the
receipt says why.

Claim safety: this is a display-derivative contract test. It makes no claim about whether any two
sequences are the same organism, and collapsing remains a display grouping, not evidence of species
or ecological identity.
"""
from __future__ import annotations

import csv
import importlib.util
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "collapse_near_identical.py")

_BASE = "ACGTACGTAC" * 10
_HEAD = ("tip", "label", "role")
_ROWS = (("REF_A", "Alpha one", "reference"), ("REF_B", "Alpha two", "reference"),
         ("REF_C", "Alpha three", "reference"), ("OG_1", "Outlier", "outgroup"))
_TAXA = {"REF_A": "Example alpha", "REF_B": "Example alpha",
         "REF_C": "Example alpha", "OG_1": "Example other"}


def _load():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    spec = importlib.util.spec_from_file_location("collapse_near_identical_under_test", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _panel(tmp_path, with_taxon):
    aln = tmp_path / "aln.fasta"
    seqs = {"REF_A": _BASE, "REF_B": _BASE, "REF_C": _BASE[:-1] + "A", "OG_1": "T" * len(_BASE)}
    aln.write_text("".join(f">{k}\n{v}\n" for k, v in seqs.items()), encoding="utf-8")
    nwk = tmp_path / "tree.nwk"
    nwk.write_text("(((REF_A:0.001,REF_B:0.001):0.001,REF_C:0.001):0.05,OG_1:0.2);\n", encoding="utf-8")
    meta = tmp_path / "meta.tsv"
    header = list(_HEAD) + (["taxon"] if with_taxon else [])
    lines = ["\t".join(header)]
    for tip, label, role in _ROWS:
        cells = [tip, label, role] + ([_TAXA[tip]] if with_taxon else [])
        lines.append("\t".join(cells))
    meta.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return aln, nwk, meta


def _run(tmp_path, with_taxon, prefix):
    aln, nwk, meta = _panel(tmp_path, with_taxon)
    return subprocess.run(
        [sys.executable, TOOL, str(aln), str(nwk), str(meta),
         "--max-nt", "5", "--min-cols", "50", "--out-prefix", str(tmp_path / prefix)],
        capture_output=True, text=True, cwd=str(tmp_path))


def _actions(tmp_path, prefix):
    path = tmp_path / f"{prefix}_collapse_ledger.tsv"
    with path.open(newline="", encoding="utf-8") as fh:
        return {r["tip"]: r["action"] for r in csv.DictReader(fh, delimiter="\t")}


def test_missing_taxon_column_is_refused(tmp_path):
    """The whole finding: no taxon column must be an error, never a silent zero-collapse run."""
    out = _run(tmp_path, with_taxon=False, prefix="noTax")
    assert out.returncode != 0, (
        "a metadata file with no `taxon` column produced a successful display derivative; "
        "every clade was silently ineligible and the receipt does not say so:\n" + out.stdout)
    assert "METADATA_REQUIRES_taxon" in (out.stdout + out.stderr)
    assert not (tmp_path / "noTax_display_receipt.json").exists(), (
        "a receipt was written for a refused run")


def test_same_panel_with_taxon_still_collapses(tmp_path):
    """Control: the refusal above must be about the column, not about this fixture being un-collapsible."""
    out = _run(tmp_path, with_taxon=True, prefix="withTax")
    assert out.returncode == 0, out.stdout + out.stderr
    actions = _actions(tmp_path, "withTax")
    assert actions["REF_A"] == "COLLAPSED_REPRESENTATIVE"
    assert actions["REF_B"] == "COLLAPSED_MEMBER" and actions["REF_C"] == "COLLAPSED_MEMBER"
    assert actions["OG_1"] == "RETAINED", "an outgroup must never be collapsed into a reference clade"


def test_read_meta_names_the_missing_column(tmp_path):
    """The error has to name `taxon`; a generic METADATA error would not tell an operator what to add."""
    collapse = _load()
    _, _, meta = _panel(tmp_path, with_taxon=False)
    with pytest.raises(ValueError) as excinfo:
        collapse.read_meta(meta)
    assert "taxon" in str(excinfo.value)


def test_taxon_column_present_but_blank_still_refuses_that_clade(tmp_path):
    """A blank taxon is missing data, not a shared taxon — the pre-existing guard must survive.

    This is the half that was already right, kept as a regression anchor: requiring the column must
    not be mistaken for accepting an empty value in it.
    """
    collapse = _load()
    aln, nwk, meta = _panel(tmp_path, with_taxon=True)
    text = meta.read_text(encoding="utf-8").replace("Example alpha", "", 1)
    meta.write_text(text, encoding="utf-8")
    result = collapse.build_display(aln, nwk, meta,
                                     dict(max_nt=5, min_cols=50, protect=[], prune_outgroup=False))
    ledger = result["ledger"].decode("utf-8")
    assert "COLLAPSED_MEMBER" not in ledger, (
        "a clade with a blank taxon was collapsed; blank is missing data, not agreement")
