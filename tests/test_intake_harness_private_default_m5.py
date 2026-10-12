"""Parser-only privacy regression: no engine, staging or filesystem mutation."""
import argparse
import ast
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1] / "tools/intake_harness.py"

def _parse(extra):
    tree = ast.parse(HARNESS.read_text())
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    statements = []
    for node in main.body:
        statements.append(node)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "a" for t in node.targets):
            break
    namespace = {"argparse": argparse}
    # Only argparse construction and argument declarations precede parse_args.
    parser_statements = statements[:-1]
    exec(compile(ast.Module(body=parser_statements, type_ignores=[]), str(HARNESS), "exec"), namespace)
    return namespace["ap"].parse_args(["--inputs", "synthetic.zip", "--outdir", "out", "--registry", "reg.csv", "--metrics", "metrics.csv", *extra])

def test_new_batch_defaults_to_private_without_asserting_public_provenance():
    args = _parse([])
    assert args.release == "PRIVATE"
    assert args.source == "not verified"

def test_reviewed_public_override_remains_explicit():
    args = _parse(["--release", "PUBLIC", "--source", "reviewed public accession"])
    assert args.release == "PUBLIC"
    assert args.source == "reviewed public accession"

def test_resume_does_not_change_release_default():
    args = _parse(["--resume"])
    assert args.resume and args.release == "PRIVATE"
