"""
H4: nucleoside->antifungal axis gate activated by CGAD chitin context.
build_lead_tiers.axis() must:
  - return 'antifungal (Candida)' when chitin_context=True AND product/trigger is nucleoside
  - return 'nucleoside-antibiotic candidate (axis uncertain)' when chitin_context=False
  - (AF scoring bonus in scoring.py fires regardless — RANKING only, not axis labeling)
_emit_bgc_bank must write cgad_active=True when source_scans.chitinase has counts.
"""
import json
import sys
import types
from pathlib import Path

# --- test the axis() function ---
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.build_lead_tiers import axis

def test_nucleoside_with_chitin_context_is_antifungal():
    result = axis('nucleoside', '', '', chitin_context=True)
    assert result == 'antifungal (Candida)', f"Expected antifungal (Candida), got: {result}"

def test_nucleoside_without_chitin_context_is_uncertain():
    result = axis('nucleoside', '', '', chitin_context=False)
    assert 'uncertain' in result.lower(), f"Expected uncertain axis, got: {result}"

def test_t43nuc_trigger_with_chitin_context_is_antifungal():
    result = axis('', 'T43-NUC_nucleoside fired', '', chitin_context=True)
    assert result == 'antifungal (Candida)', f"Expected antifungal (Candida), got: {result}"

def test_t43nuc_trigger_without_chitin_context_is_uncertain():
    result = axis('', 'T43-NUC_nucleoside fired', '', chitin_context=False)
    assert 'uncertain' in result.lower(), f"Expected uncertain axis, got: {result}"

def test_non_nucleoside_unaffected_by_chitin_context():
    # A glycopeptide BGC should still return anti-MRSA regardless of chitin context
    result_with = axis('glycopeptide', 'vancomycin', '', chitin_context=True)
    result_without = axis('glycopeptide', 'vancomycin', '', chitin_context=False)
    assert result_with == result_without, "Chitin context should not affect non-nucleoside axis"
    assert 'mrsa' in result_with.lower() or 'gram' in result_with.lower()

# --- test that _emit_bgc_bank writes cgad_active ---
def test_emit_bgc_bank_writes_cgad_active_true(tmp_path):
    from mamey.cli import _emit_bgc_bank
    manifest = {
        "strain_id": "SID-TEST",
        "taxonomy": "Streptomyces test",
        "assembly": {"contigs": 10, "n50": 50000, "genome_bp": 8000000, "gc_pct": 72.0, "largest_contig": 200000},
        "bgc_counts": {"raw": 3, "interior": 2, "edge": 1, "full_contig": 0, "corrected": 2.5},
        "source_scans": {
            "chitinase": {"counts": {"gh18": 2, "cbm_chitin": 1}},
        },
        "bgcs": [],
    }
    _emit_bgc_bank(tmp_path, manifest)
    data = json.loads((tmp_path / "bgc_data.json").read_text())
    assert data["strains"]["SID-TEST"]["cgad_active"] is True

def test_emit_bgc_bank_writes_cgad_active_false_when_no_chitin(tmp_path):
    from mamey.cli import _emit_bgc_bank
    manifest = {
        "strain_id": "SID-TEST2",
        "taxonomy": "Streptomyces test",
        "assembly": {}, "bgc_counts": {},
        "source_scans": {"chitinase": {"counts": {"gh18": 0}}},
        "bgcs": [],
    }
    _emit_bgc_bank(tmp_path, manifest)
    data = json.loads((tmp_path / "bgc_data.json").read_text())
    assert data["strains"]["SID-TEST2"]["cgad_active"] is False

def test_emit_bgc_bank_writes_cgad_active_false_when_no_source_scans(tmp_path):
    from mamey.cli import _emit_bgc_bank
    manifest = {
        "strain_id": "SID-TEST3",
        "taxonomy": "Streptomyces test",
        "assembly": {}, "bgc_counts": {},
        "source_scans": None,
        "bgcs": [],
    }
    _emit_bgc_bank(tmp_path, manifest)
    data = json.loads((tmp_path / "bgc_data.json").read_text())
    assert data["strains"]["SID-TEST3"]["cgad_active"] is False
