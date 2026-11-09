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



def _bank_reader_scope(func):
    import sys as _bank_sys
    from pathlib import Path as _BankPath
    _bank_sys.path.insert(0, str(_BankPath(__file__).resolve().parent.parent))
    from mamey.bank_transaction import reader_scope
    return reader_scope(func)

def _bank_read_guard(bank):
    if bank is None:
        return
    import sys as _bank_sys
    from pathlib import Path as _BankPath
    _bank_sys.path.insert(0, str(_BankPath(__file__).resolve().parent.parent))
    from mamey.bank_transaction import hold_reader
    hold_reader(bank)

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
    """Rows from a cohort snapshot ({strain: record} or [record, ...]) or one package record.

    A package's own `<strain>_Project_Memory_Snapshot.json` is an alias stub that resolves to
    its flat `manifest.json` record; that is read as one strain. Any other shape is refused
    with a clear message instead of failing on a string.
    """
    snap=_read_json(path); rows=[]
    if isinstance(snap,dict) and ('assembly' in snap or 'bgc_counts' in snap) and \
            not all(isinstance(v,dict) for v in snap.values()):
        items=[(snap.get('strain_id') or snap.get('strain'), snap)]
    elif isinstance(snap,dict):
        items=snap.items()
    elif isinstance(snap,list):
        items=[(s.get('strain') or s.get('strain_id'),s) if isinstance(s,dict) else (None,s) for s in snap]
    else:
        raise SystemExit(f"ASSEMBLY_QC_SNAPSHOT_SHAPE: {path} is neither a cohort snapshot "
                         "(mapping of strain to record, or a list of records) nor one package record")
    for sid,d in items:
        if not isinstance(d,dict):
            raise SystemExit(f"ASSEMBLY_QC_SNAPSHOT_SHAPE: {path}: entry {sid!r} is not a strain record; "
                             "pass a cohort snapshot (mapping of strain to record) or one package manifest")
        a=d.get('assembly',{}); c=d.get('bgc_counts',{})
        rows.append({'strain':sid,'genome_bp':a.get('genome_bp'),'contigs':a.get('contigs'),'n50':a.get('n50'),
            'raw_bgcs':c.get('raw'),'interior_pct':c.get('interior_pct'),'genus':(d.get('taxonomy') or d.get('genus') or '')})
    return rows


class QcInputError(ValueError):
    """An input the gate cannot read without guessing (for example a repeated strain)."""


def refuse_repeated_strains(rows, source):
    """A strain listed twice is an error, never a silent second row or overwrite."""
    seen=Counter(r['strain'] for r in rows)
    repeated=sorted(str(k) for k,n in seen.items() if n>1)
    if repeated:
        raise QcInputError(f"{source} lists strain(s) more than once: {', '.join(repeated)}")


def roster_gaps(banked, rows):
    """Bank fallback: rows for strains.json members that have no BGC rows (QC not computed).

    derive_from_banks evaluates only strains with BGC rows. A roster member without any is kept
    visible as NOT_CHECKED, with blank measurements (never 0), so a missing row is never read as
    a pass. A strain listed twice in strains.json is refused.
    """
    roster=[s['sid'] for s in _read_json(os.path.join(banked,'strains.json'))]
    refuse_repeated_strains([{'strain':sid} for sid in roster], 'strains.json')
    have={r['strain'] for r in rows}
    return [{'strain':sid,'genome_bp':None,'contigs':None,'n50':None,'raw_bgcs':None,'interior_pct':None,
             'genus':'','qc_not_computed':'in strains.json but no BGC rows in bgc_data.json'}
            for sid in roster if sid not in have]


def _output_refusal(out, inputs, replace):
    """Return why --out may not be written, or None. Checked before any input is parsed."""
    from pathlib import Path as _P
    _sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    from mamey.output_transaction import preflight_output_roster
    target=_P(out); sources=[_P(p) for p in inputs]
    if target.exists() or target.is_symlink():
        for src in sources:
            if src.exists() and (target.resolve()==src.resolve() or target.samefile(src)):
                return f"REFUSED: --out {out} is the input {src}"
        if not replace:
            return f"REFUSED: --out {out} already exists; choose a new path or pass --replace"
        if target.is_symlink() or not target.is_file():
            return f"REFUSED: --replace only replaces a regular file: {out}"
        return None
    try:
        preflight_output_roster([target.parent.resolve()/target.name], protected_paths=sources)
    except ValueError as exc:
        return f"REFUSED: --out {out}: {exc}"
    return None


def evaluate(r, genus_max=None, literal=False):
    if r.get('qc_not_computed'):
        return 'NOT_CHECKED', [r['qc_not_computed'] + '; QC not computed, review the source']
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

@_bank_reader_scope
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--snapshot', default=None); ap.add_argument('--banked-dir', default='cohort')
    ap.add_argument('--out', default='assembly_qc.json'); ap.add_argument('--genus-table', default=None)
    ap.add_argument('--literal-or', action='store_true', help="apply the spec's exact OR-logic (any rule → FLAG)")
    ap.add_argument('--replace', action='store_true',
                    help="allow replacing an existing --out regular file; an input is never replaced")
    a=ap.parse_args(); _bank_read_guard(getattr(a, "banked_dir", None))
    # --out must be new (or --replace) and never an input; checked before any write.
    inputs=[a.snapshot] if a.snapshot else [os.path.join(a.banked_dir,'bgc_data.json'),
                                            os.path.join(a.banked_dir,'strains.json')]
    if a.genus_table: inputs.append(a.genus_table)
    refusal=_output_refusal(a.out, inputs, a.replace)
    if refusal: ap.error(refusal)
    rows = from_snapshot(a.snapshot) if a.snapshot else derive_from_banks(a.banked_dir)
    try:
        refuse_repeated_strains(rows, a.snapshot or 'bgc_data.json')
        if not a.snapshot: rows += roster_gaps(a.banked_dir, rows)
    except QcInputError as exc:
        ap.error(f"REFUSED: {exc}")
    genus_max=_read_json(a.genus_table) if a.genus_table else None
    out=[]
    for r in rows:
        st,reasons=evaluate(r, genus_max, a.literal_or)
        out.append({**r,'status':st,'reasons':reasons})
    out.sort(key=lambda x:{'FLAG':0,'NOT_CHECKED':1,'WARN':2,'PASS':3}[x['status']])
    flagged=[x['strain'] for x in out if x['status']=='FLAG']; warned=[x['strain'] for x in out if x['status']=='WARN']
    unchecked=[x['strain'] for x in out if x['status']=='NOT_CHECKED']
    # v9.7.371 fix: was json.dump(..., open(a.out,'w'), indent=2) -- non-atomic (an interrupted
    # write leaves a truncated/corrupted assembly_qc.json, the gate this file's own docstring says
    # runs BEFORE lead_board -- a downstream consumer reading a half-written receipt fails opaquely
    # rather than the gate itself reporting a clean error) and the bare open() leaks its handle,
    # the exact bug class this file's own _read_json() docstring already documents fixing once
    # ("P3b: context-managed JSON read; closes the handle a bare open() leaked."). Route through
    # the established atomic_write_text (tmp-sibling + os.replace) instead.
    atomic_write_text(a.out, json.dumps(
        {'gate':'assembly_qc','mode':'literal-or' if a.literal_or else 'size-anchored',
         'held_qc':flagged,'warn':warned,'not_checked':unchecked,'strains':out}, indent=2))
    emit(f"  wrote {a.out} — {len(flagged)} FLAG (HOLD-QC), {len(warned)} WARN, "
         f"{len(out)-len(flagged)-len(warned)-len(unchecked)} PASS"
         + (f", {len(unchecked)} NOT_CHECKED (no BGC rows): {', '.join(unchecked)}" if unchecked else ""))
    if flagged: emit(f"    HELD: {', '.join(flagged)}")
    if not any(r.get('genome_bp') for r in rows):
        emit("    [note] no genome_bp in inputs — co-assembly FLAG cannot fire; raw/contig trips are WARN-only "
              "(can't separate co-assembly from fragmentation without genome size). Provide a snapshot with assembly.genome_bp.")

if __name__=='__main__': main()
