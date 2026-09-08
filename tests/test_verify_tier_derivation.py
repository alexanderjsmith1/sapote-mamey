"""tests/test_verify_tier_derivation.py — regression guard for the
as_only mismatch found in v9.7.151b.

verify_tier_derivation.py's redact_text()/redact_py() previously hardcoded
as_only=False with a comment claiming this "mirrors the code/sid public-tier
scrub" — but every real call site in tools/make_public_tier.sh passes
--as-only, which keeps public SID strain identifiers (Chevrette 2019 attine
ant dataset) untouched. The verifier was checking against a stricter,
never-actually-used policy and would false-positive (FATAL: drift) on any
document mentioning a real SID strain number — first triggered by the
docs/batches/ batch document set, the first bundle content to cite specific
SID numbers (SID8370/8371/8375) in prose.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))


def test_redact_text_leaves_sid_untouched():
    """SID strain IDs are public (Chevrette 2019) and must survive
    verify_tier_derivation's redaction pass, matching the real tier-build
    policy (--as-only) rather than the previously-hardcoded as_only=False."""
    from verify_tier_derivation import redact_text

    text = "A BGC was detected in SID8370 (NODE_3 · region_004) with no close KCB match."
    redacted = redact_text(text)
    assert "SID8370" in redacted, (
        "SID strain IDs must NOT be redacted — they are public (Chevrette 2019). "
        "If this fails, as_only has regressed to False."
    )


def test_redact_text_is_unconditional_for_public_derivation():
    """Public-tier derivation must redact cohort IDs regardless of the legacy AS_SCRUB flag.

    The cut builder now performs this transformation unconditionally. The parity verifier must
    model the resulting tree exactly instead of allowing an environment variable to redefine it.
    """
    import importlib, os
    text = "Strain AS-999 showed a novel phosphonate BGC."
    os.environ.pop("AS_SCRUB", None)
    import verify_tier_derivation as vtd
    importlib.reload(vtd)
    assert "AS-999" not in vtd.redact_text(text)
    os.environ["AS_SCRUB"] = "0"
    importlib.reload(vtd)
    assert "AS-999" not in vtd.redact_text(text)
    os.environ["AS_SCRUB"] = "1"
    importlib.reload(vtd)
    assert "AS-999" not in vtd.redact_text(text)
    os.environ.pop("AS_SCRUB", None)
    importlib.reload(vtd)


def test_public_derivation_models_internal_and_run_directory_stripping():
    from verify_tier_derivation import _is_stripped

    assert _is_stripped("future_improvements/gap_analysis.md")
    assert _is_stripped("runs/example/package.json")
    assert _is_stripped("runs-old/example/package.json")
    assert _is_stripped("private/cohort.tsv")
    assert _is_stripped("docs/legacy/obsolete.md")
    assert _is_stripped(".pytest_cache/README.md")
    assert not _is_stripped("mamey/cli.py")
    assert not _is_stripped("docs/PUBLIC_RELEASE_GUIDE.md")


def test_redact_py_leaves_sid_untouched():
    """Same fix, .py code-comment path (redact_py uses the same as_only flag)."""
    from verify_tier_derivation import redact_py

    text = '# Reference strain: SID8371\nSTRAIN_ID = "SID8371"\n'
    redacted = redact_py(text)
    assert "SID8371" in redacted


def test_path_level_derivation_keeps_python_byte_identical():
    from verify_tier_derivation import redact

    text = 'HOST_GROUPS = {"AS-103": "ATTINE_ANT"}\n'
    assert redact("mamey/widget_data.py", text) == text


def test_redact_matches_real_tier_build_policy():
    """Source-level regression guard: redact_text/redact_py must call the
    underlying redaction function with as_only=True, matching every call
    site in tools/make_public_tier.sh. Catches a future re-introduction of
    the as_only=False mismatch even before it produces a false drift report.

    Checks only actual call sites (`as_only=False)` as a function-call
    argument, not prose mentions of the string in explanatory comments —
    this file's own changelog comment legitimately quotes "as_only=False"
    while describing the historical bug it fixed.
    """
    src = (pathlib.Path(__file__).resolve().parents[1]
           / "tools" / "verify_tier_derivation.py").read_text(encoding="utf-8")
    import re
    # Match it as a real call-site argument: `as_only=False)` or `as_only=False,`
    call_site_pattern = re.compile(r"as_only\s*=\s*False\s*[,)]")
    bad_call_sites = [
        line for line in src.splitlines()
        if call_site_pattern.search(line) and not line.strip().startswith("#")
    ]
    assert not bad_call_sites, (
        f"Found live as_only=False call site(s), not just comment mentions: {bad_call_sites}. "
        "This diverges from the real tier-build policy (--as-only) and produces "
        "false-positive drift reports on any document naming a public SID strain."
    )
    assert src.count("as_only=True") >= 2, (
        "Expected as_only=True in both redact_text and redact_py wrappers"
    )
