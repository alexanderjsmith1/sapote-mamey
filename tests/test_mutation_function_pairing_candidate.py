from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("pairing_probe", Path(__file__).resolve().parents[1] / "tools/gate_mutation_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def row(source="tools/example.py", old="return True", tests="tests/test_example.py"):
    return dict(id="CUSTOM:EXAMPLE", source=source, old=old, new="return False", tests=tests)


def setup_source(tmp_path, text="def example_gate():\n    return True\n"):
    (tmp_path / "tools").mkdir(exist_ok=True)
    (tmp_path / "tools/example.py").write_text(text)
    return tmp_path


def test_exact_contained_mutation_pairs_custom_id(tmp_path):
    setup_source(tmp_path)
    assert probe.function_mutation_id(tmp_path, row()) == "FUNC:tools/example.py:example_gate"


def test_same_name_other_file_is_not_paired(tmp_path):
    setup_source(tmp_path)
    (tmp_path / "tools/other.py").write_text("def example_gate():\n    return False\n")
    assert probe.function_mutation_id(tmp_path, row(source="tools/other.py")) is None


def test_duplicate_text_and_module_level_mutations_remain_unpaired(tmp_path):
    setup_source(tmp_path, "FLAG = True\ndef example_gate():\n    return FLAG\n")
    assert probe.function_mutation_id(tmp_path, row(old="FLAG = True")) is None
    (tmp_path / "tools/example.py").write_text("def example_gate():\n    return True\ndef other_gate():\n    return True\n")
    assert probe.function_mutation_id(tmp_path, row()) is None


def test_nested_function_does_not_claim_outer_gate(tmp_path):
    setup_source(tmp_path, "def example_gate():\n    def helper():\n        return True\n    return helper()\n")
    assert probe.function_mutation_id(tmp_path, row()) == "FUNC:tools/example.py:helper"


def test_unsafe_source_and_missing_tests_are_unpaired(tmp_path):
    setup_source(tmp_path)
    assert probe.function_mutation_id(tmp_path, row(source=str(tmp_path / "tools/example.py"))) is None
    assert probe.function_mutation_id(tmp_path, row(tests="")) is None


def test_alias_preserves_failed_baseline_instead_of_claiming_detection(tmp_path):
    setup_source(tmp_path)
    item=dict(id="FUNC:tools/example.py:example_gate",kind="function",source="tools/example.py")
    result=dict(id="CUSTOM:EXAMPLE", classification="HOLD_BASELINE_FAILED", mutation_status="NOT_RUN", tests="tests/test_example.py",log="baseline.log")
    aliases=probe.inventory_results(tmp_path,[row()],[result],[item])
    assert aliases[0]["classification"] == "PAIRED_HOLD_BASELINE_FAILED"
    assert aliases[0]["paired_mutation_ids"] == "CUSTOM:EXAMPLE"


def test_no_hardcoded_inventory_suppression(tmp_path):
    item=dict(id="FUNC:mamey/rggmci.py:_geometry_gate",kind="function",source="mamey/rggmci.py")
    assert probe.inventory_results(tmp_path,[],[],[item])[0]["classification"] == "UNPAIRED"
