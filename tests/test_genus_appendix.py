"""AF/AB by-genus appendix — report-only cohort reporting."""
import json
from mamey.genus_appendix import run, _genus_of, _match, AF_KEYWORDS, AB_KEYWORDS


def test_genus_parse():
    assert _genus_of("Streptomyces sp.") == "Streptomyces"
    assert _genus_of("Amycolatopsis sp. AS-846") == "Amycolatopsis"
    assert _genus_of("") == "Unknown"
    assert _genus_of("uncultured bacterium") == "Unknown"


def test_keyword_matching():
    assert "polyene" in _match("polyene macrolide", AF_KEYWORDS)
    assert "streptophenazine" in _match("streptophenazine B", AB_KEYWORDS)
    assert _match("terpene", AF_KEYWORDS) == []


def _pkg(tmp_path, strain, taxonomy, rows):
    pkg = tmp_path / strain / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain, "taxonomy": taxonomy, "release": "PRIVATE"}))
    header = "BGC_ID,Products,KCB_top,Boundary\n"
    body = "".join(f"{b},{p},{k},{bd}\n" for b, p, k, bd in rows)
    (pkg / f"{strain}_2_inventory.csv").write_text(header + body)
    return pkg


def test_run_flags_af_and_ab(tmp_path):
    _pkg(tmp_path, "AS-999", "Streptomyces sp.", [
        ("BGC001", "polyene", "candicidin", "Full-contig"),   # AF
        ("BGC002", "NRPS", "streptophenazine B", "Full-contig"),  # AB
        ("BGC003", "terpene", "hopene", "Interior"),          # neither -> excluded
    ])
    res = run(tmp_path, depth=3)
    assert res["packages"] == 1
    assert res["af_candidate_rows"] == 1
    assert res["ab_candidate_rows"] == 1
    assert "Streptomyces" in res["af_markdown"]
    assert "candicidin" in res["af_markdown"]
    assert "streptophenazine" in res["ab_markdown"]
    # claim-safety header present, no bioactivity claim
    assert "NOT claims of production" in res["af_markdown"]


def test_emits_files(tmp_path):
    _pkg(tmp_path, "AS-998", "Amycolatopsis sp.", [("BGC001", "polyene", "amphotericin", "Interior")])
    out = tmp_path / "appendix"
    res = run(tmp_path, out_dir=out, depth=3)
    assert (out / "GENUS_ANTIFUNGAL_APPENDIX.md").is_file()
    assert (out / "GENUS_ANTIBACTERIAL_APPENDIX.md").is_file()
    assert "Amycolatopsis" in (out / "GENUS_ANTIFUNGAL_APPENDIX.md").read_text()
