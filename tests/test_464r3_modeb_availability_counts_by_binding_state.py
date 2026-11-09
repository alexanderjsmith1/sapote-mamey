"""A stream record count belongs to the state it is reported with.

One exact-locus record plus nine unbound records for the same strain and alias
used to be reported as EXACT_LOCUS with 10 records. The count now covers only
the exact-locus record, and a per-state breakdown keeps the other nine visible.
"""
from mamey.mode_b import availability


def _obs(binding, source, records=1):
    return availability.EvidenceObservation(
        channel="blastp_per_gene", source_label="synthetic", source_path=source,
        source_sha256="a" * 64, source_bytes=1, strain="TEST-1", bgc="BGC001",
        full_node="ctg1", region="region001", binding_state=binding,
        freshness_state="CURRENT", record_count=records,
    )


def _rows():
    return [_obs("EXACT_LOCUS", "exact")] + [_obs("UNBOUND", f"unbound{i}") for i in range(9)]


def test_best_state_counts_only_the_reported_state():
    assert availability._best_state(_rows()) == ("EXACT_LOCUS", 1, "CURRENT")


def test_bgc_row_reports_breakdown_by_state():
    locus = availability.InventoryLocus("TEST-1", "BGC001", "ctg1", "region001",
                                        "TEST-1 / ctg1 / region001 / BGC001")
    bgc_rows, _, _ = availability.build_availability([locus], _rows(), availability.load_contract())
    row = bgc_rows[0]
    assert row["blastp_per_gene_state"] == "EXACT_LOCUS"
    assert row["blastp_per_gene_records"] == 1
    assert row["blastp_per_gene_records_by_state"] == "EXACT_LOCUS=1;UNBOUND=9"
    # A stream with no observation stays blank, never 0 under a state.
    assert row["domains_hmm_state"] == "ABSENT"
    assert row["domains_hmm_records_by_state"] == ""
