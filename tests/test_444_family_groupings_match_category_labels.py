"""Figure and report groupings read antiSMASH families, so they do not move when products hold types only.

Up to .443 the parser appended antiSMASH's category word ("PKS", "NRPS", "RiPP", ...) to every region's products,
and groupings leaned on it: an arylpolyene or hglE-KS region counted as PKS, a NAPAA region as NRPS, a
lanthipeptide-class-i region as RiPP. The .444 parser keeps product types only. Each grouping below must give the
same answer for the old products (type plus category word) as for the types alone, for every type antiSMASH uses.
"""
import csv
from types import SimpleNamespace

import pytest

from mamey import (activity_lead_genes, cohort_figures, cohort_figures_extended, compile_report,
                   enrichment_sections, figure_policy, lead_pages, length_weighted, master_workbook,
                   p450_tailoring, source_scans)
from mamey.class_architecture import ANTISMASH_PRODUCT_CATEGORY, with_family_labels
from mamey.models import BGCRecord

LABEL = {"nrps": "NRPS", "pks": "PKS", "ripp": "RiPP", "terpene": "terpene", "saccharide": "saccharide",
         "other": "other"}
# each type alone, and each type with saccharide (the pure-saccharide figure rule and sugar arms)
CASES = [[t] for t in sorted(ANTISMASH_PRODUCT_CATEGORY)] + \
        [[t, "saccharide"] for t in sorted(ANTISMASH_PRODUCT_CATEGORY) if t != "saccharide"]


def old_products(types):
    """Products as the .443 parser wrote them: the types, then each category word once (antiSMASH writes the NRPS
    type and the NRPS category the same way, so they were one entry)."""
    out = list(types)
    for t in types:
        word = LABEL[ANTISMASH_PRODUCT_CATEGORY[t]]
        if word.lower() not in {p.lower() for p in out}:
            out.append(word)
    return out


def ids(case):
    return "+".join(case)


def test_labels_are_antismash_category_words():
    assert with_family_labels(["T1PKS", "NRPS"]) == ["T1PKS", "NRPS", "PKS"]
    assert with_family_labels("arylpolyene;NAPAA") == ["arylpolyene", "NAPAA", "PKS", "NRPS"]
    assert with_family_labels(None) == []


@pytest.mark.parametrize("types", CASES, ids=ids)
def test_string_groupings(types):
    old, new = ";".join(old_products(types)), ";".join(types)
    assert p450_tailoring._scaffold_of(new) == p450_tailoring._scaffold_of(old)
    assert lead_pages.classify("", "", new) == lead_pages.classify("", "", old)
    assert cohort_figures_extended.norm_arch(new) == cohort_figures_extended.norm_arch(old)
    assert activity_lead_genes._source_classes(new) == activity_lead_genes._source_classes(old)
    assert figure_policy.is_pure_saccharide(new) == figure_policy.is_pure_saccharide(old)
    assert bool(enrichment_sections.emit_peptide_precursor([], new)) == \
        bool(enrichment_sections.emit_peptide_precursor([], old))
    lw_new, lw_old = (length_weighted.nominal_length_profile(t) for t in (types, old_products(types)))
    assert lw_new["nominal_bp"] == lw_old["nominal_bp"]
    # a type that the category word used to map keeps a family (the type's own alias may now name it)
    assert (lw_new["nominal_basis_family"] == "UNMAPPED") == (lw_old["nominal_basis_family"] == "UNMAPPED")


def _bgc(i, products):
    return BGCRecord(bgc_id=f"BGC{i:03d}", contig=f"c{i}", region_number=1, start=1, end=10_000,
                     contig_length=50_000, products=list(products))


def test_ripp_maturation_scan():
    new = [_bgc(i, t) for i, t in enumerate(CASES, 1)]
    old = [_bgc(i, old_products(t)) for i, t in enumerate(CASES, 1)]
    verdicts = lambda bgcs: {k: v["needs_maturation"] for k, v in source_scans.scan_umed([], bgcs)["per_bgc"].items()}
    assert verdicts(new) == verdicts(old)


def test_workbook_category_columns():
    def row(products_per_region):
        run = SimpleNamespace(bgcs=[_bgc(i, p) for i, p in enumerate(products_per_region, 1)],
                              context=SimpleNamespace(strain_id="S1"), source_scans=None)
        return master_workbook._b2_product_class_rows(run, "OK")[0]
    assert row(CASES) == row([old_products(t) for t in CASES])


def _inventory(folder, cases, product_col="Products"):
    folder.mkdir()
    with open(folder / "S1_2_inventory.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", product_col])
        w.writerows([f"BGC{i:03d}", ";".join(p)] for i, p in enumerate(cases, 1))
    return folder


def test_figure_product_rows(tmp_path):
    counts = lambda pkg: {k: dict(v) for k, v in cohort_figures.products_per_strain({"S1": {"pkg": str(pkg)}},
                                                                                    ["S1"]).items()}
    new = counts(_inventory(tmp_path / "new", CASES))
    old = counts(_inventory(tmp_path / "old", [old_products(t) for t in CASES]))
    assert new == old


def test_fermentation_draft(tmp_path):
    def draft(folder, cases):
        folder.mkdir()
        with open(folder / "S1_4_triage_board.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["BGC_ID", "Products"])
            w.writerows([f"BGC{i:03d}", ";".join(p)] for i, p in enumerate(cases, 1))
        return compile_report._fermentation_draft(folder)
    for types in (["arylpolyene"], ["NAPAA"], ["lanthipeptide-class-i"], ["hglE-KS", "NAPAA"]):
        assert draft(tmp_path / f"n_{ids(types)}", [types]) == draft(tmp_path / f"o_{ids(types)}",
                                                                    [old_products([t.lower() for t in types])])


def _tool(name):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_family_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_class_labels():
    inventory = _tool("build_inventory_table")
    leads = _tool("render_activity_lead_reports")
    for types in CASES:
        old, new = ";".join(old_products(types)), ";".join(types)
        assert leads._primary_class(new) == leads._primary_class(old), types
        if "napaa" not in types:   # NAPAA stays excluded in the inventory table (2026-09-27)
            assert inventory.headline_class(new) == inventory.headline_class(old), types


def test_cohort_tool_classes():
    size = _tool("build_size_profile")
    sugar = _tool("build_saccharide_triage")
    readiness = _tool("build_metabolomics_readiness")
    vignettes = _tool("build_thesis_vignettes")
    for types in CASES:
        old, new = ";".join(old_products(types)), ";".join(types)
        row = lambda p: {"sid": "S1", "bgc_id": "BGC001", "products": p, "length_kb": 20}
        assert size._primary(row(new)) == size._primary(row(old)), types
        # GCF tags show the type and bucket it on its own (test_444_gcf_tags_and_napaa_housekeeping.py);
        # the saccharide triage no longer reads NAPAA as an NRPS backbone
        if "napaa" not in types:
            assert sugar.classify(row(new)) == sugar.classify(row(old)), types
        assert readiness.base_class(new, "") == readiness.base_class(old, ""), types
        assert vignettes.size_context("S1", "BGC001", [row(new)])["class"] == \
            vignettes.size_context("S1", "BGC001", [row(old)])["class"], types
