#!/usr/bin/env python3
"""Validate a frozen GToTree execution packet before launch or postflight."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def validate(packet, root, postflight=False):
    root=Path(root).resolve()
    for key in ("run_id","gtotree","hmm","panel","working_directory","output_directory","max_concurrent_jobs"):
        if key not in packet: raise ValueError("PACKET_FIELD_MISSING: "+key)
    gt=packet["gtotree"]; hmm=packet["hmm"]
    if not re.search(r"(?:^|\D)1\.8\.19(?:\D|$)", str(gt.get("version",""))):
        raise ValueError("GTOTREE_VERSION: production packet requires 1.8.19")
    for label,item in (("GTOTREE",gt),("HMM",hmm)):
        path=Path(item.get("path","")).resolve()
        if not path.is_file() or digest(path)!=item.get("sha256"):
            raise ValueError(label+"_IDENTITY")
    work=Path(packet["working_directory"]).resolve(); out=Path(packet["output_directory"]).resolve()
    if work==root or out==root or work==out or root not in work.parents or root not in out.parents:
        raise ValueError("RUN_DIRECTORY_ISOLATION")
    jobs=int(packet["max_concurrent_jobs"])
    if jobs < 1 or jobs > 4: raise ValueError("CONCURRENCY_CAP")
    panel=packet["panel"]
    if not panel or len({r.get("tip") for r in panel}) != len(panel): raise ValueError("PANEL_IDENTITY")
    seen=set()
    for row in panel:
        p=Path(row.get("genome_path","")).resolve()
        if not p.is_file() or digest(p)!=row.get("sha256"): raise ValueError("GENOME_IDENTITY: "+str(row.get("tip")))
        if row.get("sha256") in seen: raise ValueError("DUPLICATE_GENOME_CONTENT")
        seen.add(row["sha256"])
    if postflight:
        receipt=packet.get("postflight",{})
        retained=set(receipt.get("retained_tips",[])); expected={r["tip"] for r in panel}
        if retained != expected: raise ValueError("SILENT_TIP_LOSS")
        if not receipt.get("alignment_path") or not Path(receipt["alignment_path"]).is_file():
            raise ValueError("ALIGNMENT_MISSING")
    return {"status":"GTOTREE_EXECUTION_GATE_PASS", "panel_size":len(panel),
            "postflight":bool(postflight), "ceiling":"Execution identity/QC only; no biological conclusion."}

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("packet");p.add_argument("--root",required=True);p.add_argument("--postflight",action="store_true")
    a=p.parse_args(argv);print(json.dumps(validate(json.loads(Path(a.packet).read_text()),a.root,a.postflight),indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
