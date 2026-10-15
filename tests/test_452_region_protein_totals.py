"""Card attine_452_region_protein_totals: tools/region_protein_totals.py, the B03 per-genome amino-acid totals.

Protein in antiSMASH regions per genome with saccharide-only regions left out (the bee and moss Fig. 3B measure);
CDS without a translation are counted, not guessed. Synthetic ZIPs only (SYN-* records).
"""
import csv
import importlib.util
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/region_protein_totals.py"
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("region_protein_totals_t", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

GBK = """LOCUS       {rec}               100 bp    DNA     linear   UNK 01-JAN-1980
FEATURES             Location/Qualifiers
     region          1..100
{products}
{cds}ORIGIN
        1 acgt
//
"""


def cds(translation=None):
    q = f'                     /translation="{translation}"\n' if translation else '                     /locus_tag="SYN_x"\n'
    return "     CDS             1..9\n" + q


def make_zip(path, strictness, regions):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(f"{path.stem}.json", '{"records": [], "strictness": "%s"}' % strictness)
        for i, (products, translations) in enumerate(regions, 1):
            prod = "\n".join(f'                     /product="{p}"' for p in products)
            zf.writestr(f"SYN-REC-{i}.region001.gbk", GBK.format(rec=f"SYN-REC-{i}", products=prod,
                                                                 cds="".join(cds(t) for t in translations)))
    return path


def run(tmp_path, zips, strictness="loose"):
    out = tmp_path / "totals.tsv"
    rc = mod.main(["--zips", *map(str, zips), "--strictness", strictness, "--out", str(out)])
    return rc, ({r["strain"]: r for r in csv.DictReader(out.open(), delimiter="\t")} if rc == 0 else None)


def test_saccharide_only_regions_are_left_out_and_missing_translations_counted(tmp_path):
    z = make_zip(tmp_path / "SYN-971.zip", "loose", [(["T1PKS"], ["MKV", "MAAAA", None]), (["saccharide"], ["MAAA"]),
                                                     (["saccharide", "NRPS"], ["MK"])])
    rc, rows = run(tmp_path, [z])
    r = rows["SYN-971"]
    assert rc == 0
    assert (r["regions"], r["saccharide_only_regions"], r["cds"], r["missing_CDS_lengths"]) == ("3", "1", "5", "1")
    assert (r["amino_acids_all_regions"], r["amino_acids"]) == ("14", "10")


def test_mixed_strictness_is_refused(tmp_path):
    a = make_zip(tmp_path / "SYN-971.zip", "loose", [(["T1PKS"], ["MKV"])])
    b = make_zip(tmp_path / "SYN-972.zip", "relaxed", [(["T1PKS"], ["MKV"])])
    rc, _ = run(tmp_path, [a, b])
    assert rc == 2 and not (tmp_path / "totals.tsv").exists()


def test_two_zips_for_one_strain_are_refused(tmp_path):
    (tmp_path / "x").mkdir()
    a = make_zip(tmp_path / "SYN-971.zip", "loose", [(["T1PKS"], ["MKV"])])
    b = make_zip(tmp_path / "x" / "SYN-971.zip", "loose", [(["T1PKS"], ["MKV"])])
    rc, _ = run(tmp_path, [a, b])
    assert rc == 2
