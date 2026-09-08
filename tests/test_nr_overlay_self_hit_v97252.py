"""v9.7.252 — the nr overlay must exclude the genome's own deposited proteins.

THE BUG. `write_nr_overlay` recorded the rank-1 BLASTp hit per gene. For a **deposited type
strain or reference genome**, the strain's own proteins are in nr, so the rank-1 hit is the
query genome itself at ~100% identity. That drives `conservation_median_id` to 100, which is
the input to `scan_divergence` (the exploration board's novelty axis) and to the
`NOVELTY_CONTRADICTION` readiness guard. The result is that arming the overlay -- the very act
meant to *improve* the evidence -- silently **inverts** the divergence signal.

Observed on real data (v9.7.250, *Nocardia rhizosphaerae* type strain, GCA_042650365.1):

  * BGC022, the strain's most divergent locus, `median_id` 55.0 -> **100.0**
  * its `exploration_interest` 45.5 -> 35.5, dropping it out of the exploration top-5
  * both covered genes hit *Nocardia rhizosphaerae* at 100.000%
  * across six freshly-ingested type-strain genomes, **67 of 234 overlay rows (29%)** were
    >= 99.9% identity

For `ctg7_50` the informative comparator sat one rank down: rank 2 = 77.3% to
*Nocardia* sp. NPDC058633. This is the same failure class as the `kcb_top` genome-self-hit
bug fixed in v9.7.22.

THE FIX. The overlay records the best hit to **another organism**. A hit is a self-hit when
the subject's binomial equals the query genome's binomial AND identity is >= 99.0%. Unnamed
species ("Micromonospora sp.") never match, because "genus sp." would exclude every unnamed
congener in nr. A same-species hit from a *different* strain at moderate identity is a real
comparator and is retained. When no self-hits exist the behaviour is exactly the old rank-1
selection, so the P7a contract is preserved.
"""
import csv
import json
from pathlib import Path

import pytest

from mamey.blastp_ingest import _is_self_hit, _self_binomial, write_nr_overlay


def _pkg(tmp_path: Path, display_name: str) -> Path:
    pkg = tmp_path / "package"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "manifest.json").write_text(json.dumps({"display_name": display_name}), encoding="utf-8")
    return pkg


def _row(bgc, gene, acc, pid, sciname, bits, rank="1"):
    return {
        "strain": "X", "BGC_ID": bgc, "contig": "c1",
        "query_locus": f"X|{bgc}|slot=1|role=core|gene={gene}|aa=400|reason=x",
        "query_len": "", "hit_rank": rank, "subject_acc": acc,
        "subject_desc": "some protein", "sciname": sciname, "pct_identity": pid,
        "align_len": "100", "q_start": "1", "q_end": "100",
        "evalue": "0.0", "bitscore": bits, "source": "nr",
    }


def _overlay(pkg: Path, bgc: str) -> list[dict]:
    with (pkg / "blastp_online" / f"{bgc}_online_blastp.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------
# the self-hit predicate
# --------------------------------------------------------------------------

def test_self_binomial_from_manifest(tmp_path):
    pkg = _pkg(tmp_path, "Nocardia rhizosphaerae (type strain)")
    assert _self_binomial(pkg) == "nocardia rhizosphaerae"


@pytest.mark.parametrize("name", ["Micromonospora sp. AS-696", "Streptomyces sp.", "Nocardia"])
def test_self_binomial_none_for_unnamed_species(tmp_path, name):
    """'genus sp.' must NOT become a self-binomial, or every unnamed congener is excluded."""
    assert _self_binomial(_pkg(tmp_path, name)) is None


def test_is_self_hit_matches_same_binomial_at_high_identity():
    assert _is_self_hit("Nocardia rhizosphaerae", 100.0, "nocardia rhizosphaerae") is True
    assert _is_self_hit("Nocardia rhizosphaerae", "99.5", "nocardia rhizosphaerae") is True


def test_is_self_hit_retains_same_species_different_strain_at_moderate_identity():
    """92% to the same species is a real comparator, not the genome itself."""
    assert _is_self_hit("Nocardia rhizosphaerae", 92.0, "nocardia rhizosphaerae") is False


def test_is_self_hit_retains_other_organisms():
    assert _is_self_hit("Nocardia ignorata", 100.0, "nocardia rhizosphaerae") is False
    assert _is_self_hit("", 100.0, "nocardia rhizosphaerae") is False
    assert _is_self_hit("Nocardia ignorata", 100.0, None) is False


# --------------------------------------------------------------------------
# the overlay
# --------------------------------------------------------------------------

def test_overlay_skips_self_hit_and_takes_best_non_self_hit(tmp_path):
    """The real BGC022 shape: rank1 = self @100%, rank2 = 77.3% to another Nocardia."""
    pkg = _pkg(tmp_path, "Nocardia rhizosphaerae (type strain)")
    res = write_nr_overlay(pkg, [
        _row("BGC022", "ctg7_50", "WP_SELF", "100.000", "Nocardia rhizosphaerae", "900", rank="1"),
        _row("BGC022", "ctg7_50", "WP_REAL", "77.300", "Nocardia sp. NPDC058633", "700", rank="2"),
    ])
    rows = _overlay(pkg, "BGC022")
    assert len(rows) == 1
    assert rows[0]["blastp_accession"] == "WP_REAL", "self-hit must not win the overlay slot"
    assert rows[0]["pct_identity"].startswith("77")
    assert res["self_hits_excluded"] == 1


def test_gene_with_only_self_hits_is_omitted(tmp_path):
    """A gene whose every hit is its own genome carries no conservation information."""
    pkg = _pkg(tmp_path, "Nocardia rhizosphaerae (type strain)")
    res = write_nr_overlay(pkg, [
        _row("BGC022", "ctg7_50", "WP_SELF", "100.000", "Nocardia rhizosphaerae", "900"),
    ])
    assert res["self_hits_excluded"] == 1
    assert res["genes"] == 0
    assert not (pkg / "blastp_online" / "BGC022_online_blastp.csv").exists()


def test_unnamed_species_genome_keeps_all_hits(tmp_path):
    """AS-series strains are 'Micromonospora sp. AS-696' -- nothing may be excluded."""
    pkg = _pkg(tmp_path, "Micromonospora sp. AS-696")
    res = write_nr_overlay(pkg, [
        _row("BGC020", "ctg4_1", "WP_A", "100.000", "Micromonospora sp. NPDC1", "900"),
    ])
    assert res["self_hits_excluded"] == 0
    assert _overlay(pkg, "BGC020")[0]["blastp_accession"] == "WP_A"


def test_no_self_hits_preserves_rank_1_behaviour(tmp_path):
    """P7a contract: with no self-hits, the best (rank-1) hit still wins."""
    pkg = _pkg(tmp_path, "Nocardia rhizosphaerae (type strain)")
    write_nr_overlay(pkg, [
        _row("BGC001", "ctg1_1", "WP_A", "96.5", "Nocardia ignorata", "900", rank="1"),
        _row("BGC001", "ctg1_1", "WP_B", "75.6", "Nocardia fluminea", "700", rank="2"),
    ])
    rows = _overlay(pkg, "BGC001")
    assert len(rows) == 1 and rows[0]["blastp_accession"] == "WP_A"
