"""Generic regression tests for the fail-closed public archive transaction."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import shutil
import stat
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "finalize_public_archive.py"


def _module():
    spec = importlib.util.spec_from_file_location("archive_transaction", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stage(tmp_path: Path) -> tuple[Path, Path]:
    stage, output = tmp_path / "stage", tmp_path / "output"
    (stage / "nested").mkdir(parents=True)
    output.mkdir()
    (stage / "nested" / "record.txt").write_text("generic fixture\n", encoding="utf-8")
    return stage, output


def test_finalizer_commits_exact_audited_archive_and_is_deterministic(tmp_path):
    mod = _module()
    stage, output = _stage(tmp_path)
    one = mod.finalize_archive(stage, output, "one.zip")
    two = mod.finalize_archive(stage, output, "two.zip")
    assert one.status == two.status == "COMMITTED"
    assert (output / "one.zip").read_bytes() == (output / "two.zip").read_bytes()
    assert one.archive_sha256 == hashlib.sha256((output / "one.zip").read_bytes()).hexdigest()


def test_existing_final_is_preserved_without_probe_or_temp(tmp_path):
    mod = _module()
    stage, output = _stage(tmp_path)
    target = output / "taken.zip"
    target.write_bytes(b"existing")
    before = target.read_bytes()
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-TXN-001"):
        mod.finalize_archive(stage, output, target.name)
    assert target.read_bytes() == before
    assert not list(output.glob(".*.archtxn.tmp"))


def test_stage_symlink_refuses_before_final(tmp_path):
    mod = _module()
    stage, output = _stage(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("keep", encoding="utf-8")
    (stage / "bad").symlink_to(outside, target_is_directory=True)
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-STAGE-001"):
        mod.finalize_archive(stage, output, "candidate.zip")
    assert (outside / "keep").read_text(encoding="utf-8") == "keep"
    assert not (output / "candidate.zip").exists()


def test_supplied_stage_root_symlink_refuses_before_resolution_and_preserves_sentinels(tmp_path):
    mod = _module()
    stage, output = _stage(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_sentinel = outside / "keep.txt"
    outside_sentinel.write_bytes(b"outside-unchanged")
    source_sentinel = stage / "nested" / "record.txt"
    source_before = source_sentinel.read_bytes()
    stage_link = tmp_path / "stage-link"
    stage_link.symlink_to(stage, target_is_directory=True)

    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-STAGE-001: stage_root_symlink"):
        mod.finalize_archive(stage_link, output, "candidate.zip")

    assert source_sentinel.read_bytes() == source_before
    assert outside_sentinel.read_bytes() == b"outside-unchanged"
    assert not (output / "candidate.zip").exists()
    assert not list(output.glob(".*.archtxn.tmp"))


def test_stage_root_identity_change_refuses_before_commit(tmp_path, monkeypatch):
    mod = _module()
    stage, output = _stage(tmp_path)
    displaced = tmp_path / "stage-original"
    original_audit = mod.audit_archive

    def replace_root_after_archive_audit(archive_path, expected):
        result = original_audit(archive_path, expected)
        stage.rename(displaced)
        shutil.copytree(displaced, stage)
        return result

    monkeypatch.setattr(mod, "audit_archive", replace_root_after_archive_audit)
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-STAGE-006: stage_root_identity_changed"):
        mod.finalize_archive(stage, output, "candidate.zip")
    assert (displaced / "nested" / "record.txt").read_text(encoding="utf-8") == "generic fixture\n"
    assert (stage / "nested" / "record.txt").read_text(encoding="utf-8") == "generic fixture\n"
    assert not (output / "candidate.zip").exists()
    assert not list(output.glob(".*.archtxn.tmp"))


def test_archive_rejects_duplicate_and_traversal_members(tmp_path):
    mod = _module()
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("same.txt", b"a")
        zf.writestr("same.txt", b"b")
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-ZIP-003"):
        mod.audit_archive(archive, [])
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.txt", b"x")
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-PATH-005"):
        mod.audit_archive(archive, [])


def test_archive_rejects_noncanonical_member_metadata(tmp_path):
    mod = _module()
    archive = tmp_path / "bad-metadata.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        info = zipfile.ZipInfo("member.txt")
        info.create_system = 3
        info.external_attr = (0o120777) << 16
        zf.writestr(info, b"x")
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-ZIP-004"):
        mod.audit_archive(archive, [])


def _canonical_info(mod, name, compression):
    info = zipfile.ZipInfo(name, date_time=mod._ZIP_EPOCH)
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.reserved = 0
    info.flag_bits = 0x0800 if any(ord(char) > 127 for char in name) else 0x0000
    info.volume = 0
    info.internal_attr = 0
    info.compress_type = compression
    info.external_attr = mod._DIRECTORY_ATTR if name.endswith("/") else mod._REGULAR_ATTR
    info.extra = b""
    info.comment = b""
    if name.endswith("/"):
        info.file_size = info.compress_size = info.CRC = 0
    return info


@pytest.mark.parametrize(
    ("name", "compression", "payload"),
    [
        ("ascii-stored.txt", zipfile.ZIP_STORED, b"stored"),
        ("utf8-stored-\N{GREEK SMALL LETTER BETA}.txt", zipfile.ZIP_STORED, b"stored"),
        ("ascii-deflated.txt", zipfile.ZIP_DEFLATED, b"deflated"),
        ("utf8-deflated-\N{GREEK SMALL LETTER BETA}.txt", zipfile.ZIP_DEFLATED, b"deflated"),
        ("ascii-directory/", zipfile.ZIP_STORED, b""),
        ("utf8-directory-\N{GREEK SMALL LETTER BETA}/", zipfile.ZIP_STORED, b""),
    ],
)
def test_closed_zip_metadata_classifier_accepts_exact_six_shapes(tmp_path, name, compression, payload):
    mod = _module()
    archive = tmp_path / "canonical.zip"
    info = _canonical_info(mod, name, compression)
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr(info, payload)
    expected = [
        mod.Member(
            name,
            "DIRECTORY_NO_CONTENT" if name.endswith("/") else "REGULAR_FILE",
            len(payload),
            "" if name.endswith("/") else hashlib.sha256(payload).hexdigest(),
            0o755 if name.endswith("/") else 0o644,
        )
    ]
    mod.audit_archive(archive, expected)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("create_system", 0),
        ("create_version", 21),
        ("extract_version", 21),
        ("reserved", 1),
        ("volume", 1),
        ("internal_attr", 1),
        ("external_attr", ((stat.S_IFREG | 0o640) << 16)),
        ("extra", b"\x01\x00\x00\x00"),
        ("comment", b"noncanonical"),
        ("date_time", (2024, 1, 2, 3, 4, 6)),
    ],
)
def test_closed_zip_metadata_classifier_rejects_each_noncanonical_field(field, value):
    mod = _module()
    info = _canonical_info(mod, "member.txt", zipfile.ZIP_STORED)
    setattr(info, field, value)
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-ZIP-012"):
        mod._classify_zip_member(info)


@pytest.mark.parametrize("bit", range(16))
def test_closed_zip_metadata_classifier_rejects_every_ascii_flag_bit(bit):
    mod = _module()
    info = _canonical_info(mod, "member.txt", zipfile.ZIP_STORED)
    info.flag_bits = 1 << bit
    expected = "ARCHTXN-ZIP-005" if bit == 0 else "ARCHTXN-ZIP-012"
    with pytest.raises(mod.ArchiveTransactionError, match=expected):
        mod._classify_zip_member(info)


@pytest.mark.parametrize("bit", [bit for bit in range(16) if bit != 11])
def test_closed_zip_metadata_classifier_rejects_extra_utf8_flag_bits(bit):
    mod = _module()
    info = _canonical_info(mod, "member-\N{GREEK SMALL LETTER BETA}.txt", zipfile.ZIP_STORED)
    info.flag_bits |= 1 << bit
    expected = "ARCHTXN-ZIP-005" if bit == 0 else "ARCHTXN-ZIP-012"
    with pytest.raises(mod.ArchiveTransactionError, match=expected):
        mod._classify_zip_member(info)


def test_closed_zip_metadata_classifier_rejects_missing_utf8_flag_and_deflated_directory():
    mod = _module()
    utf8 = _canonical_info(mod, "member-\N{GREEK SMALL LETTER BETA}.txt", zipfile.ZIP_STORED)
    utf8.flag_bits = 0
    directory = _canonical_info(mod, "directory/", zipfile.ZIP_DEFLATED)
    for info in (utf8, directory):
        with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-ZIP-012"):
            mod._classify_zip_member(info)


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("create-system", lambda info: setattr(info, "create_system", 0)),
        ("timestamp", lambda info: setattr(info, "date_time", (2024, 1, 2, 3, 4, 6))),
    ],
)
def test_independently_reproduced_zip_variants_now_refuse(tmp_path, label, mutate):
    mod = _module()
    archive = tmp_path / f"{label}.zip"
    info = _canonical_info(mod, "member.txt", zipfile.ZIP_STORED)
    mutate(info)
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr(info, b"x")
    expected = [mod.Member("member.txt", "REGULAR_FILE", 1, hashlib.sha256(b"x").hexdigest(), 0o644)]
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-ZIP-012"):
        mod.audit_archive(archive, expected)


def test_noreplace_argument_grammar_refuses_path_and_replace_shapes(tmp_path):
    mod = _module()
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-ARG-001"):
        mod._canonical_basename("../target.zip")
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-ARG-001"):
        mod._canonical_basename("target:zip")


def test_postcommit_durability_failure_retains_final(tmp_path):
    mod = _module()
    stage, output = _stage(tmp_path)
    def fail_fsync(_fd):
        raise OSError("synthetic")
    with pytest.raises(mod.ArchiveTransactionError, match="ARCHTXN-TXN-006") as raised:
        mod.finalize_archive(stage, output, "durable.zip", postcommit_fsync=fail_fsync)
    assert raised.value.committed is True
    assert (output / "durable.zip").is_file()


def test_error_surface_contains_only_typed_values(tmp_path, capsys):
    mod = _module()
    private_root = tmp_path / "private-location"
    stage, output = _stage(private_root)
    rc = mod._main(["--stage-root", str(stage), "--output-dir", str(output), "--archive-name", "../bad.zip"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "ARCHTXN-ARG-001" in captured.err
    assert str(private_root) not in captured.err
