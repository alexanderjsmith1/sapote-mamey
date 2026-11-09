"""tests/_modeb_card_fixtures.py — shared test helper for generating a
structurally-valid §1–§30 Mode B card stub.

Why this exists (v9.7.151): the W4-era ingest tests (test_auto_detect_ingest.py,
test_ingest_one_card.py, test_mode_b_receipt.py) used a minimal placeholder
card body like "## Mode B card content\n\nReal content here." This was fine
before W9 (v9.7.150) added the structure gate — those tests were exercising
ingest *mechanics* (register state transitions, file discovery, idempotency),
not card *content*, and the placeholder was never meant to be a real card.

Once the structure gate started linting every card before persisting it,
these placeholder cards were correctly refused as structurally invalid
(missing 21 of 22 always-required sections) — a real bug exposed by a real
pytest run, not a flaky test. The ingest mechanics being tested were never
the problem; the test fixtures were just pre-W9.

This helper builds a minimal-but-genuinely-valid card from the live
§1–§30 contract (mamey.modeb_structure_gate.load_contract) so tests that
care about ingest mechanics, not content depth, get a card that actually
clears the gate. Verified to produce zero ERROR-severity findings as of
v9.7.151 — re-verify if the contract JSON ever changes shape.
"""
from __future__ import annotations


def fixture_region(bgc_id: str) -> str:
    """The region a fixture card and its triage row share: BGC007 -> region007."""
    import re
    m = re.search(r"(\d+)", str(bgc_id))
    return f"region{int(m.group(1)):03d}" if m else "region001"


def write_identity_triage_board(pkg, strain_id: str, bgc_ids, node: str = "NODE_1",
                                extra: dict | None = None):
    """Write ``<strain>_4_triage_board.csv`` binding each alias to ``node`` and its
    fixture region, so a ``valid_modeb_card_stub`` card for it is identity-bound.

    ``extra`` maps column -> value (or column -> {bgc_id: value}) for further columns.
    """
    import csv
    from pathlib import Path
    extra = dict(extra or {})
    cols = ["BGC_ID", "Contig", "antiSMASH_Region", *extra.keys()]
    path = Path(pkg) / f"{strain_id}_4_triage_board.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for bid in bgc_ids:
            vals = [v.get(bid, "") if isinstance(v, dict) else v for v in extra.values()]
            w.writerow([bid, node, fixture_region(bid), *vals])
    return path


def valid_modeb_card_stub(bgc_id: str = "BGC001", node: str = "NODE_1",
                          strain_id: str = "AS-XXX") -> str:
    """Return a §1–§30-contract-valid Mode B card with stub prose under
    every always-required section heading, PLUS §24 (Scaffold novelty
    score). Passes modeb_structure_gate.lint_card with zero ERROR findings
    against both bgc_context=None and a realistic triage-row context.

    Why §24 is included even though it's conditional: its predicate
    (novel_or_no_mibig) fires whenever a BGC context has no `kcb_top`
    field — which is the default state of almost any synthetic/minimal
    test fixture triage row (a real "no KCB hit" BGC, or simply a fixture
    that never set the field). Tests that build a real triage board via
    `_bgc_context_from_triage` will hit this predicate essentially every
    time unless the fixture explicitly sets kcb_top to a non-empty value.
    Including §24 unconditionally in the stub avoids every such test
    needing to special-case this — same principle as the rest of this
    helper: test ingest *mechanics*, not card *content*.

    Use this as test fixture content wherever a test needs "a real,
    persistable card" without needing the interpretive content itself
    to be meaningful (e.g. testing ingest, auto-detect, idempotency,
    register state transitions — not testing the card's scientific
    content).
    """
    try:
        from mamey.modeb_structure_gate import load_contract
        contract = load_contract()
        sections = [s for s in contract["sections"]
                   if s["required"] == "always" or s["number"] == 24]
        sections.sort(key=lambda s: s["number"])
    except Exception:
        # Fail-open fallback if the contract can't load — a minimal
        # §1-20 + §24 + §28 + §30 list matching the contract as of v9.7.151.
        # Should never fire in practice; here so a contract-load failure
        # degrades to *something* testable rather than crashing the fixture.
        sections = [
            {"number": n, "title": t} for n, t in [
                (1, "Identity and node/region"), (2, "Why this BGC was selected"),
                (3, "Boundary and assembly status"), (4, "Gene-by-gene interpretation"),
                (5, "Core biosynthetic logic"), (6, "Tailoring and maturation logic"),
                (7, "Transport, resistance, and regulation"), (8, "Comparator/KCB interpretation"),
                (9, "Alternative hypotheses"), (10, "Fragmentation and co-capture risks"),
                (11, "Product-family interpretation"), (12, "Bee/microbe ecological interpretation"),
                (13, "Antibacterial/antifungal relevance"), (14, "What cannot be claimed"),
                (15, "Missing evidence"), (16, "BLASTP/HMMER next steps"),
                (17, "LC-MS / fermentation implications"), (18, "Figure/locus-map notes"),
                (19, "Final Mode B judgement"), (20, "Next actions"),
                (24, "Scaffold novelty score"),
                (28, "Evidence provenance ledger"), (30, "Experimental decision tree"),
            ]
        ]

    # The four-part exact-locus header (strain / full node-or-contig / region / alias):
    # every ingest route requires it to match the package triage row before a card is
    # recorded COMPLETE. Pair this stub with ``write_identity_triage_board``.
    lines = [f"# Mode B — {strain_id} / {node} / {fixture_region(bgc_id)} / {bgc_id}", ""]
    for s in sections:
        lines.append(f"## §{s['number']} {s['title']}")
        lines.append("Stub content for testing.")
        lines.append("")
    return "\n".join(lines)
