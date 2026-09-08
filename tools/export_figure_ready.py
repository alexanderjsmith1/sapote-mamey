#!/usr/bin/env python3
"""export_figure_ready.py — emit tidy, figure-ready CSVs from a Sapote-Mamey master workbook.

Why: the master workbook is human-optimised (coded sheets, wide matrices, formulas, units in
headers). Downstream figure workflows (ggplot2, seaborn/matplotlib, Tableau) want TIDY data:
one observation per row, snake_case headers, no formulas, no merged cells, a data dictionary.
This tool converts the workbook into a portable `figure_ready/` folder anyone can plot from
without wrangling. Reads only B1_BGC_Master + A2_Strain_Registry (+ optional cross-strain /
TIGRFAM sheets); dependency-light (openpyxl + stdlib).

Usage:  python tools/export_figure_ready.py <master_workbook.xlsx> [out_dir]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, os, csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from collections import Counter, defaultdict
import openpyxl

def rows(ws):
    it=ws.iter_rows(values_only=True); hdr=list(next(it))
    for r in it:
        if any(c is not None for c in r): yield dict(zip(hdr,r))

def main(wb_path, out=None):
    out=out or os.path.join(os.path.dirname(wb_path) or '.', 'figure_ready')
    os.makedirs(out, exist_ok=True)
    wb=openpyxl.load_workbook(wb_path, read_only=True, data_only=True)
    def W(csvname, header, records):
        with open(os.path.join(out,csvname),'w',newline='',encoding='utf-8') as f:
            w=_SafeWriter(f); w.writerow(header)
            for rec in records: w.writerow(rec)
        return len(records)

    # ---- strain_summary ----
    # Read from the canonical v1.1 sheets: A2_Strain_Registry holds assembly/taxonomy fields,
    # A3_Run_Manifest holds raw_bgcs + corrected_bgcs (the only place the corrected count is stored).
    # (Pre-v1.1 this read Raw_BGCs/Corrected_BGCs/Genus/Host_Source/Assembly_Grade from A2 — those
    # columns never existed under the canonical schema, so every row silently emitted blanks. Fixed.)
    A2=list(rows(wb['A2_Strain_Registry']))
    # corrected-BGC count per strain from A3_Run_Manifest, keyed by strain
    corr_by_strain={}
    if 'A3_Run_Manifest' in wb.sheetnames:
        for r in rows(wb['A3_Run_Manifest']):
            s=r.get('strain')
            if s is not None:
                corr_by_strain[s]={'raw':r.get('raw_bgcs'), 'corrected':r.get('corrected_bgcs')}
    N=len(A2)
    def num(x):
        try: return float(x)
        except (TypeError, ValueError): return None
    def genus_of(tax):
        # genus = first whitespace-delimited token of the taxonomy string
        return (str(tax).split()[0] if tax else '') or ''
    ss=[]
    for r in A2:
        strain=r.get('strain')
        a3=corr_by_strain.get(strain, {})
        raw=num(a3.get('raw')); raw=raw if raw is not None else (num(r.get('bgc_count')) or 0)
        corr=num(a3.get('corrected')); corr=corr if corr is not None else 0
        ss.append([strain, r.get('taxonomy'), genus_of(r.get('taxonomy')), r.get('ecology_source'),
                   r.get('assembly_tier'), r.get('contigs'), r.get('n50'), r.get('assembly_bp'),
                   r.get('gc_pct'), r.get('interior_pct'), raw, corr, round((raw or 0)-(corr or 0),2)])
    # v9.7.374: named so DATA_DICTIONARY.md below can quote the REAL header instead of a
    # hand-typed copy -- a hand-typed copy is exactly how "sid"/"organism"/"host_source"/
    # "genome_bp" (none of which this function has ever written) ended up in the shipped
    # dictionary, undetected until now, right next to a comment about fixing this same class
    # of drift for one single column ("assembly_tier") at v9.7.371.
    ss_hdr = ['strain','taxonomy','genus','ecology_source','assembly_tier','contigs','n50','assembly_bp',
              'gc_pct','interior_pct','raw_bgcs','corrected_bgcs','fragmentation_loss']
    n1=W('strain_summary.csv', ss_hdr,
         sorted(ss, key=lambda r:-(r[11] or 0)))  # corrected-BGC rank order (convention)

    # ---- bgc_inventory + class explode ----
    # Canonical B1_BGC_Master headers are lowercase: products, contig, region, boundary, length_kb,
    # kcb_top, kcb_score (not Products/Edge_Status/KCB_Top_Hit/KCB_Cumulative). Pre-v1.1 names here
    # silently produced empty inventories — fixed to match CANONICAL_V1_HEADERS.
    B1=list(rows(wb['B1_BGC_Master']))
    inv=[]; clong=[]
    for r in B1:
        cls=[c.strip() for c in str(r.get('products') or '').split(';') if c.strip()]
        kcb_present=1 if (r.get('kcb_top') not in (None,'','NOT_APPLICABLE')) else 0
        inv.append([r.get('strain'), r.get('BGC_ID'), r.get('contig'), r.get('region'),
                    r.get('boundary'), r.get('length_kb'), len(cls), kcb_present,
                    r.get('kcb_score'), r.get('kcb_top'), r.get('safe_claim')])
        for c in cls:
            clong.append([r.get('strain'), r.get('BGC_ID'), r.get('contig'), r.get('region'), c])
    inv_hdr = ['strain','bgc_id','contig','region','boundary','length_kb','n_product_classes',
               'kcb_top_present','kcb_score','kcb_top','safe_claim']
    n2=W('bgc_inventory.csv', inv_hdr, inv)
    n3=W('bgc_class_long.csv', ['strain','bgc_id','contig','region','product_class'], clong)

    # ---- class_by_strain + class_prevalence ----
    by=Counter((r[0],r[4]) for r in clong); cls_strains=defaultdict(set); cls_bgc=Counter()
    for r in clong: cls_strains[r[4]].add(r[0]); cls_bgc[r[4]]+=1
    n4=W('class_by_strain.csv', ['strain','product_class','n_bgcs'],
         [[s,c,n] for (s,c),n in sorted(by.items())])
    UNIV={'saccharide','fatty_acid','other','terpene'}
    def band(n): return 'CORE' if n==N else 'COMMON' if n>=N*0.5 else 'UNIQUE' if n==1 else 'ACCESSORY'
    prev=[[c, len(cls_strains[c]), round(100*len(cls_strains[c])/N,1), cls_bgc[c], band(len(cls_strains[c])),
           'no' if c in UNIV else 'yes']
          for c in sorted(cls_strains, key=lambda x:(-len(cls_strains[x]),-cls_bgc[x]))]
    n5=W('class_prevalence.csv',
         ['product_class','n_strains','pct_strains','n_bgcs','band','informative_for_comparison'], prev)

    # ---- optional: diagnostics + findings passthrough ----
    n6=n7=0
    if 'TIGRFAM_Check' in wb.sheetnames:
        DN={'TIGR01454':'ansamycin','TIGR03604':'thiopeptide','TIGR03828':'enediyne','TIGR04186':'nucleoside'}
        dl=[]
        for r in rows(wb['TIGRFAM_Check']):
            sid=r.get('strain') or r.get('strain')
            for acc,nm in DN.items():
                v=r.get(acc)
                if v is not None:
                    nn=num(v) or 0; dl.append([sid,acc,nm,1 if nn>0 else 0,int(nn)])
        if dl: n6=W('diagnostics_long.csv',['strain','tigrfam_acc','diagnostic_name','present','n_hits'],dl)
    if 'Cross_Strain_Findings' in wb.sheetnames:
        fr=[[r.get('#'),r.get('finding'),r.get('metric'),r.get('value'),r.get('claim_status'),r.get('note')]
            for r in rows(wb['Cross_Strain_Findings']) if r.get('finding')]
        if fr: n7=W('cross_strain_findings.csv',['n','finding','metric','value','claim_status','note'],fr)

    # ---- data dictionary ----
    dd=f"""# Figure-Ready Export — Data Dictionary

Tidy long-format CSVs derived from `{os.path.basename(wb_path)}` ({N} strains).
All headers are snake_case; one observation per row; no formulas; UTF-8.
Class-level labels are antiSMASH product-class calls (hypotheses), never assayed chemistry.

## strain_summary.csv  ({n1} rows — one per strain)
Columns (exact CSV header): {', '.join(ss_hdr)}.
# v9.7.374: the column list above is now quoted directly from `ss_hdr` (the same list literal
# passed to W() a few lines up), not hand-retyped. A hand-typed copy is exactly how this section
# previously read "sid, organism, ..., host_source, ..., genome_bp, ..." -- none of which this
# function has ever written (real names: strain, taxonomy, ..., ecology_source, ..., assembly_bp)
# -- and was also silently missing interior_pct entirely. That drift sat undetected right next to
# a v9.7.371 comment about fixing this exact class of bug for one single column
# ("assembly_tier"/"assembly_grade") without a wider audit of the rest of this string.
strain (id), taxonomy, genus, ecology_source, assembly_tier (GOOD/MOD/POOR), contigs (int),
n50 (bp), assembly_bp (bp), gc_pct (%), interior_pct (%), raw_bgcs (int), corrected_bgcs
(Interior + 0.5*Edge + 0.25*FullContig), fragmentation_loss (raw - corrected).

## bgc_inventory.csv  ({n2} rows — one per BGC)
Columns (exact CSV header): {', '.join(inv_hdr)}.
strain (id), bgc_id, contig, region, boundary (Interior/Edge/Full-contig), length_kb,
n_product_classes (int), kcb_top_present (1/0; presence of a KnownClusterBlast top hit — a CLASS
anchor, NOT a known-compound call), kcb_score (cumulative SCORE, not a percent identity), kcb_top
(the KnownClusterBlast top-hit reference id), safe_claim (claim-safe display text for this BGC).

## bgc_class_long.csv  ({n3} rows — one per BGC x product_class)
strain, bgc_id, contig, region, product_class. The tidy table for class-based figures.

## class_by_strain.csv  ({n4} rows — one per strain x class)
strain, product_class, n_bgcs. Plot directly as a heatmap or stacked bar.

## class_prevalence.csv  ({n5} rows — one per class)
product_class, n_strains, pct_strains, n_bgcs, band (CORE/COMMON/ACCESSORY/UNIQUE),
informative_for_comparison (no = universal non-discriminating class; exclude from shared/novel claims).

## diagnostics_long.csv  ({n6} rows — one per strain x TIGRFAM diagnostic)
strain, tigrfam_acc, diagnostic_name, present (1/0), n_hits.

## cross_strain_findings.csv  ({n7} rows)
n, finding, metric, value, claim_status (GROUNDED/FLAG/METHOD CAVEAT/PRIORITY/UNEXERCISED), note.

## Caveats that travel with the data
- kcb_score is a cumulative SCORE, not a % identity — never plot/label it as "% known".
- The four universal classes (saccharide, fatty_acid, other, terpene) are non-discriminating
  (informative_for_comparison = no).
- Strain-unique classes are sample-limited and provisional.
"""
    open(os.path.join(out,'DATA_DICTIONARY.md'),'w',encoding='utf-8').write(dd)
    emit(f"figure-ready export -> {out}")
    for f in ['strain_summary.csv','bgc_inventory.csv','bgc_class_long.csv','class_by_strain.csv',
              'class_prevalence.csv','diagnostics_long.csv','cross_strain_findings.csv','DATA_DICTIONARY.md']:
        p=os.path.join(out,f); emit(f"  {'OK ' if os.path.exists(p) else 'skip'} {f}")

if __name__=='__main__':
    if len(sys.argv)<2: emit(__doc__); sys.exit(1)
    main(sys.argv[1], sys.argv[2] if len(sys.argv)>2 else None)
