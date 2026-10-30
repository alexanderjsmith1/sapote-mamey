"""File publication must not redirect a planned output into retained input."""
import pytest

from mamey.blastp_ingest import BlastpFileSetCommitError, _commit_text_file_set


@pytest.mark.parametrize("alias_kind", ["file", "parent", "deletion"])
def test_commit_refuses_symlink_before_modifying_retained_files(tmp_path, alias_kind):
    package = tmp_path / "package"
    package.mkdir()
    retained = package / "retained"
    retained.mkdir()
    source = retained / "input.txt"
    marker = b"unique engineering source marker\n"
    source.write_bytes(marker)
    if alias_kind == "parent":
        alias = package / "output_alias"
        alias.symlink_to(retained.name, target_is_directory=True)
        target = alias / source.name
    else:
        target = package / "planned_output.txt"
        target.symlink_to(source.relative_to(package))
    with pytest.raises(BlastpFileSetCommitError):
        _commit_text_file_set(
            package,
            {} if alias_kind == "deletion" else {target: "new output\n"},
            {target} if alias_kind == "deletion" else None,
        )
    assert source.read_bytes() == marker
    assert target.read_bytes() == marker
    assert not (package / ".blastp_fileset_transactions").exists()


def test_commit_keeps_regular_output_publication(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    retained = package / "input.txt"
    retained.write_text("retained\n")
    target = package / "store" / "output.txt"
    _commit_text_file_set(package, {target: "first\n"})
    _commit_text_file_set(package, {target: "second\n"})
    assert target.read_text() == "second\n"
    assert retained.read_text() == "retained\n"
    assert not (package / ".blastp_fileset_transactions").exists()
