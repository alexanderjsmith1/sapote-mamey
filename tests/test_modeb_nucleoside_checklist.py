"""test_modeb_nucleoside_checklist.py — the nucleoside class-content layer (v9.7.354).

Encodes the nucleoside class-content lesson: a 'nucleoside' locus must be treated as a nucleoside (not a RiPP),
and a nucleoside-antibiotic capacity call must NOT rest on a housekeeping tRNA-modification gene
(truD) or a bare 'nikJ' name. The checklist WARNs (CONTENT_GAP) when a card skips those concepts.
"""
from mamey.modeb_class_checklist import classes_for_products, check_class_content


def test_nucleoside_product_label_maps_to_nucleoside_key():
    assert "nucleoside" in classes_for_products("nucleoside; other")
    # hybrid label still triggers nucleoside
    assert "nucleoside" in classes_for_products("NRPS; nucleoside")


def test_thin_nucleoside_card_trips_housekeeping_and_subtype_gaps():
    # a card that over-calls nikkomycin from truD + a named nikJ, with no housekeeping distinction
    thin = (
        "This nucleoside locus carries nikJ and is a nikkomycin-like antifungal chitin synthase "
        "inhibitor. The truD gene supports the nucleoside class."
    )
    findings = check_class_content(thin, "nucleoside; other")
    concepts = {f["concept"] for f in findings}
    # the housekeeping-vs-secondary distinction is the key BGC008 lesson and must be flagged as missing
    assert any("housekeeping-vs-secondary" in c for c in concepts), concepts
    # all findings are advisory WARN, never blocking
    assert all(f["severity"] == "WARN" and f["code"] == "CONTENT_GAP" for f in findings)


def test_deep_nucleoside_card_has_no_gaps():
    deep = (
        "This is a nucleoside locus (nucleobase / ribosyl core formation), not a RiPP — no leader or "
        "precursor peptide. Subtype: a peptidyl-nucleoside; the polyoxin/nikkomycin chitin synthase "
        "inhibitor mechanism is antifungal CLASS context only (contrast the capuramycin/muraymycin "
        "translocase MraY inhibitors, antibacterial). Housekeeping-vs-secondary: the truD "
        "tRNA-pseudouridine synthase is primary metabolism and is necessary-not-sufficient — the "
        "capacity call does not rest on a tRNA-modification gene alone. Tailoring: 2OG-Fe(II) "
        "oxygenase, aminotransferase, a radical-SAM (nikJ), and an ATP-grasp amide-bond ligase. "
        "Self-resistance/immunity: an antibacterial nucleoside inhibiting an ESSENTIAL producer "
        "target (translocase-I/MraY) is expected to co-encode a resistant target paralog or a "
        "dedicated exporter; a chitin-synthase-inhibitor antifungal has no essential producer target."
    )
    findings = check_class_content(deep, "nucleoside; other")
    nuc_gaps = [f for f in findings if f["class"] == "nucleoside"]
    assert nuc_gaps == [], nuc_gaps


def test_nucleoside_addition_does_not_disturb_existing_classes():
    # a thioamide card is unaffected by the new nucleoside key
    assert "thioamide" in classes_for_products("NRPS; thioamide-NRP")
    assert "nucleoside" not in classes_for_products("NRPS; thioamide-NRP")


def test_nucleoside_card_missing_self_resistance_is_flagged():
    # v9.7.355: a card that addresses core/subtype/housekeeping/tailoring but NOT self-resistance
    # still trips the new self-resistance/immunity CONTENT_GAP (advisory WARN).
    no_sr = (
        "This is a nucleoside (ribosyl core formation), not a RiPP — no leader peptide. Subtype: a "
        "liponucleoside translocase/MraY inhibitor (antibacterial CLASS context). Housekeeping-vs-"
        "secondary: truD is primary metabolism, necessary-not-sufficient. Tailoring: radical-SAM, "
        "aminotransferase, 2OG-Fe(II) oxygenase."
    )
    findings = check_class_content(no_sr, "nucleoside; other")
    concepts = {f["concept"] for f in findings}
    assert any("self-resistance" in c for c in concepts), concepts
    assert all(f["severity"] == "WARN" and f["code"] == "CONTENT_GAP" for f in findings)
