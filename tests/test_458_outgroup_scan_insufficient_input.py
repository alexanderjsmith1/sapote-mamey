"""mlsa_outgroup_scan refuses a verdict it cannot support.

One tree used to exit 0, and trees sharing no ingroup split printed STABLE with RF 0 of 0.
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("mlsa_outgroup_scan_458", ROOT / "tools" / "mlsa_outgroup_scan.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tree(tmp_path, name, newick):
    d = tmp_path / name
    d.mkdir()
    f = d / "tree.treefile"
    f.write_text(newick + "\n")
    return str(f)


def test_one_tree_is_insufficient(tmp_path, capsys):
    mod = _load()
    t = _tree(tmp_path, "a", "((A,B),(C,D),X_OUTGROUP);")
    assert mod.main(["--trees", t]) == 1
    assert "INSUFFICIENT" in capsys.readouterr().out


def test_no_shared_split_is_not_stable(tmp_path, capsys):
    mod = _load()
    a = _tree(tmp_path, "a", "(A,B,X_OUTGROUP);")
    b = _tree(tmp_path, "b", "(A,B,Y_OUTGROUP);")
    assert mod.main(["--trees", a, b]) == 1
    out = capsys.readouterr().out
    assert "INSUFFICIENT" in out and "STABLE" not in out


def test_same_ingroup_topology_is_stable(tmp_path, capsys):
    mod = _load()
    a = _tree(tmp_path, "a", "(((A,B),C),(D,E),X_OUTGROUP);")
    b = _tree(tmp_path, "b", "(((A,B),C),(D,E),Y_OUTGROUP);")
    assert mod.main(["--trees", a, b]) == 0
    assert "STABLE" in capsys.readouterr().out
