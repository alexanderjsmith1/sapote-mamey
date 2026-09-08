"""test_resolver_allowlist.py — resolver allowlist hardening + AS-regex tests (v9.7.81).

P1 item 6: actino_status now has an expanded allowlist; 'unknown' is a review tag.
P2 item 9: AS-regex canonical choice is optional hyphen (AS-123 and AS123 both match).
"""
import pytest
from mamey.cohort_resolver import actino_status, ACTINO_GENERA, _genus


# ---------------------------------------------------------------------------
# P1 item 6: allowlist hardening
# ---------------------------------------------------------------------------

class TestActinoStatus:
    def test_streptomyces_actinomycete(self):
        assert actino_status("Streptomyces sp.") == "actinomycete"

    def test_saccharopolyspora_actinomycete(self):
        assert actino_status("Saccharopolyspora sp. AS-901") == "actinomycete"

    def test_actinophytocola_now_actinomycete(self):
        """Actinophytocola was previously falling to 'unknown' — must now be actinomycete."""
        assert actino_status("Actinophytocola sp.") == "actinomycete"

    def test_crossiella_now_actinomycete(self):
        """Crossiella was absent from the old allowlist."""
        assert actino_status("Crossiella equi") == "actinomycete"

    def test_polymorphospora_now_actinomycete(self):
        """Polymorphospora rubra (quinolidomicin producer) was absent."""
        assert actino_status("Polymorphospora rubra") == "actinomycete"

    def test_dactylosporangium_now_actinomycete(self):
        assert actino_status("Dactylosporangium sp.") == "actinomycete"

    def test_bacillus_non_actinomycete(self):
        assert actino_status("Bacillus subtilis") == "non_actinomycete"

    def test_pseudomonas_non_actinomycete(self):
        assert actino_status("Pseudomonas aeruginosa") == "non_actinomycete"

    def test_unknown_genus_review_tag(self):
        """An unrecognised genus returns 'unknown' — the review tag."""
        result = actino_status("Weirdusgenus sp.")
        assert result == "unknown", (
            "Unrecognised genera should return 'unknown' as a review tag"
        )

    def test_empty_organism_unknown(self):
        assert actino_status("") == "unknown"

    def test_candidatus_prefix_stripped(self):
        """'Candidatus' prefix is stripped before genus lookup."""
        assert actino_status("Candidatus Saccharibacteria sp.") == "unknown"

    def test_genera_set_is_all_lowercase(self):
        """ACTINO_GENERA must be all lowercase (the matcher lowercases the genus)."""
        assert all(g == g.lower() for g in ACTINO_GENERA), (
            "ACTINO_GENERA entries must be lowercase for case-insensitive matching"
        )

    def test_no_genus_duplicates(self):
        """ACTINO_GENERA must have no duplicate entries.

        NOTE: ``ACTINO_GENERA`` is a *set* literal, so Python deduplicates it at parse
        time — ``len(ACTINO_GENERA) == len(set(ACTINO_GENERA))`` is a tautology that can
        never fail and is structurally blind to a duplicated token in the source. To
        actually catch a duplicate we must inspect the source literal itself.
        """
        import ast
        import inspect
        from mamey import cohort_resolver

        src = inspect.getsource(cohort_resolver)
        tree = ast.parse(src)
        literal_strings: list[str] = []
        for node in ast.walk(tree):
            # find the `ACTINO_GENERA = { ... }` assignment and read its element strings
            if (isinstance(node, ast.Assign)
                    and any(getattr(t, "id", None) == "ACTINO_GENERA" for t in node.targets)
                    and isinstance(node.value, ast.Set)):
                for elt in node.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        literal_strings.append(elt.value)
        assert literal_strings, "could not locate ACTINO_GENERA set literal in source"
        dupes = sorted({g for g in literal_strings if literal_strings.count(g) > 1})
        assert not dupes, f"duplicate genus token(s) in ACTINO_GENERA source literal: {dupes}"


class TestSidHyphenResolution:
    """Regression: a hyphenated public SID in the organism string must resolve to the
    SID cohort. The module docstring's motivating example uses the hyphenated form
    ("Streptomyces sp. SID-XXX"), so the embedded-SID regex must accept the hyphen.
    """

    def test_hyphenated_sid_in_organism_resolves(self):
        from mamey.cohort_resolver import resolve_cohort
        r = resolve_cohort("WWGG00000000", "Streptomyces sp. SID-441")
        assert r["cohort"] == "SID"
        assert r["resolved_sid"] == "SID441"

    def test_unhyphenated_sid_still_resolves(self):
        # the existing WGS form must keep working unchanged
        from mamey.cohort_resolver import resolve_cohort
        r = resolve_cohort("WWGG00000000", "Streptomyces sp. SID8375")
        assert r["cohort"] == "SID"
        assert r["resolved_sid"] == "SID8375"

    def test_spaced_sid_still_resolves(self):
        from mamey.cohort_resolver import resolve_cohort
        r = resolve_cohort("WWGG00000000", "Streptomyces sp. SID 10815")
        assert r["cohort"] == "SID"
        assert r["resolved_sid"] == "SID10815"


# ---------------------------------------------------------------------------
# P2 item 9: AS-regex canonical choice
# ---------------------------------------------------------------------------

class TestASRegex:
    """The canonical AS-regex uses optional hyphen: AS-123 and AS123 both match."""

    def _matches_as(self, s: str) -> bool:
        from mamey.cohort_resolver import _AS_RE
        return bool(_AS_RE.match(s.upper()))

    def test_as_with_hyphen(self):
        assert self._matches_as("AS-901")

    def test_as_without_hyphen(self):
        """AS123 (no hyphen) must also match under optional-hyphen canonical."""
        assert self._matches_as("AS901")

    def test_as_with_underscore_does_not_match(self):
        """AS_760 with underscore should NOT match (underscore was in the old regex)."""
        # After the fix, the canonical pattern is AS-? (hyphen only, not underscore)
        from mamey.cohort_resolver import _AS_RE
        assert not _AS_RE.match("AS_760")

    def test_ajs_matches(self):
        # .402 r3 (ajs_routing_only_boundary): AJS-shaped IDs no longer resolve as AS —
        # Codex REPAIR_FIRST disposition confirmed the old match was the defect (AJS is an
        # optional external benchmark, never pooled into AS membership). Inverted lock.
        assert not self._matches_as("AJS001")

    def test_non_as_does_not_match(self):
        assert not self._matches_as("SID1234")
        assert not self._matches_as("WAC00040")

    def test_dedup_guard_as_pattern_optional_hyphen(self):
        """dedup_and_guard.AS_PATTERN must match both AS-123 and AS123."""
        from mamey.dedup_and_guard import AS_PATTERN
        assert AS_PATTERN.search("AS-901")
        assert AS_PATTERN.search("AS901")
        assert not AS_PATTERN.search("WAC00040")
