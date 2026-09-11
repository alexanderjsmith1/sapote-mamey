#!/usr/bin/env python3
"""blastp_campaign.py — headless, resumable, checkpoint-first NCBI BLASTp campaign runner.

Fixes the two confirmed failures in the current `blastp-online` workflow (v9.7.207):
  1. NOT WORKING: `run_batches_online` holds RIDs in memory then polls in memory — a timeout mid-poll
     loses every RID (NCBI keeps results ~24h but the client discarded the handles), so a large run
     resubmits from zero each time and never completes. FIX: checkpoint RIDs to disk *before* polling;
     `harvest` is re-runnable and only touches not-yet-done RIDs.
  2. TOKEN SINK: raw BLAST XML is ~65k chars / 5 proteins → ~6M chars (~1.5M tokens) for a 492-protein
     run. If any of it transits the LLM context the run costs >1M tokens. FIX: the runner parses XML to a
     compact per-protein top-N hits CSV on disk (~50KB for 492 proteins); the LLM reads the CSV, never XML.

Usage (LLM invokes each once; ZERO LLM-in-the-loop polling):
  python blastp_campaign.py submit  --batches <dir_of_faa> --out <run_dir>   # submit-all, checkpoint RIDs
  python blastp_campaign.py harvest --out <run_dir>                          # resumable: poll+parse ready
  # re-run `harvest` until it reports done; each call is idempotent and appends only new results.

Discipline: BLASTp = similarity, not identity. Output is capacity-level homology evidence. Loci carry
strain|BGC|gene; provenance = store-backed (NCBI web-BLASTp result).
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, json, os, re, sys, time, urllib.parse, urllib.request
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_dump_json


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


NCBI = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"


def _post(fields, timeout=45):
    return urllib.request.urlopen(NCBI, data=urllib.parse.urlencode(fields).encode(), timeout=timeout).read().decode("utf-8", "replace")


def _parse_faa(path):
    prots, hdr, buf = [], None, []
    for line in open(path, encoding="utf-8"):
        if line.startswith(">"):
            if hdr:
                prots.append((hdr, "".join(buf)))
            parts = line[1:].strip().split("|")
            gene = next((p.split("=", 1)[1] for p in parts if p.startswith("gene=")), parts[-1])
            hdr = f"{parts[0]}|{parts[1]}|{gene}" if len(parts) > 1 else parts[0]
            buf = []
        else:
            buf.append(line.strip())
    if hdr:
        prots.append((hdr, "".join(buf)))
    return prots


def cmd_submit(a):
    os.makedirs(a.out, exist_ok=True)
    ck = os.path.join(a.out, "rids.json")
    done = {r["locus"] for r in _read_json(ck, encoding="utf-8")} if os.path.exists(ck) else set()
    recs = _read_json(ck, encoding="utf-8") if os.path.exists(ck) else []
    faas = sorted(glob.glob(os.path.join(a.batches, "**", "*.faa"), recursive=True) or glob.glob(os.path.join(a.batches, "*.faa")))
    n = 0
    for faa in faas:
        for locus, seq in _parse_faa(faa):
            if locus in done:
                continue
            try:
                put = _post({"CMD": "Put", "PROGRAM": "blastp", "DATABASE": a.database,
                             "QUERY": f">{locus}\n{seq}", "HITLIST_SIZE": str(a.hits)})
                m = re.search(r"RID = (\w+)", put)
                rec = {"locus": locus, "rid": m.group(1) if m else None, "status": "WAITING" if m else "SUBMIT_FAIL"}
            except Exception as exc:
                rec = {"locus": locus, "rid": None, "status": f"SUBMIT_ERR:{type(exc).__name__}"}
            recs.append(rec)
            # v9.7.371 fix: was a bare open(ck,'w') -- this tool's whole stated purpose is
            # surviving "a timeout mid-poll loses every RID" by checkpointing to disk before
            # polling; a process killed mid-write on this exact checkpoint left rids.json
            # truncated/corrupt, so the NEXT submit/harvest invocation raised on json.load and lost
            # the whole in-flight RID set -- precisely the failure this tool exists to prevent,
            # just moved one level down into its own recovery file.
            atomic_dump_json(recs, ck)  # CHECKPOINT AFTER EVERY SUBMIT — never lose a RID
            n += 1
            time.sleep(a.submit_gap)
    emit(f"submitted {n} new proteins; {len(recs)} total in {ck}")


def _top_hits(xml, top_n):
    out = []
    for hit in re.findall(r"<Hit>.*?</Hit>", xml, re.S)[:top_n]:
        d = (re.search(r"<Hit_def>([^<]+)</Hit_def>", hit) or [None, ""])[1] if re.search(r"<Hit_def>([^<]+)</Hit_def>", hit) else ""
        d = re.sub(r"&gt;.*", "", d).strip()
        idn = re.search(r"<Hsp_identity>(\d+)</Hsp_identity>", hit)
        aln = re.search(r"<Hsp_align-len>(\d+)</Hsp_align-len>", hit)
        bits = re.search(r"<Hsp_bit-score>([\d.]+)</Hsp_bit-score>", hit)
        ev = re.search(r"<Hsp_evalue>([\d.eE+-]+)</Hsp_evalue>", hit)
        sci = re.search(r"\[([^\]]+)\]", d)
        pid = round(100 * int(idn.group(1)) / int(aln.group(1)), 1) if (idn and aln) else None
        out.append({"subject_desc": d[:80], "sciname": sci.group(1) if sci else "",
                    "pct_identity": pid, "bitscore": bits.group(1) if bits else "", "evalue": ev.group(1) if ev else ""})
    return out


def cmd_harvest(a):
    ck = os.path.join(a.out, "rids.json")
    recs = _read_json(ck, encoding="utf-8")
    hits_csv = os.path.join(a.out, "blastp_hits.csv")
    seen = set()
    if os.path.exists(hits_csv):
        seen = {row["locus"] for row in csv.DictReader(open(hits_csv, encoding="utf-8"))}
    fh = open(hits_csv, "a", newline="", encoding="utf-8")
    w = _SafeDictWriter(fh, fieldnames=["locus", "hit_rank", "subject_desc", "sciname", "pct_identity", "bitscore", "evalue"])
    if not seen:
        w.writeheader()
    pending = [r for r in recs if r.get("rid") and r["locus"] not in seen and r.get("status") != "DONE"]
    waited = 0
    while pending and waited < a.max_wait:
        for r in list(pending):
            try:
                info = _post({"CMD": "Get", "RID": r["rid"], "FORMAT_OBJECT": "SearchInfo"})
                st = (re.search(r"Status=(\w+)", info) or [None, "?"])[1]
                if st == "READY":
                    xml = _post({"CMD": "Get", "RID": r["rid"], "FORMAT_TYPE": "XML",
                                 "ALIGNMENTS": str(a.hits), "DESCRIPTIONS": str(a.hits)})
                    for i, h in enumerate(_top_hits(xml, a.hits), 1):
                        w.writerow({"locus": r["locus"], "hit_rank": i, **h})
                    fh.flush(); r["status"] = "DONE"; seen.add(r["locus"]); pending.remove(r)
                    atomic_dump_json(recs, ck)  # checkpoint status
            except Exception:
                pass
            time.sleep(a.poll_gap)
        if pending:
            waited += a.first_delay if waited == 0 else a.poll_interval
            time.sleep(a.first_delay if waited == 0 else a.poll_interval)
    fh.close()
    remaining = [r for r in recs if r.get("rid") and r.get("status") != "DONE"]
    emit(f"harvested {len(seen)} proteins -> {hits_csv}; {len(remaining)} still pending "
          f"({'re-run harvest to continue' if remaining else 'COMPLETE'})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit"); s.add_argument("--batches", required=True); s.add_argument("--out", required=True)
    s.add_argument("--database", default="nr"); s.add_argument("--hits", type=int, default=6)
    s.add_argument("--submit-gap", type=float, default=3.0, dest="submit_gap"); s.set_defaults(func=cmd_submit)
    h = sub.add_parser("harvest"); h.add_argument("--out", required=True); h.add_argument("--hits", type=int, default=6)
    h.add_argument("--max-wait", type=int, default=240, dest="max_wait")
    h.add_argument("--first-delay", type=float, default=30.0, dest="first_delay")
    h.add_argument("--poll-interval", type=float, default=20.0, dest="poll_interval")
    h.add_argument("--poll-gap", type=float, default=1.0, dest="poll_gap"); h.set_defaults(func=cmd_harvest)
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
