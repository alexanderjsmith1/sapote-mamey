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

from mamey import blastp_ingest as bi
from mamey.blastp_ingest import (
    BlastpOverlayReadError,
    _is_self_hit,
    _read_optional_package_manifest,
    _self_binomial,
    blastp_status,
    write_nr_overlay,
)

_TXN_DIR_NAME = ".blastp_fileset_transactions"


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


def _two_bgc_rows():
    """Rows for two complete test identities used by the file-set fault controls.

    STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001
    STRAIN-TEST / NODE_2_length_1000_cov_20 / region001 / BGC002
    """
    return [
        _row("BGC001", "ctg1_1", "WP_ONE", "72.0", "Other species", "201"),
        _row("BGC002", "ctg2_1", "WP_TWO", "73.0", "Other species", "202"),
    ]


def _inject_staged_replace_failure(monkeypatch, fail_position: int):
    original_replace = Path.replace
    seen = 0

    def fail_selected_staged_replace(source, target):
        nonlocal seen
        if source.name.startswith("staged_") and source.parent.parent.name == _TXN_DIR_NAME:
            seen += 1
            if seen == fail_position:
                raise OSError(f"fixture fails staged commit position {fail_position}")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_selected_staged_replace)


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


def test_unreadable_existing_overlay_is_preserved_and_blocks_replacement(tmp_path, monkeypatch):
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001 stays immutable on read failure."""
    pkg = _pkg(tmp_path, "Nocardia rhizosphaerae (type strain)")
    overlay = pkg / "blastp_online" / "BGC001_online_blastp.csv"
    overlay.parent.mkdir()
    original = b"locus_tag,bitscore\nctg1_9,999\n"
    overlay.write_bytes(original)
    original_open = Path.open

    def refuse_overlay_read(path, *args, **kwargs):
        if path == overlay and not args and "mode" not in kwargs:
            raise PermissionError("fixture denies prior-overlay read")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refuse_overlay_read)
    with pytest.raises(BlastpOverlayReadError, match="BLASTP_OVERLAY_READ_HOLD"):
        write_nr_overlay(pkg, [
            _row("BGC001", "ctg1_1", "WP_NEW", "70.0", "Nocardia ignorata", "500"),
        ])
    assert overlay.read_bytes() == original


def test_corrupt_manifest_cannot_disable_self_hit_exclusion(tmp_path):
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001 fails before nr overlay output."""
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="BLASTP_PACKAGE_MANIFEST_HOLD"):
        write_nr_overlay(pkg, [
            _row("BGC001", "ctg1_1", "WP_SELF", "100.0", "Nocardia testii", "900"),
        ])
    assert not (pkg / "blastp_online").exists()


@pytest.mark.parametrize("field,value", [
    ("pct_identity", "not-a-number"),
    ("pct_identity", "nan"),
    ("hit_rank", "not-a-rank"),
])
def test_undecidable_probable_self_hit_is_a_typed_hold(field, value):
    row = {"pct_identity": "100.0", "hit_rank": "1"}
    row[field] = value
    with pytest.raises(bi.BlastpNumericEvidenceError, match="BLASTP_NUMERIC_EVIDENCE_HOLD"):
        _is_self_hit("", row["pct_identity"], "nocardia testii", row["hit_rank"])


def test_named_self_subject_with_invalid_identity_is_a_typed_hold():
    with pytest.raises(bi.BlastpNumericEvidenceError, match="BLASTP_NUMERIC_EVIDENCE_HOLD"):
        _is_self_hit("Nocardia testii", "not-a-number", "nocardia testii", "1")


def test_invalid_bitscore_cannot_enter_or_rank_an_overlay(tmp_path):
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001 fails before output."""
    pkg = _pkg(tmp_path, "Micromonospora sp. AS-696")
    with pytest.raises(bi.BlastpNumericEvidenceError, match="BLASTP_NUMERIC_EVIDENCE_HOLD"):
        write_nr_overlay(pkg, [
            _row("BGC001", "ctg1_1", "WP_BAD", "72.0", "Other species", "not-a-score"),
        ])
    assert not (pkg / "blastp_online").exists()


def test_nonself_subject_does_not_require_identity_for_self_exclusion():
    """Unrelated organism identity is not consulted by the self-hit predicate."""
    assert _is_self_hit("Nocardia ignorata", "not-a-number", "nocardia testii", "1") is False


def test_package_traversal_error_cannot_become_missing_domain_context(tmp_path, monkeypatch):
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001 fails before output."""
    pkg = _pkg(tmp_path, "Micromonospora sp. AS-696")
    original_iterdir = Path.iterdir

    def refuse_package(path):
        if path == pkg:
            raise PermissionError("fixture denies package traversal")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", refuse_package)
    with pytest.raises(ValueError, match="BLASTP_PACKAGE_DISCOVERY_HOLD"):
        write_nr_overlay(pkg, [
            _row("BGC001", "ctg1_1", "WP_1", "72.0", "Other species", "200"),
        ])
    assert not (pkg / "blastp_online").exists()


def test_status_refuses_unreadable_overlay_directory(tmp_path, monkeypatch):
    pkg = _pkg(tmp_path, "Micromonospora sp. AS-696")
    outdir = pkg / "blastp_online"
    outdir.mkdir()
    original_iterdir = Path.iterdir

    def refuse_store(path):
        if path == outdir:
            raise PermissionError("fixture denies overlay-status traversal")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", refuse_store)
    with pytest.raises(BlastpOverlayReadError, match="BLASTP_OVERLAY_READ_HOLD"):
        blastp_status(pkg)


def test_status_missing_overlay_directory_remains_empty(tmp_path):
    pkg = _pkg(tmp_path, "Micromonospora sp. AS-696")
    assert blastp_status(pkg) == []


def test_existing_manifest_cannot_become_missing_via_exists_suppression(tmp_path, monkeypatch):
    pkg = _pkg(tmp_path, "Nocardia testii (type strain)")
    manifest = pkg / "manifest.json"
    original_exists = Path.exists

    def suppress_manifest_stat(path):
        if path == manifest:
            return False
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", suppress_manifest_stat)
    assert _read_optional_package_manifest(pkg)["display_name"].startswith("Nocardia testii")


@pytest.mark.parametrize("fail_position", [1, 2])
def test_two_overlay_commit_failure_removes_every_new_output(tmp_path, monkeypatch, fail_position):
    """Caught failure at either commit position restores the absent-output file set."""
    pkg = _pkg(tmp_path, "Micromonospora sp. AS-696")
    _inject_staged_replace_failure(monkeypatch, fail_position)

    with pytest.raises(RuntimeError, match="BLASTP_FILESET_COMMIT_HOLD"):
        write_nr_overlay(pkg, _two_bgc_rows())

    assert not (pkg / "blastp_online" / "BGC001_online_blastp.csv").exists()
    assert not (pkg / "blastp_online" / "BGC002_online_blastp.csv").exists()


@pytest.mark.parametrize("fail_position", [1, 2])
def test_two_overlay_commit_failure_restores_every_existing_output(
        tmp_path, monkeypatch, fail_position):
    """Caught failure at either commit position restores exact pre-commit bytes."""
    pkg = _pkg(tmp_path, "Micromonospora sp. AS-696")
    write_nr_overlay(pkg, _two_bgc_rows())
    paths = [pkg / "blastp_online" / f"BGC00{number}_online_blastp.csv"
             for number in (1, 2)]
    originals = [path.read_bytes() for path in paths]
    replacement_rows = [
        _row("BGC001", "ctg1_2", "WP_NEW_ONE", "82.0", "Other species", "301"),
        _row("BGC002", "ctg2_2", "WP_NEW_TWO", "83.0", "Other species", "302"),
    ]
    _inject_staged_replace_failure(monkeypatch, fail_position)

    with pytest.raises(RuntimeError, match="BLASTP_FILESET_COMMIT_HOLD"):
        write_nr_overlay(pkg, replacement_rows)

    assert [path.read_bytes() for path in paths] == originals


def test_pending_rollback_is_recovered_before_next_overlay_validation(tmp_path, monkeypatch):
    """A rollback failure leaves a recovery hold; the next writer restores before validating."""
    pkg = _pkg(tmp_path, "Micromonospora sp. AS-696")
    write_nr_overlay(pkg, _two_bgc_rows())
    paths = [pkg / "blastp_online" / f"BGC00{number}_online_blastp.csv"
             for number in (1, 2)]
    originals = [path.read_bytes() for path in paths]
    original_replace = Path.replace
    staged_seen = 0
    restore_failed = False

    def fail_commit_then_first_rollback(source, target):
        nonlocal staged_seen, restore_failed
        if source.name.startswith("staged_") and source.parent.parent.name == _TXN_DIR_NAME:
            staged_seen += 1
            if staged_seen == 2:
                raise OSError("fixture fails second staged commit")
        if source.name == "restore_0.tmp" and not restore_failed:
            restore_failed = True
            raise OSError("fixture fails first rollback attempt")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_commit_then_first_rollback)
    with pytest.raises(RuntimeError, match="BLASTP_FILESET_RECOVERY_HOLD"):
        write_nr_overlay(pkg, [
            _row("BGC001", "ctg1_2", "WP_NEW_ONE", "82.0", "Other species", "301"),
            _row("BGC002", "ctg2_2", "WP_NEW_TWO", "83.0", "Other species", "302"),
        ])
    assert (pkg / _TXN_DIR_NAME).is_dir()

    monkeypatch.setattr(Path, "replace", original_replace)
    invalid = _row("BGC001", "ctg1_9", "WP_BAD", "70.0", "Other species", "bad")
    with pytest.raises(bi.BlastpNumericEvidenceError, match="BLASTP_NUMERIC_EVIDENCE_HOLD"):
        write_nr_overlay(pkg, [invalid])

    assert [path.read_bytes() for path in paths] == originals
    assert not (pkg / _TXN_DIR_NAME).exists()


def test_successful_two_overlay_commit_cleans_transaction_debris(tmp_path):
    """A normal two-file commit publishes both complete identities and removes its journal."""
    pkg = _pkg(tmp_path, "Micromonospora sp. AS-696")
    result = write_nr_overlay(pkg, _two_bgc_rows())
    assert result["bgcs"] == 2
    assert _overlay(pkg, "BGC001")[0]["blastp_accession"] == "WP_ONE"
    assert _overlay(pkg, "BGC002")[0]["blastp_accession"] == "WP_TWO"
    assert not (pkg / _TXN_DIR_NAME).exists()
