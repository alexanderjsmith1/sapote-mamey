"""v9.7.44 — accession->SID/cohort resolver + non-actinomycete flag (F-7 / B-1)."""
from mamey.cohort_resolver import resolve_cohort, actino_status


def test_as_id_is_private_actino_cohort():
    r = resolve_cohort("AS-1", "Streptomyces sp.")
    assert r["cohort"] == "AS"


def test_as_prefix_is_exact_anchored_not_shape_matched():
    # v9.7.402 (W402-35 round 3): the AS-cohort regex previously admitted a second,
    # unrelated two-letter-prefix shape as an alternate branch -- any identifier beginning with
    # that other prefix was swept into cohort "AS". Generic, non-project-specific fixtures below
    # prove the regex is exact-anchored: ONLY a leading "AS" (optionally hyphenated, then a
    # digit) matches; no other prefix, however similarly shaped, is treated as this project's
    # private cohort by shape alone.
    for prefix in ("XJ", "ZA", "BA", "AA", "SA", "AJ"):
        r = resolve_cohort(f"{prefix}S-1", "")
        assert r["cohort"] != "AS", f"{prefix}S-1 must not resolve to cohort AS"


def test_unrecognized_prefix_is_routing_only_not_authoritative_membership():
    # v9.7.402 (W402-35 round 3): OTHER is a generic routing/diagnostic bucket, not confirmed
    # scientific cohort/study membership. A caller must be able to tell the two apart without
    # inferring anything from the identifier's shape.
    r = resolve_cohort("ZZZQ00000000", "Streptomyces sp.")
    assert r["cohort"] == "OTHER"
    assert r["membership_authority"] == "ROUTING_ONLY_NOT_SCIENTIFIC_COHORT_MEMBERSHIP"


def test_as_and_sid_cohorts_carry_no_membership_authority_claim():
    # AS/SID resolution is this module's existing, unchanged prefix/accession logic -- adding
    # membership_authority must not silently assert a new authority claim about it.
    assert resolve_cohort("AS-1", "Streptomyces sp.")["membership_authority"] is None
    assert resolve_cohort("SID8374", "Streptomyces sp.")["membership_authority"] is None


def test_sid_id_is_sid_cohort():
    assert resolve_cohort("SID8374", "Streptomyces sp.")["cohort"] == "SID"


def test_accession_resolves_embedded_sid_from_organism():
    # the core fix: WGS accession + organism "Streptomyces sp. SID8375" -> SID, not OTHER.
    r = resolve_cohort("WWGG00000000", "Streptomyces sp. SID8375")
    assert r["cohort"] == "SID"
    assert r["resolved_sid"] == "SID8375"
    assert "resolved" in r["note"]


def test_accession_without_sid_stays_other():
    r = resolve_cohort("JUNK01000000", "Streptomyces sp.")
    assert r["cohort"] == "OTHER"
    assert r["actino_status"] == "actinomycete"  # genus known, just no SID


def test_bacillus_flagged_non_actinomycete():
    r = resolve_cohort("WWJQ00000000", "Bacillus thuringiensis")
    assert r["cohort"] == "OTHER"
    assert r["actino_status"] == "non_actinomycete"
    assert r["note"] and "non-actinomycete" in r["note"]


def test_actino_status_genus_classification():
    assert actino_status("Streptomyces sp. SID1") == "actinomycete"
    assert actino_status("Pseudonocardia sp.") == "actinomycete"
    assert actino_status("Bacillus subtilis") == "non_actinomycete"
    assert actino_status("Pseudomonas aeruginosa") == "non_actinomycete"
    assert actino_status("") == "unknown"
    assert actino_status("Weirdgenus novum") == "unknown"


def test_cohort_vocabulary_unchanged():
    # downstream consumers must still see only AS/SID/OTHER.
    for sid, org in [("AS-1", "x"), ("SID9", "x"), ("WW1", "Streptomyces sp. SID5"),
                     ("WW2", "Bacillus x"), ("WW3", "Streptomyces sp.")]:
        assert resolve_cohort(sid, org)["cohort"] in {"AS", "SID", "OTHER"}
