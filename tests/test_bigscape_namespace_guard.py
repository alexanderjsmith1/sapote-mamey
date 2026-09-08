"""The frozen 126-case BiG-SCAPE namespace acceptance denominator."""
import ast
import hashlib
import importlib.util
import os
import sqlite3
from pathlib import Path

import pytest

from mamey import bigscape_namespace as ns

ROOT = Path(__file__).resolve().parents[1]
CONSUMERS = (
    "tools/bigscape_ingest_to_mamey.py", "tools/bigscape_cross_strain.py",
    "mamey/interactive_figures/bigscape_extension.py", "tools/antismash_bigscape_join.py",
    "tools/bigslice_query.py", "tools/bigscape_known_novel.py", "mamey/cohort_context.py",
    "tools/bigscape_mibig_anchors.py", "tools/bigscape_family_domains.py",
    "tools/strain_bigscape_report.py", "mamey/modeb_cards.py",
    "tools/bigscape_merge_anchors.py", "mamey/modeb_structure_gate.py",
)
MATRIX_CASES = ("valid", "bare", "run_mismatch", "cutoff_mismatch", "exact_duplicate", "conflict", "typed")


def _row(run="7", cutoff="0.5", family="fam/α", locator="SYN:NODE_1.region001"):
    identity = ns.build_family_identity(run, cutoff, family)
    return {
        "run_id": str(identity.run_id), "normalized_cutoff": identity.normalized_cutoff,
        "family_id": identity.family_id, "qualified_family_id": identity.qualified_family_id,
        "gcf_namespace": identity.gcf_namespace, "locator": locator, "payload": "same",
    }


@pytest.mark.parametrize("case", ("canonical", "zero_negative", "bool_float", "leading_whitespace", "malformed"))
def test_atg01_shared_run_grammar(case):
    if case == "canonical":
        assert ns.normalize_run_id(7) == ns.normalize_run_id("7") == 7; return
    values = {"zero_negative": (0, -1), "bool_float": (True, 1.0),
              "leading_whitespace": ("01", " 1"), "malformed": (None, "x")}[case]
    for value in values:
        with pytest.raises(ns.NamespaceError, match="RUN_ID_INVALID"):
            ns.normalize_run_id(value)


@pytest.mark.parametrize("case", ("equivalent", "distinct", "nonfinite_malformed", "zero_negative", "above_one"))
def test_atg02_shared_decimal_grammar(case):
    if case == "equivalent":
        assert {ns.normalize_cutoff(x) for x in ("0.50", "0.5", "5E-1", "0.5000")} == {"0.5"}; return
    if case == "distinct":
        assert ns.normalize_cutoff("0.5001") != ns.normalize_cutoff("0.5"); return
    values = {"nonfinite_malformed": ("NaN", "abc"), "zero_negative": ("0", "-0.1"),
              "above_one": ("1.0001", 2)}[case]
    for value in values:
        with pytest.raises(ns.NamespaceError, match="CUTOFF_INVALID"):
            ns.normalize_cutoff(value)


@pytest.mark.parametrize("case", ("roundtrip", "empty", "boundary_space", "controls_newline", "invalid_encoding"))
def test_atg03_shared_literal_grammar(case):
    if case == "roundtrip":
        value = "α family/?#% ~._-"
        assert ns.parse_family_identity(ns.qualified_family_id(2, "0.4", value)).family_id == value; return
    if case == "invalid_encoding":
        with pytest.raises(ns.NamespaceError, match="QUALIFIED_ID_INVALID"):
            ns.parse_family_identity("bigscape-gcf:v1/run/2/cutoff/0.4/family/%FF")
        return
    values = {"empty": ("",), "boundary_space": (" x", "x "),
              "controls_newline": ("x\u0000y", "x\ny")}[case]
    for value in values:
        with pytest.raises(ns.NamespaceError, match="FAMILY_ID_INVALID"):
            ns.build_family_identity(2, "0.4", value)


@pytest.mark.parametrize("case", ("roundtrip", "bad_prefix", "component_mismatch"))
def test_atg04_qualified_build_parse(case):
    identity = ns.build_family_identity(3, "0.30", "fam7")
    if case == "roundtrip":
        assert ns.parse_family_identity(identity.qualified_family_id) == identity; return
    if case == "bad_prefix":
        with pytest.raises(ns.NamespaceError, match="QUALIFIED_ID_INVALID"):
            ns.parse_family_identity(identity.qualified_family_id.replace("v1", "v2", 1))
        return
    row = _row(); row["family_id"] = "other"
    with pytest.raises(ns.NamespaceError, match="QUALIFIED_COMPONENT_MISMATCH"):
        ns.validate_membership_row(row)


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("case", MATRIX_CASES)
def test_atg05_consumer_seven_case_matrix(consumer, case):
    source = (ROOT / consumer).read_text(encoding="utf-8")
    assert "bigscape_namespace" in source
    row = _row()
    if case == "valid":
        assert ns.validate_membership_rows([row], key_fields=("locator",))[0]["family_id"] == "fam/α"
    elif case == "bare":
        with pytest.raises(ns.NamespaceError, match="LEGACY_LOCAL_ONLY_UNQUALIFIED"):
            ns.validate_membership_row({"family_id": "7", "locator": row["locator"]})
    elif case == "run_mismatch":
        with pytest.raises(ns.NamespaceError, match="RUN_ID_MISMATCH"):
            ns.validate_membership_row(row, expected_run="8")
    elif case == "cutoff_mismatch":
        with pytest.raises(ns.NamespaceError, match="CUTOFF_MISMATCH"):
            ns.validate_membership_row(row, expected_cutoff="0.6")
    elif case == "exact_duplicate":
        assert len(ns.validate_membership_rows([row, dict(row)], key_fields=("locator",))) == 1
    elif case == "conflict":
        other = _row(family="other")
        with pytest.raises(ns.NamespaceError, match="DUPLICATE_CONFLICT"):
            ns.validate_membership_rows([row, other], key_fields=("locator",))
    else:
        try:
            ns.validate_membership_row({"family_id": "7"})
        except ns.NamespaceError as error:
            text = ns.public_error(error)
            assert text.startswith("BIGSCAPE_NAMESPACE_ERROR[") and "/Users/" not in text and "Traceback" not in text


@pytest.mark.parametrize("case", ("insertion_hash", "product_tie", "member_tie", "staged_failure", "output_collision", "stdout_redaction", "receipt_redaction", "multi_output_noncreation"))
def test_atg06_global_order_and_transaction(case, tmp_path, monkeypatch):
    if case in {"insertion_hash", "product_tie", "member_tie"}:
        rows = [_row(family="b", locator="S:B"), _row(family="a", locator="S:A")]
        first = ns.validate_membership_rows(rows, key_fields=("locator",))
        second = ns.validate_membership_rows(reversed(rows), key_fields=("locator",))
        assert hashlib.sha256(repr(first).encode()).digest() == hashlib.sha256(repr(second).encode()).digest(); return
    if case == "staged_failure":
        target = tmp_path / "target"; target.write_text("old")
        monkeypatch.setattr(ns.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("stop")))
        with pytest.raises(OSError): ns.atomic_write_text(target, "new")
        assert target.read_text() == "old"; return
    if case == "output_collision":
        row = _row(); other = dict(row, payload="different")
        with pytest.raises(ns.NamespaceError, match="DUPLICATE_CONFLICT"):
            ns.validate_membership_rows([row, other], key_fields=("locator",))
        return
    if case in {"stdout_redaction", "receipt_redaction"}:
        message = ns.public_error(ns.NamespaceError("TEST", "portable refusal"))
        assert message == "BIGSCAPE_NAMESPACE_ERROR[TEST]: portable refusal" and str(tmp_path) not in message; return
    output = tmp_path / "must_not_exist.tsv"
    spec = importlib.util.spec_from_file_location("cross_guard", ROOT / "tools/bigscape_cross_strain.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.main(["--db", "unused", "--out", str(output), "--run-id", "01"]) == 2
    assert not output.exists()


@pytest.mark.parametrize("case", ("detect", "inspect_only", "no_inference", "regeneration_required", "qualified_admitted"))
def test_atg07_legacy_migration(case):
    bare = {"family_id": "7", "locator": "S:L"}
    if case in {"detect", "inspect_only", "no_inference", "regeneration_required"}:
        with pytest.raises(ns.NamespaceError, match="LEGACY_LOCAL_ONLY_UNQUALIFIED"):
            ns.validate_membership_row(bare)
    else:
        assert ns.validate_membership_row(_row()).qualified_family_id.startswith("bigscape-gcf:v1/")


@pytest.mark.parametrize("case", ("stdlib_leaf", "no_cycle", "direct_tool_import", "manifest_parity"))
def test_atg08_import_and_accretion(case):
    owner = ROOT / "mamey/bigscape_namespace.py"
    tree = ast.parse(owner.read_text(encoding="utf-8"))
    imported = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imported |= {str(node.module or "").split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    if case == "stdlib_leaf":
        assert not ({"numpy", "pandas", "matplotlib", "mamey"} & imported)
    elif case == "no_cycle":
        assert "tools" not in imported and "interactive_figures" not in imported
    elif case == "direct_tool_import":
        for relative in ("tools/bigscape_cross_strain.py", "tools/bigscape_known_novel.py"):
            spec = importlib.util.spec_from_file_location("direct_" + Path(relative).stem, ROOT / relative)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    else:
        manifest = {line.split("\t", 1)[0] for line in (ROOT / "MODULE_MANIFEST.txt").read_text().splitlines() if line.startswith("mamey/")}
        actual = {str(path.relative_to(ROOT)) for path in (ROOT / "mamey").rglob("*.py")}
        assert actual == manifest
