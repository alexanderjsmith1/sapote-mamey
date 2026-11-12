"""SOP CLI examples must pass literal paths as arguments, not shell redirection."""
import re
import shlex
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("page", [
    "SOP-00_Start_Here_Choosing_Path.md",
    "SOP-02_ChatGPT_Safe_Smoke_Run.md",
    "SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md",
    "SOP-07_Single_Region_Public_Accession_Inputs.md",
])
def test_sop_mamey_examples_do_not_redirect_placeholder_paths(page):
    text = (ROOT / "docs/SOPs" / page).read_text(encoding="utf-8")
    commands = [item for item in re.findall(r"`([^`\n]+)`", text)
                if item.startswith("python mamey_run.py ")]
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        block = block.replace("\\\n", " ")
        commands.extend(line.strip() for line in block.splitlines()
                        if line.strip().startswith("python mamey_run.py "))
    assert commands, f"No CLI example was checked in {page}"
    for command in commands:
        tokens = list(shlex.shlex(command, posix=True, punctuation_chars="<>"))
        assert not any(set(token) <= set("<>") for token in tokens), command
