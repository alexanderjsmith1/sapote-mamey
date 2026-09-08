"""Tests for Gap 3 — cohort_synthesis writer. The novelty_basis correctness is the headline."""
import sys, os, pathlib
import pytest
_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
from mamey.cohort_synthesis import (load_master, novelty_by_host, differentiating_capacities,
                              write_synthesis, _is_fully_dark, _is_dark_or_unresolved,
                              meta_from_differentiating_csv)
from mamey.master_workbook import CANONICAL_V1_HEADERS

MASTER = str(_ROOT / "private" / "cohort_fixtures" / "_cohort_master_v2.xlsx")
DIFF = "/mnt/user-data/uploads/Cohort_Differentiating_Capacities.csv"
# TEST-02: previously a module-level `pytestmark` skipped EVERY test whenever the non-shipped
# scored master fixture was absent (which is always, in this tier) — hiding the pure-logic and
# self-contained tests too. Scope the skip to only the tests that genuinely need the xlsx/csv;
# the dark-helper unit test and the two build-your-own-workbook refuse tests run unconditionally.
needs_master = pytest.mark.skipif(not os.path.exists(MASTER),
                                  reason="scored cohort master fixture not present in this tier")


@pytest.fixture(scope="module")
def host_ov():
    # genus+host sourced from the differentiating CSV (registry taxonomy is unpopulated in this cut)
    return meta_from_differentiating_csv(DIFF) if os.path.exists(DIFF) else {}


@pytest.fixture(scope="module")
def M(host_ov):
    return load_master(MASTER, meta_overrides=host_ov)


@needs_master
def test_master_loads(M):
    assert M["N"] == 24
    assert len(M["bgcs"]) == 1131


@needs_master
def test_fully_dark_is_164(M):
    """fully_dark must reproduce the canonical 164/1131 (matches the findings sheet)."""
    assert sum(b["fully_dark"] for b in M["bgcs"]) == 164


@needs_master
def test_dark_or_unresolved_is_423(M):
    """dark_or_unresolved must reproduce 423/1131 (the broader novelty signal)."""
    assert sum(b["dark_or_unresolved"] for b in M["bgcs"]) == 423


@needs_master
def test_the_two_bases_differ(M):
    """The whole point of novelty_basis: the two definitions are NOT the same number."""
    fd = sum(b["fully_dark"] for b in M["bgcs"])
    du = sum(b["dark_or_unresolved"] for b in M["bgcs"])
    assert fd != du
    assert du > fd  # broader basis counts more


def test_dark_helpers_unit():
    assert _is_fully_dark("") is True
    assert _is_fully_dark("None") is True
    assert _is_fully_dark("BGC0000664.5 | isorenieratene") is False
    assert _is_fully_dark("Pseudonocardia sp. chromosome") is False  # a hit, not fully dark
    assert _is_dark_or_unresolved("") is True
    assert _is_dark_or_unresolved("Pseudonocardia sp. chromosome") is True  # bare ref = unresolved
    assert _is_dark_or_unresolved("BGC0000664.5 | x") is False  # MIBiG = resolved


@needs_master
def test_differentiating_capacities_eleven(M):
    assert len(differentiating_capacities(M["prevalence"])) == 11


@needs_master
def test_synthesis_reports_both_bases(host_ov):
    """Headline uses chosen basis but the alternate is ALWAYS reported and labeled."""
    syn = write_synthesis(MASTER, novelty_basis="fully_dark", meta_overrides=host_ov)
    assert "basis: `fully_dark`" in syn
    assert "164" in syn and "15%" in syn          # chosen headline
    assert "423" in syn and "37%" in syn          # alternate, explicitly shown
    assert "do not mix" in syn                     # the anti-conflation guard


@needs_master
def test_synthesis_basis_flips_headline(host_ov):
    syn = write_synthesis(MASTER, novelty_basis="dark_or_unresolved", meta_overrides=host_ov)
    assert "basis: `dark_or_unresolved`" in syn
    assert "423" in syn  # now the headline
    assert "164" in syn  # alternate still shown


@needs_master
def test_bad_basis_raises(host_ov):
    with pytest.raises(ValueError):
        write_synthesis(MASTER, novelty_basis="whatever", meta_overrides=host_ov)


def test_stale_master_refuses(tmp_path):
    """A master missing required sheets must raise, not emit wrong prose."""
    from openpyxl import Workbook
    p = tmp_path / "empty.xlsx"
    Workbook().save(p)
    with pytest.raises(RuntimeError):
        write_synthesis(p, novelty_basis="fully_dark")


@needs_master
def test_genus_from_differentiating_csv_populates_signatures(host_ov):
    """v9.7.116 reconciliation: when the master registry taxonomy is unpopulated, genus is sourced
    from the differentiating CSV so genus signatures resolve (not '*not*')."""
    syn = write_synthesis(MASTER, novelty_basis="fully_dark", meta_overrides=host_ov)
    # the validated genus signature: Actinophytocola is present and PKS/halogenated-led
    assert "Actinophytocola" in syn
    assert "Streptomyces" in syn
    # the unresolved-genus bucket must be suppressed, not emitted as '**not**'
    assert "**not**" not in syn


@needs_master
def test_differentiating_capacities_carry_real_genus(host_ov):
    """The 11 differentiating leads must show real genus (from the registry, now populated), not the
    unpopulated 'not'. Asserts the structural property without hard-coding a real strain ID."""
    syn = write_synthesis(MASTER, novelty_basis="fully_dark", meta_overrides=host_ov)
    # the crocagin lead line must carry a real italicised genus, not the unpopulated placeholder
    croc_line = next(l for l in syn.splitlines() if l.startswith("- **crocagin**"))
    assert "*Nocardia" in croc_line          # genus resolved (Nocardia or Nocardia sp.)
    assert "(*not*," not in syn
    assert "(*not verified*," not in syn


@pytest.mark.skipif(not os.path.exists(DIFF), reason="upload CSV not present")
def test_meta_from_csv_covers_expected_strains():
    """The CSV helper resolves genus/host. Strains are looked up by their differentiating capacity,
    not by hard-coded real ID, so no real strain literal sits in the test source."""
    meta = meta_from_differentiating_csv(DIFF)
    import csv as _csv
    rows = list(_csv.DictReader(open(DIFF)))
    polyyne_strain = next(r["strain"] for r in rows if r["differentiating_class"] == "polyyne")
    moss_strain = next(r["strain"] for r in rows if r["host"] == "Moss")
    assert meta.get(polyyne_strain, {}).get("genus", "").startswith("Actinophytocola")
    assert meta.get(moss_strain, {}).get("host") == "Moss"


def test_empty_bgc_master_refuses(tmp_path):
    """Bug Hunt v9.7.117: a master whose required sheets exist but B1_BGC_Master is header-only
    (0 BGCs) must refuse cleanly, not ZeroDivisionError on the novelty-fraction math.

    COH-02 (v9.7.338): the fixture now uses the SHIPPED lowercase headers (strain/taxonomy/
    ecology_source, strain/…/products/…/kcb_top) so the empty-B1 refusal is exercised for the
    real schema rather than being masked by a foreign-schema column-resolution raise."""
    import openpyxl
    p = tmp_path / "empty_b1.xlsx"
    wb = openpyxl.Workbook()
    reg = wb.active; reg.title = "A2_Strain_Registry"
    reg.append(["strain", "taxonomy", "ecology_source", "habitat", "n50", "bgc_count"])
    reg.append(["AS-900", "Streptomyces sp.", "Bombus terrestris", "hive", 500000, 0])
    prev = wb.create_sheet("Cross_Strain_Class_Prevalence")
    prev.append(["product_class", "n_strains", "pct_strains", "n_BGCs", "band"])
    prev.append(["PKS", 1, 100, 5, "CORE"])
    b1 = wb.create_sheet("B1_BGC_Master")
    b1.append(["strain", "assembly_locator", "contig", "region", "BGC_ID", "start", "end",
               "length_kb", "products", "boundary", "arch", "kcb_top"])   # header only
    wb.save(p)
    with pytest.raises(RuntimeError):
        write_synthesis(p, novelty_basis="fully_dark")


# --- COH-02 regression: load_master must resolve the REAL master_workbook schema -------------
# These build a genuine master with the shipped CANONICAL_V1_HEADERS (mamey/master_workbook.py),
# so the column-resolution bug (KCB_Top_Hit->products, Products->a coordinate, Genus->ecology_source)
# is caught for real instead of hidden behind a fixture that used the same fake capitalized headers.

_A2_SHIPPED = CANONICAL_V1_HEADERS["A2_Strain_Registry"]
_B1_SHIPPED = CANONICAL_V1_HEADERS["B1_BGC_Master"]


def _b1_row(strain, bgc, products, kcb):
    return [strain, "loc", "ctg1", "r1", bgc, 100, 2000, 1.9, products, "complete", "high", kcb]


def _build_real_master(path):
    """A 3-strain master using the shipped lowercase headers.

    AS-900/AS-901 = Streptomyces / Apis (4 NRPS BGCs total, all Apis → COH-05 host-bias),
    AS-902 = Nocardia / Bombus, carrying the only lassopeptide (a §5 differentiating lead)."""
    import openpyxl
    wb = openpyxl.Workbook()
    reg = wb.active; reg.title = "A2_Strain_Registry"
    reg.append(_A2_SHIPPED)
    reg.append(["AS-900", "Streptomyces sp.", "Apis mellifera gut", "hive", 8_000_000, 5, 500000, 70, 2])
    reg.append(["AS-901", "Streptomyces sp.", "Apis mellifera gut", "hive", 8_100_000, 6, 480000, 71, 2])
    reg.append(["AS-902", "Nocardia sp.", "Bombus terrestris", "nest", 7_000_000, 9, 300000, 68, 2])
    b2 = wb.create_sheet("B2_Product_Class_Matrix")
    b2.append(["strain", "NRPS", "PKS", "lassopeptide", "counts_reliability"])
    b2.append(["AS-900", 1, 0, 0, "ok"])
    b2.append(["AS-901", 1, 0, 0, "ok"])
    b2.append(["AS-902", 0, 1, 1, "ok"])
    b1 = wb.create_sheet("B1_BGC_Master")
    b1.append(_B1_SHIPPED)
    b1.append(_b1_row("AS-900", "AS-900_BGC0001", "NRPS", ""))                       # fully dark
    b1.append(_b1_row("AS-900", "AS-900_BGC0002", "NRPS", "BGC0001234 | thing"))     # resolved
    b1.append(_b1_row("AS-901", "AS-901_BGC0001", "NRPS", "Streptomyces sp. genome"))  # unresolved bare ref
    b1.append(_b1_row("AS-901", "AS-901_BGC0002", "NRPS", "BGC0005678 | other"))     # resolved
    b1.append(_b1_row("AS-902", "AS-902_BGC0001", "PKS", "BGC0009999 | z"))          # resolved
    b1.append(_b1_row("AS-902", "AS-902_BGC0002", "lassopeptide", ""))              # fully dark
    wb.save(path)


def test_load_master_resolves_shipped_headers(tmp_path):
    """COH-02: genus from `taxonomy`, host from `ecology_source`, kcb from `kcb_top`, products from
    `products` — NOT the capitalized names / positional fallbacks that landed on wrong columns."""
    p = tmp_path / "real_master.xlsx"
    _build_real_master(p)
    M = load_master(p)
    assert M, "real shipped-header master must load (not return {})"
    assert M["N"] == 3
    reg = M["registry"]
    # genus derived from taxonomy first token, NOT the old Genus->ecology_source mis-read
    assert reg["AS-900"]["genus"] == "Streptomyces"
    assert reg["AS-902"]["genus"] == "Nocardia"
    assert reg["AS-900"]["genus"] != "Apis mellifera gut"   # the exact old-bug value
    # host from ecology_source -> host_group
    assert reg["AS-900"]["host_group"] == "Apis"
    assert reg["AS-902"]["host_group"] == "Bombus"
    # kcb_top read from the real column: exactly two empty hits are fully-dark
    assert sum(b["fully_dark"] for b in M["bgcs"]) == 2
    # dark_or_unresolved adds the bare "Streptomyces sp. genome" ref -> 3
    assert sum(b["dark_or_unresolved"] for b in M["bgcs"]) == 3
    # products read from the real column (a coordinate/int would never contain 'lassopeptide')
    assert any(b["products"] == "lassopeptide" for b in M["bgcs"])


def test_differentiating_reads_real_products(tmp_path):
    """COH-02/§5: the cohort-unique lead is the lassopeptide carried only by AS-902."""
    p = tmp_path / "real_master.xlsx"
    _build_real_master(p)
    M = load_master(p)
    assert differentiating_capacities(M["prevalence"]) == ["lassopeptide"]


def test_write_synthesis_on_real_master(tmp_path):
    """End-to-end on the shipped schema: composition + §5 lead + genus resolve to real values."""
    p = tmp_path / "real_master.xlsx"
    _build_real_master(p)
    syn = write_synthesis(p, novelty_basis="fully_dark")
    assert "Streptomyces" in syn and "Nocardia" in syn
    assert "lassopeptide" in syn
    assert "(*not*," not in syn and "ecology_source" not in syn


def test_coh05_non_allowlisted_host_bias_reports(tmp_path):
    """COH-05: NRPS is 100% Apis-associated across 4 BGCs. The old `top in (Bombus, Attine)`
    allowlist made this structurally unreportable; now §3 must surface it."""
    p = tmp_path / "real_master.xlsx"
    _build_real_master(p)
    syn = write_synthesis(p, novelty_basis="fully_dark")
    # §3 host-biased section now reports the Apis specialization
    assert "Apis-associated" in syn
    assert "No class exceeded the 55% host-bias threshold" not in syn


def test_foreign_capitalized_schema_refuses(tmp_path):
    """COH-02: a master carrying the OLD capitalized headers (Genus/Host_Source/Products/
    KCB_Top_Hit) must RAISE now that positional fallbacks are gone — never silently mis-read."""
    import openpyxl
    p = tmp_path / "foreign_master.xlsx"
    wb = openpyxl.Workbook()
    reg = wb.active; reg.title = "A2_Strain_Registry"
    reg.append(["strain", "taxonomy", "Genus", "Host_Source"])   # missing ecology_source
    reg.append(["AS-900", "sp.", "Streptomyces", "Bombus"])
    b2 = wb.create_sheet("B2_Product_Class_Matrix")
    b2.append(["strain", "NRPS", "counts_reliability"]); b2.append(["AS-900", 1, "ok"])
    b1 = wb.create_sheet("B1_BGC_Master")
    b1.append(["strain", "Products", "KCB_Top_Hit"])
    b1.append(["AS-900", "NRPS", ""])
    wb.save(p)
    with pytest.raises(RuntimeError):
        write_synthesis(p, novelty_basis="fully_dark")
