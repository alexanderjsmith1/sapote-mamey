"""v9.7.335 — known-bad-input regression tests for the four Tier-1 gate fixes.

Every fix in the .335 "evidence honesty" patch is the same shape: **a check that reported
success without having checked**. The failure mode of such a bug is that it passes every
known-GOOD input, so a test suite built only on good inputs cannot see it — which is exactly
how each of these shipped green.

The project's own lesson from the v9.7.321-.330 run (verify_blastp's gene counter, the
two-model silent PASS, the coverage-denominator silent zero) is written down as: *verify a
gate FIRES on a known-bad input, not just that it passes on a known-good one.* These tests do
that. Each one feeds the gate the specific artifact that used to slip through and asserts the
gate now refuses it. Each is paired with a good-input control so a future refactor cannot make
the test pass by breaking the gate in the other direction.

Fixes locked here (patch card v9.7.335, Tier 1):
  1. validate.validate_package  — a corrupt manifest.json UPGRADED the verdict to PASS
  2. validate.validate_package  — gold_completeness PASS decided by a filename substring
  3. mode_b_receipt.ingest_one_card — a CRASHED structure gate recorded as a clean card
  4. modeb_structure_gate       — the §4 evidence gate could not fail (two ways)
"""

import json
from pathlib import Path

import pytest

from mamey.validate import validate_package
from mamey import modeb_structure_gate as msg


# --------------------------------------------------------------------------------------
# shared fixture: a minimal package that validates cleanly, so that when we corrupt ONE
# thing the resulting FAIL is attributable to that thing and not to fixture noise.
# --------------------------------------------------------------------------------------

_LOCKED = ["BGC001", "BGC002"]



def _seal04_write_manifest(pkg) -> None:
    """Write a genuine checksums_sha256.txt covering every file currently in `pkg`.

    Fixtures here previously wrote an empty manifest as filler. Since SEAL-04 that is an
    integrity error in its own right, so the filler is replaced by a real (and trivially
    correct) manifest, keeping these controls focused on the gates they actually test.
    """
    import hashlib as _hashlib
    from pathlib import Path as _Path
    pkg = _Path(pkg)
    lines = []
    for p in sorted(pkg.rglob("*")):
        if not p.is_file() or p.name == "checksums_sha256.txt":
            continue
        rel = p.relative_to(pkg).as_posix()
        lines.append(f"{_hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
    (pkg / "checksums_sha256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

def _make_min_package(tmp_path: Path, *, manifest_text: str | None = None) -> Path:
    """Build the smallest package that validate_package() accepts, mode=gold."""
    pkg = tmp_path / "AS-TEST"
    pkg.mkdir()

    manifest = {
        "strain_id": "AS-TEST",
        "mode": "gold",
        "bgcs": [{"bgc_id": b} for b in _LOCKED],
    }
    (pkg / "manifest.json").write_text(
        manifest_text if manifest_text is not None else json.dumps(manifest),
        encoding="utf-8",
    )

    # every BGC carries a depth-floor assignment -> every_bgc_assigned is True
    (pkg / "AS-TEST_2_inventory.csv").write_text(
        "bgc_id,Depth_floor\n"
        "BGC001,full_mode_b\n"
        "BGC002,abbreviated_ledger\n",
        encoding="utf-8",
    )
    (pkg / "AS-TEST_4A_RGGMCI_full.json").write_text(
        json.dumps({"status": "NULL_NO_RGGMCI_PAIRS", "pairs_total": 0,
                    "reference_record_count": 0}), encoding="utf-8")

    for stub in ("AS-TEST_1_intake.json", "AS-TEST_3_scan_states.json",
                 "commit_receipt.json", "Project_Memory_Snapshot.json",
                 "manifest_short.json"):
        (pkg / stub).write_text("{}", encoding="utf-8")
    for stub in ("AS-TEST_4A_RGGMCI_ranked_pairs.csv", "AS-TEST_4A_RGGMCI_evidence.csv",
                 "AS-TEST_4_triage_board.csv", "AS-TEST_7_cell_provenance.csv"):
        (pkg / stub).write_text("col\n", encoding="utf-8")
    (pkg / "AS-TEST_5_workbook.xlsx").write_bytes(b"stub")
    (pkg / "issue_log.md").write_text("# issues\n", encoding="utf-8")
    (pkg / "OPEN_ME_FIRST.html").write_text("<html></html>", encoding="utf-8")
    # SEAL-04 (v9.7.396): an EMPTY manifest is now itself an integrity error (a zero-scan
    # PASS previously let a tampered package validate clean), so this fixture — which is
    # about other gates, not checksums — writes a real manifest over its own files.
    _seal04_write_manifest(pkg)
    return pkg


# --------------------------------------------------------------------------------------
# FIX 1 — a corrupt manifest.json must not score BETTER than a good one.
#
# Known-bad input: manifest.json that will not parse. The parse error was swallowed, so
# `mode` stayed None (gold block skipped), the reporting-v2 gate degraded to
# LEGACY_NOT_APPLICABLE, and status fell through to PASS. manifest.json is excluded from
# the checksum set, so nothing downstream caught it either.
# --------------------------------------------------------------------------------------

def test_control_good_manifest_is_not_failed_by_the_fixture(tmp_path):
    """Control: a well-formed manifest parses, so any FAIL is attributable elsewhere.

    v9.7.337 (GATE-12): this used to also assert ``status != "FAIL"``. GATE-12 deliberately
    tightened gold completeness — a gold package whose judgment register does not confirm its
    cards now reports ``JUDGMENT_PENDING`` rather than PASS, and the overall status follows. This
    stub fixture writes no judgment register, so it is legitimately not gold-complete. The control
    that matters here is narrower and still holds: the manifest parsed, so a corrupt-manifest
    verdict is not what is driving the result.
    """
    pkg = _make_min_package(tmp_path)
    result = validate_package(pkg, enrichment_check=True)
    assert result.get("manifest_parse") == "PASS"
    assert result["status"] != "FAIL", result


def test_corrupt_manifest_fails_closed(tmp_path):
    """KNOWN-BAD: unparseable manifest.json -> FAIL, never PASS."""
    pkg = _make_min_package(tmp_path, manifest_text='{"mode": "gold", NOT JSON')
    result = validate_package(pkg, enrichment_check=True)
    assert str(result.get("manifest_parse", "")).startswith("FAIL"), result
    assert result["status"] == "FAIL", (
        "a package whose manifest.json will not parse must fail closed; it previously "
        f"returned {result.get('status')!r} because the parse error was swallowed"
    )


def test_corrupt_manifest_is_not_reported_as_mamey_complete(tmp_path):
    """KNOWN-BAD: the package_status handoff must not claim completeness either."""
    pkg = _make_min_package(tmp_path, manifest_text="not json at all")
    result = validate_package(pkg, enrichment_check=True)
    assert result["status"] == "FAIL"
    assert result.get("package_status") != "MAMEY_COMPLETE", result


# --------------------------------------------------------------------------------------
# FIX 2 — gold_completeness must open and attribute cards, not match a filename substring.
#
# Known-bad input: a single ZERO-BYTE file named "mode_b.md". The old test was
# `any("mode_b" in p.name.lower() ...)` — no card opened, none counted, no BGC id checked.
# --------------------------------------------------------------------------------------

def test_zero_byte_mode_b_file_does_not_pass_gold_completeness(tmp_path):
    """KNOWN-BAD: one empty mode_b.md must not flip gold_completeness to PASS."""
    pkg = _make_min_package(tmp_path)
    (pkg / "mode_b.md").write_text("", encoding="utf-8")
    result = validate_package(pkg, enrichment_check=True)
    assert result.get("gold_completeness") != "PASS", (
        "an empty file whose NAME contains 'mode_b' must not satisfy gold completeness; "
        f"note was: {result.get('gold_note')!r}"
    )


# An authored Mode-B card is well over 200 bytes of §-structured content. Use a realistic
# body so the GATE-12 size floor (>=200 B) is satisfied by genuine cards.
# v9.7.409 (gate-completeness content-commitment): a card now counts toward gold completeness only
# if it carries >= 3 recognised Mode-B §-headings (plus >=200 authored chars). The prior control
# fixture carried only §1 + §4 (2 headings) — thinner than any genuine §1–§30 card and below the new
# floor. Widen it to a realistic §-structured card (§1/§2/§3/§4). This is a fixture bless, not a
# behavior relaxation: the assertion (real authored cards for every locked id PASS) is unchanged.
_AUTHORED_CARD = (
    "<!-- MODE B: {bgc} -->\n"
    "# {bgc} Mode B card\n\n"
    "## §1 Region summary\n"
    "antiSMASH region; class-level hypothesis only, judgment deferred.\n\n"
    "## §2 Architecture\n"
    "NRPS module architecture; C-A-PCP core with a terminal thioesterase.\n\n"
    "## §3 Domain inventory\n"
    "Condensation, AMP-binding (A), PCP/thiolation domains recognised by antiSMASH.\n\n"
    "## §4 Gene-by-gene evidence\n"
    "| Locus | aa | domains | BLASTp top hit | %id | Reconciliation |\n"
    "|---|---|---|---|---|---|\n"
    "| ctg1_1 | 512 | Condensation | NRPS [Streptomyces sp.] | 71.4 | CONFIRM |\n"
)


def test_cards_for_only_some_bgcs_do_not_pass_gold_completeness(tmp_path):
    """KNOWN-BAD: partial coverage (1 of 2 locked BGCs) must not read as complete."""
    pkg = _make_min_package(tmp_path)
    (pkg / "AS-TEST_BGC001_mode_b.md").write_text(
        _AUTHORED_CARD.format(bgc="BGC001"), encoding="utf-8")
    result = validate_package(pkg, enrichment_check=True)
    assert result.get("gold_completeness") != "PASS", result.get("gold_note")


def test_empty_per_bgc_stub_cards_do_not_pass_gold_completeness(tmp_path):
    """KNOWN-BAD (GATE-12, v9.7.338): a stub card per locked id (correct FILENAME, but
    empty/near-empty content) must not flip gold_completeness to PASS.

    Inversion documented: the v9.7.335 hardening matched card filenames against the locked
    ids but never opened them, so one zero/near-zero-byte ``AS-XXX_BGCNNN_mode_b.md`` per
    locked id satisfied ``_locked.issubset(_card_bgcs)`` and reported "All N BGCs accounted
    for with Mode B cards" — a gate greenlighting unauthored stubs. GATE-12 adds a >=200-byte
    authored-content floor; this test feeds the exact known-bad artifact (one sub-200-byte
    stub per locked id) and asserts the gate now refuses it.
    """
    pkg = _make_min_package(tmp_path)
    for bgc in _LOCKED:
        # correct per-BGC filename, but only a header — under the 200-byte authored floor.
        (pkg / f"AS-TEST_{bgc}_mode_b.md").write_text("# card\n", encoding="utf-8")
    result = validate_package(pkg, enrichment_check=True)
    assert result.get("gold_completeness") != "PASS", (
        "sub-200-byte per-BGC stub cards must not satisfy gold completeness; "
        f"note was: {result.get('gold_note')!r}"
    )


def test_control_cards_for_every_locked_bgc_do_pass(tmp_path):
    """Control: real (authored, >=200 B) per-BGC cards for every locked id still PASS.

    v9.7.338 (GATE-12): the card body was widened from a 7-byte ``"# card\\n"`` stub to a
    realistic authored §-structured card. Under the new size floor a 7-byte file is a stub and
    no longer counts — which is the whole point of GATE-12 — so the control now uses genuine
    card content. This is a fixture bless, not a behavior relaxation: the assertion (real cards
    for every locked id PASS, with an auditable numerator/denominator note) is unchanged.
    """
    pkg = _make_min_package(tmp_path)
    for bgc in _LOCKED:
        (pkg / f"AS-TEST_{bgc}_mode_b.md").write_text(
            _AUTHORED_CARD.format(bgc=bgc), encoding="utf-8")
    result = validate_package(pkg, enrichment_check=True)
    assert result.get("gold_completeness") == "PASS", result.get("gold_note")
    # the fix also requires the note to carry its own numerator/denominator
    assert "BGC ids matched" in str(result.get("gold_note", "")), result.get("gold_note")


# --------------------------------------------------------------------------------------
# FIX 3 — a crashed structure gate must not be recorded as a clean card.
#
# Known-bad input: lint_card raises. `structure_findings = []` is byte-identical to a clean
# lint, so the CLI printed "structure: PASS (§1-§30 contract satisfied)" and wrote the card
# into the judgment register. Absence of a check is not a pass.
# --------------------------------------------------------------------------------------

def _pkg_with_register(tmp_path: Path, strain="AS-TEST", bgc_ids=("BGC001",)) -> Path:
    from mamey.judgment_store import init_register
    pkg = tmp_path / strain
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain}), encoding="utf-8")
    init_register(pkg, strain_id=strain, bgc_ids=list(bgc_ids))
    return pkg


def test_crashed_structure_gate_is_not_recorded_as_a_clean_card(tmp_path, monkeypatch):
    """KNOWN-BAD: gate raises -> an explicit ERROR sentinel, not an empty (clean) finding list."""
    from mamey import mode_b_receipt

    def _boom(*a, **k):
        raise RuntimeError("simulated bundle-integrity fault")

    # Patch the helper called inside the SAME try: block as lint_card. It lives on
    # mode_b_receipt itself, so this is order-independent under a full-suite run (patching
    # modeb_structure_gate.lint_card is not — other tests load modules by file path).
    monkeypatch.setattr(mode_b_receipt, "_bgc_context_from_triage", _boom)

    pkg = _pkg_with_register(tmp_path)
    card = tmp_path / "AS-TEST_BGC001_mode_b.md"
    card.write_text("<!-- MODE B: BGC001 -->\n# whatever\n", encoding="utf-8")

    summary = mode_b_receipt.ingest_one_card(pkg, card)
    findings = summary.get("structure_findings") or []

    assert findings, (
        "a gate that crashed must not yield an empty finding list — an empty list is "
        "indistinguishable from a clean lint and was printed as 'structure: PASS'"
    )
    assert any(f.get("code") == "GATE_UNAVAILABLE" and f.get("severity") == "ERROR"
               for f in findings), findings
    assert summary.get("status") != "RECORDED", summary


# --------------------------------------------------------------------------------------
# FIX 4 — the §4 evidence gate must be capable of failing.
#
# Known-bad input (a): the pipeline's OWN unauthored §4 skeleton, whose guidance text
# contains "CONFIRM / REFINE / OVERTURN" as plain body text. The old bare-verdict branch
# matched it, so EVIDENCE_GAP was dead on every card produced through the supported workflow.
# Known-bad input (b): a core row whose ONLY digits live inside its locus tag (ctg13_108),
# which satisfied the percent-identity clause by itself.
# --------------------------------------------------------------------------------------

_SKELETON_S4 = """## §4 Gene-by-gene evidence

<!-- author the evidence grid here -->
For each core gene give the BLASTp top hit and a reconciliation verdict of
CONFIRM / REFINE / OVERTURN against the antiSMASH call.
"""

_PROSE_NEGATIVE_S4 = """## §4 Gene-by-gene evidence

We could not confirm any characterised homolog for the core genes in this region.
"""

_REAL_S4 = """## §4 Gene-by-gene evidence

| Locus | aa | antiSMASH domains | BLASTp top hit (nr) | %id | Reconciliation |
|---|---|---|---|---|---|
| ● ctg13_108 | 512 | Condensation | non-ribosomal peptide synthetase [Streptomyces sp.] | 71.4 | CONFIRM |
| ● ctg13_109 | 388 | AMP-binding | amino acid adenylation domain [Streptomyces sp.] | 64.2 | REFINE |
"""


def test_unauthored_s4_skeleton_does_not_count_as_a_blastp_table():
    """KNOWN-BAD: the emitter's own guidance text must not satisfy the §4 evidence gate."""
    assert msg._has_blastp_table(_SKELETON_S4) is False, (
        "the unauthored §4 skeleton contains 'CONFIRM / REFINE / OVERTURN' as body text; "
        "matching it made EVIDENCE_GAP dead on every card from the supported workflow"
    )


def test_prose_negative_does_not_count_as_a_blastp_table():
    """KNOWN-BAD: 'we could not confirm ...' must not satisfy the gate via \\bconfirm\\b."""
    assert msg._has_blastp_table(_PROSE_NEGATIVE_S4) is False


def test_control_real_evidence_grid_still_counts_as_a_blastp_table():
    """Control: a genuine §4 grid must still pass, or the fix has broken real cards."""
    assert msg._has_blastp_table(_REAL_S4) is True


def test_locus_tag_digits_do_not_satisfy_the_percent_identity_clause():
    """KNOWN-BAD: a row whose only digits are its locus tag must not read as covered."""
    row_no_identity = "| ● ctg13_108 | Condensation | no hit returned | CONFIRM |"
    stripped = msg._s4_strip_locus(row_no_identity)
    assert msg._S4_PCTID_RE.search(stripped) is None, (
        "after stripping the locus tag this row carries no percent identity; "
        f"the digits in 'ctg13_108' previously supplied it (stripped={stripped!r})"
    )


def test_control_real_identity_survives_locus_stripping():
    """Control: stripping the locus tag must not remove a genuine identity value."""
    row = "| ● ctg13_108 | 512 | NRPS [Streptomyces sp.] | 71.4 | CONFIRM |"
    stripped = msg._s4_strip_locus(row)
    assert msg._S4_PCTID_RE.search(stripped) is not None, stripped


def test_node_name_digits_do_not_satisfy_the_percent_identity_clause():
    """KNOWN-BAD: node names carry digits too (NODE_12_length_406707_cov_34.08)."""
    row = "| ● ctg13_108 | NODE_12_length_406707_cov_34.08 | no hit | CONFIRM |"
    stripped = msg._s4_strip_locus(row)
    assert msg._S4_PCTID_RE.search(stripped) is None, stripped
