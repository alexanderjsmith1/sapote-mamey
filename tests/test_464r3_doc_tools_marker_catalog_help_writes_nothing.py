"""`gen_marker_catalog.py --help` and unknown options exit without rewriting the catalog."""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gen_marker_catalog_464r3", ROOT / "tools" / "gen_marker_catalog.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


@pytest.mark.parametrize("argv", [["--help"], ["-h"], ["--chek"]])
def test_help_or_typo_never_writes(monkeypatch, argv):
    calls = []
    monkeypatch.setattr(gen, "write", lambda payload: calls.append(payload))
    monkeypatch.setattr(gen, "collect", lambda: calls.append("collect") or {"tables": {}, "sha256": "0" * 12})
    with pytest.raises(SystemExit) as caught:
        gen.main(argv)
    assert caught.value.code in (0, 2)
    assert calls == []


def test_no_option_still_writes(monkeypatch):
    calls = []
    monkeypatch.setattr(gen, "write", lambda payload: calls.append("write"))
    monkeypatch.setattr(gen, "collect", lambda: {"tables": {}, "sha256": "0" * 12})
    assert gen.main([]) == 0
    assert calls == ["write"]
