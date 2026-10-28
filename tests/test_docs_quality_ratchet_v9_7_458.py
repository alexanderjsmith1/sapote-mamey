"""Docs-quality ratchet: source line references and over-long sentences in reader docs may only go down.

Scope matches the docs-quality metric used for the .458 docs review: every Markdown page outside
tests/, history/, archive/, patch_notes/ and working/, excluding CHANGELOG, RELEASES_LOG, FILE_ATLAS
and *.generated.md, with fenced code removed.

- A line reference is `path.ext:NNN`, `path.ext:LNNN` or `path.ext#LNNN` (with optional ranges),
  or a bare `(:NNN–NNN)` locator. `file.md#5-heading` is an anchor, not a line reference.
  Line numbers go stale at every cut; cite the module or the function instead.
- A long sentence has more than 40 words.

Hedge phrases are deliberately not ratcheted: most are claim-safety wording ("does not establish").
When a cut lowers a count, lower its ceiling here to the measured value. Never raise it.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {"tests", "history", "archive", "patch_notes", "working", ".git"}
SKIP_NAMES = {"CHANGELOG.md", "RELEASES_LOG.md", "FILE_ATLAS.md"}
LINEREF = re.compile(r"\b[\w/.-]+\.(?:py|R|sh|json|md)(?::L?\d+|#L\d+)(?:\s*[–-]\s*L?\d+)?\b|\(`?:\d+[–-]\d+`?\)")

LINEREF_CEILING = 72   # measured on the .460 stack; .458 measured 73, .457 measured 539
LONG_SENTENCE_CEILING = 1113   # measured on the .458 stack; .457 measured 2,446


def _measure():
    linerefs = longs = 0
    for p in sorted(ROOT.rglob("*.md")):
        rel = p.relative_to(ROOT)
        if SKIP_PARTS & set(rel.parts) or p.name in SKIP_NAMES or p.name.endswith(".generated.md"):
            continue
        body = re.sub(r"```.*?```", "", p.read_text(encoding="utf-8", errors="ignore"), flags=re.S)
        linerefs += len(LINEREF.findall(body))
        longs += sum(1 for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", body)) if len(s.split()) > 40)
    return linerefs, longs


def test_docs_line_references_do_not_grow():
    linerefs, _ = _measure()
    assert linerefs <= LINEREF_CEILING, (
        f"{linerefs} source line references in reader docs (ceiling {LINEREF_CEILING}); "
        "cite the module or function instead of a line number")


def test_docs_long_sentences_do_not_grow():
    _, longs = _measure()
    assert longs <= LONG_SENTENCE_CEILING, (
        f"{longs} sentences over 40 words in reader docs (ceiling {LONG_SENTENCE_CEILING}); "
        "split them, one idea per sentence")
