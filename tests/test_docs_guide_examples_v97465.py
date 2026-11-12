"""Check documentation commands and raw-HTML placeholders without executing analysis."""
from pathlib import Path
from html.parser import HTMLParser
import re
import shlex
ROOT = Path(__file__).resolve().parents[1]
def commands(page):
    text = (ROOT / page).read_text(encoding="utf-8")
    out = [s for s in re.findall(r"`([^`\n]+)`", text) if s.startswith("python ")]
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        block = block.replace("\\\n", " ")
        out.extend(s.strip() for s in block.splitlines() if s.strip().startswith("python "))
    return out
def test_router_examples_do_not_redirect_placeholder_arguments():
    examples = commands("docs/user_guides/CHOOSE_NEXT_COMMAND.md")
    assert examples
    for line in examples:
        tokens = list(shlex.shlex(line, posix=True, punctuation_chars="<>"))
        assert not any(set(token) <= set("<>") for token in tokens), line
def test_pilot_builder_example_selects_external_output():
    examples = [s for s in commands("examples/README.md") if "build_pilot_inputs.py" in s]
    assert examples, "Guide needs an explicit builder command with its output destination"
    for line in examples:
        tokens = shlex.split(line)
        assert "--out" in tokens
        out = tokens[tokens.index("--out") + 1]
        assert "pilot_project" not in Path(out).parts, "Do not target shipped fixture assets"
def test_recordkeeping_headings_have_no_raw_identity_placeholder_tag():
    class Tags(HTMLParser):
        def __init__(self):
            super().__init__(); self.tags = []
        def handle_starttag(self, tag, attrs):
            self.tags.append(tag)
    text = (ROOT / "docs/audit_recordkeeping/SAPOTE_AUDIT_RECORDKEEPING_PROTOCOL.md").read_text(encoding="utf-8")
    parser = Tags()
    parser.feed("\n".join(line for line in text.splitlines() if line.startswith("#")))
    assert "strain" not in parser.tags, "Raw HTML would hide the heading's placeholder"
