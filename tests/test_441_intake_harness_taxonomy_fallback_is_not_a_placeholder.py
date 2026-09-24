"""The batch harness must not hand the engine the one string the engine refuses.

`tools/intake_harness.py` builds the engine command line itself. Its taxonomy fallback was the
literal `"sp."`, and `mamey.cohort_resolver.is_placeholder_taxonomy("sp.")` is True, so every
genome whose antiSMASH GBK carries no ORGANISM was refused with TAXONOMY_PLACEHOLDER. A genome
submitted to antiSMASH as FASTA has no ORGANISM anywhere in the record, so that is the whole
owner cohort.

Pinned at the seam where the two sides meet: the literal the harness passes, checked against the
guard the engine applies. Reading either file alone would not catch it.
"""
import re
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUNDLE))

from mamey.cohort_resolver import is_placeholder_taxonomy  # noqa: E402

HARNESS = BUNDLE / "tools" / "intake_harness.py"


def _fallback_literal() -> str:
    """The right-hand side of the `--taxonomy` argument's `or` fallback, read from the source."""
    source = HARNESS.read_text(encoding="utf-8")
    match = re.search(r'"--taxonomy",\s*org\s+or\s+"([^"]*)"', source)
    assert match, "could not find the --taxonomy fallback in tools/intake_harness.py"
    return match.group(1)


def test_the_harness_fallback_is_not_what_the_engine_refuses():
    fallback = _fallback_literal()
    assert not is_placeholder_taxonomy(fallback), (
        f"intake_harness passes --taxonomy {fallback!r} when the GBK has no ORGANISM, and "
        "mamey.cohort_resolver.is_placeholder_taxonomy rejects it, so every such strain fails "
        "with TAXONOMY_PLACEHOLDER before any filesystem work")


def test_the_fallback_preserves_uncertainty_rather_than_naming_a_taxon():
    """'not verified' is the engine's own documented spelling for unresolved taxonomy. A fallback
    that invented a genus would be worse than the bug it replaced."""
    assert _fallback_literal() == "not verified"


def test_the_guard_still_rejects_a_real_placeholder():
    """The fix must not be a weakening of the guard."""
    assert is_placeholder_taxonomy("sp.")
    assert not is_placeholder_taxonomy("Streptomyces sp.")
    assert not is_placeholder_taxonomy("not verified")
