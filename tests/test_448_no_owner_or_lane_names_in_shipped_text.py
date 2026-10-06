"""Shipped text names no person, working-chat lane, session id or task number.

Rulings and history are written with role nouns ("the owner", "the release owner"); attribution lives in LICENSE,
the README copyright line, citation records and the reference volumes' author lines. The public release audit checks
workspace paths and a short codename list; this guard covers the rest of the shipped text, code comments included.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Built from parts so this file does not match itself.
_OWNER = "Al" + "ex"
_LANES = ["Am" + "ber", "Egg" + "plant", "Black " + "Cherry", "Blizzard " + "Blue", "Razzle " + "Dazzle", "Golden" + "rod",
          "Cer" + "ulean", "Aqua" + "rius", "Ki" + "wi", "Mango " + "Tango", "Laser " + "Lemon", "V" + "GP", "B" + "C2"]
PATTERNS = {
    "owner first name": re.compile(rf"\b{_OWNER}\b(?! ?(?:2026|Smith))"),
    "lane name": re.compile(r"\b(?:" + "|".join(re.escape(x) for x in _LANES) + r")\b"),
    "task label": re.compile(r"\b(?:Codex )?Task[ _]\d{1,3}\b"),
    "session id": re.compile(r"\b(?:d4cc32a9|eb3df1ef|9a8398df|1955a8c0|88fdad06|fa3e5fb1|1947ad84|9c92d456|283f1f96|1246f6ce|"
                             r"afc034dc|ce787e3d|1c20b8bd|2d6758ab|195c219b|9c5f37d0|a5b97902|6275a90d|fd48f690|09af774e|"
                             r"59196886|b4640264|33ea24d7|841e7b03|3ab51b5f)\b", re.I),
}
# Files that must hold these words: the audits and guards that search for them, licences, citations, vendored code,
# the two signed governance records, which only their signer changes, and hash-bound contracts.
ALLOW = {
    "LICENSE", "LICENSE-DOCS.txt", "README.md", "CITATION.cff", "GOVERNANCE_DECISIONS.json", "STRICT_HEALTH_WAIVER.json",
    "mamey/data/tool_citations.json", "tools/public_release_audit.py",
    # hash-bound: Mode B work binds to this contract by sha256; a name change needs a new contract version
    "mamey/data/mode_b/modeb_current50_v2_contract.json",
    "tests/test_448_no_owner_or_lane_names_in_shipped_text.py",
    "tests/public/test_public_release_v9_7_381.py", "tests/public/test_release_audit_fails_closed_v9_7_381.py",
    "tests/test_strict_disclosure_redaction_v97405.py", "tests/test_strict_source_disclosure_audit_v97395.py",
    "tests/test_silent_swallow_sol01_round02.py", "tests/test_workspace_path_portability.py",
    "tests/test_methods_documentation_contract.py", "tests/test_complete_exact_locus_prompt_v97401.py",
    "tests/test_project_data_home_initializer_v97429.py", "tests/test_wiki_in_bundle_v97401.py",
    "tests/test_447_antismash_web_sop.py",
}
ALLOW_PREFIX = ("mamey/_vendor/", "docs/reference/", "Wheelhouse/", "wheels/")
TEXT = {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".sh", ".R", ".r", ".csv", ".tsv", ".html", ".cfg", ".rst"}


def _hits():
    out = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if (not p.is_file() or "__pycache__" in p.parts or p.suffix not in TEXT or rel in ALLOW
                or rel.startswith(ALLOW_PREFIX) or p.stat().st_size > 5_000_000):
            continue
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            for what, rx in PATTERNS.items():
                m = rx.search(line)
                if m:
                    out.append(f"{rel}:{i}: {what} {m.group(0)!r}")
    return out


def test_shipped_text_names_no_person_lane_session_or_task():
    hits = _hits()
    assert not hits, "write a role noun or drop the label:\n" + "\n".join(hits[:40])


def test_the_patterns_catch_what_they_are_for():
    assert PATTERNS["owner first name"].search(f"({_OWNER}, 2026-09-24)")
    assert not PATTERNS["owner first name"].search(f"{_OWNER}ander")
    assert PATTERNS["lane name"].search(f"v9.7.417 ({_LANES[0]}):")
    assert PATTERNS["task label"].search("Codex Task 24 benchmark") and PATTERNS["task label"].search("Task_362 file")
    assert not PATTERNS["task label"].search("--start-batch 10")
