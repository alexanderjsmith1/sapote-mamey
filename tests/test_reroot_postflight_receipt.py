"""Hermetic synthetic tests for the neutral reroot/postflight receipt contract."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "reroot_postflight_receipt.py"
SPEC = importlib.util.spec_from_file_location("reroot_postflight_receipt", TOOL)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


GOOD = "((Alpha_one:0.1,Beta_two:0.2)90:0.3,Gamma_OUTGROUP:0.4);\n"


def run(tmp_path, tree_text=GOOD, outgroup="Gamma_OUTGROUP", replace=False):
    input_path = tmp_path / "input.tree"
    output_path = tmp_path / "rooted.tree"
    receipt_path = tmp_path / "receipt.json"
    input_path.write_text(tree_text, encoding="utf-8")
    argv = [
        str(input_path),
        "--outgroup", outgroup,
        "--rooted-output", str(output_path),
        "--receipt", str(receipt_path),
        "--locator-root", str(tmp_path),
    ]
    if replace:
        argv.append("--replace")
    code = mod.main(argv)
    return code, output_path, receipt_path, json.loads(receipt_path.read_text(encoding="utf-8"))


def sha256_and_bytes(path):
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def portable_argv(input_path, output_path, receipt_path, locator_root, *extra):
    return [
        str(input_path), "--outgroup", "Gamma_OUTGROUP",
        "--rooted-output", str(output_path), "--receipt", str(receipt_path),
        "--locator-root", str(locator_root), *extra,
    ]


def run_cli(*argv, no_site=False):
    command = [sys.executable]
    if no_site:
        command.append("-S")
    command.extend([str(TOOL), *map(str, argv)])
    return subprocess.run(command, text=True, capture_output=True, check=False)


def test_successful_exact_outgroup_records_hashes_and_root_state(tmp_path):
    code, output, receipt_path, receipt = run(tmp_path)
    assert code == 0
    assert receipt["state"] == "PASS"
    assert receipt["resolved_outgroup"] == {
        "match_count": 1,
        "matches": ["Gamma_OUTGROUP"],
        "root_child_after_reroot": True,
        "state": "RESOLVED_UNIQUE",
    }
    assert receipt["tip_checks"]["tip_set_parity"]["parity"] is True
    assert receipt["input_tree"]["sha256"] and receipt["input_tree"]["bytes"] > 0
    assert receipt["rooted_output"]["sha256"] and receipt["rooted_output"]["bytes"] == output.stat().st_size
    assert receipt["tool"]["version"] == mod.TOOL_VERSION
    assert receipt["parameters"]["outgroup_match_mode"] == "EXACT_TIP_LABEL"
    assert receipt["locator_contract"]["absolute_locator_policy"] == "FORBIDDEN_IN_RECEIPT"
    assert receipt["input_tree"]["locator"] == "input.tree"
    assert receipt["rooted_output"]["requested_locator"] == "rooted.tree"
    assert receipt["receipt_locator"] == "receipt.json"
    assert "NO PHYLOGENETIC" in receipt["claim_ceiling"]
    assert receipt_path.is_file()


def test_success_console_uses_logical_locators_only(tmp_path, capsys):
    code, output, receipt_path, _ = run(tmp_path)
    captured = capsys.readouterr()
    assert code == 0 and output.exists() and receipt_path.exists()
    assert str(tmp_path) not in captured.out + captured.err
    assert "receipt=receipt.json" in captured.out
    assert "rooted_output=rooted.tree" in captured.out


def test_missing_outgroup_is_typed_failure_and_writes_no_tree(tmp_path):
    code, output, _, receipt = run(tmp_path, outgroup="Absent_tip")
    assert code == 1
    assert receipt["state"] == "FAIL"
    assert receipt["resolved_outgroup"]["state"] == "MISSING"
    assert receipt["errors"][0]["code"] == "OUTGROUP_MISSING"
    assert not output.exists()


def test_tip_set_change_detection_reports_added_and_removed_labels():
    report = mod.tip_set_report(["Alpha", "Beta", "Out"], ["Alpha", "Gamma", "Out"])
    assert report["parity"] is False
    assert report["removed"] == ["Beta"]
    assert report["added"] == ["Gamma"]
    assert report["input_sorted_tip_sha256"] != report["output_sorted_tip_sha256"]


def test_duplicate_tip_is_typed_failure(tmp_path):
    code, output, _, receipt = run(
        tmp_path,
        tree_text="(Alpha:0.1,Alpha:0.2,Gamma_OUTGROUP:0.3);\n",
    )
    assert code == 1
    assert receipt["errors"][0]["code"] == "DUPLICATE_TIP_LABEL"
    assert receipt["tip_checks"]["exact_duplicates"] == [{"count": 2, "label": "Alpha"}]
    assert not output.exists()


def test_near_duplicate_tip_is_deterministic_hold_not_collapse(tmp_path):
    code, output, _, receipt = run(
        tmp_path,
        tree_text="(Alpha-1:0.1,Alpha_1:0.2,Gamma_OUTGROUP:0.3);\n",
    )
    assert code == 0
    assert receipt["state"] == "PASS_WITH_HOLDS"
    assert receipt["holds"][0]["code"] == "NEAR_DUPLICATE_TIP_LABEL"
    assert receipt["tip_checks"]["tip_set_parity"]["parity"] is True
    assert output.exists()


def test_malformed_newick_is_typed_failure(tmp_path):
    code, output, _, receipt = run(tmp_path, tree_text="((Alpha:0.1,Beta:0.2);\n")
    assert code == 1
    assert receipt["errors"][0]["code"] == "MALFORMED_NEWICK"
    assert not output.exists()


def test_deterministic_rerun_has_exact_output_and_receipt_parity(tmp_path):
    _, output, receipt_path, _ = run(tmp_path, replace=True)
    first_output = output.read_bytes()
    first_receipt = receipt_path.read_bytes()
    _, output, receipt_path, second = run(tmp_path, replace=True)
    assert second["state"] == "PASS"
    assert output.read_bytes() == first_output
    assert receipt_path.read_bytes() == first_receipt


def test_cli_paths_with_spaces(tmp_path):
    spaced = tmp_path / "directory with spaces"
    spaced.mkdir()
    code, output, receipt_path, receipt = run(spaced)
    assert code == 0
    assert output.exists() and receipt_path.exists()
    assert receipt["input_tree"]["locator"] == "input.tree"
    assert receipt["rooted_output"]["requested_locator"] == "rooted.tree"
    assert str(spaced) not in receipt_path.read_text(encoding="utf-8")


def test_portable_receipt_redacts_absolute_private_like_paths(tmp_path):
    private_like = tmp_path / "private analyst workspace"
    private_like.mkdir()
    code, output, receipt_path, receipt = run(private_like)
    serialized = receipt_path.read_text(encoding="utf-8")
    assert code == 0 and output.exists()
    assert str(private_like) not in serialized
    assert receipt["input_tree"]["locator"] == "input.tree"
    assert receipt["locator_contract"]["locator_root_serialization"] == "NOT_SERIALIZED"


def test_outside_locator_root_is_typed_refusal_without_outside_receipt_write(tmp_path, capsys):
    runtime_dir = tmp_path / "private runtime"
    portable_root = tmp_path / "portable root"
    runtime_dir.mkdir()
    portable_root.mkdir()
    input_path = runtime_dir / "input.tree"
    output_path = runtime_dir / "rooted.tree"
    receipt_path = runtime_dir / "receipt.json"
    input_path.write_text(GOOD, encoding="utf-8")
    code = mod.main([
        str(input_path), "--outgroup", "Gamma_OUTGROUP",
        "--rooted-output", str(output_path), "--receipt", str(receipt_path),
        "--locator-root", str(portable_root),
    ])
    captured = capsys.readouterr()
    assert code == 1 and "code=LOCATOR_OUTSIDE_ROOT" in captured.out
    assert str(runtime_dir) not in captured.out + captured.err
    assert str(portable_root) not in captured.out + captured.err
    assert not receipt_path.exists()
    assert not output_path.exists()


def test_each_outside_locator_role_refuses_without_creating_receipt_or_output(tmp_path, capsys):
    root = tmp_path / "portable"
    outside = tmp_path / "private outside"
    root.mkdir()
    outside.mkdir()
    root_input = root / "input.tree"
    root_input.write_text(GOOD, encoding="utf-8")
    cases = [
        (outside / "input.tree", root / "rooted-a.tree", root / "receipt-a.json"),
        (root_input, outside / "rooted-b.tree", root / "receipt-b.json"),
        (root_input, root / "rooted-c.tree", outside / "receipt-c.json"),
    ]
    for input_path, output_path, receipt_path in cases:
        if input_path.parent == outside:
            input_path.write_text(GOOD, encoding="utf-8")
        code = mod.main(portable_argv(input_path, output_path, receipt_path, root))
        captured = capsys.readouterr()
        assert code == 1 and "code=LOCATOR_OUTSIDE_ROOT" in captured.out
        assert str(root) not in captured.out + captured.err
        assert str(outside) not in captured.out + captured.err
        assert not output_path.exists() and not receipt_path.exists()


def test_missing_locator_root_is_argparse_refusal_without_private_path_echo(tmp_path, capsys):
    input_path = tmp_path / "private input.tree"
    input_path.write_text(GOOD, encoding="utf-8")
    try:
        mod.main([
            str(input_path), "--outgroup", "Gamma_OUTGROUP",
            "--rooted-output", str(tmp_path / "rooted.tree"),
            "--receipt", str(tmp_path / "receipt.json"),
        ])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse contract
        raise AssertionError("missing --locator-root must fail")
    captured = capsys.readouterr()
    assert str(tmp_path) not in captured.out + captured.err
    assert not (tmp_path / "rooted.tree").exists()
    assert not (tmp_path / "receipt.json").exists()


def test_unexpected_failure_is_generic_in_receipt_and_default_console(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "private input.tree"
    output_path = tmp_path / "rooted.tree"
    receipt_path = tmp_path / "receipt.json"
    input_path.write_text(GOOD, encoding="utf-8")

    def raise_private_error(_tree):
        raise RuntimeError(f"private failure at {tmp_path}")

    monkeypatch.setattr(mod, "render_newick", raise_private_error)
    code = mod.main(portable_argv(input_path, output_path, receipt_path, tmp_path))
    captured = capsys.readouterr()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    serialized = receipt_path.read_text(encoding="utf-8")
    assert code == 1 and receipt["errors"][-1]["code"] == "UNEXPECTED_TOOL_ERROR"
    assert receipt["errors"][-1]["detail"] == {"diagnostic": "LOCAL_EXCEPTION_REDACTED"}
    assert str(tmp_path) not in serialized and str(tmp_path) not in captured.out + captured.err
    assert "code=UNEXPECTED_TOOL_ERROR" in captured.out
    assert not output_path.exists()


def test_local_debug_is_explicit_and_never_enters_portable_receipt(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "private input.tree"
    output_path = tmp_path / "rooted.tree"
    receipt_path = tmp_path / "receipt.json"
    input_path.write_text(GOOD, encoding="utf-8")

    def raise_private_error(_tree):
        raise RuntimeError(f"private failure at {tmp_path}")

    monkeypatch.setattr(mod, "render_newick", raise_private_error)
    code = mod.main(portable_argv(input_path, output_path, receipt_path, tmp_path, "--local-debug"))
    captured = capsys.readouterr()
    assert code == 1
    assert "LOCAL_NONPORTABLE_DIAGNOSTIC" in captured.err and str(tmp_path) in captured.err
    assert str(tmp_path) not in receipt_path.read_text(encoding="utf-8")


def test_receipt_parent_not_directory_leaves_no_orphan_output_or_traceback(tmp_path, capsys):
    input_path = tmp_path / "input.tree"
    output_path = tmp_path / "rooted.tree"
    blocked_parent = tmp_path / "blocked receipt parent"
    receipt_path = blocked_parent / "receipt.json"
    input_path.write_text(GOOD, encoding="utf-8")
    blocked_parent.write_text("not a directory", encoding="utf-8")
    code = mod.main(portable_argv(input_path, output_path, receipt_path, tmp_path))
    captured = capsys.readouterr()
    assert code == 1 and "code=RECEIPT_PARENT_UNAVAILABLE" in captured.out
    assert "Traceback" not in captured.err
    assert str(tmp_path) not in captured.out + captured.err
    assert not output_path.exists() and not receipt_path.exists()
    assert blocked_parent.read_text(encoding="utf-8") == "not a directory"


def test_preexisting_output_is_untouched_without_replace(tmp_path, capsys):
    input_path = tmp_path / "input.tree"
    output_path = tmp_path / "rooted.tree"
    receipt_path = tmp_path / "receipt.json"
    input_path.write_text(GOOD, encoding="utf-8")
    output_path.write_bytes(b"pre-existing user output\x00")
    before_identity = sha256_and_bytes(output_path)
    before_mode = output_path.stat().st_mode & 0o7777
    code = mod.main(portable_argv(input_path, output_path, receipt_path, tmp_path))
    captured = capsys.readouterr()
    assert code == 1 and "code=ROOTED_OUTPUT_EXISTS" in captured.out
    assert sha256_and_bytes(output_path) == before_identity
    assert output_path.stat().st_mode & 0o7777 == before_mode
    assert not receipt_path.exists()


def test_replace_rollback_restores_preexisting_output_bytes_and_mode(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "input.tree"
    output_path = tmp_path / "rooted.tree"
    receipt_path = tmp_path / "receipt.json"
    input_path.write_text(GOOD, encoding="utf-8")
    output_path.write_bytes(b"pre-existing user output\x00\xff")
    os.chmod(output_path, 0o640)
    before_identity = sha256_and_bytes(output_path)
    before_mode = output_path.stat().st_mode & 0o7777
    real_replace = mod.replace_temp
    calls = {"receipt": 0}

    def fail_receipt_commit(temp_path, target):
        if target == receipt_path and calls["receipt"] == 0:
            calls["receipt"] += 1
            raise OSError(f"private receipt commit failure at {tmp_path}")
        return real_replace(temp_path, target)

    monkeypatch.setattr(mod, "replace_temp", fail_receipt_commit)
    code = mod.main(portable_argv(input_path, output_path, receipt_path, tmp_path, "--replace"))
    captured = capsys.readouterr()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert code == 1 and receipt["errors"][-1]["code"] == "ARTIFACT_TRANSACTION_FAILED"
    assert receipt["errors"][-1]["detail"]["output_rollback"] == "COMPLETED"
    assert sha256_and_bytes(output_path) == before_identity
    assert output_path.stat().st_mode & 0o7777 == before_mode
    assert str(tmp_path) not in receipt_path.read_text(encoding="utf-8")
    assert str(tmp_path) not in captured.out + captured.err


def test_black_box_cli_success_and_default_console_redaction(tmp_path):
    input_path = tmp_path / "private input.tree"
    output_path = tmp_path / "rooted.tree"
    receipt_path = tmp_path / "receipt.json"
    input_path.write_text(GOOD, encoding="utf-8")
    result = run_cli(*portable_argv(input_path, output_path, receipt_path, tmp_path))
    assert result.returncode == 0
    assert str(tmp_path) not in result.stdout + result.stderr
    assert "receipt=receipt.json" in result.stdout and "rooted_output=rooted.tree" in result.stdout
    assert str(tmp_path) not in receipt_path.read_text(encoding="utf-8")


def test_black_box_cli_missing_locator_and_outside_receipt_are_nonleaking(tmp_path):
    root = tmp_path / "portable root"
    input_path = root / "private input.tree"
    output_path = root / "rooted.tree"
    receipt_path = root / "receipt.json"
    outside = tmp_path / "outside"
    root.mkdir()
    input_path.write_text(GOOD, encoding="utf-8")
    outside.mkdir()
    missing = run_cli(
        input_path, "--outgroup", "Gamma_OUTGROUP", "--rooted-output", output_path,
        "--receipt", receipt_path,
    )
    assert missing.returncode == 2 and str(tmp_path) not in missing.stdout + missing.stderr
    outside_receipt = outside / "receipt.json"
    result = run_cli(*portable_argv(input_path, output_path, outside_receipt, root))
    assert result.returncode == 1 and "code=LOCATOR_OUTSIDE_ROOT" in result.stdout
    assert str(tmp_path) not in result.stdout + result.stderr
    assert not output_path.exists() and not outside_receipt.exists()


def test_black_box_cli_receipt_parent_and_preexisting_output_safety(tmp_path):
    input_path = tmp_path / "input.tree"
    output_path = tmp_path / "rooted.tree"
    input_path.write_text(GOOD, encoding="utf-8")
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("file", encoding="utf-8")
    blocked = run_cli(*portable_argv(input_path, output_path, blocked_parent / "receipt.json", tmp_path))
    assert blocked.returncode == 1 and "code=RECEIPT_PARENT_UNAVAILABLE" in blocked.stdout
    assert "Traceback" not in blocked.stderr and str(tmp_path) not in blocked.stdout + blocked.stderr
    assert not output_path.exists()
    output_path.write_bytes(b"pre-existing\x00bytes")
    before = sha256_and_bytes(output_path)
    existing = run_cli(*portable_argv(input_path, output_path, tmp_path / "receipt.json", tmp_path))
    assert existing.returncode == 1 and "code=ROOTED_OUTPUT_EXISTS" in existing.stdout
    assert sha256_and_bytes(output_path) == before


def test_black_box_cli_no_biopython_is_typed_and_nonleaking(tmp_path):
    input_path = tmp_path / "input.tree"
    output_path = tmp_path / "rooted.tree"
    receipt_path = tmp_path / "receipt.json"
    input_path.write_text(GOOD, encoding="utf-8")
    result = run_cli(*portable_argv(input_path, output_path, receipt_path, tmp_path), no_site=True)
    assert result.returncode == 1 and "code=BIOPYTHON_UNAVAILABLE" in result.stdout
    assert str(tmp_path) not in result.stdout + result.stderr
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["errors"][-1]["detail"] == "OPTIONAL_DEPENDENCY_IMPORT_REDACTED"
    assert not output_path.exists()
