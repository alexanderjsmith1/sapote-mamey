"""P5 acceptance: the public-release audit FAILS CLOSED on a planted leak.

These are hermetic: each builds a minimal tree with the Sapote identity anchors
(`mamey/__init__.py` + `BUILD_STAMP.txt`) so the audit proceeds past root-validation into the
whole-tree scan. Whether the LIVE bundle is clean is a CI question against the actual public
artifact, not a unit test asserting the internal dev tree is leak-free.
"""
import shutil, subprocess, sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.public
_ROOT = Path(__import__("mamey").__file__).parent.parent
_AUDIT = _ROOT / "tools" / "public_release_audit.py"


def _run(tree):
    args = (tree,)
    import json
    profile = Path(args[0]).parent / "operator_policy.json"
    profile.write_text(json.dumps({
        "schema_version": "sapote_privacy_profile_v1", "profile_id": "synthetic-cli-policy",
        "default_tier": "INTERNAL", "tiers": [{"tier_id": "INTERNAL", "public_export": False}],
        "strain_assignments": [], "public_export_policy": {"private_identifiers": [
            {"identifier_id": "synthetic-marker", "literal": "SYNTHETIC_PRIVATE_TEST_MARKER"},
            {"identifier_id": "synthetic-marker-two", "literal": "regression_review"}]}}))
    return subprocess.run([sys.executable, str(_AUDIT), str(tree), "--privacy-profile", str(profile)], capture_output=True, text=True)


def _valid_tree(tmp_path):
    """A minimal tree that passes root-validation (anchors present) and is otherwise clean."""
    tree = tmp_path / "t"
    (tree / "mamey" / "data").mkdir(parents=True)
    (tree / "tools").mkdir()
    (tree / "mamey" / "__init__.py").write_text("__version__ = '0.0.0'\n")
    (tree / "BUILD_STAMP.txt").write_text("version=0.0.0\nbuild=test\nengine=0.0.0\n")
    shutil.copy(_AUDIT, tree / "tools" / "public_release_audit.py")
    return tree


def test_missing_root_fails_closed(tmp_path):
    r = _run(tmp_path / "does-not-exist")
    assert r.returncode == 1 and "root does not exist" in r.stdout


def test_root_without_anchors_fails_closed(tmp_path):
    bare = tmp_path / "bare"; (bare / "mamey").mkdir(parents=True)
    r = _run(bare)
    assert r.returncode == 1 and "identity anchor" in r.stdout


def test_clean_valid_tree_passes(tmp_path):
    tree = _valid_tree(tmp_path)
    (tree / "mamey" / "engine.py").write_text("def f():\n    return 1\n")
    r = _run(tree)
    assert r.returncode == 0, r.stdout


def test_empty_file_is_not_a_finding(tmp_path):
    # regression: a legitimately-empty file must not be reported as "unreadable"
    tree = _valid_tree(tmp_path)
    (tree / "mamey" / "empty.py").write_text("")
    r = _run(tree)
    assert r.returncode == 0, r.stdout
    assert "unreadable" not in r.stdout


def test_planted_roster_fails(tmp_path):
    tree = _valid_tree(tmp_path)
    (tree / "mamey" / "data" / "strain_genus.csv").write_text("strain,genus\nAS-999,Streptomyces\n")
    r = _run(tree)
    assert r.returncode == 1 and "strain_genus.csv" in r.stdout


def test_planted_personal_path_fails(tmp_path):
    tree = _valid_tree(tmp_path)
    (tree / "mamey" / "leak.py").write_text('ROOT = "/Users/someone/some_workspace/"\n')
    r = _run(tree)
    assert r.returncode == 1 and "personal path" in r.stdout


def test_planted_codename_fails(tmp_path):
    tree = _valid_tree(tmp_path)
    (tree / "mamey" / "note.py").write_text('# staged in the regression_review audit lane\n')
    r = _run(tree)
    assert r.returncode == 1 and "PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_CONTENT" in r.stdout


def _container_path_audit_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("container_path_audit", _AUDIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("relative_path,path", [
    ("docs/history/retired_458/RIPPER_ARCHIVED_LOCAL_CONTRACT.md", "/home/mnt/gbk/*.gbk"),
    ("docs/history/retired_458/RIPPER_ARCHIVED_LOCAL_CONTRACT.md", "/home/mnt/faa/query.faa"),
    ("docs/RIPPER_OPTIONAL_ADAPTER.md", "/home/mnt/te_accessions.txt"),
])
def test_exact_documented_container_paths_are_not_personal(relative_path, path):
    module = _container_path_audit_module()
    assert not module._personal_path_in_line(f"fixed container `{path}`", relative_path)
    assert module._personal_path_in_line(f"fixed container `{path}`", "docs/OTHER.md")
    assert module._personal_path_in_line(f"fixed container `{path}.backup`", relative_path)
    assert module._personal_path_in_line(f"fixed container `{path}/../private`", relative_path)
    assert module._personal_path_in_line(f"fixed container {path}", relative_path)
    assert module._personal_path_in_line(f"prefixed `/srv/private{path}`", relative_path)
    assert module._personal_path_in_line(f"unquoted {path}`", relative_path)
    assert module._personal_path_in_line(
        f"fixed container `{path}`; personal /home/example-owner/work", relative_path)
    assert module._personal_path_in_line(
        f"fixed container `{path}`; personal /Users/example-owner/work", relative_path)
    # Bare operator-private words are tested through selected policy, not path syntax.


def test_documented_container_examples_pass_the_default_audit(tmp_path):
    tree = _valid_tree(tmp_path)
    (tree / "docs" / "history" / "retired_458").mkdir(parents=True)
    (tree / "docs" / "history" / "retired_458" / "RIPPER_ARCHIVED_LOCAL_CONTRACT.md").write_text(
        "fixed container `/home/mnt/gbk/*.gbk` and `/home/mnt/faa/query.faa`\n")
    (tree / "docs" / "RIPPER_OPTIONAL_ADAPTER.md").write_text(
        "container command `./ripper_run.sh /home/mnt/te_accessions.txt`\n")
    result = _run(tree)
    assert result.returncode == 0, result.stdout


def test_personal_path_beside_a_container_example_still_fails(tmp_path):
    tree = _valid_tree(tmp_path)
    (tree / "docs").mkdir()
    (tree / "docs" / "RIPPER_OPTIONAL_ADAPTER.md").write_text(
        "container `/home/mnt/te_accessions.txt`; personal /home/example-owner/work\n")
    result = _run(tree)
    assert result.returncode == 1 and "personal path" in result.stdout
