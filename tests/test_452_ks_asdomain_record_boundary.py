"""aSDomain qualifier parsing stops at ORIGIN and // so sequence text never joins a translation (P300-093)."""
from mamey import ks_phylogeny as kp

SEQ = "MKTAYIAKQRQISFVKSHFSRQ"


def _record(locus, last):
    return "\n".join([
        f"LOCUS       {locus}                   900 bp    DNA     linear   UNK 01-JAN-1980",
        "FEATURES             Location/Qualifiers",
        "     aSDomain        1..90",
        '                     /aSDomain="PKS_KS"',
        '                     /domain_id="ks1"',
        f'                     /translation="{SEQ}"',
        "     aSDomain        91..180",
        '                     /aSDomain="PKS_KS"',
        '                     /domain_id="ks2"',
        f'                     /translation="{last}',
        f'                     {last}"',
        "ORIGIN",
        "        1 atgaaaacgg cgtatattgc gaaacagcgc cagattagct ttgtgaaaag",
        "//",
    ])


def test_last_translation_stops_at_origin():
    doms = kp._parse_gbk_asdomains(_record("REF1", "MSEQ") + "\n", "", "")
    assert [d["translation"] for d in doms] == [SEQ, "MSEQMSEQ"]


def test_second_record_header_does_not_join_the_first_record():
    text = _record("REF1", "MAAA") + "\n" + _record("REF2", "MCCC") + "\n"
    doms = kp._parse_gbk_asdomains(text, "", "")
    assert [d["translation"] for d in doms] == [SEQ, "MAAAMAAA", SEQ, "MCCCMCCC"]
    assert [d["domain_id"] for d in doms] == ["ks1", "ks2", "ks1", "ks2"]


def test_reference_module_ks_reads_clean_translations(tmp_path):
    g = tmp_path / "BGC0000001.gbk"
    g.write_text(_record("REF1", "MSEQ") + "\n")
    tips = kp.reference_module_ks(g)
    assert [t["translation"] for t in tips] == [SEQ, "MSEQMSEQ"]
    assert all(t["translation"].isalpha() for t in tips)
