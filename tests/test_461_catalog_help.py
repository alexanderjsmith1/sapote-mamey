"""Catalog help must be read-only and reject unknown switches."""
import pytest
from tools import gen_user_catalog as catalog

@pytest.mark.parametrize("argv, status", [(["--help"], 0), (["--not-a-real-option"], 2)])
def test_catalog_cli_parses_before_build(monkeypatch, capsys, argv, status):
    monkeypatch.setattr(catalog.sys, "argv", ["gen_user_catalog.py", *argv])
    def forbidden():
        pytest.fail("CLI help or invalid arguments must not build or write catalogs")
    monkeypatch.setattr(catalog, "build_catalog", forbidden)
    with pytest.raises(SystemExit) as exc:
        catalog.main()
    assert exc.value.code == status
    if status == 0:
        assert "--check" in capsys.readouterr().out
