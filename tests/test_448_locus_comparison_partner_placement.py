"""Card 12: a partner contig stays under the reference genes it matches; its heading takes the side that fits."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT))
import rescue_locus_comparison as rlc  # noqa: E402


def _gene(i, start, group=""):
    return {"id": f"g{i}", "start": start, "end": start + 900, "strand": 1, "group": group}


def _ref():
    genes = [_gene(i, i * 1000, f"G{i}" if i in (20, 30, 31) else "") for i in range(60)]  # room on the right, so no heading is forced left
    return {"id": "ref", "kind": "reference", "orientation": 1, "anchor_gene": "g30", "genes": genes}


def _partner(pid, group, n=6):
    genes = [{"id": f"{pid}_{k}", "start": k * 1000, "end": k * 1000 + 900, "strand": 1,
              "group": group if k == 2 else ""} for k in range(n)]
    return {"id": pid, "kind": "bgc", "orientation": 1, "anchor_gene": f"{pid}_2", "genes": genes,
            "identity": {"strain": "ISOLATE_001", "contig": f"NODE_{pid}_length_9000_cov_1", "region": "no antiSMASH region",
                         "bgc": "no BGC alias"}}


def _core():
    return {"id": "core", "kind": "bgc", "orientation": 1, "anchor_gene": "c0", "offset_bp": 0,
            "genes": [{"id": "c0", "start": 0, "end": 900, "strand": 1, "group": "G30"}]}


def _drawn_anchor_offset(t, ref, rg):
    return t["offset_bp"] - rlc._mid_x(ref, rg)


def test_a_partner_with_free_space_stays_under_its_match():
    ref = _ref()
    p1, p2 = _partner("p1", "G31"), _partner("p2", "G20")  # p2's genes fit left of p1; only a right-running heading would reach it
    rlc.level_partners([_core(), ref, p1, p2], ref)
    assert abs(_drawn_anchor_offset(p2, ref, "g20")) < 1     # previously pushed right past p1, kb away from its match
    assert p2.get("heading_align") == "right"


def test_a_heading_that_cannot_run_right_costs_the_neighbour_at_most_a_heading_width():
    ref = _ref(); ref["genes"] = ref["genes"][:40]              # the first partner's heading must now run left
    p1, p2 = _partner("p1", "G31"), _partner("p2", "G20")
    rlc.level_partners([_core(), ref, p1, p2], ref)
    assert abs(_drawn_anchor_offset(p2, ref, "g20")) < 15000
    assert abs(_drawn_anchor_offset(p1, ref, "g31")) < 1


def test_partners_that_truly_overlap_move_the_least_distance():
    ref = _ref()
    p1, p2 = _partner("p1", "G30"), _partner("p2", "G31")  # matches 1 kb apart: the second must move
    rlc.level_partners([_core(), ref, p1, p2], ref)
    lo1 = min(rlc._mid_x(p1, g["id"]) + p1["offset_bp"] for g in p1["genes"])
    hi1 = max(rlc._mid_x(p1, g["id"]) + p1["offset_bp"] for g in p1["genes"])
    xs2 = [rlc._mid_x(p2, g["id"]) + p2["offset_bp"] for g in p2["genes"]]
    assert max(xs2) < lo1 or min(xs2) > hi1                  # gene spans do not overlap
    assert abs(_drawn_anchor_offset(p2, ref, "g31")) < 40000  # moved, but not across the whole figure
