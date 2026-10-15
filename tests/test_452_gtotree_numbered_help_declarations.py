"""Released GToTree 1.8.19 help declares -H on a numbered line; the interface gate must read it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import _gtotree_versions as g  # noqa: E402

# Line shapes copied from the released 1.8.19 `GToTree -h` output (numbered input groups, bulleted options).
HELP_1_8_19 = "\n".join([
    "  REQUIRED INPUTS:",
    "      1) Input genomes in one or any combination of the following formats:",
    "        - [-f <file>] single-column file with the paths to each fasta file",
    "      2)  [-H <file>] location of the uncompressed target SCGs HMM file",
    "        - [-o <str>] default: GToTree_output",
    "        - [-m <file>] mapping file specifying desired genome labels",
    "        - [-N ] do not make a tree; default: false",
    "        - [-k ] keep individual target gene alignments; default: false",
    "        - [-M <int> ] num muscle threads; default: 5",
    "        - [-j ] num jobs; default: 1",
])


def test_numbered_declaration_is_read():
    assert "-H" in g.declared_help_options("      2)  [-H <file>] location of the HMM file")


def test_released_1_8_19_help_declares_every_common_option():
    found = g.declared_help_options(HELP_1_8_19)
    assert set(g._COMMON_OPTIONS) <= found


def test_numbered_prose_and_bare_mentions_still_do_not_declare():
    assert not g.declared_help_options("      1) Input genomes, see -f or -H below")
    assert not g.declared_help_options("This prose mentions -f -H -m -j -M -N -k -o but declares no options.")
