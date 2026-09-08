"""Regression test — v97395 tick 17: resolve_strain_id() misses accession-PREFIXED zip stems.

Real-world shape: NCBI assembly-report download filenames commonly look like
``GCA_009862675.1_ASM986267v1_genomic.zip`` — a real accession as a *prefix*, followed by
more filename content (an assembly name + "_genomic"). ``looks_like_accession()`` is a
full-string match, so it never fires on this shape even though the resulting fallback strain
id (``GCA_009862675_1_ASM986267v1_genomic`` after sanitization) is exactly the kind of
accession-derived, non-identity label this module exists to warn about — the 2026-08-20
incident this module's own docstring documents (CP025018_1, CP108695_1, ...) was a *bare*
accession stem; this is the same failure mode one filename-shape away.
"""
from mamey.strain_identity import resolve_strain_id


def test_zip_stem_accession_prefixed_filename_warns_v97395():
    fake_zip = "/nonexistent/GCA_009862675.1_ASM986267v1_genomic.zip"
    ident = resolve_strain_id(None, fake_zip)
    assert ident.strain_id == "GCA_009862675_1_ASM986267v1_genomic"
    assert ident.message, "accession-prefixed zip-stem fallback must warn, not stay silent"
    assert "accession" in ident.message.lower()


def test_zip_stem_accession_prefixed_message_says_prefix_not_pure_accession_v97395():
    fake_zip = "/nonexistent/GCA_009862675.1_ASM986267v1_genomic.zip"
    ident = resolve_strain_id(None, fake_zip)
    # the fallback id is accession-PREFIXED, not a bare accession -- the warning wording should
    # say so rather than reusing the bare-accession phrasing verbatim.
    assert "begins with" in ident.message.lower()


def test_bare_accession_stem_still_warns_no_regression_v97395():
    fake_zip = "/nonexistent/CP108695.1.zip"
    ident = resolve_strain_id(None, fake_zip)
    assert ident.strain_id == "CP108695_1"
    assert ident.message
    assert "accession" in ident.message.lower()


def test_real_cohort_style_stem_not_falsely_flagged_v97395():
    # SID10815-shaped and AS-705-shaped stems must NOT be flagged -- this is the module's own
    # documented tight-count design (2-letter prefixes demand >=6 digits; SID has only 3 letters
    # + 5 digits). The fix must not regress this.
    for stem in ("SID10815", "AS-705", "AS_705_extraction_2"):
        fake_zip = f"/nonexistent/{stem}.zip"
        ident = resolve_strain_id(None, fake_zip)
        assert not ident.message, f"{stem!r} must not be flagged as accession-derived"
