"""v9.7.285: the node·region locator parser must survive SPAdes coverage with a dot
(e.g. cov_19.006984) — the old [^.]*? regex stopped at the dot and fell back to the full
filename, silently breaking the cite-by-node·region contract and any downstream join."""
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("_bcs", ROOT / "tools" / "bigscape_cross_strain.py")
_bcs = importlib.util.module_from_spec(spec); spec.loader.exec_module(_bcs)


def test_dotted_coverage_locator_parses_to_node_region():
    fn = "AS-311_NODE_107_length_28859_cov_19.006984.region001.gbk"
    m = _bcs.LOCATOR.search(fn)
    assert m is not None, "regex failed on dotted coverage"
    node, region = m.group(1), m.group(2)
    assert node == "NODE_107_length_28859_cov_19.006984", node
    assert region == "region001", region


def test_undotted_coverage_still_parses_identically():
    fn = "AS-311_NODE_5_length_120000_cov_42.region002.gbk"
    m = _bcs.LOCATOR.search(fn)
    assert m and m.group(1) == "NODE_5_length_120000_cov_42" and m.group(2) == "region002"
