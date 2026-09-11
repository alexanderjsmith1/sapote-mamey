"""v9.7.92 smoke test: mamey.cohort_figures emits the gold gene/domain figure suite.

Builds minimal synthetic gold packages (no antiSMASH/scipy required) and asserts the
module produces PNG + sidecar CSV outputs for both multi-strain and single-strain modes,
and that PUBLIC/PRIVATE ordering puts AS-* last.
"""
import json, csv, glob, os
import pytest

mpl = pytest.importorskip("matplotlib")
np = pytest.importorskip("numpy")
from mamey import cohort_figures as cf

# Measured slow on the v9.7.417 seal (>=2s for this file alone; see the INDIGO_418 timing table).
# Marked explicitly rather than inferred from the filename, so the fast partition is defined by
# measurement and a rename cannot silently change what runs.
pytestmark = pytest.mark.slow


def _arch(dc):
    return {"bgc_id": dc["bgc_id"], "architecture": repr({"domain_counts": dc["counts"]})}


def _make_pkg(root, sid, tier, release, taxonomy, n_bgc=4):
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
        domain_arch.append(_arch({"bgc_id": bid, "counts": {
            "PKS_KS": i % 3, "PKS_AT": i % 2, "PKS_KR": (i + 1) % 2, "PKS_DH": i % 2,
            "NRPS_C": i % 2, "NRPS_A": (i + 1) % 3, "NRPS_T_PCP": i % 2, "TE_release": i % 2}}))
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
        w = csv.writer(fh); w.writerow(["BGC_ID", "Products"])
        for i in range(n_bgc):
            w.writerow([f"BGC{i+1:03d}", ["terpene", "NRPS", "T1PKS", "RiPP"][i % 4]])
    return pkg


def test_cohort_figures_multi(tmp_path):
    runs = tmp_path / "runs"
    _make_pkg(str(runs), "SID9001", "GOOD", "PUBLIC", "Streptomyces sp.", 5)
    _make_pkg(str(runs), "AS-901", "POOR", "PRIVATE", "Micromonospora sp.", 4)
    out = tmp_path / "figs"
    res = cf.generate(runs_dir=str(runs), out=str(out))
    assert res["figures"] >= 10, res
    # v9.7.222: public/private split retired (AS cohort public) — axis is now ascending strain number.
    # AS-901 (901) sorts before SID9001 (9001), so no more "PRIVATE last".
    import re as _re
    nums = [int(_re.search(r"(\d+)", s).group(1)) for s in res["strains"]]
    assert nums == sorted(nums), res["strains"]        # ascending strain number
    assert len(glob.glob(f"{out}/*.png")) == res["figures"]
    assert len(glob.glob(f"{out}/*.svg")) == res["figures"]
    receipt_rows = [json.loads(line) for line in (out / "figure_receipts.jsonl").read_text().splitlines()]
    assert len(receipt_rows) == res["figures"]
    assert len(glob.glob(f"{out}/*_data.csv")) >= res["figures"]      # every figure has a sidecar


def test_cohort_figures_single(tmp_path):
    runs = tmp_path / "runs"
    _make_pkg(str(runs), "AS-902", "VERY_POOR", "PRIVATE", "Streptomyces sp.", 6)
    out = tmp_path / "figs1"
    res = cf.generate(runs_dir=str(runs), out=str(out), strains=["AS-902"])
    assert res["figures"] >= 1, res
    assert glob.glob(f"{out}/*AS-902*perBGC_domain_heatmap.png")


def test_cohort_figures_public_only(tmp_path):
    runs = tmp_path / "runs"
    _make_pkg(str(runs), "SID9002", "GOOD", "PUBLIC", "Streptomyces sp.", 4)
    _make_pkg(str(runs), "AS-903", "POOR", "PUBLIC", "Streptomyces sp.", 4)   # v9.7.229: AS- is public now
    _make_pkg(str(runs), "AJS-1", "POOR", "PRIVATE", "Streptomyces sp.", 4)   # genuinely unpublished series
    out = tmp_path / "figs_pub"
    res = cf.generate(runs_dir=str(runs), out=str(out), public_only=True)
    # AS- and SID are public and kept; only the AJS-/PENDING- series is filtered out
    assert "AJS-1" not in res["strains"], res["strains"]
    assert any(s.startswith("AS-") for s in res["strains"]) and any(s.startswith("SID") for s in res["strains"]), res["strains"]
