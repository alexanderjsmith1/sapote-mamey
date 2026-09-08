#!/usr/bin/env python3
"""assembly_qc_check.py — deterministic assembly-QC gate (Mamey, runs before lead_board).

Flags mixed-culture / co-assembly strains (oversized genomes, inflated BGC counts, shattered assemblies) and
holds their leads so they never pollute the Lead_Board. Reads banked snapshot data only.

IMPORTANT REFINEMENT vs the bare spec (see SPEC: gate logic). The co-assembly signature is an OVERSIZED GENOME.
A *fragmented single genome* (POOR assembly) inflates raw BGC count and contig count exactly the way a
co-assembly does, so `raw_bgcs > 60` or `contigs > 3000` ALONE cannot tell the two apart — in the SID reference
cohort, SID-XXX (179 raw / POOR) and SID-XXX (134 raw) would false-FLAG on raw count yet are single genomes.
Therefore, by default:
  • genome_bp over the ceiling (or > 1.5x genus max) → HARD FLAG (the real co-assembly tell).
  • raw_bgcs / contig-shatter WITHOUT an oversized genome → WARN ("inflated count — likely fragmentation;
    verify purity"), NOT a hard FLAG.
  • genome_bp UNKNOWN + raw/contig trip → WARN + note "needs genome size to confirm co-assembly vs fragmentation".
Pass --literal-or to apply the spec's exact OR-logic (any rule → FLAG) once you've tuned thresholds to a cohort
where genome_bp isolates the offenders (the author's AS cohort: AS-XXX/AS-XXX/AS-XXX).

Usage:
  python tools/assembly_qc_check.py --snapshot Project_Memory_Snapshot.json --out assembly_qc.json
  python tools/assembly_qc_check.py --banked-dir cohort --out assembly_qc.json   # derive raw/contigs (no genome_bp)
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, sys, json
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        _d = _json.load(_fh)
    # v9.7.400: a Project_Memory_Snapshot may be an alias STUB pointing at manifest.json
    # (the pre-.400 snapshot duplicated the whole manifest; see mamey/snapshot_alias.py).
    if (isinstance(_d, dict) and _d.get("alias_of") and "source_scans" not in _d
            and "Project_Memory_Snapshot" in os.path.basename(str(_path))):
        _mp = os.path.join(os.path.dirname(str(_path)) or ".", str(_d["alias_of"]))
        if os.path.isfile(_mp):
            with open(_mp, encoding=encoding) as _fh:
                return _json.load(_fh)
    return _d


GENOME_CEILING=14_000_000; GENOME_WARN=12_000_000; RAW_FLAG=60; RAW_WARN=45; CONTIG_SHATTER=3000; INTERIOR_MIN=10

def derive_from_banks(banked):
    bgc=_read_json(os.path.join(banked,'bgc_data.json'))
    raw=Counter(); contigs=defaultdict(set); edge=defaultdict(Counter); org={}
    for s in _read_json(os.path.join(banked,'strains.json')): org[s['sid']]=s.get('organism','')
    for b in bgc['bgcs']:
        sid=b['sid']; raw[sid]+=1; contigs[sid].add(b.get('contig')); edge[sid][b.get('edge_status')]+=1
    rows=[]
    for sid in raw:
        n=raw[sid]; ipct=round(100*edge[sid]['Interior']/n) if n else 0
        rows.append({'strain':sid,'genome_bp':None,'contigs':len(contigs[sid]),'n50':None,
                     'raw_bgcs':n,'interior_pct':ipct,'genus':(org.get(sid,'') or ' ').split()[0]})
    return rows

def from_snapshot(path):
    snap=_read_json(path); rows=[]
    items=snap.items() if isinstance(snap,dict) else [(s.get('strain'),s) for s in snap]
    for sid,d in items:
        a=d.get('assembly',{}); c=d.get('bgc_counts',{})
        rows.append({'strain':sid,'genome_bp':a.get('genome_bp'),'contigs':a.get('contigs'),'n50':a.get('n50'),
            'raw_bgcs':c.get('raw'),'interior_pct':c.get('interior_pct'),'genus':(d.get('taxonomy') or d.get('genus') or '')})
    return rows

def evaluate(r, genus_max=None, literal=False):
    reasons=[]; gbp=r.get('genome_bp'); raw=r.get('raw_bgcs') or 0; ctg=r.get('contigs') or 0; ipct=r.get('interior_pct')
    oversized = (gbp is not None and gbp>GENOME_CEILING)
    if oversized: reasons.append(f"genome {gbp/1e6:.1f} Mb > {GENOME_CEILING/1e6:.0f} Mb ceiling (co-assembly tell)")
    if genus_max and gbp and gbp>1.5*genus_max.get(r.get('genus'),1e12):
        oversized=True; reasons.append(f"genome > 1.5x {r.get('genus')} typical max")
    raw_trip = raw>RAW_FLAG; shatter = (ctg>CONTIG_SHATTER and ipct is not None and ipct<INTERIOR_MIN)
    if literal:
        if oversized or raw_trip or shatter:
            if raw_trip and 'genome' not in ' '.join(reasons): reasons.append(f"raw_bgcs {raw} > {RAW_FLAG}")
            if shatter: reasons.append(f"contigs {ctg} > {CONTIG_SHATTER} & interior {ipct}% < {INTERIOR_MIN}%")
            return 'FLAG', reasons
    else:
        if oversized:
            if raw_trip: reasons.append(f"+ inflated raw_bgcs {raw}")
            return 'FLAG', reasons
        # raw/contig trips WITHOUT oversize → WARN (fragmentation-ambiguous), not hard FLAG
        warn=[]
        if raw_trip: warn.append(f"raw_bgcs {raw} > {RAW_FLAG} but genome size {'unknown' if gbp is None else 'normal'} — likely fragmentation; verify purity")
        if shatter: warn.append(f"shattered ({ctg} contigs, interior {ipct}%) — nothing callable; verify purity")
        if warn: return 'WARN', warn
    # soft WARN thresholds
    if (gbp and gbp>GENOME_WARN) or raw>RAW_WARN:
        return 'WARN', [f"oversized assembly — verify purity (genome {f'{gbp/1e6:.1f} Mb' if gbp else 'n/a'}, raw {raw})"]
    return 'PASS', []

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--snapshot', default=None); ap.add_argument('--banked-dir', default='cohort')
    ap.add_argument('--out', default='assembly_qc.json'); ap.add_argument('--genus-table', default=None)
    ap.add_argument('--literal-or', action='store_true', help="apply the spec's exact OR-logic (any rule → FLAG)")
    a=ap.parse_args()
    rows = from_snapshot(a.snapshot) if a.snapshot else derive_from_banks(a.banked_dir)
    genus_max=_read_json(a.genus_table) if a.genus_table else None
    out=[]
    for r in rows:
        st,reasons=evaluate(r, genus_max, a.literal_or)
        out.append({**r,'status':st,'reasons':reasons})
    out.sort(key=lambda x:{'FLAG':0,'WARN':1,'PASS':2}[x['status']])
    flagged=[x['strain'] for x in out if x['status']=='FLAG']; warned=[x['strain'] for x in out if x['status']=='WARN']
    # v9.7.371 fix: was json.dump(..., open(a.out,'w'), indent=2) -- non-atomic (an interrupted
    # write leaves a truncated/corrupted assembly_qc.json, the gate this file's own docstring says
    # runs BEFORE lead_board -- a downstream consumer reading a half-written receipt fails opaquely
    # rather than the gate itself reporting a clean error) and the bare open() leaks its handle,
    # the exact bug class this file's own _read_json() docstring already documents fixing once
    # ("P3b: context-managed JSON read; closes the handle a bare open() leaked."). Route through
    # the established atomic_write_text (tmp-sibling + os.replace) instead.
    atomic_write_text(a.out, json.dumps(
        {'gate':'assembly_qc','mode':'literal-or' if a.literal_or else 'size-anchored',
         'held_qc':flagged,'warn':warned,'strains':out}, indent=2))
    emit(f"  wrote {a.out} — {len(flagged)} FLAG (HOLD-QC), {len(warned)} WARN, {len(out)-len(flagged)-len(warned)} PASS")
    if flagged: emit(f"    HELD: {', '.join(flagged)}")
    if not any(r.get('genome_bp') for r in rows):
        emit("    [note] no genome_bp in inputs — co-assembly FLAG cannot fire; raw/contig trips are WARN-only "
              "(can't separate co-assembly from fragmentation without genome size). Provide a snapshot with assembly.genome_bp.")

if __name__=='__main__': main()
