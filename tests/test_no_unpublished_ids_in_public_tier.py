import importlib.util
import re, pathlib, pytest

from mamey.privacy_profile import PublicExportIdentifier, PublicExportPolicy


ROOT = pathlib.Path(__file__).resolve().parent.parent
AS_RE = re.compile(r"(?<![A-Za-z])AS-[0-9]{2,4}")
TEXT_EXT = {".md",".csv",".py",".cff",".txt",".json",".sh",".yaml",".yml",".toml",".cfg",".ini"}


def _is_private_tier():
    return (ROOT/"private").is_dir() or (ROOT/"BUNDLE_FINGERPRINT.txt").is_file()


# v9.7.409 V1: `test_as_mention_inventory` (an `assert True` that wrote to /tmp) was DELETED. A test that
# cannot fail is not a gate (GOVERNANCE_DECISIONS.json GOV-002 rationale). AS- identifiers are PUBLIC per
# GOV-001, so an enforced AS- scan would be wrong; the withheld classes (AJS-/PENDING-, personal paths,
# codenames) are enforced by tests/test_mamey_source_cohort_id_guard_v97401.py (engine source) and by
# tools/public_release_audit.py --strict-source-disclosure (the cut).


def test_public_policy_rejects_synthetic_host_site_and_collaborator_tokens(tmp_path):
    """Non-strain private metadata is covered by the portable literal policy.

    Values are deliberately synthetic. Real host, collection-site, or
    collaborator rows must never be copied into a public-tier regression
    fixture merely to prove the release boundary.
    """
    tool = ROOT / "tools" / "public_release_audit.py"
    spec = importlib.util.spec_from_file_location("public_release_audit_f8", tool)
    audit = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(audit)

    tree = tmp_path / "public-tree"
    (tree / "mamey").mkdir(parents=True)
    (tree / "mamey" / "__init__.py").write_text('__version__ = "1.0.0"\n', encoding="utf-8")
    (tree / "BUILD_STAMP.txt").write_text("build=synthetic\n", encoding="utf-8")
    (tree / "docs").mkdir()

    synthetic = {
        "private-host": "SYNTHETIC-HOST-ALPHA",
        "private-site": "SYNTHETIC-SITE-BRAVO",
        "private-collaborator": "SYNTHETIC-COLLABORATOR-CHARLIE",
    }
    (tree / "docs" / "metadata.md").write_text(
        "\n".join(synthetic.values()) + "\n", encoding="utf-8"
    )
    policy = PublicExportPolicy(
        excluded_root_names=frozenset(),
        excluded_relative_paths=frozenset(),
        private_identifiers=tuple(
            PublicExportIdentifier(identifier_id, literal)
            for identifier_id, literal in synthetic.items()
        ),
        allowlisted_occurrences=(),
    )

    findings = audit.audit(tree, policy)
    for identifier_id in synthetic:
        assert any(
            f"PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_CONTENT: {identifier_id}: docs/metadata.md" in item
            for item in findings
        )
