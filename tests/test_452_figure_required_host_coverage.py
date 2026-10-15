import json
import pytest
from tools.figure_check import check

@pytest.mark.parametrize("state", ["missing", "empty", "not_supplied"])
def test_required_query_host_map_is_not_silently_unchecked(tmp_path, state):
    tree = tmp_path / "tree.treefile"
    tree.write_text("(Syntheticus_AS-971:0.1,Reference_OUTGROUP:0.1);")
    host = tmp_path / "host.json"
    if state == "empty": host.write_text("{}")
    path = None if state == "not_supplied" else str(host)
    ok, message = check(str(tree), hostmap=path)
    assert not ok
    assert "F1 MARKER_COVERAGE" in message
    assert check(str(tree), hostmap=path, marker_checks=False)[0]
