"""Card 464_gene_first_channel_state_counts: the gene-first channel summary reported a channel bound for
19 of 26 genes as "BOUND, 26 records, 26 gene-specific records", because unbound rows were counted as
records. The status stays the strongest state present; per-state counts now sit beside it.
Synthetic observations only.
"""
from mamey.mode_b.gene_first_explore import _channel_summary


def _obs(channel, gene, state):
    return {"channel": channel, "gene": gene, "evidence_state": state, "source_locator": ""}


def test_partly_bound_channel_shows_its_unbound_genes():
    observations = ([_obs("local_swissprot", f"g{i}", "BOUND") for i in range(19)]
                    + [_obs("local_swissprot", f"u{i}", "UNBOUND") for i in range(7)])
    row = {r["channel"]: r for r in _channel_summary(observations)}["local_swissprot"]
    assert row["status"] == "BOUND" and row["record_count"] == 26
    assert row["state_counts"] == "BOUND=19;UNBOUND=7"


def test_channel_without_rows_keeps_missing_and_empty_counts():
    row = {r["channel"]: r for r in _channel_summary([])}["nr"]
    assert row["status"] == "MISSING" and row["state_counts"] == ""


# A partly bound channel is a workflow gap for its unbound genes: the synthesis lists it under the gaps and the
# next-analysis routing points at the highest-ranked gene that channel does not cover.
from mamey.mode_b.gene_first_explore import CHANNELS, _render_synthesis, choose_next_analysis

IDENTITY = {"exact_identity": "SYN-1 / NODE_1_length_9000_cov_1.5 / region001 / BGC001"}


def _every_channel_bound_except_swissprot_for_g2():
    observations = [_obs(channel, "g1", "BOUND") for channel, _ in CHANNELS]
    observations += [_obs(channel, "g2", "BOUND") for channel, _ in CHANNELS if channel != "local_swissprot"]
    observations.append(_obs("local_swissprot", "g2", "UNBOUND"))
    channels = _channel_summary(observations)
    every = ";".join(channel for channel, _ in CHANNELS)
    ranked = [
        {"rank": 1, "locus_tag": "g1", "review_priority_category": "CORE", "product_qualifier": "",
         "sec_met_domains": "", "bound_gene_channels": every},
        {"rank": 2, "locus_tag": "g2", "review_priority_category": "CORE", "product_qualifier": "",
         "sec_met_domains": "", "bound_gene_channels": every.replace("local_swissprot;", "")},
    ]
    return channels, ranked


def test_mixed_channel_is_routed_as_a_gap_at_its_uncovered_gene():
    channels, ranked = _every_channel_bound_except_swissprot_for_g2()
    swiss = {r["channel"]: r for r in channels}["local_swissprot"]
    assert swiss["status"] == "BOUND" and swiss["partly_bound"]
    step = choose_next_analysis(channels, ranked, IDENTITY)
    assert step["analysis_id"] == "FILL_LOCAL_SWISSPROT_GAP"
    assert step["target"].endswith("/ g2")


def test_mixed_channel_is_listed_under_workflow_gaps():
    channels, ranked = _every_channel_bound_except_swissprot_for_g2()
    text = _render_synthesis(IDENTITY, {"products": ["T1PKS"], "edge_status": "Interior"}, ranked, channels,
                             choose_next_analysis(channels, ranked, IDENTITY), 0)
    gaps = next(line for line in text.splitlines() if line.startswith("Workflow gaps retained separately:"))
    bound = next(line for line in text.splitlines() if line.startswith("Bound channel families:"))
    assert "Local Swiss-Prot (partly bound: BOUND=1;UNBOUND=1)" in gaps
    assert "Local Swiss-Prot" not in bound and "NCBI nr" in bound
