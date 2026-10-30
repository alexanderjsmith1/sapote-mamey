"""An unreadable register is unmeasured; a valid empty register is observed zero."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "judgment_receipt_unknown_461", ROOT / "tools/sapote_judgment_receipt.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _receipt(module, monkeypatch, tmp_path, register, raw=2, legacy=False):
    package = tmp_path / "package"
    package.mkdir(exist_ok=True)
    (package / "manifest.json").write_text(json.dumps({"bgc_counts": {"raw": raw}}))
    output = tmp_path / "receipt.json"
    args = ["sapote_judgment_receipt.py", "--package", str(package), "--out", str(output)]
    if register is not None:
        args.extend(["--register", str(register)])
    if legacy:
        args.extend(["--modeb", str(tmp_path / "cards" / "*.md")])
    monkeypatch.setattr(module.sys, "argv", args)
    # Isolate the card-count gate from unrelated suite contents.
    monkeypatch.setattr(module, "suite_pass", lambda *args: (True, []))
    with pytest.raises(SystemExit) as exc:
        module.main()
    return json.loads(output.read_text()), exc.value.code


def test_missing_register_file_keeps_count_unknown_and_names_path(monkeypatch, tmp_path):
    module = _load()
    register = tmp_path / "PUBLIC_EXAMPLE_judgment_register.json"
    receipt, code = _receipt(module, monkeypatch, tmp_path, register, raw=0)
    assert receipt["modeb_cards_written"] is None
    assert receipt["modeb_card_count_status"] == "UNKNOWN"
    assert receipt["judgment_register_status"] == "MISSING"
    assert receipt["judgment_register_path"] == str(register)
    assert str(register) in receipt["judgment_register_error"]
    assert receipt["modeb_complete"] is False
    assert receipt["gold_completeness"] == "JUDGMENT_PENDING" and code == 1


def test_package_without_register_reports_expected_pattern(monkeypatch, tmp_path):
    module = _load()
    register_dir = tmp_path / "registers"
    register_dir.mkdir()
    receipt, _ = _receipt(module, monkeypatch, tmp_path, register_dir)
    assert receipt["modeb_cards_written"] is None
    assert receipt["judgment_register_path"] == str(register_dir / "*_judgment_register.json")
    assert receipt["judgment_register_path"] in receipt["judgment_register_error"]


@pytest.mark.parametrize("payload", [b"not json", b"\xff"])
def test_unreadable_register_keeps_count_unknown(monkeypatch, tmp_path, payload):
    module = _load()
    register = tmp_path / "PUBLIC_EXAMPLE_judgment_register.json"
    register.write_bytes(payload)
    receipt, code = _receipt(module, monkeypatch, tmp_path, register)
    assert receipt["modeb_cards_written"] is None
    assert receipt["register_complete_bgcs"] is None
    assert receipt["register_total_bgcs"] is None
    assert receipt["judgment_register_status"] == "UNREADABLE"
    assert str(register) in receipt["judgment_register_error"]
    assert receipt["modeb_complete"] is False and code == 1


@pytest.mark.parametrize("payload", [[], {}, {"complete_bgcs": -1, "total_bgcs": 2},
                                     {"complete_bgcs": "2", "total_bgcs": 2},
                                     {"complete_bgcs": True, "total_bgcs": 2}])
def test_invalid_register_counts_are_unknown(monkeypatch, tmp_path, payload):
    module = _load()
    register = tmp_path / "PUBLIC_EXAMPLE_judgment_register.json"
    register.write_text(json.dumps(payload))
    receipt, code = _receipt(module, monkeypatch, tmp_path, register)
    assert receipt["modeb_cards_written"] is None
    assert receipt["judgment_register_status"] == "INVALID"
    assert str(register) in receipt["judgment_register_error"]
    assert receipt["modeb_complete"] is False and code == 1


@pytest.mark.parametrize("raw", [0, 2])
def test_valid_empty_register_is_observed_zero(monkeypatch, tmp_path, raw):
    module = _load()
    register = tmp_path / "PUBLIC_EXAMPLE_judgment_register.json"
    register.write_text(json.dumps({"complete_bgcs": 0, "total_bgcs": raw}))
    receipt, code = _receipt(module, monkeypatch, tmp_path, register, raw=raw)
    assert receipt["modeb_cards_written"] == 0
    assert receipt["register_complete_bgcs"] == 0
    assert receipt["register_total_bgcs"] == raw
    assert receipt["modeb_complete"] is (raw == 0)
    assert code == (0 if raw == 0 else 1)


def test_valid_complete_register_preserves_existing_completion(monkeypatch, tmp_path):
    module = _load()
    register = tmp_path / "PUBLIC_EXAMPLE_judgment_register.json"
    register.write_text(json.dumps({"complete_bgcs": 2, "total_bgcs": 2}))
    receipt, code = _receipt(module, monkeypatch, tmp_path, register)
    assert receipt["modeb_cards_written"] == 2
    assert receipt["modeb_complete"] is True
    assert receipt["gold_completeness"] == "COMPLETE" and code == 0
    assert module.cards_from_register(str(register)) == (2, 2)


def test_valid_legacy_count_remains_available_if_register_missing(monkeypatch, tmp_path):
    module = _load()
    register = tmp_path / "PUBLIC_EXAMPLE_judgment_register.json"
    monkeypatch.setattr(module, "count_modeb_cards", lambda *args, **kwargs: 2)
    receipt, code = _receipt(module, monkeypatch, tmp_path, register, legacy=True)
    assert receipt["modeb_cards_written"] == 2
    assert receipt["modeb_card_source"] == "file_glob_regex"
    assert receipt["modeb_complete"] is True and code == 0


def test_no_count_source_is_unknown_not_observed_zero(monkeypatch, tmp_path):
    module = _load()
    receipt, code = _receipt(module, monkeypatch, tmp_path, None, raw=0)
    assert receipt["modeb_cards_written"] is None
    assert receipt["modeb_card_count_status"] == "UNKNOWN"
    assert receipt["modeb_card_source"] == "none"
    assert receipt["judgment_register_status"] == "NOT_REQUESTED"
    assert receipt["modeb_complete"] is False and code == 1


def test_failed_legacy_fallback_does_not_supply_a_zero_count(monkeypatch, tmp_path):
    module = _load()
    register = tmp_path / "PUBLIC_EXAMPLE_judgment_register.json"

    def unavailable(*args, **kwargs):
        raise RuntimeError("structure gate unavailable")

    monkeypatch.setattr(module, "count_modeb_cards", unavailable)
    receipt, code = _receipt(module, monkeypatch, tmp_path, register, raw=0, legacy=True)
    assert receipt["modeb_cards_written"] is None
    assert receipt["modeb_card_count_status"] == "UNKNOWN"
    assert receipt["modeb_card_source"] == "file_glob_structure_gate_error"
    assert receipt["modeb_card_validation_error"] == "structure gate unavailable"
    assert receipt["modeb_complete"] is False and code == 1
