"""v9.7.20 T-4 + T-3: the shared contig_key normaliser and the summary-row sentinel.

T-4: contig_key is the single normaliser for every contig / Source_GBK join (was a local def in source_scans);
it collapses cov-float formatting variants to one key so cross-file joins (GBK merges, package-dir/strain-id
reconciliation) all match. T-3: is_summary_row guards cohort-keyed parsers against the merged "TOTAL" footer.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mamey.crosswalk import contig_key
from mamey.merge_policy import is_summary_row, SUMMARY_ROW_SENTINEL


def test_contig_key_collapses_cov_float_variants():
    a = "NODE_10_length_54129_cov_63.42318"
    b = "NODE_10_length_54129_cov_63.042318"
    assert contig_key(a) == contig_key(b) == "NODE_10_length_54129"


def test_contig_key_distinguishes_real_contigs_and_handles_blank():
    assert contig_key("NODE_10_length_54129_cov_72") != contig_key("NODE_11_length_54129_cov_72")
    assert contig_key("") == ""
    assert contig_key("ctg1_cov=5.5") == "ctg1"   # non-NODE fallback still strips the cov suffix


def test_source_scans_and_dkp_use_the_shared_key():
    # both modules pull the normaliser from crosswalk (not a private copy). Assert by origin + behaviour
    # rather than object identity, since mixed sys.path insertions across the suite can duplicate modules.
    from mamey.source_scans import _contig_key as ss_key
    from mamey.dkp_cdps import contig_key as dkp_key
    for fn in (ss_key, dkp_key):
        assert fn.__qualname__ == "contig_key" and fn.__module__.endswith("crosswalk")
        assert fn("NODE_9_length_100_cov_1.20") == contig_key("NODE_9_length_100_cov_1.20") == "NODE_9_length_100"


def test_is_summary_row_flags_footers_not_strains():
    assert is_summary_row("TOTAL") and is_summary_row("__SUMMARY__") and is_summary_row(" total ")
    assert not is_summary_row("AS-XXX") and not is_summary_row("SID-XXX") and not is_summary_row(None)
    assert SUMMARY_ROW_SENTINEL == "__SUMMARY__"


if __name__ == "__main__":
    for fn in [test_contig_key_collapses_cov_float_variants, test_contig_key_distinguishes_real_contigs_and_handles_blank,
               test_source_scans_and_dkp_use_the_shared_key, test_is_summary_row_flags_footers_not_strains]:
        fn()
    print("contig_key + summary-row regressions: all pass")
