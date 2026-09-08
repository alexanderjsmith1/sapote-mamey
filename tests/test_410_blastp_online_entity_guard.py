"""v9.7.410 hostile audit (round 6) — entity-expansion replies to the online BLASTp client.

A billion-laughs body kept `parse_blast_xml` busy ~20 s (10^6 expansions stay under expat's
amplification threshold, so the interpreter's own guard does not trip). NCBI never sends an
internal DTD subset, so any `<!ENTITY` declaration is refused before parsing — the existing
fail-closed "no hits" path. The real NCBI DOCTYPE line (external DTD, no subset) must still parse."""
from __future__ import annotations

import time

import pytest

pytest.importorskip("Bio")
from mamey import blastp_online as bo  # noqa: E402

BATCH = [("ctg1_1", "MKVLAAGIVALLLAAGCSAQ")]


def _lol(depth: int) -> str:
    ents = ['<!ENTITY lol "lol">'] + [
        f'<!ENTITY lol{i} "' + "".join(f"&lol{i - 1 if i > 1 else ''};" for _ in range(10)) + '">'
        for i in range(1, depth + 1)]
    return ('<?xml version="1.0"?><!DOCTYPE BlastOutput [' + "".join(ents) + ']>'
            f'<BlastOutput><BlastOutput_iterations><Iteration><Iteration_query-def>&lol{depth};'
            '</Iteration_query-def></Iteration></BlastOutput_iterations></BlastOutput>')


def test_entity_declarations_are_refused_fast():
    t = time.time()
    assert bo.parse_blast_xml(_lol(6), BATCH, top_n=3) == []
    assert time.time() - t < 1.0


def test_real_ncbi_doctype_line_is_not_refused():
    xml = ('<?xml version="1.0"?>\n<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" '
           '"http://www.ncbi.nlm.nih.gov/dtd/NCBI_BlastOutput.dtd">\n'
           '<BlastOutput><BlastOutput_iterations></BlastOutput_iterations></BlastOutput>')
    # no hits in it, but it must reach the parser (no exception, no early refusal on DOCTYPE)
    assert bo.parse_blast_xml(xml, BATCH, top_n=3) == []
