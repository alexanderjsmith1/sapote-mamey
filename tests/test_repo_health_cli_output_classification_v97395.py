import ast
import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_repo_health():
    spec = importlib.util.spec_from_file_location(
        "repo_health_v97395", ROOT / "tools" / "repo_health.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phylo_place_is_explicit_operator_cli_output_surface():
    repo_health = _load_repo_health()
    assert "phylo_place.py" in repo_health.CLI_TOOL_EXCLUDE_FILES


def test_gene_first_cli_does_not_add_bare_print_debt():
    source = (ROOT / "mamey" / "mode_b" / "gene_first_explore.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
        for node in ast.walk(tree)
    )


def test_gene_first_cli_still_emits_one_json_receipt(monkeypatch, capsys):
    from mamey.mode_b import gene_first_explore

    expected = {"schema": "synthetic/1", "status": "PASS"}
    monkeypatch.setattr(
        gene_first_explore,
        "run_gene_first_exploration",
        lambda **kwargs: expected,
    )
    args = Namespace(
        package="package",
        strain="SYNTH-001",
        full_node="NODE_1_length_1000_cov_10.0",
        region="region001",
        bgc_alias="BGC001",
        out="output",
        gene_table=None,
        evidence_index=None,
    )
    assert gene_first_explore.gene_first_command(args) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected
    assert captured.err == ""
