"""Tests for the assembly-line report layer (roadmap #6, report half). Freeze-safe report over
the native _domains.csv."""
import csv

try:
    from mamey import assembly_line as al
except ImportError:
    import assembly_line as al


def _write_domains(path, rows):
    cols = ["bgc_id", "locus_tag", "feature_type", "domain", "pfam_acc", "database",
            "start", "end", "strand", "bitscore", "evalue", "substrate"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            d = {c: "" for c in cols}
            d["feature_type"] = "aSDomain"
            d.update(r)
            w.writerow(d)


def _dom(**kw):
    d = {"feature_type": "aSDomain", "bgc_id": "BGC", "locus_tag": "ctg_1", "domain": "", "substrate": "", "start": "0"}
    d.update(kw)
    return d


def test_gpa_heptapeptide_is_class_consistent():
    # 5+ Hpg/dHpg A-domains + an epimerization -> GPA-aglycone-consistent
    doms = []
    subs = ["Hpg", "Dhpg", "bOH-Tyr", "Hpg", "Dhpg", "Tyr"]
    for i, s in enumerate(subs):
        doms.append(_dom(bgc_id="BGC1", locus_tag=f"ctg1_{i}", domain="AMP-binding",
                         substrate=s, start=str(i * 100)))
    doms.append(_dom(bgc_id="BGC1", locus_tag="ctg1_9", domain="Epimerization", start="999"))
    a = al.assembly_for_bgc(doms)
    assert len(a["monomers"]) == 6
    assert "GPA-aglycone-consistent" in a["class_consistency"]
    assert a["epim"] == 1


def test_modular_polyketide_is_class_consistent():
    doms = []
    for i in range(6):
        doms.append(_dom(bgc_id="BGC2", locus_tag=f"ctg2_{i}", domain="PKS_KS", start=str(i * 100)))
        doms.append(_dom(bgc_id="BGC2", locus_tag=f"ctg2_{i}", domain="PKS_AT",
                         substrate="mal", start=str(i * 100 + 10)))
    doms.append(_dom(bgc_id="BGC2", locus_tag="ctg2_9", domain="Thioesterase", start="9999"))
    a = al.assembly_for_bgc(doms)
    assert a["n_ks"] == 6 and a["te"] == 1
    assert "modular-polyketide-consistent" in a["class_consistency"]


def test_bare_terpene_has_no_assembly_line(tmp_path):
    dcsv = tmp_path / "SYN-1_domains.csv"
    _write_domains(dcsv, [{"bgc_id": "BGC3", "locus_tag": "ctg3_1", "domain": "Terpene_synth", "start": "1"}])
    res = al.run(str(tmp_path), out_dir=str(tmp_path))
    assert res["status"] == "ok" and res["bgcs"] == 0  # omitted (no A/AT/KS/C)


def test_run_emits_csv(tmp_path):
    dcsv = tmp_path / "SYN-2_domains.csv"
    rows = [{"bgc_id": "BGC4", "locus_tag": "ctg4_1", "domain": "PKS_KS", "start": "1"},
            {"bgc_id": "BGC4", "locus_tag": "ctg4_1", "domain": "PKS_AT", "substrate": "mmal", "start": "10"}]
    _write_domains(dcsv, rows)
    res = al.run(str(tmp_path), out_dir=str(tmp_path))
    assert res["status"] == "ok" and res["bgcs"] == 1
    out = tmp_path / "ASSEMBLY_LINES" / "SYN-2_assembly_lines.csv"
    assert out.exists()
    with open(out) as fh:
        r = [x for x in csv.DictReader((l for l in fh if not l.startswith("#")))]
    assert r[0]["extenders"] == "mmal"


def test_no_domains_csv_is_clean_skip(tmp_path):
    res = al.run(str(tmp_path), out_dir=str(tmp_path))
    assert res["status"] == "no_domains_csv"  # never an error
