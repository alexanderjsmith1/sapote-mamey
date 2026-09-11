"""Regression test — v97395 tick 19: check_tier_parity.py's own docstring contradicts its
enforced policy.

The module docstring's REGISTRY-presence bullet claimed the registry is "absent where
intentionally stripped (code, clean)". But `REGISTRY_EXPECTED = {"merged", "sid", "code",
"clean"}` -- ALL FOUR recognized tiers -- with its own inline comment explaining why: "registry
inventory is code-adjacent (0 strain IDs) -- ships in all tiers". The enforcement loop in
main() only ever flags a MISSING registry where expected; it has no code path that would ever
flag a registry PRESENT in a tier the docstring claims strips it. A maintainer reading only the
docstring could "fix" a correctly-shipping code/clean-tier registry as a leak, or conversely
never notice the docstring is simply stale relative to a reasoned later policy change.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))


def test_registry_expected_covers_all_recognized_tiers_v97395():
    from check_tier_parity import REGISTRY_EXPECTED
    # v9.7.408: the `sid` tier is now `cohort` (owner ruling 2026-09-04); `sid` survives only as a
    # deprecated alias in tools/tier_vocabulary.py, never as a canonical member of this set.
    assert REGISTRY_EXPECTED == {"merged", "cohort", "code", "clean", "public"}


def test_docstring_does_not_claim_a_tier_strips_the_registry_v97395():
    from check_tier_parity import REGISTRY_EXPECTED
    src = (pathlib.Path(__file__).resolve().parents[1] / "tools" / "check_tier_parity.py").read_text(
        encoding="utf-8"
    )
    docstring = src.split('"""')[1]
    assert "absent where intentionally stripped" not in docstring, (
        "docstring still claims some tier strips the registry, contradicting "
        f"REGISTRY_EXPECTED={sorted(REGISTRY_EXPECTED)!r}, which the code treats as present "
        "everywhere"
    )
