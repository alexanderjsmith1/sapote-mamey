#!/usr/bin/env python3
"""Report repair-spec binding and figure-receipt readiness states."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys
from pathlib import Path, PurePosixPath

# BC2-407: this tool did not previously import from mamey.* at all, so it never needed the
# sys.path guard every sibling tools/*.py that does carries (see tests/test_tool_front_doors.py,
# which fails any mamey-importing tool that omits this). Required as soon as the shared-gate
# import below was added -- discovered by a composed-set full-suite run, not by this card's own
# original (too-narrow) verification scope.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# BC2-407: use the canonical typed gate from publication_bridge instead of a second,
# independently-drifting string check on the same "binding_state == PROVISIONAL_BINDING"
# signal -- see PATCH_CARD for the tick that found the two checks living apart.
from mamey.interactive_figures.publication_bridge import (  # noqa: E402
    PublicationBridgeRefusal,
    validate_figure_receipt_for_publication,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs" / "figure_factory"

class ReadinessRefusal(RuntimeError): pass

def _qid(value: str) -> str:
    match = re.search(r"Q-?0*(\d+)", value.upper())
    return f"Q-{int(match.group(1)):03d}" if match else ""

def _owner_items(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^## Owner binding required\s*$([\s\S]*?)(?=^## |\Z)", text, re.M)
    if not match: raise ReadinessRefusal(f"READINESS_OWNER_BLOCK_MISSING: {path.name}")
    body = match.group(1).strip()
    if re.search(r"^None\b", body, re.I): return []
    return [re.sub(r"^\d+\.\s*", "", line).strip() for line in body.splitlines() if re.match(r"^\d+\.\s+", line)]

def _receipts(root: Path) -> dict[str, dict]:
    found = {}
    for path in sorted(root.rglob("figure_receipts.jsonl")):
        for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try: row = json.loads(raw)
            except json.JSONDecodeError as exc: raise ReadinessRefusal(f"READINESS_RECEIPT_INVALID: {path}:{number}") from exc
            qid = _qid(str(row.get("figure_id") or ""))
            if qid: found[qid] = {**row, "_root": path.parent}
    return found

def _verified(row: dict) -> bool:
    outputs=row.get("outputs"); root=row.get("_root")
    if not isinstance(outputs,dict) or not isinstance(root,Path): return False
    for kind in ("png","svg"):
        rec=outputs.get(kind)
        if not isinstance(rec,dict): return False
        loc=rec.get("logical_locator"); pure=PurePosixPath(loc) if isinstance(loc,str) else None
        if pure is None or pure.is_absolute() or ".." in pure.parts: return False
        path=root/pure
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=rec.get("sha256") or path.stat().st_size!=rec.get("bytes"): return False
    return True

def build_board(spec_root: Path, receipt_root: Path) -> dict:
    receipts=_receipts(receipt_root); rows=[]
    for path in sorted(spec_root.glob("REPAIR_SPEC_Q-*.md")):
        qid=_qid(path.name); items=_owner_items(path); receipt=receipts.get(qid)
        if receipt:
            try:
                validate_figure_receipt_for_publication(receipt)
            except PublicationBridgeRefusal:
                state = "PROVISIONAL"
            else:
                state = "RECEIPT_VERIFIED" if _verified(receipt) else "BUILT"
        elif not items:
            state = "BOUND"
        else:
            state = "OWNER_HELD"
        rows.append({"queue_id":qid,"spec":path.name,"state":state,"binding_required":items,
                     "figure_id":receipt.get("figure_id") if receipt else None})
    return {"schema_version":"sapote-mamey.figure-readiness-board.v1","status":"PASS","figures":rows}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--spec-root",type=Path,default=SPEC_ROOT); p.add_argument("--receipt-root",type=Path,default=ROOT); p.add_argument("--json",action="store_true"); a=p.parse_args(argv)
    try: board=build_board(a.spec_root,a.receipt_root)
    except ReadinessRefusal as exc: sys.stderr.write(str(exc)+"\n"); return 2
    if a.json: sys.stdout.write(json.dumps(board,indent=2,sort_keys=True)+"\n")
    else:
        sys.stdout.write("queue_id\tstate\tfigure_id\tbinding_items\n")
        for row in board["figures"]: sys.stdout.write(f"{row['queue_id']}\t{row['state']}\t{row['figure_id'] or ''}\t{len(row['binding_required'])}\n")
    return 0
if __name__=="__main__": raise SystemExit(main())
