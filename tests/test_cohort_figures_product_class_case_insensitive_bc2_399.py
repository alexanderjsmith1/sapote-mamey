"""BC2 .399 audit (CORRECTED v2 — see PATCH_CARD.md). mamey/cohort_figures.py's F03
product-class heatmap keys its `pc` lookup by the raw, unmodified antiSMASH Products token,
with no case normalization. This is HARDENING against a mixed-case cohort (an older/
differently-configured antiSMASH run, or future casing drift) — NOT a fix for a demonstrated
defect on current-engine data: verified directly against a real engine-1.9.142 board
(AS-705 strict, September 1 2026 Claude/MAMEY_RUNS_engine1.9.142_2026-09-01/) that real
Products tokens are already canon-cased and match the `keep` allowlist's own casing exactly.
The original v1 fix's premise (lowercase real-world tokens) was WRONG, caught by independent
peer review — corrected here.

The v1 fix ALSO had a real, independent code defect (also peer-caught): its
`pc_ci = {k.lower(): v for k, v in pc.items()}` dict comprehension REPLACES on a case
collision rather than merging, so a genuinely mixed-case cohort (the exact scenario this
hardening exists for) would silently drop one spelling's entire per-strain count dict --
exactly the class of data loss this patch exists to prevent. This file now proves the
corrected merge behavior directly.
"""
import csv
import json
import os

import pytest

mpl = pytest.importorskip("matplotlib")
np = pytest.importorskip("numpy")
from mamey import cohort_figures as cf

# Measured slow on the v9.7.417 seal (>=2s for this file alone; see the INDIGO_418 timing table).
# Marked explicitly rather than inferred from the filename, so the fast partition is defined by
# measurement and a rename cannot silently change what runs.
pytestmark = pytest.mark.slow


def _make_pkg(root, sid, tier, release, taxonomy, products, n_bgc=4):
    """Same synthetic gold package as tests/test_cohort_figures_v9792.py::_make_pkg, with a
    caller-supplied Products list so different tests can exercise different casings."""
    pkg = os.path.join(root, sid, "package")
    os.makedirs(pkg, exist_ok=True)
    bgc_profile, domain_hits, active_sites, substrates, domain_arch = [], [], [], [], []
    triggers = ["T43-HAL_halogenase", "T43-LAN_lanthipeptide", "T43-THA_thioamide"]
    tiers = ["NULL_NO_SOURCE_DERIVED_RESISTANCE", "T3_TRANSPORTER_ONLY_ROUTING",
             "T2_RESISTANCE_LIKE_SOURCE_DERIVED", "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED"]
    for i in range(n_bgc):
        bid = f"BGC{i+1:03d}"
        bgc_profile.append({
            "sid": sid, "bgc_id": bid, "resistance_tier": tiers[i % len(tiers)],
            "cctt_triggers": triggers[i % len(triggers)],
            "PKS_KS": i % 3, "PKS_AT": i % 2, "PKS_KR": (i + 1) % 2, "PKS_DH": i % 2,
            "NRPS_C": i % 2, "NRPS_A": (i + 1) % 3, "NRPS_T_PCP": i % 2,
            "TE_release": i % 2, "Transporter": i % 2, "Regulator": (i + 1) % 2,
            "Oxidoreductase": i % 2,
        })
        domain_arch.append({"bgc_id": bid, "architecture": repr({"domain_counts": {
            "PKS_KS": i % 3, "PKS_AT": i % 2, "PKS_KR": (i + 1) % 2, "PKS_DH": i % 2,
            "NRPS_C": i % 2, "NRPS_A": (i + 1) % 3, "NRPS_T_PCP": i % 2, "TE_release": i % 2}})})
        active_sites.append({"domain_id": f"ctg{i+1}_1_PKS_KS", "locus": f"ctg{i+1}_1",
                             "active_site_calls": "His: True, Cys: False"})
        substrates.append({"domain_id": f"ctg{i+1}_1_AMP-binding", "substrate": ["ala", "val", "ser"][i % 3]})
        substrates.append({"domain_id": f"ctg{i+1}_2_PKS_AT", "substrate": ["mal", "mmal"][i % 2]})
    for p in ["PKS_KS", "AMP-binding", "Condensation", "Trp_halogenase", "Glyco_hydro_18",
              "ABC_tran", "MFS_1", "TetR_N", "GntR", "IucA_IucC", "FhuF", "LANC_like"]:
        for _ in range(3):
            domain_hits.append({"pfam": p, "tier1": p in ("PKS_KS", "AMP-binding", "Condensation")})
    json.dump({"bgc_profile": bgc_profile, "domain_hits": domain_hits, "active_sites": active_sites},
              open(os.path.join(pkg, "deep_data.json"), "w"))
    json.dump({"substrates": substrates, "domain_arch": domain_arch, "ripp": [{"family": "lanthipeptides"}]},
              open(os.path.join(pkg, "gene_data.json"), "w"))
    json.dump({"assembly_tier": tier, "raw_bgcs": n_bgc, "corrected_bgcs": n_bgc,
               "release": release, "taxonomy": taxonomy},
              open(os.path.join(pkg, "manifest_short.json"), "w"))
    with open(os.path.join(pkg, f"{sid}_2_inventory.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Products"])
        for i in range(n_bgc):
            w.writerow([f"BGC{i+1:03d}", products[i % len(products)]])
    return pkg


def test_mixed_case_cohort_merges_not_replaces(tmp_path):
    """The consequential proof of the CORRECTED fix: a cohort where one strain's board uses
    'NRPS' and another (older/differently-cased) board uses 'nrps' for the same class must
    have BOTH strains' counts summed into one row, not one spelling silently dropped."""
    runs = tmp_path / "runs"
    _make_pkg(str(runs), "SID9097", "GOOD", "PUBLIC", "Streptomyces sp.",
              products=["NRPS", "terpene", "saccharide"], n_bgc=3)
    _make_pkg(str(runs), "SID9096", "GOOD", "PUBLIC", "Streptomyces sp.",
              products=["nrps", "terpene", "saccharide"], n_bgc=3)
    out = tmp_path / "figs"
    res = cf.generate(runs_dir=str(runs), out=str(out))
    assert res["figures"] >= 1, res

    import glob
    matches = glob.glob(str(out / "*product_class_heatmap_data.csv"))
    assert matches, f"sidecar not produced; files present: {os.listdir(out)}"
    with open(matches[0]) as f:
        rows = list(csv.reader(f))
    header = rows[0]
    nrps_rows = [r for r in rows[1:] if r and r[0].lower() == "nrps"]
    assert len(nrps_rows) == 1, f"expected exactly one merged NRPS row, got: {nrps_rows}"
    # both strains contributed 1 NRPS-class BGC each; a correct merge shows both counts,
    # not one strain's column silently zeroed by a dropped spelling.
    row = dict(zip(header, nrps_rows[0]))
    for sid in ("SID9096", "SID9097"):
        assert sid in row, f"strain column {sid} missing from sidecar header: {header}"
        assert int(float(row[sid])) >= 1, (
            f"strain {sid}'s NRPS count was dropped by a case-collision replace instead of "
            f"merge: row={row}"
        )


def test_canon_cased_real_data_still_shows_all_classes(tmp_path):
    """No regression: real-shaped canon-cased data (matching what current-engine boards
    actually emit) still populates the figure correctly."""
    runs = tmp_path / "runs"
    _make_pkg(str(runs), "SID9099", "GOOD", "PUBLIC", "Streptomyces sp.",
              products=["NRPS", "T1PKS", "T2PKS", "T3PKS", "terpene", "saccharide"], n_bgc=6)
    _make_pkg(str(runs), "SID9098", "GOOD", "PUBLIC", "Streptomyces sp.",
              products=["NRPS", "T1PKS", "T2PKS", "T3PKS", "terpene", "saccharide"], n_bgc=5)
    out = tmp_path / "figs"
    res = cf.generate(runs_dir=str(runs), out=str(out))
    assert res["figures"] >= 1, res

    import glob
    matches = glob.glob(str(out / "*product_class_heatmap_data.csv"))
    assert matches
    rows = [r[0] for r in csv.reader(open(matches[0])) if r]
    row_labels_upper = {r.upper() for r in rows}
    for c in ("NRPS", "T1PKS", "T2PKS", "T3PKS"):
        assert c in row_labels_upper, f"canon-cased real class {c} missing from rows: {rows}"
