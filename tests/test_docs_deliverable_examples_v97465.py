"""Review documented CLI argument wiring without executing analysis commands."""
from pathlib import Path
import re
import shlex
import pytest
ROOT = Path(__file__).resolve().parents[1]
@pytest.mark.parametrize("page", [
    "DELIVERABLE_ContigRescueReconstruction.md",
    "DELIVERABLE_EcologicalSynthesis.md",
    "DELIVERABLE_SubsetPanel.md",
    "MODE_B_DEPTH_POLICY.md",
])
def test_deliverable_commands_are_arguments_not_shell_placeholders(page):
    text = (ROOT / "docs/modules" / page).read_text(encoding="utf-8")
    commands = [c for c in re.findall(r"`([^`\n]+)`", text) if c.startswith("python ")]
    for block in re.findall(r"```(?:bash)?\n(.*?)```", text, re.S):
        block = block.replace("\\\n", " ")
        commands.extend(c.strip() for c in block.splitlines() if c.strip().startswith("python "))
    assert commands, page
    for command in commands:
        tokens = list(shlex.shlex(command, posix=True, punctuation_chars="<>"))
        assert not any(set(t) <= set("<>") for t in tokens), command
        assert "…" not in tokens and "..." not in tokens, command
