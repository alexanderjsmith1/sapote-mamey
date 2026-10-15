"""Every interpolated operand in the marker plan is shell-quoted; nothing is executed.

An assembly path with spaces or shell metacharacters must stay one literal word, and the
plan must say that the GFF-to-FASTA extraction is a separate step it does not perform.
"""
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import marker_candidate_search as marker  # noqa: E402

ASSEMBLY = "my dir/a b;$(touch x).fna"
QUERY = "Q 1"


def _plan(capsys, markers, *extra):
    marker.main(["plan-blast", "--assembly", ASSEMBLY, "--query", QUERY, "--markers", markers, *extra])
    return capsys.readouterr().out


def _command(text, prefix):
    return next(line for line in text.splitlines() if line.startswith(prefix))


def test_barrnap_line_quotes_assembly_and_output(capsys):
    line = _command(_plan(capsys, "16S", "--remote"), "barrnap ")
    head, _, tail = line.partition(" | ")
    assert shlex.split(head) == ["barrnap", "--kingdom", "bac", ASSEMBLY]
    assert shlex.split(tail.split(">", 1)[1]) == [f"{QUERY}_16S.gff"]


def test_plan_states_extraction_is_not_run(capsys):
    text = _plan(capsys, "16S", "--remote")
    assert "NOT RUN" in text and "does not create" in text


def test_remote_blastn_and_protein_lines_are_quoted(capsys):
    text = _plan(capsys, "16S,rpoB", "--remote")
    blastn = shlex.split(_command(text, "blastn ").split("#", 1)[0])
    assert blastn[blastn.index("-query") + 1] == f"{QUERY}_16S.fna"
    assert blastn[blastn.index("-out") + 1] == f"{QUERY}_16S_hits.tsv"
    prodigal = shlex.split(_command(text, "prodigal ").split("#", 1)[0])
    assert prodigal[prodigal.index("-i") + 1] == ASSEMBLY
    assert prodigal[prodigal.index("-a") + 1] == f"{QUERY}.faa"
    blastp = shlex.split(_command(text, "blastp "))
    assert blastp[blastp.index("-out") + 1] == f"{QUERY}_rpoB_hits.tsv"


def test_to_panel_hint_is_quoted(capsys):
    line = _command(_plan(capsys, "16S", "--remote"), "# then: ")
    words = shlex.split(line[len("# then: "):])
    assert words[words.index("--query") + 1] == QUERY
    assert words[words.index("--out") + 1] == f"{QUERY}_candidates.tsv"
