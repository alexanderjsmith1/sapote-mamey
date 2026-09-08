"""Cross-assistant bootstrap discoverability from bootstrap_contract.yml.

The bundle must be self-starting in ChatGPT and Claude without making the
CHATGTP transposition alias authoritative. Required canonical/mirror surfaces are
hard gates; optional aliases are rescue shims.

One-door discoverability (v9.7.409): the operating contract + the timeout-safe
first run are guaranteed by the ONE canonical door — AGENTS.md (= CLAUDE.md) and
the runtime `start` output — plus the two assistant contracts. Every other root
door only has to REDIRECT there; it is NOT required to re-carry the full token
set. Dropping that redundancy mandate is what lets the non-canonical doors shrink
to <=3-line redirect stubs (co-apply lane: CLAUDE_409_onboarding_one_door).
"""
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Roles whose surfaces are the CANONICAL contracts an operator actually reads.
_CANONICAL_CONTRACT_ROLES = {"canonical_chatgpt_contract", "canonical_claude_contract"}
# Generated report; not an operator-facing door.
_GENERATED_MAP_ROLES = {"generated_bootstrap_map"}

# A door "redirects" if it names any of the canonical entry points. AGENTS.md (the
# one door) and the `start` command are the funnel targets a <=3-line stub uses;
# the two assistant contract filenames are accepted so today's fuller doors also
# qualify. Any one pointer is enough — that is the whole point of the redesign.
_REDIRECT_POINTERS = (
    "AGENTS.md",
    "mamey_run.py start",
    "-m mamey start",
    "CHATGPT_START_HERE.md",
    "CLAUDE_START_HERE.md",
)
# The full guarantee the canonical door must carry: both contracts are findable
# and the timeout-safe first run is right there.
_TIMEOUT_SAFE_FLAGS = ("--capped-session", "--chatgpt-safe")


def _surfaces():
    data = yaml.safe_load((ROOT / "bootstrap_contract.yml").read_text(encoding="utf-8"))
    return data["bootstrap_surfaces"]


def test_required_bootstrap_surfaces_exist():
    missing = [s["path"] for s in _surfaces() if s.get("required") and not (ROOT / s["path"]).exists()]
    assert not missing, f"missing required bootstrap surfaces: {missing}"


def test_canonical_one_door_carries_the_full_bootstrap_guarantee():
    """The guarantee lives in ONE place, not smeared across every door.

    AGENTS.md (and its byte-identical CLAUDE.md copy) must name both assistant
    contracts and carry the timeout-safe first-run flag. This is the single
    surface a landing coding agent auto-reads, so the guarantee is anchored here
    rather than duplicated into README/router/alias doors.
    """
    door = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert (ROOT / "CLAUDE.md").read_text(encoding="utf-8") == door, \
        "AGENTS.md and CLAUDE.md must stay one door under two names"
    assert "CHATGPT_START_HERE.md" in door, "the one door must point ChatGPT to its contract"
    assert "CLAUDE_START_HERE.md" in door, "the one door must point Claude to its contract"
    assert any(f in door for f in _TIMEOUT_SAFE_FLAGS), \
        "the one door must carry the timeout-safe first run (--capped-session / --chatgpt-safe)"


def test_start_runtime_carries_timeout_safe_first_run_and_names_the_one_door():
    """`start` is generated from the running bundle, so it is the authoritative
    timeout-safe first-run carrier. It must show the capped-session run and route
    the operator to AGENTS.md."""
    out = subprocess.run(
        [sys.executable, str(ROOT / "mamey_run.py"), "start", "--no-doctor"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr[-500:]
    assert any(f in out.stdout for f in _TIMEOUT_SAFE_FLAGS), \
        "start must print the timeout-safe capped-session run in the happy path"
    assert "AGENTS.md" in out.stdout, "start must route the operator to the one door"


def test_timeout_word_survives_in_the_canonical_contracts():
    """Keep the literal 'timeout' guarantee alive where it is authoritative — the
    two assistant contracts — instead of forcing the word into every root file."""
    for role in ("canonical_chatgpt_contract", "canonical_claude_contract"):
        surface = next(s for s in _surfaces() if s.get("role") == role)
        txt = (ROOT / surface["path"]).read_text(encoding="utf-8")
        assert "timeout" in txt.lower(), \
            f"{surface['path']} (canonical contract) must explain timeout-safe behavior"


def test_non_canonical_doors_redirect_instead_of_re_carrying_the_full_token_set():
    """The structural enabler for the one-door design.

    Every non-canonical, non-generated .md surface must REDIRECT to a canonical
    entry point (AGENTS.md / `start` / an assistant contract). It is NOT required
    to re-carry both filenames + the run flag + 'timeout' — that redundancy
    mandate is exactly what blocked <=3-line redirect stubs. A door that only
    redirects passes; a door with no pointer to the one door fails.
    """
    for surface in _surfaces():
        rel = surface["path"]
        p = ROOT / rel
        if not p.exists() or p.suffix != ".md":
            continue
        if surface.get("role") in _CANONICAL_CONTRACT_ROLES | _GENERATED_MAP_ROLES:
            continue
        txt = p.read_text(encoding="utf-8")
        assert any(ptr in txt for ptr in _REDIRECT_POINTERS), (
            f"{rel} must redirect to the one door (one of {_REDIRECT_POINTERS}); "
            "a door with no canonical pointer strands the operator"
        )


def test_typo_alias_rescues_chatgtp_misspelling_without_authority():
    surfaces = {s["path"]: s for s in _surfaces()}
    alias = surfaces["CHATGTP_READ_ME_FIRST.md"]
    assert alias["required"] is False
    assert alias["scanner_authority"] is False
    txt = (ROOT / "CHATGTP_READ_ME_FIRST.md").read_text(encoding="utf-8")
    assert "ChatGTP" in txt or "CHATGTP" in txt
    assert "You probably meant" in txt
    assert "accidental" in txt.lower()


def test_root_bootstrap_declares_contract_map_not_exact_six_authority():
    txt = (ROOT / "000_READ_ME_FIRST_CHATGPT_CLAUDE.md").read_text(encoding="utf-8")
    assert "bootstrap_contract.yml" in txt
    assert "typo-rescue aliases" in txt or "rescue shims" in txt
    for surface in _surfaces():
        assert surface["path"] in txt


def test_chatgpt_contract_mentions_contract_and_typo_alias_policy():
    txt = (ROOT / "CHATGPT_START_HERE.md").read_text(encoding="utf-8")
    assert "000_READ_ME_FIRST_CHATGPT_CLAUDE.md" in txt
    assert "CHATGTP_READ_ME_FIRST.md" in txt
    assert "optional typo rescue" in txt or "optional accidental-typo rescue" in txt
    assert "--capped-session" in txt or "--chatgpt-safe" in txt


def test_chatgpt_init_lists_canonical_bootstrap_files():
    out = subprocess.run(
        [sys.executable, "-m", "mamey.cli", "chatgpt-init"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert out.returncode == 0
    stdout = out.stdout
    for rel in ["000_READ_ME_FIRST_CHATGPT_CLAUDE.md", "CHATGPT_START_HERE.md", "CHATGPT_READ_ME_FIRST.md", "CLAUDE_START_HERE.md"]:
        assert rel in stdout
    assert "bootstrap_contract.yml" in stdout
