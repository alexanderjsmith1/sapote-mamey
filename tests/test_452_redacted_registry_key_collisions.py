import json
import pytest
from tools.redact_public_tier import _redact_json_registry

@pytest.mark.parametrize("existing_first", [True, False])
def test_disambiguation_never_overwrites_an_existing_masked_suffix(existing_first):
    original = [("AS-XXX-1", {"marker": "existing"}), ("AS-971", {"marker": "first"}), ("AS-972", {"marker": "second"})]
    if not existing_first: original = original[1:] + original[:1]
    payload = {"strains": dict(original), "n_strains": 3}
    result = json.loads(_redact_json_registry(json.dumps(payload), as_only=True))
    assert result["n_strains"] == 3
    assert {row["marker"] for row in result["strains"].values()} == {"existing", "first", "second"}
