"""`ingest-receipts` writes Mode B cards into the covered judgment/ subtree, so it must refresh
post_seal_checksums.txt like the other post-seal authoring commands. Otherwise a later
`validate` reports the recorded cards as injected files."""
from mamey import cli, packaging


def test_ingest_receipts_refreshes_post_seal_checksums(tmp_path, monkeypatch):
    package = tmp_path / "package"
    (package / "judgment").mkdir(parents=True)
    called = []

    def fake_ingest(args):
        (package / "judgment" / "X_BGC001_mode_b.md").write_text("card")
        return 0

    monkeypatch.setattr(cli, "ingest_receipts_command", fake_ingest)
    monkeypatch.setattr(packaging, "refresh_post_seal_checksums", lambda root: called.append(str(root)))
    assert cli.main(["ingest-receipts", "--package", str(package), "--auto-detect"]) == 0
    assert called == [str(package)]


def test_read_only_list_bgcs_still_does_not_refresh(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(packaging, "refresh_post_seal_checksums", lambda root: called.append(str(root)))
    assert "list-bgcs" not in cli_authoring_commands()
    assert called == []


def cli_authoring_commands():
    import inspect
    src = inspect.getsource(cli)
    start = src.index("_POST_SEAL_AUTHORING_COMMANDS = frozenset({")
    return src[start:src.index("})", start)]
