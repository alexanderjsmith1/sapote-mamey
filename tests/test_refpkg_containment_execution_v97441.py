"""Exercise the real build-ref entry before any external phylogenetic compute."""
from types import SimpleNamespace
import pytest
from tools import phylo_place as tool

@pytest.mark.parametrize("route", ["direct", "alias", "sibling"])
def test_actual_build_ref_containment(tmp_path, monkeypatch, route):
    bundle = tmp_path / "bundle"
    (bundle / "tools").mkdir(parents=True)
    (bundle / "BUILD_STAMP.txt").write_text("fixture")
    monkeypatch.setattr(tool, "__file__", str(bundle / "tools/phylo_place.py"))
    monkeypatch.setattr(tool, "_is_protein", lambda _: False)
    monkeypatch.setattr(tool, "_which", lambda *args: None)
    if route == "alias":
        alias = tmp_path / "outside_alias"
        alias.symlink_to(bundle, target_is_directory=True)
        out = alias / "refpkg"
    elif route == "direct":
        out = bundle / "refpkg"
    else:
        out = tmp_path / "bundle-sibling/refpkg"
    args = SimpleNamespace(group="streptomyces", approved_by="test-fixture",
                           ref_fasta="unused", refpkg=str(out))
    with pytest.raises(SystemExit) as exc:
        tool.cmd_build_ref(args)
    if route == "sibling":
        assert "mafft not found" in str(exc.value)
        assert out.is_dir()
    else:
        assert "OUTPUT-CONTAINMENT" in str(exc.value)
        assert not out.exists()
