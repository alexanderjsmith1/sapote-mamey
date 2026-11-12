"""Required locus identities must not admit JSON null or container values."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test modules import by bare name
from test_locus_comparison import m, sample  # noqa: E402

@pytest.mark.parametrize("kind,field", [("bgc", key) for key in ("strain", "contig", "region", "bgc")] + [("reference", key) for key in ("accession", "description")])
@pytest.mark.parametrize("invalid", [None, False, [], {}])
def test_invalid_identity_is_refused(kind, field, invalid):
    data = sample()
    track = data["tracks"][0]
    track["kind"] = kind
    track["identity"] = ({"strain":"X", "contig":"contig1", "region":"region001", "bgc":"BGC001"} if kind == "bgc" else {"accession":"REF1", "description":"Synthetic reference"})
    track["identity"][field] = invalid
    with pytest.raises(ValueError, match="complete BGC identity"):
        m.validate(data)

@pytest.mark.parametrize("region", ["region001", 1])
def test_complete_bgc_identity_allows_existing_region_forms(region):
    data = sample()
    data["tracks"][0].update(kind="bgc", identity={"strain":"X", "contig":"contig1", "region":region, "bgc":"BGC001"})
    m.validate(data)
