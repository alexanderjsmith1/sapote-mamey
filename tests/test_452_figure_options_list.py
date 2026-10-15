"""tools/gen_figure_options.py (card 018c0f08_452_figure_options_list): the figure options list is generated from each
registered tool's own --help, so people and LLMs see the options the code has. Synthetic tools only."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gen_figure_options_t", ROOT / "tools/gen_figure_options.py")
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

HELP = """usage: syn.py [-h] --out OUT [--layout {a,b}]

Synthetic tool.

options:
  -h, --help       show this help message and exit
  --out OUT        output folder
  --layout {a,b}   which layout (default: a)
  --width WIDTH    printed width in inches; a long help line that
                   wraps onto a second line
  -q, --quiet      say less
"""

SUBHELP = """usage: syn2.py [-h] {pairs,render} ...

positional arguments:
  {pairs,render}

options:
  -h, --help      show this help message and exit
"""


def test_parse_help_reads_flags_choices_defaults_and_wrapped_lines():
    opts, subs = g.parse_help(HELP)
    by = {o["flag"]: o for o in opts}
    assert set(by) == {"--out", "--layout", "--width", "--quiet"} and subs == []
    assert by["--layout"]["choices"] == ["a", "b"] and by["--layout"]["default"] == "a"
    assert by["--out"]["value"] == "OUT"
    assert by["--width"]["help"].endswith("wraps onto a second line")


def test_parse_help_finds_subcommands():
    assert g.parse_help(SUBHELP)[1] == ["pairs", "render"]


def _tree(tmp_path, monkeypatch, tools):
    (tmp_path / "tools").mkdir(); (tmp_path / "docs").mkdir(); (tmp_path / "mamey/data").mkdir(parents=True)
    figs = []
    for i, (name, body) in enumerate(tools.items()):
        (tmp_path / "tools" / name).write_text(body)
        figs.append({"id": f"X{i}", "name": f"synthetic {i}", "draws": "toy", "tool": f"tools/{name}"})
    figs.append({"id": "X9", "name": "missing", "draws": "toy", "tool": "tools/absent.py"})
    reg = tmp_path / "mamey/data/figure_tools.json"
    reg.write_text(json.dumps({"common": [{"flag": "--dpi", "help": "resolution"}], "figures": figs}))
    monkeypatch.setattr(g, "ROOT", tmp_path); monkeypatch.setattr(g, "REGISTRY", reg)
    monkeypatch.setattr(g, "MD_OUT", tmp_path / "docs/FIGURE_OPTIONS.generated.md")
    monkeypatch.setattr(g, "JSON_OUT", tmp_path / "docs/figure_options.generated.json")


GOOD = "import argparse\np=argparse.ArgumentParser()\np.add_argument('--out',required=True)\np.add_argument('--mode',choices=['x','y'])\np.parse_args()\n"
SUB = ("import argparse\np=argparse.ArgumentParser()\ns=p.add_subparsers(dest='c')\na=s.add_parser('make')\n"
       "a.add_argument('--n',help='count')\np.parse_args()\n")
BAD = "import not_a_module_anywhere\n"


def test_generate_check_and_honest_failures(tmp_path, monkeypatch):
    _tree(tmp_path, monkeypatch, {"good.py": GOOD, "sub.py": SUB, "bad.py": BAD})
    assert g.main([]) == 0
    data = json.loads((tmp_path / "docs/figure_options.generated.json").read_text())
    st = {f["id"]: f["status"] for f in data["figures"]}
    assert st["X0"] == "OK" and st["X1"] == "OK" and st["X2"].startswith("HELP_FAILED") and st["X9"] == "TOOL_NOT_IN_THIS_TREE"
    good = data["figures"][0]["commands"][0]["options"]
    assert {o["flag"] for o in good} == {"--out", "--mode"}
    assert data["figures"][1]["commands"][0]["command"] == "make"
    md = (tmp_path / "docs/FIGURE_OPTIONS.generated.md").read_text()
    assert "## X0: synthetic 0" in md and "`--mode`" in md and "HELP_FAILED" in md
    assert g.main(["--check"]) == 0
    (tmp_path / "tools/good.py").write_text(GOOD.replace("'--mode'", "'--style'"))
    assert g.main(["--check"]) == 1
