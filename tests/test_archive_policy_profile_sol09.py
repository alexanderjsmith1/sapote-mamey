"""Privacy-profile literals must be checked inside bounded ZIP-family content."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"sol09_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _zip(entries: dict[str, str | bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    return out.getvalue()


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    (root / "mamey").mkdir(parents=True)
    (root / "mamey" / "__init__.py").write_text('__version__ = "1.0.0"\n', encoding="utf-8")
    (root / "BUILD_STAMP.txt").write_text("build=test\n", encoding="utf-8")
    (root / "fixtures").mkdir()
    return root


def _profile(tmp_path: Path, *, archive_rel: str | None = None,
             archive_bytes: bytes | None = None) -> Path:
    allowances = []
    if archive_rel is not None and archive_bytes is not None:
        allowances.append({
            "identifier_id": "project-code",
            "relative_path": archive_rel,
            "sha256": hashlib.sha256(archive_bytes).hexdigest(),
            "reason": "generic exact archive fixture",
            "purpose": "CONTENT_ONLY_EXCEPTION",
            "state": "ACTIVE",
        })
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({
        "schema_version": "sapote_privacy_profile_v1",
        "profile_id": "generic-archive-policy",
        "default_tier": "INTERNAL",
        "tiers": [{"tier_id": "INTERNAL", "public_export": False}],
        "strain_assignments": [],
        "public_export_policy": {
            "exclude_root_names": [],
            "exclude_relative_paths": [],
            "private_identifiers": [
                {"identifier_id": "project-code", "literal": "PROJECT-ORCHID-EMBER"}
            ],
            "allowlisted_occurrences": allowances,
        },
    }), encoding="utf-8")
    return path


def test_nested_policy_literal_fails_with_redacted_container_provenance(tmp_path):
    audit = _load("public_release_audit")
    root = _tree(tmp_path)
    inner = _zip({"notes.txt": "PROJECT-ORCHID-EMBER\n"})
    (root / "fixtures" / "bundle.zip").write_bytes(_zip({"inner.zip": inner}))
    policy = audit.load_public_export_policy(_profile(tmp_path))

    hits = audit.audit(root, policy)

    expected = (
        "PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_ARCHIVE_CONTENT: project-code: "
        "fixtures/bundle.zip!inner.zip!notes.txt"
    )
    assert expected in hits
    assert "PROJECT-ORCHID-EMBER" not in "\n".join(hits)


def test_member_path_literal_is_redacted_and_never_content_allowlisted(tmp_path):
    audit = _load("public_release_audit")
    root = _tree(tmp_path)
    archive_bytes = _zip({"PROJECT-ORCHID-EMBER.txt": "ordinary\n"})
    rel = "fixtures/bundle.zip"
    (root / rel).write_bytes(archive_bytes)
    policy = audit.load_public_export_policy(
        _profile(tmp_path, archive_rel=rel, archive_bytes=archive_bytes))

    hits = audit.audit(root, policy)

    assert hits == [
        "PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_ARCHIVE_MEMBER_PATH: project-code: "
        "fixtures/bundle.zip!<private:project-code>.txt"
    ]


def test_archive_content_allowance_is_outer_path_and_byte_bound(tmp_path):
    audit = _load("public_release_audit")
    root = _tree(tmp_path)
    archive_bytes = _zip({"notes.txt": "PROJECT-ORCHID-EMBER\n"})
    rel = "fixtures/bundle.zip"
    target = root / rel
    target.write_bytes(archive_bytes)
    policy = audit.load_public_export_policy(
        _profile(tmp_path, archive_rel=rel, archive_bytes=archive_bytes))
    assert audit.audit(root, policy) == []

    target.write_bytes(_zip({"notes.txt": "PROJECT-ORCHID-EMBER changed\n"}))
    assert any("PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_ARCHIVE_CONTENT" in hit
               for hit in audit.audit(root, policy))


def test_depth_truncation_is_a_public_policy_failure_not_a_clean_scan(tmp_path):
    audit = _load("public_release_audit")
    root = _tree(tmp_path)
    payload = _zip({"notes.txt": "PROJECT-ORCHID-EMBER\n"})
    for depth in range(5):
        payload = _zip({f"inner-{depth}.zip": payload})
    (root / "fixtures" / "deep.zip").write_bytes(payload)
    policy = audit.load_public_export_policy(_profile(tmp_path))

    hits = audit.audit(root, policy)

    assert any(hit.startswith("PUBLIC_POLICY_ARCHIVE_SCAN_INCOMPLETE: depth_limit_truncated:")
               for hit in hits), hits
    assert not any("PRIVATE_IDENTIFIER_IN_ARCHIVE_CONTENT" in hit for hit in hits)


def test_scanner_cli_returns_error_for_incomplete_depth_scan(tmp_path, capsys):
    scanner = _load("archive_leak_scan")
    inner = _zip({"notes.txt": "ordinary\n"})
    (tmp_path / "outer.zip").write_bytes(_zip({"inner.zip": inner}))

    result = scanner.main([str(tmp_path), "--max-depth", "0"])

    assert result == 2
    assert "INCOMPLETE" in capsys.readouterr().out


def test_member_size_bound_is_visible_and_surface_report_is_typed(tmp_path):
    scanner = _load("archive_leak_scan")
    audit = _load("public_release_audit")
    root = _tree(tmp_path)
    target = root / "fixtures" / "bundle.zip"
    target.write_bytes(_zip({"notes.txt": "ordinary content\n"}))

    findings = scanner.scan_archive(target, max_member_bytes=3)
    assert [finding["kind"] for finding in findings] == ["member_size_limit_exceeded"]

    policy = audit.load_public_export_policy(_profile(tmp_path))
    report = audit.audit_surface_report(root, policy)
    assert report["ARCHIVE_POLICY_SCANNED"] == 1
    assert report["BINARY_PATH_ONLY"] == 0


def test_read_error_uses_caller_supplied_portable_archive_label(tmp_path):
    scanner = _load("archive_leak_scan")
    findings = scanner.scan_archive(
        tmp_path / "missing.zip", archive_label="fixtures/missing.zip")
    assert findings[0]["kind"] == "read_error"
    assert findings[0]["archive"] == "fixtures/missing.zip"
    assert str(tmp_path) not in findings[0]["archive"]


def test_symlink_archive_is_incomplete_without_reading_external_bytes(tmp_path):
    audit = _load("public_release_audit")
    root = _tree(tmp_path)
    outside = tmp_path / "outside.zip"
    outside.write_bytes(_zip({"notes.txt": "PROJECT-ORCHID-EMBER\n"}))
    os.symlink(outside, root / "fixtures" / "linked.zip")
    policy = audit.load_public_export_policy(_profile(tmp_path))

    hits = audit.audit(root, policy)

    assert hits == [
        "PUBLIC_POLICY_ARCHIVE_SCAN_INCOMPLETE: archive_symlink: fixtures/linked.zip"
    ]
    assert str(outside) not in "\n".join(hits)


def test_broken_archive_symlink_is_not_silently_filtered_before_lstat(tmp_path):
    audit = _load("public_release_audit")
    root = _tree(tmp_path)
    os.symlink(tmp_path / "missing-target.zip", root / "fixtures" / "broken.zip")
    policy = audit.load_public_export_policy(_profile(tmp_path))

    hits = audit.audit(root, policy)

    assert hits == [
        "PUBLIC_POLICY_ARCHIVE_SCAN_INCOMPLETE: archive_symlink: fixtures/broken.zip"
    ]
    assert audit.audit_surface_report(root, policy)["ARCHIVE_POLICY_SCANNED"] == 1


def test_archive_named_directory_is_typed_nonregular_not_silently_skipped(tmp_path):
    audit = _load("public_release_audit")
    root = _tree(tmp_path)
    (root / "fixtures" / "directory.zip").mkdir()
    policy = audit.load_public_export_policy(_profile(tmp_path))

    hits = audit.audit(root, policy)

    assert hits == [
        "PUBLIC_POLICY_ARCHIVE_SCAN_INCOMPLETE: archive_not_regular_file: "
        "fixtures/directory.zip"
    ]
    assert audit.audit_surface_report(root, policy)["ARCHIVE_POLICY_SCANNED"] == 1


def test_scan_tree_lexically_enumerates_every_archive_shaped_candidate(tmp_path):
    scanner = _load("archive_leak_scan")
    root = tmp_path / "scan-root"
    root.mkdir()
    real = root / "real.zip"
    real.write_bytes(_zip({"notes.txt": "ordinary\n"}))
    os.symlink(real, root / "internal.zip")
    os.symlink(root / "missing.zip", root / "broken.zip")
    (root / "directory.zip").mkdir()
    (root / "ordinary-directory").mkdir()

    findings, count = scanner.scan_tree(root)

    assert count == 4
    kinds = [finding["kind"] for finding in findings]
    assert kinds.count("archive_symlink") == 2
    assert kinds.count("archive_not_regular_file") == 1
