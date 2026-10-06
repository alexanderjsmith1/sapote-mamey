"""tools/gap_rescue_locus_map.py and gap_directed_rescue.redraw: a partner contig is drawn only when it holds a SUPPORTED
find, and the adjudicator's verdicts replace the run's own.

The owner, 2026-10-02, of a contig pulled onto a halogenated indolocarbazole map by one set-aside transporter: "This does not
belong with this slide or this bgc." The adjudicator also rated a sugar gene beside the halogenase SUPPORTED where the
run's table still said PARALOG_FAMILY.
"""
import csv
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gap_directed_rescue as gdr  # noqa: E402

spec = importlib.util.spec_from_file_location("gap_rescue_locus_map_447s", ROOT / "tools/gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)


def test_an_adjudication_file_replaces_the_runs_partner_verdicts(tmp_path):
    run = tmp_path / "BGC001_vs_BGC0000010"
    run.mkdir()
    with open(tmp_path / "BGC001_vs_BGC0000010_ADJUDICATION.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["reference_gene", "candidate_locus", "verdict"], delimiter="\t")
        w.writeheader()
        w.writerow({"reference_gene": "abcS", "candidate_locus": "p_2", "verdict": "SUPPORTED"})
    rows = [{"name": "abcS", "best_locus": "p_2", "partner_verdict": "PARALOG_FAMILY"},
            {"name": "abcT", "best_locus": "p_3", "partner_verdict": "PARALOG_FAMILY"}]
    out = gdr.apply_adjudication(rows, run)
    assert [r["partner_verdict"] for r in out] == ["SUPPORTED", "PARALOG_FAMILY"]


def _choose(rows):
    ref = [{"i": i + 1, "name": n, "product": "p", "kind": "biosynthetic", "s": i, "e": i + 0.9, "strand": 1}
           for i, n in enumerate(["abcA", "abcB", "abcC", "abcD"])]
    prot = lambda tag, contig, start: {"tag": tag, "contig": contig, "start": start, "end": start + 900, "strand": 1,
                                       "contig_len": 20000}
    prots = {"q1": prot("c_1", "core", 1000), "q2": prot("p_1", "part", 1000), "q3": prot("p_2", "part", 2500),
             "q4": prot("f_1", "far", 1000)}
    return glm.choose(ref, rows, [], prots, "core")


def _row(pid, status, verdict, ident=60.0):
    return {"status": status, "best_protein": pid, "best_identity_pct": ident, "reciprocal_best": True,
            "partner_verdict": verdict}


def test_a_contig_with_no_supported_find_is_not_drawn():
    """A lone transporter set aside as SINGLE_GENE pulled its contig onto the map; it no longer does."""
    rows = [_row("q1", "PRESENT_IN_CORE", ""), _row("q2", "MISSING_FOUND_CLEAR", "SUPPORTED", 71.0),
            _row("q3", "MISSING_FOUND_CLEAR", "PARALOG_FAMILY", 69.0), _row("q4", "MISSING_FOUND_CLEAR", "SINGLE_GENE", 59.0)]
    drawn = {p for _, p, _ in _choose(rows)[0]}
    assert "q4" not in drawn                 # the far contig holds no supported find
    assert {"q1", "q2", "q3"} <= drawn       # the paralog-family gene is kept beside the supported one


def test_without_partner_checks_the_old_rule_holds():
    rows = [_row("q1", "PRESENT_IN_CORE", ""), _row("q4", "MISSING_FOUND_CLEAR", "", 59.0)]
    assert "q4" in {p for _, p, _ in _choose(rows)[0]}
