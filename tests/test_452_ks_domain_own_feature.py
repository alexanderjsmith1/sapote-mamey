"""A PKS_KS aSDomain reads only its own qualifiers, never a later feature's (P300-128)."""
from mamey.pks_ks_scan import ks_domains_from_gbk

KS = "M" + "KTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ" * 4      # 129 aa synthetic, not a real protein
CDS = "M" + "AVLDGRTPWEHSQNNC" * 8                     # 129 aa synthetic


def _wrap(seq, width=58):
    parts = [seq[i:i + width] for i in range(0, len(seq), width)]
    lines = [f'                     /translation="{parts[0]}']
    lines += [f"                     {p}" for p in parts[1:]]
    lines[-1] += '"'
    return lines


def _gbk(ks_qualifiers, tail):
    return "\n".join([
        "LOCUS       NODE_1                  9000 bp    DNA     linear   UNK 01-JAN-1980",
        "FEATURES             Location/Qualifiers",
        "     aSDomain        100..487",
        '                     /aSDomain="PKS_KS"',
        *ks_qualifiers,
        *tail,
        "ORIGIN",
        "        1 atgaaaacgg cgtatattgc",
        "//",
    ]) + "\n"


def _cds_tail():
    return ["     CDS             1..900",
            '                     /locus_tag="ctg1_99"',
            *_wrap(CDS)]


def test_domain_without_translation_does_not_borrow_the_next_cds():
    doms = ks_domains_from_gbk(_gbk(['                     /locus_tag="ctg1_1"'], _cds_tail()), "NODE_1", 1)
    assert doms == []


def test_domain_without_locus_tag_does_not_borrow_the_next_cds_tag():
    doms = ks_domains_from_gbk(_gbk(_wrap(KS), _cds_tail()), "NODE_1", 1)
    assert [(d["locus_tag"], d["seq"]) for d in doms] == [("?", KS)]


def test_subtype_is_not_borrowed_from_a_later_domain_feature():
    tail = ["     PFAM_domain     100..400",
            '                     /domain_subtypes="Trans-AT-KS"']
    doms = ks_domains_from_gbk(_gbk(['                     /locus_tag="ctg1_1"', *_wrap(KS)], tail), "NODE_1", 1)
    assert [d["subtype"] for d in doms] == ["UNCLASSIFIED"]


def test_owned_wrapped_translation_is_unchanged():
    quals = ['                     /locus_tag="ctg1_1"', '                     /domain_subtypes="Modular-KS"', *_wrap(KS)]
    doms = ks_domains_from_gbk(_gbk(quals, _cds_tail()), "NODE_1", 1)
    assert [(d["locus_tag"], d["seq"], d["subtype"], d["length"]) for d in doms] == [
        ("ctg1_1", KS, "Modular-KS", len(KS))]
