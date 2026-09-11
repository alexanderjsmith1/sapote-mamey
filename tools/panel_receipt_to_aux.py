#!/usr/bin/env python3
"""Export explicit query accessions from a panel receipt to a new auxiliary TSV."""
import argparse
import csv
# Use the bundle's spreadsheet-safe writers for all tabular exports.
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ModuleNotFoundError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

import json
from pathlib import Path
import re
import sys
import logging
_LOG = logging.getLogger(__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("panel_receipt")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if Path(args.out).exists():
            raise ValueError("OUTPUT_EXISTS")
        with open(args.panel_receipt) as handle:
            data = json.load(handle)
        if not isinstance(data, dict) or not isinstance(data.get("records"), list):
            raise ValueError("PANEL_RECEIPT_SCHEMA")
        rows, seen = [], set()
        for record in data["records"]:
            if not isinstance(record, dict):
                raise ValueError("PANEL_RECEIPT_ROW")
            if record.get("kind") != "query":
                continue
            tip, accession = record.get("tip"), record.get("accession")
            if not isinstance(tip, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", tip) or tip in seen:
                raise ValueError("PANEL_QUERY_IDENTITY")
            seen.add(tip)
            if not accession:
                continue
            if not isinstance(accession, str) or not re.fullmatch(r"[A-Z]{1,6}_?[0-9]+(?:\.[0-9]+)?", accession):
                raise ValueError("PANEL_QUERY_ACCESSION")
            rows.append([tip, "", "", accession])
        if not rows:
            raise ValueError("NO_QUERY_ACCESSIONS")
        with open(args.out, "x", newline="") as handle:
            writer = _SafeWriter(handle, delimiter="\t")
            writer.writerow(["strain", "host", "region", "accession"])
            writer.writerows(rows)
        _LOG.info(f"AUXILIARY_TABLE_COMPLETE {len(rows)} rows")
        return 0
    except (ValueError, OSError) as exc:
        _LOG.error(f"AUXILIARY_TABLE_REFUSED: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
