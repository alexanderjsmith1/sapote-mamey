"""v9.7.294: Bug Hunt on .292 fixes. P292-05: cross_strain requires an explicit --run-id
and accepts an exact --cutoff (multi-run DB disambiguation). P292-01/02: the ingest + join tools have no bare open().read/write (resource
hygiene). P292-03: the redundant/operator-precedence SSF block is gone from architecture_first."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_p292_05_cross_strain_has_run_id_and_cutoff():
    src = (ROOT / "tools" / "bigscape_cross_strain.py").read_text()
    assert "--run-id" in src and "--cutoff" in src
    assert 'parser.add_argument("--run-id", required=True)' in src
    assert "select max(id) from run" not in src  # never infer a newest run
    assert "build_rows(args.db, args.run_id, args.cutoff" in src


def test_p292_01_02_no_bare_open_read_write():
    for rel in ("tools/bigscape_ingest_to_mamey.py", "tools/antismash_bigscape_join.py"):
        src = (ROOT / rel).read_text()
        assert not re.search(r"open\([^)]*\)\.(read|write)\(", src), f"bare open().read/write in {rel}"
        assert "json.load(open(" not in src, f"json.load(open()) in {rel}"


def test_p292_03_no_buggy_ssf_precedence():
    src = (ROOT / "mamey" / "architecture_first.py").read_text()
    assert "if doms else False" not in src           # the buggy ternary is gone
    assert "re.search(r'\\bSSF\\b', doms)" in src     # the robust check remains
