"""Artificial text fixtures: names/classes alone pass, substantive policy failures refuse."""
from pathlib import Path
from dataclasses import replace
import sys
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import public_release_audit as audit_mod
from mamey.privacy_profile import PublicExportIdentifier, load_public_export_policy


def tree(tmp_path):
    root=tmp_path/"tree"; (root/"mamey").mkdir(parents=True)
    (root/"mamey/__init__.py").write_text('__version__ = "1.0.0"\n')
    (root/"BUILD_STAMP.txt").write_text("build=invented\n")
    (root/"docs").mkdir()
    return root


@pytest.mark.parametrize("relative,text", [
    ("docs/note.txt", "AS-705 is a label.\n"),
    ("docs/AS-705_note.md", "Name retained.\n"),
    ("mamey/data/classes.tsv", "strain\tclass\nAS-705\tNRPS\n"),
    ("tests/label.txt", "AS-705\tNRPS\n"),
    ("mamey/label.py", 'label = "AS-705"\nclass_name = "NRPS"\n'),
])
def test_names_and_class_associations_do_not_establish_disclosure(tmp_path,relative,text):
    root=tree(tmp_path); p=root/relative; p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    assert audit_mod.audit(root) == []
    assert audit_mod.audit(root,strict_source_disclosure=True) == []
    assert p.read_text() == text


@pytest.mark.parametrize("relative,text,expected", [
    ("mamey/data/strain_genus.csv", "invented,Unassigned\n", "cohort roster ships:"),
    ("OFFICIAL_DATA/exclusions.json", "{}\n", "cohort exclusions payload ships:"),
    ("docs/note.txt", "/Users/invented_person/private_input.tsv\n", "personal path / workspace name:"),
    ("docs/note.txt", "regression_review\n", "banned identity"),
])
def test_designated_private_payloads_and_personal_paths_still_refuse(tmp_path,relative,text,expected):
    root=tree(tmp_path); p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    assert any(expected in h for h in audit_mod.audit(root))


def test_explicit_operator_private_marker_still_refuses(tmp_path):
    root=tree(tmp_path);(root/"docs/note.txt").write_text("INVENTED_SECRET_REJECT_ME\n")
    policy=replace(load_public_export_policy(),private_identifiers=(PublicExportIdentifier("explicit-private-test","INVENTED_SECRET_REJECT_ME"),))
    findings=audit_mod.audit(root,policy)
    assert any("PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_CONTENT: explicit-private-test:" in h for h in findings)


def test_missing_identity_anchors_still_refuse(tmp_path):
    findings=audit_mod.audit(tmp_path)
    assert any("root missing Sapote identity anchor:" in h for h in findings)

@pytest.fixture(autouse=True)
def synthetic_private_vocabulary(monkeypatch):
    """Exercise identity detection using invented values, never deployment names."""
    monkeypatch.setattr(audit_mod, "BANNED_IDENTITY", ("SYNTHETIC_PRIVATE_TEST_MARKER", "regression_review"))

@pytest.mark.parametrize("relative", ["docs/note.txt", "tests/test_payload.py", "tools/public_release_audit.py"])
def test_external_private_policy_has_no_detector_self_exemption(tmp_path, relative):
    root = tree(tmp_path)
    marker = "EXTERNAL_POLICY_TEST_PAYLOAD"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(marker + "\n")
    policy = replace(load_public_export_policy(), private_identifiers=(
        PublicExportIdentifier("external-canary", marker),))
    findings = audit_mod.audit(root, policy)
    assert any("PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_CONTENT: external-canary:" in h for h in findings)
    assert all(marker not in h for h in findings)
