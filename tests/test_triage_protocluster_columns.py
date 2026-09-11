"""Triage-board protocluster columns (v9.7.350 / BLIZZARD_BLUE_03).

The engine resolves the region-merge structure at parse time (`parsers.py`: protocluster_breakdown,
count_single_cand_clusters, count_hybrid_cand_clusters) but v9.7.349 wrote NONE of it to a package
except one derived string, `Composite_region`, gated on `single_protocluster_count >= 3`.

Measured on the 47 sealed mamey_packages packages: 36 of 2,045 rows (1.76%) carried a value, and the
smallest was "3x single" — exactly what the >=3 gate predicts. So a TWO-protocluster merge wrote a
blank cell, indistinguishable from a clean single-protocluster region. **Blank was overloaded**: it
meant both "not composite" and "composite with exactly 2".

This card adds three unconditional columns so a consumer can tell those apart without re-parsing the
region GBK:

  Protocluster_count         - the TRUE antiSMASH `protocluster` feature count (models.py:150)
  Single_protocluster_count  - cand_clusters with /kind="single"
  Chemical_hybrid            - antiSMASH called the protoclusters FUSED (do NOT de-inflate these)

Claim safety: all three are structural CAPACITY descriptors — how many protoclusters antiSMASH
resolved and whether it called them fused. Never a product, activity, or novelty claim. No scoring,
tier, gate, or triage-order change; `Composite_region` semantics are untouched.

Standalone: python3 tests/test_triage_protocluster_columns.py
"""
from __future__ import annotations
import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.models import BGCRecord
from mamey.parsers import (
    count_hybrid_cand_clusters,
    count_single_cand_clusters,
    protocluster_breakdown,
)

CLI = Path(__file__).resolve().parent.parent / "mamey" / "cli.py"
NEW = ("Protocluster_count", "Single_protocluster_count", "Chemical_hybrid")


class _F:
    """Minimal stand-in for a Biopython SeqFeature (same shape the sibling tests use)."""

    def __init__(self, ftype, kind=None, product=None, start=0, end=0):
        self.type = ftype
        self.qualifiers = {}
        if kind is not None:
            self.qualifiers["kind"] = [kind]
        if product is not None:
            self.qualifiers["product"] = [product]
        self.location = type("L", (), {"start": start, "end": end})()


def _triage_headers() -> list[str]:
    src = CLI.read_text(encoding="utf-8")
    m = re.search(r"triage_headers\s*=\s*(\[.*?\n    \])", src, re.DOTALL)
    assert m, "could not locate the triage_headers list in cli.py"
    # strip comment lines so ast.literal_eval sees only the string literals
    body = "\n".join(ln for ln in m.group(1).splitlines() if not ln.strip().startswith("#"))
    return ast.literal_eval(body)


# ── 1. the columns exist, in the right place ──────────────────────────────────

def test_new_columns_present():
    h = _triage_headers()
    for col in NEW:
        assert col in h, f"triage board must carry {col!r}"


def test_new_columns_sit_next_to_composite_region():
    h = _triage_headers()
    i = h.index("Composite_region")
    assert h[i + 1:i + 4] == list(NEW), (
        "the structural counts belong immediately after Composite_region, which they disambiguate; "
        f"found {h[i + 1:i + 4]}"
    )


def test_composite_region_column_is_retained():
    """Backwards compatibility: this card ADDS, it does not rename or drop."""
    assert "Composite_region" in _triage_headers()


# ── 2. the real failure mode: header/row width drift ──────────────────────────

def _triage_row_cells() -> list:
    """The element list of the `w.writerow([...])` that writes a triage row.

    Parsed with `ast`, not by hand: comment prose in this row contains commas (both mine and the
    pre-existing `# v9.7.129, patched after ...`), and a character-level splitter counts those as
    cell boundaries. The AST has no comments, so it cannot be fooled that way.
    """
    tree = ast.parse(CLI.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "writerow" and len(n.args) == 1]
    # anchor on `w.writerow(triage_headers)`; the triage row is the next writerow after it.
    header_line = next((c.lineno for c in calls
                        if isinstance(c.args[0], ast.Name) and c.args[0].id == "triage_headers"), None)
    assert header_line is not None, "could not locate w.writerow(triage_headers) in cli.py"
    rows = sorted((c for c in calls
                   if isinstance(c.args[0], ast.List) and c.lineno > header_line),
                  key=lambda c: c.lineno)
    assert rows, "no writerow([...]) follows w.writerow(triage_headers)"
    return rows[0].args[0].elts


def test_header_count_matches_written_row_width():
    """A header added without a matching cell (or vice versa) silently shifts every later column,
    so every downstream reader misattributes values with no error anywhere."""
    headers = _triage_headers()
    cells = _triage_row_cells()
    assert len(cells) == len(headers), (
        f"triage board width drift: {len(headers)} headers vs {len(cells)} row cells"
    )


def test_width_guard_actually_detects_drift():
    """Mutation check: the guard above is only worth having if an added header fails it."""
    headers = _triage_headers() + ["Bogus_Column"]
    assert len(headers) != len(_triage_row_cells())


# ── 3. the blind spot this card closes ────────────────────────────────────────

def test_two_protocluster_merge_is_no_longer_invisible():
    """The case Composite_region cannot represent: exactly 2 protoclusters.

    `composite_region` is `single_cc >= 3`, so a 2-way merge left the cell blank — the same value a
    clean 1-protocluster region writes. Protocluster_count separates them.
    """
    feats = [
        _F("region"),
        _F("protocluster", product="NRPS", start=0, end=20_000),
        _F("protocluster", product="lanthipeptide", start=20_000, end=32_000),
        _F("cand_cluster", "single"),
        _F("cand_cluster", "single"),
    ]
    single_cc = count_single_cand_clusters(feats)
    pcb = protocluster_breakdown(feats)

    assert single_cc == 2
    assert (single_cc >= 3) is False, "composite_region stays False — that is the pre-existing behaviour"
    assert len(pcb) == 2, "but Protocluster_count reports 2, so the merge is visible"


def test_single_protocluster_region_is_distinguishable_from_a_two_way_merge():
    """Both wrote a blank Composite_region before this card; they must not read alike now."""
    clean = [_F("region"), _F("protocluster", product="terpene", start=0, end=9_000),
             _F("cand_cluster", "single")]
    merged = [_F("region"), _F("protocluster", product="NRPS", start=0, end=20_000),
              _F("protocluster", product="terpene", start=20_000, end=29_000),
              _F("cand_cluster", "single"), _F("cand_cluster", "single")]
    assert len(protocluster_breakdown(clean)) == 1
    assert len(protocluster_breakdown(merged)) == 2
    # ...while the legacy column is blank for BOTH:
    assert (count_single_cand_clusters(clean) >= 3) is False
    assert (count_single_cand_clusters(merged) >= 3) is False


def test_protocluster_count_is_not_single_protocluster_count():
    """models.py:150 warns these are NOT interchangeable — a chemical_hybrid region can carry
    several protoclusters but exactly one /kind="single" cand_cluster (AS-421 BGC041: 3 vs 1)."""
    feats = [
        _F("protocluster", product="T1PKS", start=0, end=10_000),
        _F("protocluster", product="NRPS", start=5_000, end=18_000),
        _F("protocluster", product="terpene", start=18_000, end=24_000),
        _F("cand_cluster", "chemical_hybrid"),
        _F("cand_cluster", "single"),
    ]
    assert len(protocluster_breakdown(feats)) == 3
    assert count_single_cand_clusters(feats) == 1


# ── 4. the RFC's own safety guard has to be readable from the package ─────────

def test_chemical_hybrid_is_surfaced():
    """The over-merge RFC forbids de-inflating a `chemical_hybrid` region — a genuinely fused
    cross-class pathway whose union product string is CORRECT. A consumer cannot apply that guard
    unless the package carries the flag."""
    fused = [_F("cand_cluster", "chemical_hybrid"), _F("cand_cluster", "single")]
    adjacent = [_F("cand_cluster", "single"), _F("cand_cluster", "single"),
                _F("cand_cluster", "neighbouring")]
    assert count_hybrid_cand_clusters(fused) == 1
    assert count_hybrid_cand_clusters(adjacent) == 0
    assert "Chemical_hybrid" in _triage_headers()


def test_hybrid_column_is_written_from_has_chemical_hybrid_not_from_composite():
    src = CLI.read_text(encoding="utf-8")
    assert 'getattr(bgc, "has_chemical_hybrid", False)' in src, (
        "Chemical_hybrid must read the parser's fused-pathway flag, not be derived from "
        "composite_region — they are opposite signals"
    )


# ── 5. unconditional: no gate, no blank-when-zero ─────────────────────────────

def test_counts_are_written_unconditionally():
    """The whole defect was a conditional write. A `0` must be recorded as 0, never as blank —
    observed-zero and not-measured are different statements."""
    src = CLI.read_text(encoding="utf-8")
    assert 'getattr(bgc, "protocluster_count", 0),' in src
    assert 'getattr(bgc, "single_protocluster_count", 0),' in src
    for guard in ('if getattr(bgc, "composite_region", False) else "",\n                getattr(bgc, "protocluster_count"',):
        assert guard not in src.replace("\r", ""), "counts must not inherit the composite_region gate"


def test_model_defaults_unchanged():
    b = BGCRecord(bgc_id="BGC1", contig="c", region_number=1, start=1, end=9, contig_length=99)
    assert b.protocluster_count == 0
    assert b.single_protocluster_count == 0
    assert b.has_chemical_hybrid is False
    assert b.composite_region is False


if __name__ == "__main__":
    import traceback
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                fails += 1
                print(f"FAIL {name}")
                traceback.print_exc()
    sys.exit(1 if fails else 0)
