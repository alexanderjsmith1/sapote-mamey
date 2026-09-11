"""CLAUDE_409_gate_completeness — regression tests for the three fail-open
validation-gate holes reported in development/audit/AUDIT_gate_completeness.md
(F1 `gate_exemption_injection`, F2 `gate_card_never_sealed`, F3
`gate_gold_stub_cards_pass`).

These assert the PATCHED (closed) behaviour. Before the .409 validate patch:
  * F3: 60 ~240-byte "x x x" stub cards flipped gold_completeness to PASS;
  * F2: validate never recorded any hash of the judgment deliverable card;
  * F1: a fabricated judgment/fake_verdict.json passed the reciprocal scan.
"""
import json
import hashlib

import pytest

from mamey.validate import validate_package, verify_checksums

# ~240 B of filler, no §-headings — deliberately OVER the old 200-byte size floor,
# reproducing the audit's exploit (a >200-byte stub the pre-.409 gate counted as a card).
_STUB = ("x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x\n" * 4)
_REAL = (
    "# Mode B card\n\n"
    "## §1 Identity and node/region\nStrain AS-TEST, node ctg1, region 1, BGC001. "
    "Real authored identity prose bound to one record and node/region tuple.\n\n"
    "## §2 Assembly context\nContig-level assembly context authored in real prose.\n\n"
    "## §3 Cluster architecture\nCore biosynthetic genes and tailoring described.\n\n"
    "## §4 Gene-by-gene\nPer-gene reconciliation authored with real body text.\n\n"
    "## §5 Forensic sweep\nEvidence-anchored forensic sweep authored in prose.\n"
)


def _make_gold_pkg(root, card_body):
    (root / "manifest.json").write_text(json.dumps({
        "mode": "gold", "strain_id": "AS-TEST",
        "bgcs": [{"bgc_id": "BGC001"}, {"bgc_id": "BGC002"}],
    }))
    (root / "AS-TEST_2_inventory.csv").write_text(
        "BGC_ID,Depth_floor\nBGC001,full_mode_b\nBGC002,full_mode_b\n")
    mb = root / "mode_b"
    mb.mkdir(exist_ok=True)
    (mb / "BGC001_mode_b.md").write_text(card_body)
    (mb / "BGC002_mode_b.md").write_text(card_body)
    return root


def test_f3_stub_cards_do_not_flip_gold_to_pass(tmp_path):
    """F3 `gate_gold_stub_cards_pass`: ~240-byte filler cards with no §-content
    must NOT satisfy gold completeness (was PASS via a filename+size test only)."""
    _make_gold_pkg(tmp_path, _STUB)
    r = validate_package(tmp_path, gold_aware=True)
    assert r["gold_completeness"] != "PASS"
    assert r["gold_completeness"] == "JUDGMENT_PENDING"


def test_real_cards_still_count_and_are_sealed(tmp_path):
    """No false-negative: genuine §-bearing cards still complete gold, and F2
    `gate_card_never_sealed` — validate now records a per-BGC SHA256 of each
    counted card, binding the judgment deliverable's content into the receipt."""
    _make_gold_pkg(tmp_path, _REAL)
    r = validate_package(tmp_path, gold_aware=True)
    assert r["gold_completeness"] == "PASS"
    seals = r.get("mode_b_card_seals")
    assert isinstance(seals, dict) and set(seals) == {"BGC001", "BGC002"}
    # the recorded hash is the SHA256 of the exact counted card content
    assert seals["BGC001"] == hashlib.sha256(_REAL.encode("utf-8")).hexdigest()


def test_card_swap_changes_recorded_seal(tmp_path):
    """A post-count card swap changes the recorded seal — the swap the audit
    said was previously invisible is now detectable on re-validate."""
    _make_gold_pkg(tmp_path, _REAL)
    h1 = validate_package(tmp_path, gold_aware=True)["mode_b_card_seals"]["BGC001"]
    (tmp_path / "mode_b" / "BGC001_mode_b.md").write_text(_REAL + "\n## §6 Swapped\nother\n")
    h2 = validate_package(tmp_path, gold_aware=True)["mode_b_card_seals"]["BGC001"]
    assert h1 != h2


def _sealed_pkg(root):
    (root / "a.txt").write_text("hello")
    (root / "judgment").mkdir()
    (root / "judgment" / "AS-TEST_x_mode_b.md").write_text(_REAL)  # legit authored .md
    digest = hashlib.sha256(b"hello").hexdigest()
    (root / "checksums_sha256.txt").write_text(f"{digest}  a.txt\n")
    return root


def test_f1_injected_verdict_json_is_refused(tmp_path):
    """F1 `gate_exemption_injection`: a fabricated judgment/fake_verdict.json
    dropped into the checksum-exempt judgment/ subtree must be flagged by the
    reciprocal scan (was silently exempt → validate PASS / MAMEY_COMPLETE)."""
    _sealed_pkg(tmp_path)
    assert verify_checksums(tmp_path) == []            # clean baseline
    (tmp_path / "judgment" / "fake_verdict.json").write_text('{"verdict":"PASS"}')
    errs = verify_checksums(tmp_path)
    assert any("fake_verdict.json" in e for e in errs)


def test_f1_legit_authored_md_under_judgment_stays_clean(tmp_path):
    """No false-positive: the governed judgment/ shape is authored Markdown, so a
    legit *_mode_b.md there must NOT be flagged by the new guard."""
    _sealed_pkg(tmp_path)
    errs = verify_checksums(tmp_path)
    assert not any("_mode_b.md" in e for e in errs)
    assert errs == []
