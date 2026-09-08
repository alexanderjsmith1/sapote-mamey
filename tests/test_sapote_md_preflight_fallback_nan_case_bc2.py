"""v9.7.398 — tools/sapote_md_preflight.py's degraded-environment fallback for a real
"boss-facing PDF must not contain a raw forbidden value" preflight check had a case-sensitivity
bug the canonical `mamey/render_safe.has_forbidden_render_string()` does not have.

`mamey/render_safe.py`'s own regex explicitly alternates `(?:nan|NaN|None)` because pandas'
`DataFrame.to_string()`/`.to_markdown()` render missing values as capitalized "NaN" by default —
the standard, common form, not an edge case. The fallback (only reached when
`from mamey.render_safe import has_forbidden_render_string` fails — e.g. this tool used as a
standalone unpacked script without the mamey package on the path) had a bare `\\bnan\\b`,
case-sensitive, matching only lowercase "nan" and missing the exact common case this preflight
exists to catch.
"""
from __future__ import annotations

import inspect
import re

from mamey.render_safe import has_forbidden_render_string as canonical
from tools.sapote_md_preflight import has_forbidden_render_string as primary_path


def _fallback_pristine(text: str) -> bool:
    """The exact pre-fix fallback regex, reconstructed for direct fail-before testing."""
    return bool(re.search(r"\bnp\.|numpy\.|\bnan\b|\bNone\b", text or ""))


def _fallback_fixed(text: str) -> bool:
    """The exact post-fix fallback regex, reconstructed for direct pass-after testing."""
    return bool(re.search(r"\bnp\.|numpy\.|\b(?:nan|NaN)\b|\bNone\b", text or ""))


def test_primary_path_already_catches_capitalized_nan():
    """The real, live import path (mamey.render_safe) is unaffected by this bug — confirms the
    fallback is the only thing that needed fixing."""
    assert primary_path("Value: NaN") is True
    assert canonical("Value: NaN") is True


def test_pristine_fallback_misses_capitalized_nan():
    """The defect, reproduced directly: pandas' standard capitalized 'NaN' representation was
    silently missed by the pre-fix fallback."""
    assert _fallback_pristine("Value: NaN") is False, (
        "if this now returns True, the pristine reconstruction above no longer matches the bug"
    )
    assert _fallback_pristine("Value: nan") is True  # lowercase always worked


def test_fixed_fallback_catches_both_nan_casings():
    assert _fallback_fixed("Value: NaN") is True
    assert _fallback_fixed("Value: nan") is True
    assert _fallback_fixed("Coverage: None") is True
    assert _fallback_fixed("raw repr: np.float64(0.23)") is True
    assert _fallback_fixed("Value: 0.42") is False


def test_fixed_fallback_matches_canonical_on_the_capitalized_case():
    """The fix's intent: mirror the canonical policy's casing exactly, not invent new coverage."""
    assert _fallback_fixed("Value: NaN") == canonical("Value: NaN") == True


def test_deployed_fallback_source_contains_the_fix():
    """Source-level regression guard: forcing the real `from mamey.render_safe import ...` to
    fail from a standalone test isn't practical (the module is already imported), so this checks
    the actual deployed except-branch body contains the case-covering pattern."""
    import tools.sapote_md_preflight as mod
    src = inspect.getsource(mod)
    # v9.7.405: the CODEX_390 third-gate hardening (B-R4) narrowed the fallback to
    # `except ImportError:`; accept either spelling — the guard is about the BODY of the branch.
    except_idx = src.index("except ImportError:") if "except ImportError:" in src else src.index("except Exception:")
    fallback_body = src[except_idx : except_idx + 700]
    assert "(?:nan|NaN)" in fallback_body or ("nan" in fallback_body and "NaN" in fallback_body), (
        "the fallback's except-branch no longer appears to cover both nan casings"
    )
