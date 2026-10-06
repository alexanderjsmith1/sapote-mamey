"""Lab Quest is an optional add-on, not part of core (2026-09-27; .444 card).

Core must not import it, its modules must not live in `mamey/`, and the CLI must work with and without it.
"""
import ast
import io
import contextlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_core_has_no_lab_quest_modules_or_hard_imports():
    assert not list((ROOT / "mamey").glob("lab_quest*.py"))
    offenders = []
    for p in (ROOT / "mamey").rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            if any("lab_quest" in n for n in names):
                offenders.append(f"{p.relative_to(ROOT)}:{node.lineno}")
    # the only permitted import is the guarded one in cli.py, behind _lab_quest_available()
    assert offenders == [o for o in offenders if o.startswith("mamey/cli.py")] and len(offenders) <= 1


def test_cli_without_the_addon_hides_the_command_and_says_how_to_install(monkeypatch):
    from mamey import cli
    monkeypatch.setattr(cli, "_lab_quest_available", lambda: False)
    assert "lab-quest" not in cli.build_parser().format_help()
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert cli.main(["lab-quest", "--help"]) == 2
    assert "pip install ./sapote_addons/lab_quest" in err.getvalue()


def test_the_addon_ships_its_sources_and_install_files():
    addon = ROOT / "sapote_addons" / "lab_quest"
    for rel in ("pyproject.toml", "README.md", "sapote_lab_quest/__init__.py", "sapote_lab_quest/lab_quest.py",
                "sapote_lab_quest/lab_quest_app.py", "sapote_lab_quest/lab_quest_registry.py"):
        assert (addon / rel).is_file(), rel
    assert "streamlit" in (addon / "pyproject.toml").read_text()
    # the .443 install defect: the launcher named a `mamey[labquest]` extra that never existed
    assert "mamey[labquest]" not in (addon / "sapote_lab_quest" / "lab_quest.py").read_text()
