"""Without region GBKs, a whole GenBank record becomes a BGC only if it carries one region."""
import zipfile

from mamey import parsers

SEQ = "acgt" * 250  # 1,000 bp


def _record(name, features=""):
    lines = ["".join(SEQ[i:i + 60]) for i in range(0, len(SEQ), 60)]
    origin = "\n".join(f"{i * 60 + 1:>9} {l}" for i, l in enumerate(lines))
    return (f"LOCUS       {name:<16} {len(SEQ)} bp    DNA     linear   UNK 01-JAN-2026\n"
            f"DEFINITION  synthetic.\nACCESSION   {name}\nVERSION     {name}\n"
            f"FEATURES             Location/Qualifiers\n{features}ORIGIN\n{origin}\n//\n")


REGION = ('     region          101..900\n                     /product="NRPS"\n'
          '                     /region_number="1"\n')
REGION2 = ('     region          901..990\n                     /product="terpene"\n'
           '                     /region_number="2"\n')


def _parse(tmp_path, records):
    z = tmp_path / "in.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("genome.gbk", "".join(records))
    return parsers.parse_bgcs_from_zip(z, json_mode="off")


def test_contigs_without_regions_are_not_bgcs(tmp_path):
    assert _parse(tmp_path, [_record("ctgA"), _record("ctgB")]) == []


def test_one_region_whole_record_is_still_admitted(tmp_path):
    bgcs = _parse(tmp_path, [_record("ctgA", REGION), _record("ctgB")])
    assert [(b.contig, b.start, b.end) for b in bgcs] == [("ctgA", 101, 900)]


def test_multi_region_whole_record_is_held(tmp_path):
    assert _parse(tmp_path, [_record("ctgA", REGION + REGION2)]) == []
