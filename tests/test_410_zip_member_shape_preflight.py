"""ZIP extraction must reject colliding target shapes before the first write."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from mamey.ziputil import _zipfile_extraction_target, safe_extract_all


def _archive(path, members):
    with zipfile.ZipFile(path, "w") as zf:
        for name, payload in members:
            zf.writestr(name, payload)
    return path


def test_file_ancestor_collision_refuses_before_partial_extraction(tmp_path):
    archive = _archive(tmp_path / "collision.zip", [
        ("NODE_1.region001.gbk", b"region bytes"),
        ("NODE_1.region001.gbk/child.txt", b"child bytes"),
    ])
    destination = tmp_path / "destination"

    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(ValueError, match="file/directory collision"):
            safe_extract_all(zf, destination)

    assert not destination.exists(), "shape preflight must finish before the first extraction write"


def test_aliases_resolving_to_same_target_are_refused_before_write(tmp_path):
    archive = _archive(tmp_path / "alias.zip", [
        ("nested/data.txt", b"first"),
        ("nested/./data.txt", b"second"),
    ])
    destination = tmp_path / "destination"

    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(ValueError, match="colliding zip extraction target"):
            safe_extract_all(zf, destination)

    assert not destination.exists()


def test_dotdot_component_alias_matching_zipfile_is_refused_before_write(tmp_path):
    archive = _archive(tmp_path / "dotdot-alias.zip", [
        ("nested/file.txt", b"first"),
        ("nested/../file.txt", b"second"),
    ])
    destination = tmp_path / "destination"

    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(ValueError, match="colliding zip extraction target"):
            safe_extract_all(zf, destination)

    assert not destination.exists()


@pytest.mark.parametrize(("first_name", "second_name"), [
    ("File.txt", "file.txt"),
    ("caf\N{LATIN SMALL LETTER E WITH ACUTE}.txt", "cafe\N{COMBINING ACUTE ACCENT}.txt"),
])
def test_portable_name_aliases_are_refused_before_write(
    tmp_path, first_name, second_name
):
    archive = _archive(tmp_path / "casefold-alias.zip", [
        (first_name, b"first"),
        (second_name, b"second"),
    ])
    destination = tmp_path / "destination"

    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(ValueError, match="portable.*collision"):
            safe_extract_all(zf, destination)

    assert not destination.exists()


@pytest.mark.parametrize(("file_name", "directory_name"), [
    ("File.txt", "file.txt"),
    ("caf\N{LATIN SMALL LETTER E WITH ACUTE}.txt", "cafe\N{COMBINING ACUTE ACCENT}.txt"),
])
@pytest.mark.parametrize("reverse", [False, True])
def test_portable_file_ancestor_aliases_are_refused_before_write(
    tmp_path, file_name, directory_name, reverse
):
    members = [
        (file_name, b"file payload"),
        (f"{directory_name}/child.txt", b"child payload"),
    ]
    if reverse:
        members.reverse()
    archive = _archive(tmp_path / "portable-ancestor.zip", members)
    destination = tmp_path / "destination"

    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(ValueError, match="portable.*file/directory collision"):
            safe_extract_all(zf, destination)

    assert not destination.exists()


@pytest.mark.parametrize("member_name", [
    "nested/../file.txt",
    "nested/./file.txt",
    "nested//file.txt",
    "/leading.txt",
])
def test_target_prediction_matches_runtime_zipfile_normalization(tmp_path, member_name):
    archive = _archive(tmp_path / "runtime-target.zip", [
        (member_name, b"payload"),
    ])
    predicted_root = tmp_path / "predicted"
    actual_root = tmp_path / "actual"

    with zipfile.ZipFile(archive) as zf:
        member = zf.infolist()[0]
        predicted = _zipfile_extraction_target(predicted_root.resolve(), member)
        actual = Path(zf.extract(member, actual_root)).resolve()

    assert predicted.relative_to(predicted_root.resolve()) == actual.relative_to(
        actual_root.resolve()
    )


@pytest.mark.parametrize("member_name", ["/leading.txt", "//leading.txt"])
def test_leading_separator_is_refused_before_write(tmp_path, member_name):
    archive = _archive(tmp_path / "leading-separator.zip", [
        (member_name, b"payload"),
    ])
    destination = tmp_path / "destination"

    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(ValueError, match="unsafe zip member path"):
            safe_extract_all(zf, destination)

    assert not destination.exists()


def test_explicit_directory_and_child_file_remain_valid(tmp_path):
    archive = _archive(tmp_path / "normal.zip", [
        ("nested/", b""),
        ("nested/data.txt", b"payload"),
    ])
    destination = tmp_path / "destination"

    with zipfile.ZipFile(archive) as zf:
        safe_extract_all(zf, destination)

    assert (destination / "nested" / "data.txt").read_bytes() == b"payload"
