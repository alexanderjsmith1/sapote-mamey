"""The built-in GenBank reader must give records the name and description Biopython gives them.

parsers._replicon_intake_key orders chromosome records before plasmid records from the record text, including
the DEFINITION line. The built-in reader (used when Biopython is not installed) left name and description empty,
so on a genome with a labelled plasmid the same ZIP got different BGC numbers with and without Biopython.
"""
import io

import pytest

from mamey._gbk_shim import parse_genbank_text
from mamey.parsers import _replicon_intake_key

SEQ = "        1 aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa\n"
GBK = (
    "LOCUS       CHR1                      60 bp    DNA     circular BCT 01-JAN-2026\n"
    "DEFINITION  Fixture bacterium strain X, complete genome.\n"
    "ACCESSION   CHR1\n"
    "VERSION     CHR1.1\n"
    "FEATURES             Location/Qualifiers\n"
    "     source          1..60\n"
    "ORIGIN\n" + SEQ + "//\n"
    "LOCUS       PLS1                      60 bp    DNA     circular BCT 01-JAN-2026\n"
    "DEFINITION  Fixture bacterium strain X plasmid pX1, complete\n"
    "            sequence.\n"
    "ACCESSION   PLS1\n"
    "VERSION     PLS1.1\n"
    "FEATURES             Location/Qualifiers\n"
    "     source          1..60\n"
    "ORIGIN\n" + SEQ + "//\n"
)
EXPECTED = [("CHR1.1", "CHR1", "Fixture bacterium strain X, complete genome"),
            ("PLS1.1", "PLS1", "Fixture bacterium strain X plasmid pX1, complete sequence")]


def test_shim_reads_locus_name_and_definition():
    assert [(r.id, r.name, r.description) for r in parse_genbank_text(GBK)] == EXPECTED


def test_shim_matches_biopython():
    SeqIO = pytest.importorskip("Bio.SeqIO")
    bio = [(r.id, r.name, r.description) for r in SeqIO.parse(io.StringIO(GBK), "genbank")]
    assert bio == EXPECTED


def test_replicon_order_is_the_same_without_biopython():
    shim = parse_genbank_text(GBK)
    order = [name for name, _ in sorted([("a.gbk", shim[0]), ("b.gbk", shim[1])], key=_replicon_intake_key)]
    assert order == ["b.gbk", "a.gbk"]   # the labelled plasmid, then the record labelled neither way
