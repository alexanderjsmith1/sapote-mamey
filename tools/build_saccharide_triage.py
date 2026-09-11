#!/usr/bin/env python3
"""build_saccharide_triage.py — separate genuine saccharide products from glycosylation noise.

antiSMASH's `saccharide` rule fires on glycosyltransferase / NDP-sugar machinery, which is overwhelmingly
(a) TAILORING that decorates other scaffolds (macrolides, aromatic PKS, glycopeptides) or (b) sugar-
metabolism machinery — not standalone saccharide natural products. Raw saccharide counts therefore top the
BGC list while being neither actionable nor reportable. This tool reclassifies every saccharide-tagged
region into three buckets and writes a Saccharide_Triage sheet, so the headline class list can exclude the
raw count (as it already excludes NAPAA) and report only the small candidate-product set.

Buckets:
  TAILORING            saccharide co-occurs with a backbone class in the same region -> glycosylation of
                       that scaffold; report under the backbone, not as a saccharide product.
  CANDIDATE_PRODUCT    standalone saccharide region whose KCB anchor names a known sugar/aminoglycoside
                       antibiotic (or a large, well-formed standalone cluster) -> the reportable set.
  MACHINERY            standalone saccharide with an uncharacterized/weak anchor or a tiny region -> sugar-
                       metabolism / trans-acting GT noise; excluded from the headline.

Usage: python tools/build_saccharide_triage.py --workbook <xlsx> --banked-dir <dir>
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, os

from _wbio import atomic_save


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

# Curated from MIBiG-derived actinomycete saccharide references (punch-card list).
# SUGAR_PRODUCTS: the sugar IS the product (aminoglycoside / cyclitol / oligosaccharide / nucleoside-sugar /
# orthosomycin / phosphoglycolipid). A standalone saccharide region anchoring here is a genuine candidate.
SUGAR_PRODUCTS=['streptomycin','kanamycin','gentamicin','neomycin','ribostamycin','validamycin','jinggangmycin',
    'acarbose','hygromycin','avilamycin','everninomicin','evernimicin','moenomycin','bambermycin','flavomycin',
    'tunicamycin','liposidomycin','caprazamycin','muraymycin','napsamycin','mureidomycin','spectinomycin',
    'apramycin','tobramycin','kasugamycin','aminoglycos','aminocyclitol','butirosin','sisomicin','fortimicin',
    'paromomycin','lividomycin','destomycin','sorbistin']
# GLYCOSYLATED_HYBRIDS: PKS/NRPS products whose deoxysugar subcluster antiSMASH may flag as a standalone
# saccharide region. Anchoring here means "likely the deoxysugar machinery of <hybrid>", not a sugar product.
GLYCOSYLATED_HYBRIDS=['erythromycin','tylosin','spiramycin','oleandomycin','spinosyn','spinosad','avermectin',
    'nystatin','amphotericin','pimaricin','natamycin','candicidin','vancomycin','teicoplanin','balhimycin',
    'chloroeremomycin','ristocetin','a40926','doxorubicin','daunorubicin','nogalamycin','mithramycin',
    'landomycin','medermycin','calicheamicin','rebeccamycin','staurosporine','urdamycin','aclacinomycin',
    'chromomycin','elloramycin','jadomycin','angucycline']
BACKBONE=['nrps','t1pks','t2pks','t3pks','transat','pks-like','hr-t2pks','terpene','lanthipeptide',
          'lassopeptide','ripp','thiopeptide','nrp-metallophore','arylpolyene','siderophore','betalactone',
          'butyrolactone','ectoine','melanin','indole','phosphonate','amglyccycl','2dos']

_REF=os.path.join(os.path.dirname(__file__),'..','data','saccharide_reference.json')
if os.path.exists(_REF):
    _r=_read_json(_REF)
    SUGAR_PRODUCTS=_r.get('sugar_products',SUGAR_PRODUCTS)
    GLYCOSYLATED_HYBRIDS=_r.get('glycosylated_hybrids',GLYCOSYLATED_HYBRIDS)

def tokens(b): return [t.strip().lower() for t in (b.get('products') or '').replace(';',',').split(',') if t.strip()]

def classify(b):
    tk=tokens(b)
    if not any('saccharide' in t for t in tk): return None
    others=[t for t in tk if 'saccharide' not in t]
    backbones=[t for t in others if any(bk in t for bk in BACKBONE)]
    if backbones:
        return ('TAILORING', 'glycosylation of '+'/'.join(sorted(set(backbones))))
    cp=(b.get('closest_kcb_product') or b.get('closest_mibig') or '').lower()
    length=b.get('length_kb',0) or 0
    if any(k in cp for k in SUGAR_PRODUCTS):
        return ('CANDIDATE_PRODUCT', f'KCB anchor: {cp[:40]}')
    if any(k in cp for k in GLYCOSYLATED_HYBRIDS):
        return ('DEOXYSUGAR_SUBCLUSTER', f'sugar machinery of {cp[:34]}')
    if length>=15:  # large, clean standalone with no named anchor — needs manual review, NOT auto-reportable
        return ('UNCHARACTERIZED_STANDALONE', f'{length:.0f} kb, anchor: {(cp[:30] or "none")}')
    return ('MACHINERY', f'{length:.0f} kb (small), anchor: {(cp[:24] or "none")}')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--workbook', required=True); ap.add_argument('--banked-dir', default='cohort')
    a=ap.parse_args()
    bgc=_read_json(os.path.join(a.banked_dir,'bgc_data.json')); bgcs=bgc['bgcs']
    rows=[]; counts={'CANDIDATE_PRODUCT':0,'DEOXYSUGAR_SUBCLUSTER':0,'UNCHARACTERIZED_STANDALONE':0,'TAILORING':0,'MACHINERY':0}
    for b in bgcs:
        c=classify(b)
        if not c: continue
        bucket,why=c; counts[bucket]+=1
        rows.append([b['sid'],b['bgc_id'],b.get('products','')[:48],round(b.get('length_kb',0) or 0,1),
                     b.get('closest_kcb_product','') or b.get('closest_mibig','') or '', bucket, why])
    order={'CANDIDATE_PRODUCT':0,'DEOXYSUGAR_SUBCLUSTER':1,'UNCHARACTERIZED_STANDALONE':2,'TAILORING':3,'MACHINERY':4}
    rows.sort(key=lambda r:(order[r[5]], r[0]))
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb=openpyxl.load_workbook(a.workbook)
    if 'Saccharide_Triage' in wb.sheetnames: del wb['Saccharide_Triage']
    ws=wb.create_sheet('Saccharide_Triage')
    hdr=['strain','BGC','products','length_kb','KCB_anchor','triage','rationale']
    ws.append(hdr)
    for c in range(1,len(hdr)+1):
        cell=ws.cell(1,c); cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='2E5E7E')
    FILL={'CANDIDATE_PRODUCT':PatternFill('solid',fgColor='E6F4EA'),
          'DEOXYSUGAR_SUBCLUSTER':PatternFill('solid',fgColor='E5F0FB'),
          'UNCHARACTERIZED_STANDALONE':PatternFill('solid',fgColor='FFFBEA'),
          'TAILORING':PatternFill('solid',fgColor='FFF4E5'),
          'MACHINERY':PatternFill('solid',fgColor='F2F2F2')}
    for r in rows:
        ws.append(r)
        for c in range(1,len(hdr)+1): ws.cell(ws.max_row,c).fill=FILL[r[5]]
    for col,w in zip('ABCDEFG',[10,7,48,11,34,18,40]): ws.column_dimensions[col].width=w
    ws.freeze_panes='A2'
    ws.append([])
    ws.append(['SUMMARY',f"{sum(counts.values())} tagged",f"CANDIDATE_PRODUCT {counts['CANDIDATE_PRODUCT']}",
               f"DEOXYSUGAR_SUBCLUSTER {counts['DEOXYSUGAR_SUBCLUSTER']}",f"UNCHAR_STANDALONE {counts['UNCHARACTERIZED_STANDALONE']}",
               f"TAILORING {counts['TAILORING']}  MACHINERY {counts['MACHINERY']}",'headline = CANDIDATE_PRODUCT'])
    atomic_save(wb, a.workbook)
    emit(f"  Saccharide_Triage: {sum(counts.values())} tagged -> {counts['CANDIDATE_PRODUCT']} candidate products, "
          f"{counts['DEOXYSUGAR_SUBCLUSTER']} deoxysugar-subclusters (of known glycosylated NPs), "
          f"{counts['UNCHARACTERIZED_STANDALONE']} uncharacterized-standalone, {counts['TAILORING']} tailoring, "
          f"{counts['MACHINERY']} machinery. Headline reportable = {counts['CANDIDATE_PRODUCT']}.")

if __name__=='__main__': main()
