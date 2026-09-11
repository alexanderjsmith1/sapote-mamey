"""Unit tests for the phylo_refset dedup logic + outgroup_registry parsing.

Hermetic: Tier-2 (sequence) dedup needs the blast env, so these tests force BLAST_BIN to a bogus path so
only Tier-1 (metadata) + the pure helpers are exercised deterministically. Tier-2 is covered by the
end-to-end validation recorded in the PATCH_CARD (Streptomyces committee 34->25).

Run: pytest candidate_files/tests/test_phylo_refset_dedup.py -q
"""
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "tools")


def _load(name):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_parse_header():
    rs = _load("phylo_refset")
    assert rs._parse_header("Streptomyces_mashuensis_strain_DSM_40221_NR_026174") == \
        ("Streptomyces", "mashuensis", "DSM40221", "NR_026174")
    # no strain token
    assert rs._parse_header("Streptomyces_albiaxialis_NR_043378")[:2] == ("Streptomyces", "albiaxialis")
    assert rs._parse_header("Streptomyces_albiaxialis_NR_043378")[3] == "NR_043378"
    # versioned accession
    assert rs._parse_header("Kitasatospora_setae_KM_6054T_NR_112082.2")[3] == "NR_112082.2"


def test_rep_score_prefers_type_collection_then_length():
    rs = _load("phylo_refset")
    dsm = ("Streptomyces_x_strain_DSM_100_NR_1", "A" * 1400)
    nrrl = ("Streptomyces_x_strain_NRRL_B_5_NR_2", "A" * 1400)
    # DSM outranks NRRL in the collection priority
    assert rs._rep_score(dsm) > rs._rep_score(nrrl)
    # longer sequence wins within the same (absent) collection
    short = ("Streptomyces_y_NR_3", "A" * 900)
    longer = ("Streptomyces_y_NR_4", "A" * 1400)
    assert rs._rep_score(longer) > rs._rep_score(short)


def test_tier1_collapses_duplicate_accession(monkeypatch):
    rs = _load("phylo_refset")
    monkeypatch.setattr(rs, "BLAST_BIN", "/nonexistent/bin")  # force Tier-2 skip -> deterministic
    recs = [
        ("Streptomyces_mashuensis_strain_DSM_40221_NR_026174", "ACGT" * 350),
        ("Streptomyces_mashuensis_strain_DSM_40221_NR_116638", "ACGT" * 350),   # same strain, dup accession
        ("Streptomyces_coelicolor_strain_DSM_40233_NR_116633", "TTTT" * 350),
    ]
    kept, collapses = rs.dedup(recs, report=None, verbose=False)
    kept_names = {h for h, _ in kept}
    assert len(kept) == 2
    assert "Streptomyces_coelicolor_strain_DSM_40233_NR_116633" in kept_names
    # exactly one mashuensis survives, and it is the kept one recorded in the collapse
    mash = [h for h in kept_names if "mashuensis" in h]
    assert len(mash) == 1
    assert any(c["tier"] == 1 for c in collapses)


def test_no_strain_token_not_collapsed_by_tier1(monkeypatch):
    rs = _load("phylo_refset")
    monkeypatch.setattr(rs, "BLAST_BIN", "/nonexistent/bin")
    # two different species with no strain token must both survive Tier-1
    recs = [
        ("Streptomyces_albiaxialis_NR_043378", "ACGT" * 300),
        ("Streptomyces_champavatii_NR_115669", "TTGG" * 300),
    ]
    kept, _ = rs.dedup(recs, report=None, verbose=False)
    assert len(kept) == 2


def _registry_oracle(path, scope, taxon):
    """Independent minimal read of the governed TSV — an ORACLE for the parser, not a second parser.

    Resolves exactly as `outgroup_registry.find_row` documents: exact scope+taxon match, preferring
    a LOCKED row among ties. Deliberately dumb (split on tabs, zip with the header) so that a bug in
    the real parser cannot hide inside the thing checking it.
    """
    header, hits = None, []
    for line in open(path, encoding="utf-8"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cells = line.rstrip("\n").split("\t")
        if header is None and cells[0] == "tree_scope":
            header = cells
            continue
        if header is None:
            continue
        row = dict(zip(header, cells))
        if row.get("tree_scope") == scope and row.get("ingroup_taxon") == taxon:
            hits.append(row)
    locked = [r for r in hits if r.get("status") == "LOCKED"]
    return (locked or hits)[0] if hits else None


def test_outgroup_registry_parses_locked_rows():
    """The parser must return what the registry SAYS — not a genus this test remembers.

    v9.7.416. This test used to assert `find_row("Streptomyces")["outgroup_genus"] ==
    "Kitasatospora"`. Alex RULED that row to Gordonia on 2026-09-07 (the registry's own rationale
    column records the ruling and the three measured gate margins: -5.9, -1.5, -6.6 on Gordonia
    versus +0.2 / +1.5 / +1.2 on Kitasatospora). The registry is the source of truth for that
    decision; this file is not. By hardcoding the answer, the test became a SECOND, competing
    record of a governed scientific ruling — and the moment the ruling changed, the bundle shipped a
    test that contradicted `OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv`.

    It failed silently for everyone else: the test skips when the governed registry is not
    provisioned, so it only goes red on a machine that actually has the data. That is the worst
    combination — wrong where it matters, quiet everywhere else.

    So this now checks the PARSER, which is what a parser test is for: that `find_row` resolves the
    rows the cohorts depend on, and returns the same row an independent read of the same file gives.
    It can never again go stale against a ruling, because it no longer holds an opinion about one.
    `test_find_row_prefers_locked_over_confirm` below is the hermetic half that would catch a parser
    genuinely reading the wrong column — the job the hardcoded literal was accidentally doing.
    """
    og = _load("outgroup_registry")
    # OUTGROUP_REGISTRY.tsv is governed workspace data, not redistributed with the bundle
    # (docs/EXTERNAL_DATA.md). Absent registry => NOT MEASURED, not a failure.
    if not os.path.exists(og.REGISTRY):
        pytest.skip(f"governed outgroup registry not provisioned: {og.REGISTRY}")
    if og.registry_binding(og.REGISTRY)["authority"] == "BUNDLED_REFERENCE_ONLY":
        assert og.load_registry(og.REGISTRY), "Bundled reference snapshot should remain inspectable"
        with pytest.raises(og.RegistryAuthorityError, match="OUTGROUP_AUTHORITY_UNBOUND"):
            og.find_row("Streptomyces")
        return
    for scope, taxon in (("genus", "Streptomyces"), ("genus", "Nocardia")):
        got = og.find_row(taxon, scope=scope)
        want = _registry_oracle(og.REGISTRY, scope, taxon)
        assert want is not None, f"the cohorts depend on a {scope} row for {taxon}; none in {og.REGISTRY}"
        assert got is not None, f"find_row returned nothing for {scope}/{taxon}"
        assert got["outgroup_genus"] == want["outgroup_genus"], (
            f"find_row disagrees with the registry for {scope}/{taxon}: "
            f"parser says {got['outgroup_genus']!r}, file says {want['outgroup_genus']!r}")
        assert got["status"] == "LOCKED", (
            f"the {scope} row for {taxon} is {got['status']!r}, not LOCKED; the cohort trees "
            f"depend on a locked outgroup for it")
    # family scope differs from genus scope for Streptomycetaceae
    fam = og.find_row("Streptomycetaceae", scope="family")
    assert fam is not None and fam["tree_scope"] == "family"


def test_find_row_prefers_locked_over_confirm(tmp_path):
    """Hermetic parser check on a synthetic registry — no governed data, no ruling encoded here."""
    og = _load("outgroup_registry")
    reg = tmp_path / "OUTGROUP_REGISTRY.tsv"
    reg.write_text(
        "# synthetic\n"
        "\t".join(og.COLS) + "\n"
        "genus\tSyntheticus\tSyntheticaceae\tAlternatus\tAlternatus one\tGCF_000000001.1\tCONFIRM\talternate sister genus\n"
        "genus\tSyntheticus\tSyntheticaceae\tPrimarius\tPrimarius one\tGCF_000000002.1\tLOCKED\tprimary\n"
        "family\tSyntheticaceae\tSyntheticaceae\tOutlandus\tOutlandus one\tGCF_000000003.1\tLOCKED\tfamily scope\n",
        encoding="utf-8")
    row = og.find_row("Syntheticus", scope="genus", path=str(reg))
    assert row is not None and row["outgroup_genus"] == "Primarius", (
        "find_row must prefer the LOCKED row over a CONFIRM alternate listed above it")
    assert row["status"] == "LOCKED"
    fam = og.find_row("Syntheticaceae", scope="family", path=str(reg))
    assert fam is not None and fam["outgroup_genus"] == "Outlandus"
