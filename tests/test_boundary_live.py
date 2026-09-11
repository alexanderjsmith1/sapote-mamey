"""End-to-end boundary-audit tests on the REAL Mamey schema (W4/W23).

Unlike the prototype (tests/test_sapote_judgment_audit.py, which uses a mocked schema),
this builds real BGCRecord objects, runs the real triage_bgcs(), serialises with the
real mamey.serialize, and audits with mamey.boundary_audit. It proves the wiring works
on actual types and that each failure class is caught.
"""
import pytest

from mamey.models import BGCRecord
from mamey.scoring import triage_bgcs
from mamey.serialize import records_payload, verdicts_payload
from mamey.boundary_audit import audit_payloads


def _bgc(bgc_id, contig, products, conf="B", edge="Interior"):
    return BGCRecord(bgc_id=bgc_id, contig=contig, region_number=int(bgc_id[-1]) if bgc_id[-1].isdigit() else 1,
                     start=0, end=30000, contig_length=60000, products=list(products),
                     edge_status=edge, architecture_confidence=conf,
                     user_label=f"{bgc_id} / {contig}")


def _payloads(bgcs):
    triage = triage_bgcs(bgcs, None, None)
    # mirror the kcb carry that write_boundary_payloads does
    by_id = {b.bgc_id: b for b in bgcs}
    for t in triage:
        b = by_id.get(t.bgc_id)
        if b is not None:
            setattr(t, "_kcb_cumulative", getattr(b, "kcb_cumulative", None))
    return records_payload("AS-TEST", bgcs), verdicts_payload("AS-TEST", triage), triage


def test_clean_run_passes():
    bgcs = [_bgc("BGC001", "NODE_5", ["NRPS"]), _bgc("BGC002", "NODE_7", ["T1PKS"])]
    recs, verds, _ = _payloads(bgcs)
    rc, problems = audit_payloads(recs, verds)
    assert rc == 0, problems


def test_excluded_class_is_downgraded_and_passes():
    # a saccharide BGC SHOULD be downgraded by triage -> exclusion fired -> audit clean
    bgcs = [_bgc("BGC001", "NODE_5", ["NRPS"]), _bgc("BGC002", "NODE_7", ["saccharide"], conf="D")]
    recs, verds, triage = _payloads(bgcs)
    sacc = next(v for v in verds["verdicts"] if v["bgc_id"] == "BGC002")
    assert sacc["standing_rule_flag"], "triage should have set a standing_rule_flag on saccharide"
    assert sacc["corrected_rank"] is None
    rc, problems = audit_payloads(recs, verds)
    assert rc == 0, problems


def test_dropped_record_is_caught():
    bgcs = [_bgc("BGC001", "NODE_5", ["NRPS"]), _bgc("BGC002", "NODE_7", ["T1PKS"])]
    recs, verds, _ = _payloads(bgcs)
    verds["verdicts"] = [v for v in verds["verdicts"] if v["bgc_id"] != "BGC002"]  # drop one
    rc, problems = audit_payloads(recs, verds)
    assert rc == 1 and any(p.startswith("DROPPED") for p in problems), problems


def test_orphan_verdict_is_caught():
    bgcs = [_bgc("BGC001", "NODE_5", ["NRPS"])]
    recs, verds, _ = _payloads(bgcs)
    verds["verdicts"].append({"bgc_id": "BGC999", "lead_tier": "Medium", "claim_confidence": "Moderate",
                              "corrected_rank": 2, "standing_rule_flag": "", "primary_metabolism_flag": False})
    rc, problems = audit_payloads(recs, verds)
    assert rc == 1 and any(p.startswith("ORPHAN") for p in problems), problems


def test_downgrade_not_honoured_is_caught():
    bgcs = [_bgc("BGC001", "NODE_5", ["saccharide"], conf="D")]
    recs, verds, _ = _payloads(bgcs)
    v = verds["verdicts"][0]
    v["corrected_rank"] = 1  # force the contradiction: flagged but still ranked
    rc, problems = audit_payloads(recs, verds)
    assert rc == 1 and any(p.startswith("DOWNGRADE") for p in problems), problems


def test_exclusion_did_not_fire_is_caught():
    # records say a still-excluded class (saccharide) but verdict shows no downgrade -> exclusion failed to fire.
    # (NAPAA is neutral as of build -q, so it is no longer the right probe for this auditor check.)
    bgcs = [_bgc("BGC001", "NODE_5", ["saccharide"])]
    recs, verds, _ = _payloads(bgcs)
    v = verds["verdicts"][0]
    v["standing_rule_flag"] = ""           # simulate the exclusion silently not firing
    v["primary_metabolism_flag"] = False
    rc, problems = audit_payloads(recs, verds)
    assert rc == 1 and any(p.startswith("EXCLUSION") for p in problems), problems


def test_bad_tier_value_is_caught():
    bgcs = [_bgc("BGC001", "NODE_5", ["NRPS"])]
    recs, verds, _ = _payloads(bgcs)
    verds["verdicts"][0]["lead_tier"] = "Legendary"  # not a real tier
    rc, problems = audit_payloads(recs, verds)
    assert rc == 1 and any(p.startswith("TIER") for p in problems), problems
