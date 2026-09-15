"""v9.7.430 — `.` and `-` must normalize identically in the admission canonical form.

`tools/phylo_sequence_admission.py::read_fasta` stripped `-` but not `.`, while its own symbol
validator admits both (`[ACGTURYSWKMBDHVN.-]+`) and `tools/_phylo16s.py::screen_query_records`
strips both under the docstring "Lengths exclude gap punctuation". So the two modules disagreed on
what the same FASTA record IS, which surfaced in two places: the `SEQUENCE_LENGTH` window, and
`sequence_sha256` — the per-sequence identity hash.

These tests pin BOTH halves, because fixing only the length check would leave two modules still
hashing the same sequence to two different digests.
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{name}_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _roster_row(tip: str, digest: str) -> dict:
    """A complete admission row. validate() checks ROSTER_COLUMNS before anything else, so a
    partial row fails on the column set and never reaches the length window under test."""
    return {"tip": tip, "role": "reference", "organism": "Example organism",
            "expected_genus": "Example", "accession": "NR_123456.1", "sequence_sha256": digest,
            "type_status": "type", "isolation_source": "soil", "geography": "Europe",
            "sequence_evidence": "type strain 16S", "metadata_evidence": "deposited record",
            "biological_sample_id": "SAMN00000001", "admission": "admitted"}


def _fasta(tmp_path: Path, name: str, sequence: str) -> Path:
    p = tmp_path / "in.fasta"
    p.write_text(f">{name}\n{sequence}\n", encoding="utf-8")
    return p


# ── the canonical form itself ────────────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("ACGT----ACGT", "ACGTACGT"),
    ("ACGT....ACGT", "ACGTACGT"),
    ("ACGT-.-.ACGT", "ACGTACGT"),
    ("acgu....acgu", "ACGTACGT"),
])
def test_both_gap_characters_normalize_to_the_same_sequence(tmp_path, raw, expected):
    admission = _load("phylo_sequence_admission")
    assert admission.read_fasta(_fasta(tmp_path, "tip", raw))["tip"] == expected


def test_dot_gapped_and_dash_gapped_inputs_hash_identically(tmp_path):
    """sequence_sha256 must be an identity of the SEQUENCE, not of the alignment it arrived in."""
    admission = _load("phylo_sequence_admission")
    core = "ACGT" * 250
    dashed = admission.read_fasta(_fasta(tmp_path, "tip", core[:500] + "-" * 40 + core[500:]))["tip"]
    tmp2 = tmp_path / "b"; tmp2.mkdir()
    dotted = admission.read_fasta(_fasta(tmp2, "tip", core[:500] + "." * 40 + core[500:]))["tip"]
    assert dashed == dotted
    assert (hashlib.sha256(dashed.encode("ascii")).hexdigest()
            == hashlib.sha256(dotted.encode("ascii")).hexdigest())


# ── cross-module consistency, the actual defect ──────────────────────────────
@pytest.mark.parametrize("gap", ["-", "."])
def test_admission_and_screen_agree_on_ungapped_length(tmp_path, gap):
    """read_fasta's stored length must equal _phylo16s' ungapped length for BOTH gap characters."""
    admission = _load("phylo_sequence_admission")
    p16 = _load("_phylo16s")
    raw = "A" * 1400 + gap * 100
    stored = admission.read_fasta(_fasta(tmp_path, "tip", raw))["tip"]
    screened = p16.screen_query_records([("tip", raw)])
    assert len(stored) == 1400, f"read_fasta kept {gap!r} padding: stored length {len(stored)}"
    assert screened[0]["length"] == 1400, screened[0]
    assert len(stored) == screened[0]["length"]


# ── the length window, which is what the defect actually broke ───────────────
def test_dot_padded_query_inside_the_window_is_not_rejected_for_its_gaps(tmp_path):
    """A 1990-base query in a 2090-character dot-gapped alignment must pass max_length=2000."""
    admission = _load("phylo_sequence_admission")
    seq = "A" * 1990 + "." * 100
    stored = admission.read_fasta(_fasta(tmp_path, "REF_A", seq))["REF_A"]
    assert len(stored) == 1990
    row = _roster_row("REF_A", hashlib.sha256(stored.encode("ascii")).hexdigest())
    admission.validate([row], {"REF_A": stored})   # must not raise at all


def test_short_sequence_padded_with_dots_is_still_too_short(tmp_path):
    """The converse failure mode: padding must not buy a fragment its way into the window."""
    admission = _load("phylo_sequence_admission")
    seq = "A" * 400 + "." * 800          # 1200 characters, 400 real bases
    stored = admission.read_fasta(_fasta(tmp_path, "REF_A", seq))["REF_A"]
    assert len(stored) == 400
    row = _roster_row("REF_A", hashlib.sha256(stored.encode("ascii")).hexdigest())
    with pytest.raises(ValueError, match="SEQUENCE_LENGTH"):
        admission.validate([row], {"REF_A": stored})


def test_symbol_validator_still_admits_both_gap_characters(tmp_path):
    """Normalizing dots away must not turn a legal dot-gapped FASTA into a FASTA_SYMBOL refusal."""
    admission = _load("phylo_sequence_admission")
    out = admission.read_fasta(_fasta(tmp_path, "tip", "ACGT.-RYSWKMBDHVN"))
    assert out["tip"] == "ACGTRYSWKMBDHVN"
