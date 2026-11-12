"""Reference helper examples must pass paths as arguments, not shell operators."""
from pathlib import Path
import re
import shlex
import pytest
ROOT = Path(__file__).resolve().parents[1]
@pytest.mark.parametrize("page", ["SCANNER_PFAM_MANIFEST.md", "06_CURRENT_SOURCE_SCOPE.md"])
def test_reference_examples_do_not_redirect_placeholder_paths(page):
    text = (ROOT / "docs/reference" / page).read_text(encoding="utf-8")
    commands = [s for s in re.findall(r"`([^`\n]+)`", text) if s.startswith(("python ", "python3 "))]
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        block = block.replace("\\\n", " ")
        commands.extend(s.strip() for s in block.splitlines() if s.strip().startswith(("python ", "python3 ")))
    assert commands
    for command in commands:
        tokens = list(shlex.shlex(command, posix=True, punctuation_chars="<>"))
        assert not any(set(t) <= set("<>") for t in tokens), command
