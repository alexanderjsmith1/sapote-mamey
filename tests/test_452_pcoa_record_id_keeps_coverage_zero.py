"""Synthetic coverage-token regression: retain the complete LOCUS identifier when a VERSION
field drops a zero after the coverage decimal point. Unrelated accession mismatches stay refused.
"""
import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("protein_pcoa_ordinate_452", ROOT / "tools" / "protein_pcoa_ordinate.py")
ppo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppo)

KS = ("MSEPIAIVGMACRLPGGVDSPESLWRLLAEGRDAVSEVPADRWDADALYDPDPDAPGKSYTRWGGFLDGVDGFDAAFFGISPREAAAMDPQQRLLLEVAWEALEDAGIAPDSL"
      "RGSRTGVFVGASSSDYAELLGRTGAGSDGYLGLGNAASVAAGRISYVLGLRGPSLSVDTACSSSLVAVHLACQSLRSGECDLALAGGVNLMLSPLTFVAFSKARALSPDGRCK"
      "AFSADADGYGRGEGAGVVVLKRLSDARRDGDRILAVVRGSAVNQDGASNGLTAPNGPAQQRVIRQALANAGLRPDQVDYVEAHGTGTRLGDPIEAGALAAVFGPHRPADRPLL"
      "LGSVKTNIGHLEAAAGIAGLIKVVLALRHGVLPPTLHLTEPNPYLDLDGSRLRLVTEPRPWPAGGRARRAGVSSFGFGGTNAHVVLEE")
FULL = "NODE_1_length_9000_cov_12.0034"        # LOCUS: the contig name every other table uses
SHORT = "NODE_1_length_9000_cov_12.34"        # VERSION as antiSMASH writes it: the 0 after the point is gone
ACC = "NZ_CP000001.1"                            # an accession record: unchanged by the rule


def region_gbk(locus, accession, version, tag):
    seq = "a" * 3000
    origin = "\n".join(f"{i + 1:>9} {seq[i:i + 60]}" for i in range(0, 3000, 60))
    return (f"LOCUS       {locus}  3000 bp    DNA     linear   UNK 01-JAN-1980\nDEFINITION  {locus}.\n"
            f"ACCESSION   {accession}\nVERSION     {version}\nFEATURES             Location/Qualifiers\n"
            f"     region          1..3000\n                     /product=\"T1PKS\"\n"
            f"     CDS             1..1500\n                     /locus_tag=\"{tag}\"\n                     /translation=\"{KS}\"\n"
            f"     aSDomain        1..1200\n                     /aSDomain=\"PKS_KS\"\n                     /aSTool=\"nrps_pks_domains\"\n"
            f"                     /domain_subtypes=\"Modular-KS\"\n                     /locus_tag=\"{tag}\"\n"
            f"                     /translation=\"{KS}\"\nORIGIN\n{origin}\n//\n")


def test_ks_meta_names_the_contig_as_locus_does(tmp_path):
    iso = tmp_path / "iso/Micromonospora"; iso.mkdir(parents=True)
    (iso / f"SYN-970__{FULL}.region001.gbk").write_text(region_gbk(FULL, FULL.rsplit(".", 1)[0], SHORT, "ctg1_1"))
    ref = tmp_path / "ref/Streptomyces"; ref.mkdir(parents=True)
    (ref / "Ref_one__NZ_CP000001.region001.gbk").write_text(region_gbk("NZ_CP000001", "NZ_CP000001", ACC, "ref_1"))
    assert ppo.main(["extract", "--kit", str(tmp_path / "kit"), "--input", f"isolate={tmp_path / 'iso'}",
                     "--input", f"reference={tmp_path / 'ref'}"]) == 0
    rows = {r["strain"]: r for r in csv.DictReader(open(tmp_path / "kit/KS_META.tsv"), delimiter="\t")}
    iso_row, ref_row = rows["SYN-970"], rows["Ref_one"]
    assert iso_row["record_id"] == FULL
    assert iso_row["assembly"] == FULL                       # no explicit binding: the default identity is the contig
    assert FULL in iso_row["locus_identity"] and SHORT not in iso_row["locus_identity"]
    assert SHORT not in "\t".join(iso_row.values())
    assert ref_row["record_id"] == ACC and ref_row["assembly"] == ACC   # accession records keep their VERSION id
