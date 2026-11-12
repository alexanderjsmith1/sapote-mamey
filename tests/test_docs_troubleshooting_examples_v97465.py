"""Intake examples must supply literal arguments without shell redirection."""
from pathlib import Path
import re
import shlex
import pytest
ROOT = Path(__file__).resolve().parents[1]
@pytest.mark.parametrize("name", ["ANTISMASH_INPUT_WORKFLOW.md", "SINGLE_REGION_ACCESSION_INPUTS.md"])
def test_troubleshooting_intake_examples_have_no_redirection_placeholders(name):
    text = (ROOT / "docs/troubleshooting" / name).read_text(encoding="utf-8")
    commands = [c for c in re.findall(r"`([^`\n]+)`", text) if c.startswith("python mamey_run.py ")]
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        block = block.replace("\\\n", " ")
        commands.extend(line.strip() for line in block.splitlines() if line.strip().startswith("python mamey_run.py "))
    assert commands, name
    for command in commands:
        tokens = list(shlex.shlex(command, posix=True, punctuation_chars="<>"))
        assert not any(set(t) <= set("<>") for t in tokens), command
