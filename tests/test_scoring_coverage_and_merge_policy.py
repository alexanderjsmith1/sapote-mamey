"""v9.7.20: (1) the absolute-default 100%-scoring completeness invariant, (2) the BGC-contig-on-record fix,
(3) the supersedure richness policy. Together they encode 'every BGC is assessed for ab/af/novelty' and
'prefer the richer source / consult before supersedure' so the BeeCohort 9%-coverage + AS-XXX-data-loss
failures cannot recur silently.
"""
import os, sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mamey.scoring import triage_bgcs, scoring_coverage, assert_full_scoring_coverage
from mamey.merge_policy import choose_authoritative_source, dominates
import pytest


def _bgc(bid, products=("nrps",), contig="NODE_10_length_54129_cov_72", region="region001"):
    return NS(bgc_id=bid, products=list(products), mibig_hits=[], kcb_top="Streptomyces sp. chromosome",
              kcb_cumulative=None, riq_score=None, edge_status="Interior", architecture_confidence="C",
              contig=contig, node_id=contig, antismash_region=region,
              user_label=f"{bid} / {contig} {region}")


# ── (1) completeness invariant ──────────────────────────────────────────────
def test_engine_scores_every_bgc_full_coverage():
    bgcs = [_bgc(f"BGC{i:03d}") for i in range(1, 21)]
    recs = triage_bgcs(bgcs, None, NS(cctt={"per_bgc": {}}, resistance_tiers={"per_bgc": {}}))
    covered, total, unscored = scoring_coverage(bgcs, recs)
    assert (covered, total, unscored) == (20, 20, [])
    assert assert_full_scoring_coverage(bgcs, recs) == ""   # full coverage -> no warning


def test_downstream_lead_only_coverage_fails_loudly():
    """The BeeCohort failure mode: only lead-tier rows carried scores. A triage missing the non-lead records
    must trip the invariant (raise by default)."""
    bgcs = [_bgc(f"BGC{i:03d}") for i in range(1, 11)]
    recs = triage_bgcs(bgcs, None, NS(cctt={"per_bgc": {}}, resistance_tiers={"per_bgc": {}}))
    lead_only = recs[:1]                                    # simulate a merge that kept ~9% of rows
    covered, total, unscored = scoring_coverage(bgcs, lead_only)
    assert covered == 1 and total == 10 and len(unscored) == 9
    with pytest.raises(ValueError, match="SCORING-COVERAGE FAIL"):
        assert_full_scoring_coverage(bgcs, lead_only, strain="AS-XXX")


# ── (2) BGC-contig-on-record (no bare "BGC003") ─────────────────────────────
def test_triage_record_carries_contig_and_user_label():
    bgcs = [_bgc("BGC003", contig="NODE_10_length_54129_cov_72")]
    rec = triage_bgcs(bgcs, None, NS(cctt={"per_bgc": {}}, resistance_tiers={"per_bgc": {}}))[0]
    assert rec.contig == "NODE_10_length_54129_cov_72"
    assert rec.user_label.startswith("BGC003 / NODE_10")   # a report can never print a bare BGC id


# ── (3) supersedure richness policy ─────────────────────────────────────────
def test_richer_standalone_supersedes_tidier_cohort():
    """AS-XXX case: standalone deep run dominates the cohort merge on every richness axis -> keep standalone."""
    v = choose_authoritative_source([
        {"label": "BeeCohort_merge", "signals": {"scored_bgcs": 6, "modeb_bgcs": 0, "domain_rows": 0, "gene_rows": 0}},
        {"label": "AS-XXX_standalone", "signals": {"scored_bgcs": 64, "modeb_bgcs": 22, "domain_rows": 635, "gene_rows": 821}},
    ])
    assert v["verdict"] == "SUPERSEDE" and v["keep"] == "AS-XXX_standalone" and v["drop"] == ["BeeCohort_merge"]


def test_no_dominator_consults_user():
    """Each source richer on some axis -> evidence loss either way -> CONSULT, never an auto-pick."""
    v = choose_authoritative_source([
        {"label": "A", "signals": {"modeb_bgcs": 22, "domain_rows": 0}},
        {"label": "B", "signals": {"modeb_bgcs": 0, "domain_rows": 600}},
    ])
    assert v["verdict"] == "CONSULT" and v["keep"] is None


def test_dominates_helper():
    assert dominates({"a": 2, "b": 2}, {"a": 1, "b": 2})
    assert not dominates({"a": 2, "b": 1}, {"a": 1, "b": 2})  # richer on a, poorer on b -> no dominance


if __name__ == "__main__":
    for fn in [test_engine_scores_every_bgc_full_coverage, test_downstream_lead_only_coverage_fails_loudly,
               test_triage_record_carries_contig_and_user_label, test_richer_standalone_supersedes_tidier_cohort,
               test_no_dominator_consults_user, test_dominates_helper]:
        fn()
    print("coverage + merge-policy + contig regressions: all pass")
