"""v9.7.93 smoke test: cohort_figures G-series, D-series, --series all, and base captions.

Builds richer synthetic gold packages (inventory with Boundary/Length_kb/KCB/Node_ID, and
bgc_profile with tta_codons + rare cctt_triggers) and asserts the G/D generators and the
caption writer run end-to-end without antiSMASH or scipy.
"""
import json, csv, glob, os
import pytest

pytest.importorskip("matplotlib")
np = pytest.importorskip("numpy")
from mamey import cohort_figures as cf

# Measured slow on the v9.7.417 seal (>=2s for this file alone; see the INDIGO_418 timing table).
# Marked explicitly rather than inferred from the filename, so the fast partition is defined by
# measurement and a rename cannot silently change what runs.
pytestmark = pytest.mark.slow


def _make_pkg(root, sid, tier, release, taxonomy, n_bgc=8):
    pkg = os.path.join(root, sid, "package"); os.makedirs(pkg, exist_ok=True)
    bgc_profile, domain_hits, active_sites, substrates, domain_arch = [], [], [], [], []
    rare = ["T43-DKP_cdps", "T43-IDC_indolocarbazole", "T43-LASSO_lassopeptide",
            "T43-NUC_nucleoside", "T43-HAL_halogenase", "T43-LAN_lanthipeptide"]
    rtiers = ["NULL_NO_SOURCE_DERIVED_RESISTANCE", "T3_TRANSPORTER_ONLY_ROUTING",
              "T2_RESISTANCE_LIKE_SOURCE_DERIVED", "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED"]
    for i in range(n_bgc):
        bid = f"BGC{i+1:03d}"
        bgc_profile.append({
            "sid": sid, "bgc_id": bid, "resistance_tier": rtiers[i % 4],
            "cctt_triggers": rare[i % len(rare)], "total_domains": 5 + 3 * i,
            "tta_codons": i % 5, "tta_cds": i % 5,
            "PKS_KS": i % 3, "PKS_AT": i % 2, "PKS_KR": (i + 1) % 2, "PKS_DH": i % 2,
            "NRPS_C": i % 4, "NRPS_A": (i + 1) % 3, "NRPS_T_PCP": i % 2,
            "TE_release": i % 2, "Transporter": i % 2, "Regulator": (i + 1) % 2, "Oxidoreductase": i % 2})
        domain_arch.append({"bgc_id": bid, "architecture": repr({"domain_counts": {
            "PKS_KS": i % 3, "PKS_AT": i % 2, "PKS_KR": (i + 1) % 2, "NRPS_C": i % 4,
            "NRPS_A": (i + 1) % 3, "TE_release": i % 2}})})
        active_sites.append({"domain_id": f"ctg{i+1}_1_PKS_KS", "locus": f"ctg{i+1}_1",
                             "active_site_calls": "His: True, Cys: False"})
        substrates.append({"domain_id": f"ctg{i+1}_1_AMP-binding", "substrate": ["ala", "val", "ser"][i % 3]})
        substrates.append({"domain_id": f"ctg{i+1}_2_PKS_AT", "substrate": ["mal", "mmal"][i % 2]})
    for p in ["PKS_KS", "AMP-binding", "Condensation", "Trp_halogenase", "Glyco_hydro_18",
              "ABC_tran", "MFS_1", "TetR_N", "GntR", "LysR_substrate", "MarR_2", "Sigma70_r2",
              "HTH_1", "IucA_IucC", "FhuF", "p450", "FAD_binding_3", "NAD_binding_4", "adh_short",
              "Radical_SAM", "Glycos_transf_1", "Methyltransf_2", "polyprenyl_synt", "LANC_like"]:
        for _ in range(3):
            domain_hits.append({"pfam": p, "tier1": p in ("PKS_KS", "AMP-binding", "Condensation")})
    json.dump({"bgc_profile": bgc_profile, "domain_hits": domain_hits, "active_sites": active_sites},
              open(os.path.join(pkg, "deep_data.json"), "w"))
    json.dump({"substrates": substrates, "domain_arch": domain_arch, "ripp": [{"family": "lanthipeptides"}]},
              open(os.path.join(pkg, "gene_data.json"), "w"))
    json.dump({"assembly_tier": tier, "raw_bgcs": n_bgc, "corrected_bgcs": n_bgc * 0.6,
               "release": release, "taxonomy": taxonomy},
              open(os.path.join(pkg, "manifest_short.json"), "w"))
    json.dump({"taxonomy": taxonomy}, open(os.path.join(pkg, f"{sid}_1_intake.json"), "w"))
    bnd = ["Interior", "Edge", "Full-contig"]
    with open(os.path.join(pkg, f"{sid}_2_inventory.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Products", "Boundary", "Length_kb", "KCB_top", "KCB_score", "Node_ID", "Contig"])
        for i in range(n_bgc):
            kcb_top = "" if i % 3 == 0 else f"BGC000{i}.1 | ref"
            kcb_score = "" if i % 3 == 0 else str(1000 + i * 800)
            w.writerow([f"BGC{i+1:03d}", ["terpene", "NRPS", "T1PKS", "RiPP", "saccharide", "NI-siderophore"][i % 6],
                        bnd[i % 3], round(5 + i * 3.5, 1), kcb_top, kcb_score,
                        f"NODE_{i+1}_length_{10000+i}_cov_50", f"NODE_{i+1}"])
    return pkg


def test_series_G(tmp_path):
    runs = tmp_path / "runs"
    _make_pkg(str(runs), "SID9001", "GOOD", "PUBLIC", "Streptomyces sp.")
    _make_pkg(str(runs), "AS-901", "POOR", "PRIVATE", "Saccharopolyspora sp.")
    out = tmp_path / "g"
    res = cf.generate(runs_dir=str(runs), out=str(out), series="G")
    assert len(glob.glob(f"{out}/G*.png")) >= 12, res
    assert os.path.exists(f"{out}/figure_captions.md")


def test_series_D(tmp_path):
    runs = tmp_path / "runs"
    _make_pkg(str(runs), "SID9002", "GOOD", "PUBLIC", "Streptomyces sp.")
    _make_pkg(str(runs), "AS-902", "VERY_POOR", "PRIVATE", "Micromonospora sp.")
    out = tmp_path / "d"
    res = cf.generate(runs_dir=str(runs), out=str(out), series="D")
    assert len(glob.glob(f"{out}/D*.png")) >= 9, res


def test_series_all_and_captions(tmp_path):
    runs = tmp_path / "runs"
    _make_pkg(str(runs), "SID9003", "GOOD", "PUBLIC", "Streptomyces sp.")
    _make_pkg(str(runs), "AS-903", "POOR", "PRIVATE", "Saccharopolyspora sp.")
    out = tmp_path / "all"
    res = cf.generate(runs_dir=str(runs), out=str(out), series="all")
    nF = len(glob.glob(f"{out}/F*.png")); nG = len(glob.glob(f"{out}/G*.png")); nD = len(glob.glob(f"{out}/D*.png"))
    assert nF >= 10 and nG >= 12 and nD >= 9, (nF, nG, nD)
    cap = open(f"{out}/figure_captions.md").read()
    assert "TetR" in cap and "KnownClusterBlast" in cap and "bldA" in cap   # glossary present


def test_generate_reports_caption_write_failure(tmp_path, monkeypatch):
    """A missing author-facing caption sidecar cannot be reported as an unqualified success."""
    monkeypatch.setattr(cf, "_HAVE_MPL", True)
    monkeypatch.setattr(cf, "load", lambda *_args, **_kwargs: {"AS-XXX": {}})
    monkeypatch.setattr(cf, "order_strains", lambda *_args, **_kwargs: ["AS-XXX"])
    monkeypatch.setattr(cf, "figs_single", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        cf, "write_captions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("caption output unavailable")),
    )

    result = cf.generate(runs_dir=str(tmp_path), out=str(tmp_path / "figures"), series="F")

    assert result["caption_status"] == "ERRORED"
    assert "caption output unavailable" in result["caption_error"]


def test_generate_reports_written_caption_sidecar(tmp_path, monkeypatch):
    """Negative control: a real caption sidecar remains reported as written."""
    monkeypatch.setattr(cf, "_HAVE_MPL", True)
    monkeypatch.setattr(cf, "load", lambda *_args, **_kwargs: {"AS-XXX": {}})
    monkeypatch.setattr(cf, "order_strains", lambda *_args, **_kwargs: ["AS-XXX"])
    monkeypatch.setattr(cf, "figs_single", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cf, "write_captions", lambda out, _files: f"{out}/figure_captions.md")

    result = cf.generate(runs_dir=str(tmp_path), out=str(tmp_path / "figures"), series="F")

    assert result["caption_status"] == "WRITTEN"
