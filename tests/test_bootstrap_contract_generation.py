"""Bootstrap contract generation and accidental-typo rescue policy.

The ChatGPT/Claude bootstrap contract must be data-driven. CHATGPT_START_HERE.md
is canonical; CHATGTP_READ_ME_FIRST.md is optional typo rescue only, never
scanner authority.
"""
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "bootstrap_contract.yml"


def _contract():
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


def test_bootstrap_contract_exists_and_declares_canonical_chatgpt_file():
    data = _contract()
    assert data["challenge_response"]["canonical_instruction_file"] == "CHATGPT_START_HERE.md"
    surfaces = {s["path"]: s for s in data["bootstrap_surfaces"]}
    assert surfaces["CHATGPT_START_HERE.md"]["status"] == "canonical"
    assert surfaces["CHATGPT_START_HERE.md"]["scanner_authority"] is True


def test_chatgtp_typo_alias_is_optional_accidental_rescue_not_authority():
    surfaces = {s["path"]: s for s in _contract()["bootstrap_surfaces"]}
    alias = surfaces["CHATGTP_READ_ME_FIRST.md"]
    assert alias["status"] == "optional_typo_rescue_alias"
    assert alias["required"] is False
    assert alias["scanner_authority"] is False
    txt = (ROOT / "CHATGTP_READ_ME_FIRST.md").read_text(encoding="utf-8")
    assert "accidental" in txt.lower()
    assert "gtp" in txt.lower()
    assert "not" in txt.lower() and "authoritative" in txt.lower()


def test_generated_bootstrap_docs_are_current():
    out = subprocess.run(
        [sys.executable, "tools/render_bootstrap_contract.py", "--check"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert '"status": "PASS"' in out.stdout


def test_known_gotchas_are_generated_from_registry():
    data = _contract()
    ids = [g["id"] for g in data["known_gotchas"] if g.get("status") == "active"]
    txt = (ROOT / "CHATGPT_START_HERE.md").read_text(encoding="utf-8")
    assert "BEGIN GENERATED: known_gotchas_section" in txt
    for gid in ids:
        assert gid in txt


def test_correctly_spelled_chatgpt_alias_exists():
    txt = (ROOT / "CHATGPT_READ_ME_FIRST.md").read_text(encoding="utf-8")
    assert "CHATGPT_START_HERE.md" in txt
    assert "CHATGTP_READ_ME_FIRST.md" in txt
    assert "typo rescue" in txt.lower() or "typo-rescue" in txt.lower()
