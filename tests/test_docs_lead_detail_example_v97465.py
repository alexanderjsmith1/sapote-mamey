"""Lead-detail wiring must contain an executable argument example, not shell placeholders."""
from pathlib import Path
import re
import shlex
def test_lead_detail_documented_command_has_real_argument_tokens():
    page = Path(__file__).resolve().parents[1] / "docs/modules/SAPOTE_LEAD_DETAIL_MODULE.md"
    commands = []
    for block in re.findall(r"```(?:bash)?\n(.*?)```", page.read_text(encoding="utf-8"), re.S):
        block = block.replace("\\\n", " ")
        commands.extend(line.strip() for line in block.splitlines()
                        if line.strip().startswith("python tools/build_lead_detail.py "))
    assert commands
    for command in commands:
        tokens = list(shlex.shlex(command, posix=True, punctuation_chars="<>"))
        assert not any(set(t) <= set("<>") for t in tokens), command
        assert "…" not in tokens and "..." not in tokens, command
        for option in ("--package", "--gbk-dir", "--leads", "--out"):
            assert option in tokens and tokens.index(option) + 1 < len(tokens), command
