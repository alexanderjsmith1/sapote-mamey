#!/usr/bin/env python3
"""tools/sapote_workflow.py — CLI shim for the mandatory Sapote workflow driver.

The implementation lives in `mamey/sapote_workflow.py` and is also reachable as
`python -m mamey workflow`. This shim exists so the tool is discoverable in `tools/`
alongside the other gates; it holds NO logic of its own — the v9.7.213 tools/ audit
retired a byte-for-byte duplicate CLI shim (build_master_figure_atlas.py) precisely
because duplicated dispatch drifts out of sync.

Restored in v9.7.238: the v9.7.237 CHANGELOG announced this file as shipped
("`tools/sapote_workflow.py` thin shim") but the cut omitted it, leaving 8 references
to a non-existent path — including the header written into every workflow ledger
(`mamey/sapote_workflow.py:276`).

  python tools/sapote_workflow.py --package <pkg> [--strict] [--json]
  python -m mamey workflow --package <pkg> [--strict] [--json]   # identical
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.sapote_workflow import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
