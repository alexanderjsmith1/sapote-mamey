"""v9.7.443: tools/blastp_crawl/ is exempt from print_calls only, never from the other checks."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("repo_health_probe", ROOT / "tools" / "repo_health.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses in the module resolve through sys.modules
    spec.loader.exec_module(mod)
    return mod


def _tree(tmp_path):
    crawl = tmp_path / "tools" / "blastp_crawl"
    crawl.mkdir(parents=True)
    (crawl / "probe.py").write_text("try:\n    x = 1\nexcept Exception:\n    pass\nprint(x)\n")
    return crawl / "probe.py"


def test_crawl_folder_is_still_scanned(tmp_path):
    rh = _load()
    probe = _tree(tmp_path)
    assert probe in rh._py_files(tmp_path)


def _count(result) -> int:
    return int(result.detail.split()[0])  # detail reads "<N> direct terminal-emission calls ..."


def test_crawl_prints_are_not_counted_but_others_are(tmp_path):
    rh = _load()
    probe = _tree(tmp_path)
    plain = tmp_path / "tools" / "plain.py"
    plain.write_text("print(1)\n")
    assert _count(rh.check_print_calls([probe], tmp_path)) == 0
    assert _count(rh.check_print_calls([probe, plain], tmp_path)) == 1


def test_crawl_swallow_is_still_counted(tmp_path):
    import ast
    rh = _load()
    probe = _tree(tmp_path)
    trees = {p: ast.parse(p.read_text()) for p in rh._py_files(tmp_path)}
    res = rh.check_silent_swallow(trees, tmp_path)
    assert _count(res) == 1, res
