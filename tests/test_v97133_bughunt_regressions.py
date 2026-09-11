"""v9.7.133 Deep Bug Hunt regression tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docs_do_not_use_removed_list_bgcs_package_flag():
    offenders = []
    for rel in ("docs/BUNDLE_CAPABILITIES.md", "docs/GUIDE/01_User_Manual.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        if "list-bgcs --package" in text:
            offenders.append(rel)
    assert not offenders, f"stale list-bgcs --package examples: {offenders}"


def test_mamey_native_declares_pandas_dependency():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "pandas>=2.0,<3.1" in pyproject
    assert "pandas>=2.0,<3.1" in requirements


def test_mode_b_kcb_absent_phrase_present():
    src = (ROOT / "mamey" / "chatgpt_commands.py").read_text(encoding="utf-8")
    assert "No KCB anchor was detected for this BGC." in src
    assert "KCB similarity: {kcb_top_str}..." not in src
