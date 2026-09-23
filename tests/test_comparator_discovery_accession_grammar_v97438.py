"""A ClusterBlast hit accession must never become a shell command.

`tools/comparator_discovery.py` parses the accession out of a ClusterBlast hit list with `(\\S+)`
and writes it into a generated bash helper — unquoted after `-id`, and again inside a double-quoted
redirect target — then marks that file executable (`chmod 0o755`). `$(id)` contains no whitespace,
so it satisfied `\\S+`, was emitted literally, and would be evaluated later when someone ran the
documented fetch step. Parsing looked harmless; execution happened downstream, in a step the
operator trusts. That is the whole shape of the bug: data becomes code one workflow stage later.

These tests drive the real generator and read the file it produces.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "comparator_discovery.py"

# The real shape, copied from AS-705_new (Loose)/knownclusterblast/NODE_402_..._c1.txt:
# "Significant hits: \n1. BGC0000551.5\tSapB\n2. BGC0000496.5\tAmfS\n\n\nDetails:"
HITS = """ClusterBlast scores for contig_1

Table of genes, locations, strands and annotations of query cluster:

Significant hits: 
{rows}


Details:
"""


def _run(tmp_path, rows, strain="AS-TEST"):
    # the tool globs `<root>/**/{clusterblast,knownclusterblast}/*.txt`, so the file has to sit
    # inside a directory with one of those names — not just any directory handed to --dir.
    root = tmp_path / "as_result"
    src = root / "knownclusterblast"
    src.mkdir(parents=True)
    (src / "contig_1_c1.txt").write_text(HITS.format(rows=rows), encoding="utf-8")
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(TOOL), "--strain", strain,
                        "--dir", str(root), "--out", str(out)],
                       capture_output=True, text=True)
    fetch = out / f"fetch_{strain}_comparators.sh"
    return r, (fetch.read_text(encoding="utf-8") if fetch.is_file() else "")


@pytest.mark.parametrize("payload", [
    "$(id)",
    "`id`",
    "${IFS}id",
    "NZ_AAA;id",
    "NZ_AAA|id",
    "NZ_AAA&&id",
    "NZ_AAA'id'",
    'NZ_AAA"id"',
    "NZ_AAA$(touch\\x20pwned)",
])
def test_a_shell_payload_in_an_accession_never_reaches_a_command(tmp_path, payload):
    r, script = _run(tmp_path, f"1. {payload}\tStreptomyces sp. evil")
    assert script, f"generator produced no helper: {r.stderr[-300:]}"
    # A payload test that passes because the script is EMPTY tests nothing. Prove the generator
    # parsed the hit list at all before asserting anything about what it did with it.
    assert "Top 0 comparators" not in script, (
        "the fixture did not parse — this test would pass vacuously")
    commands = [l for l in script.splitlines()
                if l.strip() and not l.lstrip().startswith("#")]
    for c in commands:
        assert payload not in c, f"payload survived into a command line: {c}"


def test_a_legitimate_accession_still_produces_a_working_fetch_line(tmp_path):
    """The grammar must not be so tight that the tool stops working."""
    r, script = _run(tmp_path, "1. NZ_CP023202.1\tStreptomyces xinghaiensis S187")
    assert "NZ_CP023202.1" in script
    assert "efetch -db nuccore -id NZ_CP023202.1 -format fasta" in script
    # $OUT must still be a live shell variable, not a literal
    assert '"$OUT/NZ_CP023202.1.fna"' in script


def test_a_refused_accession_is_reported_not_silently_dropped(tmp_path):
    """Silently dropping a hit would hide a poisoned input. It must be visible, as a comment."""
    r, script = _run(tmp_path, "1. $(id)\tStreptomyces sp. evil")
    if not script:
        pytest.skip("generator produced no helper")
    assert "REFUSED" in script
    assert "$(id)" in script                      # present, but only inside a comment
    for line in script.splitlines():
        if "$(id)" in line:
            assert line.lstrip().startswith("#")


def test_generated_script_has_no_unquoted_interpolation_after_id(tmp_path):
    """A structural check that survives future edits: the -id argument is always a single
    shell word made only of accession-grammar characters."""
    _, script = _run(tmp_path, "1. NZ_CP023202.1\tStreptomyces xinghaiensis S187\n"
                               "2. BGC0001522\tStreptomyces sp. ref")
    for m in re.finditer(r"-id\s+(\S+)", script):
        assert re.fullmatch(r"'?[A-Za-z0-9][A-Za-z0-9_.-]*'?", m.group(1)), m.group(1)
