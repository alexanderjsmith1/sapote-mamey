"""A partner contig's heading never moves the contig. In the v2u bee decks, 106 of 1,131 locus figures drew the second of
two partner contigs up to 20 kb from the reference genes it matches (in one genome, a partner contig drawn about 18 kb left of
its enduracidin matches), because the first partner's long heading ("no antiSMASH region · no BGC alias") was reserved as
occupied space. Headings now take a free side or are stacked by the renderer; only overlapping genes move a contig."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT))
import rescue_locus_comparison as rlc  # noqa: E402


def _ref(n=60):
    genes = [{"id": f"g{i}", "start": i * 1000, "end": i * 1000 + 900, "strand": 1,
              "group": f"G{i}" if i in (12, 24, 30) else ""} for i in range(n)]
    return {"id": "ref", "kind": "reference", "orientation": 1, "anchor_gene": "g30", "genes": genes}


def _partner(pid, group, n=3):
    genes = [{"id": f"{pid}_{k}", "start": k * 1000, "end": k * 1000 + 900, "strand": 1, "group": group if k == 1 else ""}
             for k in range(n)]
    return {"id": pid, "kind": "bgc", "orientation": 1, "anchor_gene": f"{pid}_1", "genes": genes,
            "identity": {"strain": "ISOLATE_001", "contig": f"NODE_{pid}_length_2524_cov_49.354720",
                         "region": "no antiSMASH region", "bgc": "no BGC alias"}}


def _core():
    return {"id": "core", "kind": "bgc", "orientation": 1, "anchor_gene": "c0", "offset_bp": 0,
            "genes": [{"id": "c0", "start": 0, "end": 900, "strand": 1, "group": "G30"}]}


def _anchor_dx(t, ref, rg):
    return t["offset_bp"] - rlc._mid_x(ref, rg)


def test_second_partner_stays_under_its_match_despite_the_first_partners_long_heading():
    ref = _ref()
    p1, p2 = _partner("p1", "G12"), _partner("p2", "G24")     # 12 kb apart: genes never overlap, headings would
    rlc.level_partners([_core(), ref, p1, p2], ref)
    assert abs(_anchor_dx(p1, ref, "g12")) < 1
    assert abs(_anchor_dx(p2, ref, "g24")) < 1                 # the old rule pushed p2 by a heading width


def test_only_overlapping_genes_move_a_partner():
    ref = _ref()
    p1, p2 = _partner("p1", "G24"), _partner("p2", "G24")     # same match: genes overlap, so one must move
    rlc.level_partners([_core(), ref, p1, p2], ref)
    xs1 = [rlc._mid_x(p1, g["id"]) + p1["offset_bp"] for g in p1["genes"]]
    xs2 = [rlc._mid_x(p2, g["id"]) + p2["offset_bp"] for g in p2["genes"]]
    assert max(xs2) < min(xs1) or min(xs2) > max(xs1)
    assert abs(_anchor_dx(p2, ref, "g24")) <= 7000             # a contig width plus padding (6.5 kb here), not a heading width (about 30 kb)
