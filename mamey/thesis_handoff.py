"""Build a compact, portable, hash-bound thesis handoff package."""
from __future__ import annotations
import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any
from .csv_safety import SafeDictWriter
from .deep_bgc_report import IDENTITY_KEYS
from .exact_identity import exact_locus_display, ExactLocusIdentityError

class ThesisHandoffError(ValueError):
    pass

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _safe(root: Path, locator: str) -> Path:
    rel = Path(locator)
    if not locator or rel.is_absolute() or ".." in rel.parts:
        raise ThesisHandoffError("artifact locator must be safe and relative")
    resolved=(root/rel).resolve(); root=root.resolve()
    if resolved != root and root not in resolved.parents:
        raise ThesisHandoffError("artifact locator escapes configured input root")
    if not resolved.is_file(): raise ThesisHandoffError(f"artifact not found: {locator}")
    return resolved

def build_thesis_handoff(index_tsv: Path, input_root: Path, output_dir: Path) -> dict[str, Any]:
    with index_tsv.open(newline="", encoding="utf-8-sig") as handle:
        rows=list(csv.DictReader(handle, delimiter="\t"))
    if not rows: raise ThesisHandoffError("handoff index is empty")
    admitted=[]; seen=set()
    for row in rows:
        ident={k:str(row.get(k," ")).strip() for k in IDENTITY_KEYS}
        try: display=exact_locus_display(*(ident[k] for k in IDENTITY_KEYS))
        except ExactLocusIdentityError as exc: raise ThesisHandoffError(str(exc)) from exc
        if display in seen: raise ThesisHandoffError(f"duplicate exact locus: {display}")
        seen.add(display)
        receipt_path=_safe(input_root,str(row.get("report_receipt","")))
        receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("identity") != ident: raise ThesisHandoffError("report receipt exact identity mismatch")
        report_path=_safe(input_root,str(row.get("report_markdown","")))
        map_path=_safe(input_root,str(row.get("locus_map","")))
        activity_locator=str(row.get("activity_tree","")).strip()
        activity_path=_safe(input_root,activity_locator) if activity_locator else None
        claim=str(row.get("claim_ceiling","")).strip()
        gaps=str(row.get("gaps","")).strip()
        if not claim or not gaps: raise ThesisHandoffError("claim_ceiling and gaps are mandatory")
        admitted.append((row,display,receipt_path,report_path,map_path,activity_path))
    output_dir.mkdir(parents=True, exist_ok=False)
    artifacts=output_dir/"artifacts"; artifacts.mkdir()
    index_lines=["# Thesis Handoff Index", "", "This package is a portable evidence handoff, not a release or biological acceptance record.", ""]
    gap_rows=[]
    copied=[]
    for number,(row,display,receipt,report,locus_map,activity) in enumerate(admitted,1):
        locus_dir=artifacts/f"locus_{number:03d}"; locus_dir.mkdir()
        selected=[receipt,report,locus_map]+([activity] if activity else [])
        for source in selected:
            target=locus_dir/source.name; shutil.copy2(source,target); copied.append(target)
        index_lines += [f"## {display}", "", f"Report: `artifacts/{locus_dir.name}/{report.name}`", "", f"Locus map: `artifacts/{locus_dir.name}/{locus_map.name}`", "", f"Claim ceiling: {row['claim_ceiling']}", ""]
        gap_rows.append({"exact_locus":display,"gaps":row["gaps"],"claim_ceiling":row["claim_ceiling"]})
    index_md=output_dir/"INDEX.md"; index_md.write_text("\n".join(index_lines),encoding="utf-8")
    gaps_tsv=output_dir/"GAPS_AND_CLAIM_CEILINGS.tsv"
    with gaps_tsv.open("w",newline="",encoding="utf-8") as handle:
        writer=SafeDictWriter(handle,delimiter="\t",fieldnames=list(gap_rows[0]));writer.writeheader();writer.writerows(gap_rows)
    copied += [index_md,gaps_tsv]
    checksum=output_dir/"SHA256SUMS.txt"
    checksum.write_text("".join(f"{_sha(p)}  {p.relative_to(output_dir).as_posix()}\n" for p in sorted(copied)),encoding="utf-8")
    archive=output_dir/"THESIS_HANDOFF.zip"
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(copied+[checksum]):
            info=zipfile.ZipInfo(path.relative_to(output_dir).as_posix(),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            zf.writestr(info,path.read_bytes())
    with zipfile.ZipFile(archive) as zf:
        bad=zf.testzip()
        if bad: raise ThesisHandoffError(f"ZIP CRC failure: {bad}")
    receipt={"schema":"sapote.thesis_handoff.receipt.v1","locus_count":len(admitted),"zip_crc":"PASS",
             "index_input":{"name":index_tsv.name,"sha256":_sha(index_tsv)},
             "archive":{"name":archive.name,"sha256":_sha(archive),"bytes":archive.stat().st_size}}
    receipt_path=output_dir/"HANDOFF_RECEIPT.json";receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return receipt
