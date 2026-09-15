#!/usr/bin/env python3
"""Machine-readable receipt for tips deliberately left off a GToTree panel.

The owner rule: a tip whose isolation source or geography is not recorded after its own
record was checked is omitted from the tree and listed by full name so a person can look it
up. A bare identifier list cannot distinguish that deliberate omission from a staging
regression, so the receipt carries a reason per tip.

File: ``omitted_tips.tsv`` beside the panel, tab-separated, header ``tip	name	reason``.

    tip     accession or tip label exactly as it appears (or would appear) in the tree
    name    full genus + species + strain, pasteable into a search
    reason  one of
              NO_DEPOSITED_SOURCE
              NO_DEPOSITED_GEOGRAPHY
              DUPLICATE_OF:<tip>
              OWNER_RULE:<free text>

A tip may carry more than one row (for example both NO_DEPOSITED_SOURCE and
NO_DEPOSITED_GEOGRAPHY). Nothing here infers a reason; the caller states it.

CLI::

    omitted_tips_receipt.py add   --receipt omitted_tips.tsv --tip T --name N --reason R
    omitted_tips_receipt.py check --receipt omitted_tips.tsv --prior prior_figure_metadata.tsv \
                                  --staged staged_tips.txt

``check`` applies the compose-step refusal rule: every tip of the prior panel must be either
staged or receipted. It exits non-zero and names the unaccounted tips otherwise.
"""
from __future__ import annotations

import argparse
import csv
import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import logging as _logging  # noqa: E402
import sys as _sys_for_log  # noqa: E402
_LOG = _logging.getLogger(__name__)
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import re
import sys
from pathlib import Path

COLUMNS = ("tip", "name", "reason")
FIXED_REASONS = ("NO_DEPOSITED_SOURCE", "NO_DEPOSITED_GEOGRAPHY")
REASON_RE = re.compile(r"^(NO_DEPOSITED_SOURCE|NO_DEPOSITED_GEOGRAPHY|DUPLICATE_OF:\S+|OWNER_RULE:\S.*)$")


class OmitReceiptError(ValueError):
    pass


def validate_reason(reason: str) -> str:
    reason = (reason or "").strip()
    if not REASON_RE.match(reason):
        raise OmitReceiptError(
            f"OMIT_REASON_INVALID: {reason!r}; expected NO_DEPOSITED_SOURCE, "
            "NO_DEPOSITED_GEOGRAPHY, DUPLICATE_OF:<tip> or OWNER_RULE:<text>"
        )
    return reason


def validate_row(row: dict) -> dict:
    tip = (row.get("tip") or "").strip()
    name = (row.get("name") or "").strip()
    if not tip:
        raise OmitReceiptError("OMIT_TIP_EMPTY")
    if not name:
        raise OmitReceiptError(f"OMIT_NAME_EMPTY: {tip}")
    if "\t" in name or "\n" in name:
        raise OmitReceiptError(f"OMIT_NAME_MULTILINE: {tip}")
    return {"tip": tip, "name": name, "reason": validate_reason(row.get("reason", ""))}


def read_receipt(path: str | Path) -> list[dict]:
    path = Path(path)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = tuple(reader.fieldnames or ())
        if header[: len(COLUMNS)] != COLUMNS:
            raise OmitReceiptError(f"OMIT_RECEIPT_HEADER: {path} has {header}, expected {COLUMNS}")
        return [validate_row(row) for row in reader]


def write_receipt(path: str | Path, rows: list[dict]) -> Path:
    path = Path(path)
    clean = [validate_row(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(clean)
    return path


def append_receipt(path: str | Path, row: dict) -> Path:
    path = Path(path)
    existing = read_receipt(path) if path.exists() else []
    return write_receipt(path, existing + [row])


def unaccounted_tips(prior_tips, staged_tips, receipt_rows) -> list[str]:
    """Prior-panel tips that are neither staged nor receipted (the compose refusal rule)."""
    staged = {t.strip() for t in staged_tips}
    receipted = {r["tip"] for r in receipt_rows}
    return sorted(t for t in (p.strip() for p in prior_tips) if t and t not in staged and t not in receipted)


def _tips_from_metadata(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    out = []
    for row in rows:
        for key in ("identifier", "tip"):
            if (row.get(key) or "").strip():
                out.append(row[key].strip())
    return out


def _tips_from_list(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv=None) -> int:
    _logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys_for_log.stdout)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add", help="append one receipted omission")
    add.add_argument("--receipt", required=True)
    add.add_argument("--tip", required=True)
    add.add_argument("--name", required=True)
    add.add_argument("--reason", required=True)
    chk = sub.add_parser("check", help="refuse a prior tip that is neither staged nor receipted")
    chk.add_argument("--receipt", required=True)
    chk.add_argument("--prior", required=True, help="prior panel figure_metadata.tsv (identifier/tip columns)")
    chk.add_argument("--staged", required=True, help="text file, one staged tip/accession per line")
    args = parser.parse_args(argv)

    if args.cmd == "add":
        append_receipt(args.receipt, {"tip": args.tip, "name": args.name, "reason": args.reason})
        _LOG.info(f"receipted {args.tip}: {args.reason}")
        return 0

    receipt = read_receipt(args.receipt) if Path(args.receipt).exists() else []
    prior = _tips_from_metadata(Path(args.prior))
    staged = _tips_from_list(Path(args.staged))
    missing = unaccounted_tips(prior, staged, receipt)
    if missing:
        _LOG.info(f"OMIT_UNRECEIPTED: {len(missing)} prior tip(s) neither staged nor receipted: {missing}")
        return 2
    _LOG.info(f"omit receipt complete: {len(receipt)} receipted, {len(staged)} staged, prior {len(set(prior))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
