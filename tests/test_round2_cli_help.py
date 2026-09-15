"""User-facing help must track the runtime cap and distinguish extraction from authorship."""
import pytest
from mamey import cli

@pytest.mark.parametrize("cap", [80_000_000, 81_000_000])
def test_run_help_tracks_cap_and_scope(monkeypatch, capsys, cap):
    monkeypatch.setattr(cli, "FULL_MAX_JSON_BYTES", cap)
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["run", "--help"])
    assert exc.value.code == 0
    text = " ".join(capsys.readouterr().out.split())
    assert f"{cap / 1_000_000:g} MB" in text
    assert "uncompressed" in text
    assert "authored Mode B cards require subsequent interpretation" in text
    assert "never opens JSON" not in text
    assert "every BGC gets full Mode B" not in text
