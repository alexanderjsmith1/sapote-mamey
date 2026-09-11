"""test_bunny_hop_discoverability.py — the Bunny Hop audit protocol must ship in the
bundle and be discoverable from the surfaces both assistants read, and chatgpt-init
must be a registered command.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_protocol_file_ships():
    # The canonical game rules live in debugging_modules/; docs/ has a pointer
    p = ROOT / "debugging_modules" / "BUNNY_HOP_AUDIT_GAME.md"
    assert p.exists(), "Bunny Hop protocol must ship at debugging_modules/BUNNY_HOP_AUDIT_GAME.md"
    text = p.read_text(encoding="utf-8")
    assert "Inspector" in text and "Defender" in text
    assert "patch card" in text.lower()
    # The pointer in docs/ must exist and reference the canonical location
    pointer = ROOT / "docs" / "BUNNY_HOP_AUDIT_GAME.md"
    assert pointer.exists(), "docs/BUNNY_HOP_AUDIT_GAME.md pointer must exist"
    assert "debugging_modules/" in pointer.read_text(encoding="utf-8")


def test_trigger_documented_in_how_to_use():
    text = (ROOT / "docs" / "HOW_TO_USE.md").read_text(encoding="utf-8")
    assert "BUNNY_HOP_AUDIT_GAME.md" in text
    assert "bunny hop" in text.lower()


def test_trigger_documented_in_chatgpt_contract():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "bunny hop" in text.lower()
    assert "BUNNY_HOP_AUDIT_GAME.md" in text


def test_chatgpt_init_is_registered():
    out = subprocess.run(
        [sys.executable, "-m", "mamey.cli", "--help"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert "chatgpt-init" in (out.stdout + out.stderr)


def test_chatgpt_init_runs_and_reports_contract():
    out = subprocess.run(
        [sys.executable, "-m", "mamey.cli", "chatgpt-init"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert out.returncode == 0
    # surfaces the file inventory and the version-freshness probe
    assert "AGENTS.md" in out.stdout
    assert "bundle / engine" in out.stdout
    assert "sha256" in out.stdout
