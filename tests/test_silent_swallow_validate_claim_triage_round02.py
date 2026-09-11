"""Round-02 regressions for unreadable judgment and triage evidence.

Every synthetic individual locus uses the complete identity
TEST-001 / NODE_1_length_50000_cov_20.0 / region001 / BGC001.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

from mamey.cli import claim_safety_command
from mamey.validate import validate_package


STRAIN = "TEST-001"
NODE = "NODE_1_length_50000_cov_20.0"
REGION = "region001"
BGC = "BGC001"
IDENTITY = f"{STRAIN} / {NODE} / {REGION} / {BGC}"

CARD_TEXT = (
    "# Mode B card\n\n"
    f"## §1 Complete identity\n{IDENTITY}. This record remains a class-level hypothesis.\n\n"
    "## §2 Assembly context\nThe bounded contig context is described with explicit uncertainty, "
    "source provenance, neighboring genes, boundary status, and judgment deferred.\n\n"
    "## §3 Evidence synthesis\nIndependent observations support only a candidate biosynthetic "
    "capacity statement; expression, structure, activity, and exact product identity remain unknown.\n"
)


def _gold_package(root: Path, *, with_card: bool = True) -> tuple[Path, Path | None]:
    root.mkdir()
    (root / "manifest.json").write_text(
        json.dumps({
            "mode": "gold",
            "strain_id": STRAIN,
            "bgcs": [{
                "bgc_id": BGC,
                "strain": STRAIN,
                "full_node_or_contig": NODE,
                "region": REGION,
                "bgc_alias": BGC,
                "identity_display": IDENTITY,
            }],
        }),
        encoding="utf-8",
    )
    (root / f"{STRAIN}_2_inventory.csv").write_text(
        "Strain,Full_node_or_contig,Region,BGC_ID,Depth_floor,Identity_display\n"
        f"{STRAIN},{NODE},{REGION},{BGC},full_mode_b,{IDENTITY}\n",
        encoding="utf-8",
    )
    if not with_card:
        return root, None
    card_dir = root / "mode_b"
    card_dir.mkdir()
    card = card_dir / f"{STRAIN}_{NODE}_{REGION}_{BGC}_mode_b.md"
    card.write_text(CARD_TEXT, encoding="utf-8")
    return root, card


def _claim_args(report: Path, package: Path) -> SimpleNamespace:
    return SimpleNamespace(
        path=str(report),
        package=str(package),
        compound_names=None,
        card_id=IDENTITY,
        section="§1 Complete identity",
        misanchor_flag="",
        report=None,
        json=True,
        mode="fail",
    )


def test_unreadable_mode_b_card_fails_gold_dimension_with_typed_diagnostic(
    tmp_path, monkeypatch
):
    package, card = _gold_package(tmp_path / "package")
    original_read_text = Path.read_text
    exercised = {"count": 0}

    def unreadable_card(self, *args, **kwargs):
        if self == card and kwargs.get("errors") == "replace":
            exercised["count"] += 1
            raise PermissionError("injected unreadable completed card")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable_card)
    result = validate_package(package, gold_aware=True, write_status_receipt=False)

    # Both claim-safety-status inspection and gold-card completeness read the authored card;
    # the injection therefore proves the real shared consumer path was exercised twice.
    assert exercised["count"] == 2
    assert result["gold_completeness"] == "FAIL"
    assert result["mode_b_card_read_errors"] == [{
        "path": f"mode_b/{card.name}",
        "error_type": "PermissionError",
        "error": "injected unreadable completed card",
    }]
    assert "unreadable" in result["gold_note"].lower()


def test_absent_mode_b_card_remains_judgment_pending(tmp_path):
    package, _ = _gold_package(tmp_path / "package", with_card=False)
    result = validate_package(package, gold_aware=True, write_status_receipt=False)
    assert result["gold_completeness"] == "JUDGMENT_PENDING"
    assert result.get("mode_b_card_read_errors") in (None, [])


def test_readable_substantive_mode_b_card_still_passes_gold_dimension(tmp_path):
    package, _ = _gold_package(tmp_path / "package")
    result = validate_package(package, gold_aware=True, write_status_receipt=False)
    assert result["gold_completeness"] == "PASS"
    assert result.get("mode_b_card_read_errors") in (None, [])


def test_structure_evaluator_failure_fails_gold_with_typed_diagnostic(
    tmp_path, monkeypatch
):
    package, card = _gold_package(tmp_path / "package")
    from mamey import modeb_structure_gate
    exercised = {"count": 0}

    def broken_structure_evaluator(_card_text):
        exercised["count"] += 1
        raise RuntimeError("injected structure evaluator failure")

    monkeypatch.setattr(
        modeb_structure_gate, "extract_section_titles", broken_structure_evaluator
    )
    result = validate_package(package, gold_aware=True, write_status_receipt=False)

    assert exercised["count"] == 1
    assert result["gold_completeness"] == "FAIL"
    assert result["mode_b_card_structure_errors"] == [{
        "path": f"mode_b/{card.name}",
        "error_type": "RuntimeError",
        "error": "injected structure evaluator failure",
    }]
    assert "structure" in result["gold_note"].lower()


def test_card_seal_failure_fails_gold_with_typed_diagnostic(tmp_path, monkeypatch):
    package, card = _gold_package(tmp_path / "package")
    original_sha256 = hashlib.sha256
    exercised = {"count": 0}

    def broken_card_sha256(data=b""):
        if data == CARD_TEXT.encode("utf-8"):
            exercised["count"] += 1
            raise RuntimeError("injected card seal failure")
        return original_sha256(data)

    monkeypatch.setattr(hashlib, "sha256", broken_card_sha256)
    result = validate_package(package, gold_aware=True, write_status_receipt=False)

    assert exercised["count"] == 1
    assert result["gold_completeness"] == "FAIL"
    assert result["mode_b_card_seal_errors"] == [{
        "path": f"mode_b/{card.name}",
        "bgc_alias": BGC,
        "error_type": "RuntimeError",
        "error": "injected card seal failure",
    }]
    assert "sealed" in result["gold_note"].lower()


def _claim_package(root: Path, *, with_board: bool = True) -> tuple[Path, Path | None]:
    root.mkdir()
    if not with_board:
        return root, None
    board = root / f"{STRAIN}_4_triage_board.csv"
    board.write_text(
        "Strain,Full_node_or_contig,Region,BGC_ID,Identity_display,KCB_top\n"
        f"{STRAIN},{NODE},{REGION},{BGC},{IDENTITY},BGC0000001 | coelibactin | knownclusterblast #1\n",
        encoding="utf-8",
    )
    return root, board


def test_unreadable_triage_becomes_claim_safety_finding_and_fail_mode_refusal(
    tmp_path, monkeypatch, capsys
):
    package, board = _claim_package(tmp_path / "package")
    report = tmp_path / "claim_safe.md"
    report.write_text(
        f"# {IDENTITY}\nCapacity remains unresolved; judgment deferred.\n",
        encoding="utf-8",
    )
    original_open = Path.open
    exercised = {"count": 0}

    def unreadable_board(self, *args, **kwargs):
        if self == board:
            exercised["count"] += 1
            raise PermissionError("injected unreadable triage board")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", unreadable_board)
    rc = claim_safety_command(_claim_args(report, package))
    captured = capsys.readouterr()

    assert exercised["count"] == 1
    assert rc == 1
    payload = json.loads(captured.out[captured.out.index("{"):])
    assert payload["clean"] is False
    assert payload["findings"][0]["violation_type"] == "compound_name_evidence_unreadable"
    assert payload["findings"][0]["error_type"] == "PermissionError"
    assert "injected unreadable triage board" in payload["findings"][0]["error"]


def test_missing_triage_board_retains_explicit_heuristic_fallback(tmp_path, capsys):
    package, _ = _claim_package(tmp_path / "package", with_board=False)
    report = tmp_path / "claim_safe.md"
    report.write_text(
        f"# {IDENTITY}\nCapacity remains unresolved; judgment deferred.\n",
        encoding="utf-8",
    )
    rc = claim_safety_command(_claim_args(report, package))
    captured = capsys.readouterr()

    assert rc == 0
    assert "missing/empty triage board" in captured.err
    assert json.loads(captured.out)["clean"] is True


def test_readable_triage_uses_compound_names_and_preserves_real_refusal(tmp_path, capsys):
    package, _ = _claim_package(tmp_path / "package")
    report = tmp_path / "overclaim.md"
    report.write_text(
        f"# {IDENTITY}\nThis locus is coelibactin.\n",
        encoding="utf-8",
    )
    rc = claim_safety_command(_claim_args(report, package))
    captured = capsys.readouterr()

    assert rc == 1
    payload = json.loads(captured.out[captured.out.index("{"):])
    assert payload["clean"] is False
    assert any(f["violation_type"] == "identity_overclaim" for f in payload["findings"])
