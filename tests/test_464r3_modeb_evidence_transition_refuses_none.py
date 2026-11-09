"""transition_evidence refuses None and non-string values for its required fields.

`str(None)` is the nonempty text 'None', so a missing reason, locator or
replacement id used to pass the required-value checks.
"""
import pytest

from mamey.modeb_evidence_state import EvidenceTransitionError, transition_evidence

SHA = "a" * 64


@pytest.mark.parametrize("kwargs", [
    dict(current="UNBOUND", target="ABSENT_IN_SCOPE", reason=None),
    dict(current="UNBOUND", target="ADMITTED", reason="exact result", source_locator=None, source_sha256=SHA),
    dict(current="ADMITTED", target="SUPERSEDED", reason="newer run", replacement_id=None),
    dict(current=None, target="UNBOUND", reason="x"),
    dict(current="UNBOUND", target="ABSENT_IN_SCOPE", reason=7),
])
def test_none_or_non_string_is_refused(kwargs):
    current, target = kwargs.pop("current"), kwargs.pop("target")
    with pytest.raises(EvidenceTransitionError):
        transition_evidence(current, target, **kwargs)


def test_real_strings_still_pass():
    t = transition_evidence("UNBOUND", "ADMITTED", reason="reviewed exact result",
                            source_locator="evidence://run1/hits.tsv", source_sha256=SHA)
    assert t.current_state == "ADMITTED" and t.reason == "reviewed exact result"
