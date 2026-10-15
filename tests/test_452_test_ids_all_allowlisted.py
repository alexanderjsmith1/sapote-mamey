"""Every strain-style ID in tests/ is on tools/test_synthetic_ids.txt.

The cut's public-tier audit (tools/make_public_tier.sh) refuses the CODE tier when a test carries an
AS/AJS/PENDING identifier that is not on the allowlist. This test runs the same scan before a cut, so a
missing entry fails the suite instead of aborting the release after both full-suite gates have passed.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Same pattern as make_public_tier.sh: hyphenated or dashless AS/AJS with two or more digits, or PENDING-<token>.
ID = re.compile(r"\b(?:AS|AJS|as|ajs)-?[0-9]{2,}|\bPENDING-[A-Z0-9]+")
PLACEHOLDERS = {"AS-XXX", "AJS-XXX", "PENDING-XXX"}


def _normalise(token):
    up = token.upper()
    return re.sub(r"^(AS|AJS)([0-9])", r"\1-\2", up)


def _allowlist():
    lines = (ROOT / "tools" / "test_synthetic_ids.txt").read_text().splitlines()
    return {l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")}


def test_every_test_id_is_allowlisted():
    allowed = _allowlist()
    missing = {}
    for path in sorted((ROOT / "tests").rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue  # binary fixtures: grep -I skips them too
        for tok in set(ID.findall(text)):
            if tok in PLACEHOLDERS:
                continue
            if _normalise(tok) not in allowed:
                missing.setdefault(_normalise(tok), []).append(str(path.relative_to(ROOT)))
    assert not missing, f"strain-style IDs in tests/ missing from tools/test_synthetic_ids.txt: {missing}"


def test_scan_matches_the_cut_audit_shapes():
    assert ID.findall("f'AS-92{i}'") == ["AS-92"]          # a literal prefix is a token
    assert ID.findall("f'AS-{970 + i}'") == []                # an arithmetic spelling is not
    assert ID.findall("AS971 as-972 AJS-001") == ["AS971", "as-972", "AJS-001"]
    assert _normalise("as971") == "AS-971"
