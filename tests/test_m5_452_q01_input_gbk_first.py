"""M5_452_q01_input_gbk_first: tools/assembly_stats_table.py on route-A antiSMASH ZIPs that hold no input FASTA but two whole-genome
GenBank files (top-level result record and input/ submitted record). The input record is read (full assembly, contigs < 1 kb kept);
the two must agree on contigs >= 1 kb in count and total length, else the ZIP is refused. Synthetic sequences only."""
import importlib.util, zipfile
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "assembly_stats_table.py"
spec = importlib.util.spec_from_file_location("ast_tool_q01", TOOL); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def gbk(contigs):
    out = []
    for i, s in enumerate(contigs):
        body = "".join(f"{k + 1:>9} {s[k:k + 60].lower()}\n" for k in range(0, len(s), 60))
        out.append(f"LOCUS       SYN{i:03d} {len(s)} bp    DNA     linear   BCT 01-JAN-2000\nDEFINITION  synthetic.\n"
                   f"ACCESSION   SYN{i:03d}\nVERSION     SYN{i:03d}.1\nFEATURES             Location/Qualifiers\n"
                   f"     source          1..{len(s)}\nORIGIN\n{body}//\n")
    return "".join(out)


def make(tmp, input_contigs, result_contigs):
    p = tmp / "syn.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("SYN.gbk", gbk(result_contigs)); z.writestr("input/SYN.gbk", gbk(input_contigs))
        z.writestr("SYN.region001.gbk", gbk(result_contigs[:1]))
    return p


def test_two_gbks_that_agree_read_input_first(tmp_path):
    big = ["GC" * 2500, "AT" * 1000]
    z = make(tmp_path, big + ["G" * 500], big)          # input keeps a 500 bp contig the result record dropped
    r = m.stats(*m.zip_lengths(z))
    assert r["contigs"] == "3" and r["contigs_1kb"] == "2"
    assert r["sequence_source"].startswith("input GenBank (input/SYN.gbk)")


def test_two_gbks_that_disagree_on_1kb_contigs_are_refused(tmp_path):
    z = make(tmp_path, ["GC" * 2500, "AT" * 1000], ["GC" * 2500, "AT" * 900])
    with pytest.raises(ValueError, match="ZIP_INPUT_AND_RESULT_GBK_DISAGREE_ON_CONTIGS_GE_1KB"):
        m.zip_lengths(z)
