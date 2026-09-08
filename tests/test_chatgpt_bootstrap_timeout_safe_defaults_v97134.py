"""v9.7.161: ChatGPT/Claude bootstrap must be gold-only.

Smoke was removed entirely (its triage-only package had an empty ranked board and
could not support DAPR, lead boards, or cross-strain comparison — a dead end).
Bootstrap surfaces must recommend gold as the direct run and must NOT recommend
`--mode smoke` anywhere. History: v9.7.134 required smoke-first; v9.7.160 demoted
it; v9.7.161 removed it.
"""
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _surfaces():
    data = yaml.safe_load((ROOT / "bootstrap_contract.yml").read_text(encoding="utf-8"))
    return [s["path"] for s in data["bootstrap_surfaces"] if s.get("status") != "generated_report"]


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_no_bootstrap_surface_recommends_smoke():
    """v9.7.161: smoke is removed — no bootstrap surface may recommend `--mode smoke`."""
    offenders = []
    for rel in _surfaces():
        p = ROOT / rel
        if not p.exists() or p.suffix != ".md":
            continue
        if "--mode smoke" in _text(rel):
            offenders.append(rel)
    assert not offenders, f"--mode smoke removed v9.7.161 but still recommended in: {offenders}"


def test_bootstrap_surfaces_retain_timeout_safe_flags():
    for rel in _surfaces():
        p = ROOT / rel
        if not p.exists() or p.suffix != ".md":
            continue
        txt = _text(rel)
        # only assert on surfaces that actually carry a run snippet
        if "python -m mamey run" in txt:
            assert ("--capped-session" in txt or "--chatgpt-safe" in txt), \
                f"{rel} must retain the timeout-safe flag"


def test_no_timeout_safe_snippet_pairs_standard_with_chatgpt_safe():
    bad = re.compile(r"--mode\s+standard[\s\S]{0,160}--chatgpt-safe|--chatgpt-safe[\s\S]{0,160}--mode\s+standard")
    offenders = [rel for rel in _surfaces() if (ROOT / rel).exists() and bad.search(_text(rel))]
    assert not offenders, (
        "ChatGPT-safe guidance must not pair --mode standard with --chatgpt-safe; "
        f"offenders={offenders}"
    )


def test_chatgpt_init_prints_gold_workflow():
    out = subprocess.run(
        [sys.executable, "-m", "mamey.cli", "chatgpt-init"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert out.returncode == 0
    assert "smoke" not in out.stdout.lower(), "chatgpt-init must not mention smoke (removed v9.7.161)"
