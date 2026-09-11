"""v9.7.223 SCORING: KCB ceiling coverage-gate + class-mismatch (CUT A) and edge-downgrade
assembly-awareness (CUT B). Batteries pinned as regression fixtures. BGC065 is the shared fixture."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.antismash_evidence import kcb_class_mismatch, kcb_coverage_substantial
from mamey.chatgpt_commands import _claim_ceiling
from mamey import architecture_first as A

# ---- CUT A ----
def test_bgc065_shell_capped_to_source_derived():
    # lankacidin NRPS/PKS anchor over a RiPP+cofactor core, 3-gene shell
    assert kcb_class_mismatch("NRPS:Type I+PKS", "RiPP; lanthipeptide-class-iii; redox-cofactor") is True
    assert kcb_coverage_substantial(3) is False
    row = {"KCB_score": 60000, "Products": "RiPP; lanthipeptide-class-iii; redox-cofactor"}
    bgc = {"kcb_cumulative": 60000, "kcb_protein_hits": 3,
           "clusterblast_top": "lankacidin C NRPS:Type I+PKS",
           "products": ["RiPP", "lanthipeptide-class-iii", "redox-cofactor"], "architecture_confidence": "A"}
    assert _claim_ceiling(row, bgc, n_genes=20) == "source-derived similarity"

def test_genuine_concordant_pks_not_oversuppressed():
    assert kcb_class_mismatch("T1PKS", "T1PKS") is False
    assert kcb_coverage_substantial(12) is True
    row = {"KCB_score": 60000, "Products": "T1PKS"}
    bgc = {"kcb_cumulative": 60000, "kcb_protein_hits": 12, "clusterblast_top": "polyketide T1PKS",
           "products": ["T1PKS"], "architecture_confidence": "A"}
    assert _claim_ceiling(row, bgc, n_genes=15) == "candidate product-level similarity"

# ---- CUT B ----
def _rep(conf, boundary, tier):
    r = A.ArchitectureReport.__new__(A.ArchitectureReport)
    r.confidence = conf; r.confidence_raw = conf; r.boundary_status = boundary
    r.assembly_tier = tier; r.finishing_candidate = False
    r.notes = []
    return r

def test_edge_penalty_skipped_on_poor_flagged_finishing():
    A.set_run_assembly_tier("UNKNOWN")
    out = A._apply_boundary_adjustment(_rep("HIGH", "Edge", "POOR"))
    assert out.confidence == "HIGH" and out.finishing_candidate is True

def test_edge_penalty_kept_on_good():
    out = A._apply_boundary_adjustment(_rep("HIGH", "Edge", "GOOD"))
    assert out.confidence == "MEDIUM" and out.finishing_candidate is False

def test_full_contig_penalty_kept_on_very_poor():
    out = A._apply_boundary_adjustment(_rep("HIGH", "Full-contig", "VERY_POOR"))
    assert out.confidence == "MEDIUM"

def test_unknown_tier_preserves_precut_default():
    A.set_run_assembly_tier("UNKNOWN")
    out = A._apply_boundary_adjustment(_rep("HIGH", "Edge", "UNKNOWN"))
    assert out.confidence == "MEDIUM"
