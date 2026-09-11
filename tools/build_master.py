"""
DEPRECATED — frozen cohort one-off. NOT the canonical master-workbook builder.

This script builds a master workbook from five banked per-strain JSON files using a hardcoded
cohort layout and the legacy *descriptive*, TitleCase sheet/column scheme (Gene_*, BGC_Scan_Profile,
TFBS_Motifs, Strain_Catalog, …). It predates the frozen v1.1 coded contract.

The canonical, general-purpose builder is **mamey/master_workbook.py** (coded A1–H3 scheme, snake_case
headers, stamped H3 = v1.1). It is what the documented `mamey_run.py run --master …` flow uses and what
`mamey/workbook_schema_check.py` validates against (the validator now derives its column contract directly
from master_workbook.CANONICAL_V1_HEADERS, so the two cannot drift).

Keep this script only for reproducing the original banked-cohort workbook. Do not point new work at it,
and do not use its output with the schema validator — it will (correctly) fail the coded-scheme check.
See docs/MASTER_SCHEMA_FROZEN_v1_1.md.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse as _ap_, os as _os_, sys as _sys_
from _wbio import atomic_save


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# PC-7 (v9.7.253 audit): the docstring warns a reader; nothing warned a runner. Emit a loud
# stderr banner so anyone who runs this despite the generic name is told it is not canonical.
emit(
    "\n[DEPRECATED] tools/build_master.py is a frozen cohort one-off, NOT the canonical builder.\n"
    "            Use `mamey_run.py run --master ...` (mamey/master_workbook.py) for new work;\n"
    "            its output will (correctly) fail the coded-scheme validator.\n"
    "            See docs/MASTER_SCHEMA_FROZEN_v1_1.md.\n",
    file=_sys_.stderr,
)
_p=_ap_.ArgumentParser()
_p.add_argument("--banked-dir", default=_os_.environ.get("MAMEY_BANKED_DIR", _os_.path.join(_os_.path.dirname(__file__), "..", "cohort")))
_p.add_argument("--out", default=_os_.path.join(_os_.getcwd(), "Sapote-Mamey_Master_Workbook.xlsx"))
_a=_p.parse_args(); _OUT=_os_.path.abspath(_a.out); _os_.chdir(_os_.path.abspath(_a.banked_dir))
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# AUDIT_374: deep_data.json and strains.json are NOT written by
# tools/ingest_package.py --merge (deep_data.json is a separate tool's, build_deep_data.py's,
# output; strains.json is now always created by ingest_package.py but a bank built by an older
# ingest_package.py, or built by hand, may still lack it). This script previously required both
# unconditionally, so the exact recovery flow documented in mamey/cli.py ("bank this strain into
# the cohort instead, then rebuild": ingest_package.py --merge, then this script) crashed with a
# raw FileNotFoundError on a bank that only has the core ingest_package.py stores. ingest_package.py's
# own module docstring already documents the intent that detail-level sheets are "left for
# build_master to treat as not yet computed" when absent — this makes that contract real instead
# of crashing. Sheets fed only by deep_data.json / strains.json are simply empty in that case.
def _read_json_or(path, default):
    return _read_json(path) if _os_.path.exists(path) else default

bgc=_read_json('bgc_data.json'); gene=_read_json('gene_data.json')
# gene_data.json IS always written by ingest_package.py --merge, but only its "scan_agg" and
# "tfbs" keys — "domain_arch"/"substrates"/"ripp" are detail-level lists ingest_package.py only
# lifts when present in the source snapshot (same "not yet computed" contract as deep_data.json
# above). Default the missing keys so a freshly-merged bank doesn't KeyError here too.
for _k in ('domain_arch', 'substrates', 'ripp'):
    gene.setdefault(_k, [])
deep=_read_json_or('deep_data.json', {'bgc_profile': [], 'domain_arch': [], 'class_pred': [],
                                       'substrates': [], 'active_sites': [], 'ripp': [], 'domain_hits': []})
rgf=_read_json('rggmci_full.json')
tig=_read_json('tigrfam.json'); catalog=_read_json_or('strains.json', [])
strains=bgc['strains']; bgcs=bgc['bgcs']
SIDS=list(strains.keys())
ORG={s:strains[s]['organism'] for s in SIDS}
classes=sorted({p for b in bgcs for p in b['products'].split(';') if p})
cat_by={c['sid']:c for c in catalog}

FONT='Arial'; DARK='1F3A4D'; MID='2E5E7E'; PASS='C6EFCE'; SCAF='FFF2CC'; RESC='FCE4D6'
hf=Font(name=FONT,bold=True,color='FFFFFF',size=11); hfill=PatternFill('solid',fgColor=MID)
tf=Font(name=FONT,bold=True,color='FFFFFF',size=15); tfill=PatternFill('solid',fgColor=DARK)
base=Font(name=FONT,size=10); blue=Font(name=FONT,size=10,color='0000FF'); black=Font(name=FONT,size=10,color='000000')
green=Font(name=FONT,size=10,color='008000'); boldb=Font(name=FONT,size=10,bold=True); ital=Font(name=FONT,size=9,italic=True,color='666666')
thin=Side(style='thin',color='C8C8C8'); bd=Border(thin,thin,thin,thin)
ctr=Alignment(horizontal='center',vertical='center'); lft=Alignment(horizontal='left',vertical='center',wrap_text=True)
wb=Workbook()
def H(ws,cols,row=1):
    for i,_ in enumerate(cols,1):
        c=ws.cell(row=row,column=i); c.font=hf; c.fill=hfill; c.alignment=ctr; c.border=bd
def NS(name,cols):
    ws=wb.create_sheet(name); ws.append(cols); H(ws,cols); return ws
def W(ws,m):
    for k,v in m.items(): ws.column_dimensions[k].width=v
def fillrows(ws,n,nc,f=base):
    for i in range(2,2+n):
        for cc in range(1,nc+1): ws.cell(row=i,column=cc).border=bd; ws.cell(row=i,column=cc).font=f
def jn(x): return '; '.join(map(str,x)) if isinstance(x,(list,tuple)) else (str(x) if x is not None else '')

# About
ws=wb.active; ws.title='About'
ws.merge_cells('A1:E1'); ws['A1']='Sapote-Mamey — Master Strain Workbook (pre-release test)'
ws['A1'].font=tf; ws['A1'].fill=tfill; ws['A1'].alignment=ctr; ws.row_dimensions[1].height=26
for r,(k,v) in enumerate([
 ('',''),('Schema','Master Strain Workbook, canonical v1.1 (frozen). Codes A1/A2/A4, B1-B4, C1/C2, D1/D2.'),
 ('Bundle','sapote-mamey-v9.4.1 (2026-06-10)'),
 ('Strains loaded',f'{len(SIDS)} real deterministic runs: '+', '.join(SIDS)+'. Catalog holds all 82.'),
 ('Data status','A2/B1-B4, BGC_*, Gene_*, D1/D2, TIGRFAM = real extracted values. C1/C2 DAPR = scaffold (Sapote judgment layer).'),
 ('Colour key','Blue = measured value · Black = formula · Green = cross-sheet link'),
 ('RG-GMCI','Reference-Guided Genome Mining Candidate Inference: per-strain front-end homology linkage of fragmented BGCs to a shared reference cluster. D1=summary, D2=top HIGH pairs.'),
],start=2):
    ws.cell(row=r,column=1,value=k).font=boldb if k else base
    c=ws.cell(row=r,column=2,value=v); c.font=base; c.alignment=lft
    ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=5)
W(ws,{'A':16,'B':24,'C':22,'D':22,'E':22})

# A1_Dashboard
ws=wb.create_sheet('A1_Dashboard'); ws.merge_cells('A1:B1'); ws['A1']='A1 · Dashboard'; ws['A1'].font=tf; ws['A1'].fill=tfill; ws['A1'].alignment=ctr
dash=[('type_marker','MASTER_STRAIN_WORKBOOK'),('schema_version','v1.1 (frozen)'),('generated','2026-06-10'),('batch','B1-2026-06-10'),
 ('strains_loaded','=COUNTIF(A2_Strain_Registry!$A$2:$A$1000,"SID*")'),
 ('total_BGCs_raw','=SUM(A2_Strain_Registry!$M$2:$M$1000)'),('total_BGCs_corrected','=SUM(A2_Strain_Registry!$N$2:$N$1000)'),
 ('BGC_rows_in_master','=COUNTA(B1_BGC_Master!$C$2:$C$5000)'),
 ('TIGRFAM_parity_PASS','=COUNTIF(TIGRFAM_Check!$K$2:$K$1000,"PASS")'),('TIGRFAM_parity_FAIL','=COUNTIF(TIGRFAM_Check!$K$2:$K$1000,"FAIL")'),
 ('RGGMCI_HIGH_pairs_total','=SUM(D1_RGGMCI_All_Strains!$F$2:$F$1000)'),
 ('catalog_size','=COUNTA(Strain_Catalog!$A$2:$A$1000)'),('coverage_pct','=IF(B13=0,0,B6/B13)')]
for i,(k,v) in enumerate(dash,2):
    ws.cell(row=i,column=1,value=k).font=boldb; ws.cell(row=i,column=1).border=bd
    c=ws.cell(row=i,column=2,value=v); c.font=green if str(v).startswith('=') else blue; c.alignment=ctr; c.border=bd
ws['B14'].number_format='0.0%'; W(ws,{'A':24,'B':30})

# A2_Strain_Registry
cols=['strain','taxonomy','Genus','Host_Source','WW_Accession','GCA_Accession','BioSample','Contigs','N50','Genome_bp','GC_pct','Largest_Contig','Raw_BGCs','Corrected_BGCs','Assembly_Grade','Lead_Tier','Status','Batch']
ws=NS('A2_Strain_Registry',cols)
for sid in SIDS:
    s=strains[sid]; c=cat_by.get(sid,{})
    ws.append([sid,s['organism'],s['organism'].split()[0],'—',s['ww'],c.get('gca',''),c.get('samn',''),
        s['contigs'],s['n50'],s['genome_bp'],s['gc_pct'],s['largest_contig'],s['raw_bgcs'],s['corrected_bgcs'],None,'','MAMEY_EXTRACTED','B1-2026-06-10'])
fillrows(ws,len(SIDS),18)
for i in range(2,2+len(SIDS)):
    for cc in (8,9,10,11,12,13,14): ws.cell(row=i,column=cc).font=blue; ws.cell(row=i,column=cc).alignment=ctr
    for cc in (9,10,12): ws.cell(row=i,column=cc).number_format='#,##0'
    ws.cell(row=i,column=15,value=f'=IF(I{i}>=1000000,"GOOD",IF(I{i}>=100000,"MODERATE","POOR"))').font=black; ws.cell(row=i,column=15).alignment=ctr
ws.freeze_panes='B2'; ws.auto_filter.ref=f'A1:R{1+len(SIDS)}'
W(ws,{'A':9,'B':26,'C':14,'D':12,'E':15,'F':16,'G':15,'H':9,'I':11,'J':12,'K':8,'L':12,'M':10,'N':14,'O':14,'P':10,'Q':16,'R':14})

# B1_BGC_Master
cols=['strain','taxonomy','BGC_ID','Region','Contig','Products','Edge_Status','Length_kb','KCB_Top_Hit','KCB_Cumulative','Closest_KCB_Product','Closest_MIBiG','KCB_Provenance','Source_KCB_File','RiQ']
ws=NS('B1_BGC_Master',cols)
for b in bgcs:
    ws.append([b['sid'],b['organism'],b['bgc_id'],b['region'],b['contig'],b['products'],b['edge_status'],b['length_kb'],
        b['kcb_top'],b['kcb_cumulative'],b['closest_kcb_product'],b['closest_mibig'],b['kcb_provenance'],b['source_kcb_file'],b['riq']])
fillrows(ws,len(bgcs),15)
for i in range(2,2+len(bgcs)): ws.cell(row=i,column=10).number_format='#,##0'
ws.freeze_panes='C2'; ws.auto_filter.ref=f'A1:O{1+len(bgcs)}'
W(ws,{'A':9,'B':22,'C':12,'D':7,'E':16,'F':22,'G':12,'H':9,'I':40,'J':13,'K':22,'L':14,'M':16,'N':16,'O':8})
NB=len(bgcs)

# B2_Product_Class_Matrix
cols=['strain','taxonomy']+classes+['Total_BGCs','Distinct_Classes']
ws=NS('B2_Product_Class_Matrix',cols); first=3; last=first+len(classes)-1
for ri,sid in enumerate(SIDS,2):
    ws.cell(row=ri,column=1,value=sid).font=base; ws.cell(row=ri,column=2,value=ORG[sid]).font=base
    for j,cls in enumerate(classes):
        ws.cell(row=ri,column=first+j,value=f'=SUMPRODUCT((B1_BGC_Master!$A$2:$A$1200=$A{ri})*ISNUMBER(SEARCH(";{cls};",";"&B1_BGC_Master!$F$2:$F$1200&";")))').font=black
        ws.cell(row=ri,column=first+j).alignment=ctr
    ws.cell(row=ri,column=last+1,value=f'=COUNTIF(B1_BGC_Master!$A:$A,$A{ri})').font=green
    ws.cell(row=ri,column=last+2,value=f'=COUNTIF({get_column_letter(first)}{ri}:{get_column_letter(last)}{ri},">0")').font=black
    for cc in range(1,last+3): ws.cell(row=ri,column=cc).border=bd
    ws.cell(row=ri,column=last+1).alignment=ctr; ws.cell(row=ri,column=last+2).alignment=ctr
ws.freeze_panes='C2'; W(ws,{'A':9,'B':24})
for j in range(len(classes)): ws.column_dimensions[get_column_letter(first+j)].width=max(6,min(15,len(classes[j])+2))
ws.column_dimensions[get_column_letter(last+1)].width=11; ws.column_dimensions[get_column_letter(last+2)].width=15
DISTINCT_COL=get_column_letter(last+2)

# B3_Known_Cluster_Matrix
cols=['strain','taxonomy','BGCs_total','BGCs_with_KCB_hit','BGCs_no_KCB','Pct_with_KCB','Strongest_KCB_score']
ws=NS('B3_Known_Cluster_Matrix',cols)
for ri,sid in enumerate(SIDS,2):
    ws.cell(row=ri,column=1,value=sid).font=base; ws.cell(row=ri,column=2,value=ORG[sid]).font=base
    ws.cell(row=ri,column=3,value=f'=COUNTIF(B1_BGC_Master!$A:$A,$A{ri})').font=green
    ws.cell(row=ri,column=4,value=f'=COUNTIFS(B1_BGC_Master!$A:$A,$A{ri},B1_BGC_Master!$I:$I,"?*")').font=green
    ws.cell(row=ri,column=5,value=f'=C{ri}-D{ri}').font=black
    ws.cell(row=ri,column=6,value=f'=IF(C{ri}=0,0,D{ri}/C{ri})').font=black
    ws.cell(row=ri,column=7,value=f'=SUMPRODUCT(MAX((B1_BGC_Master!$A$2:$A$1200=$A{ri})*B1_BGC_Master!$J$2:$J$1200))').font=green
    for cc in range(1,8): ws.cell(row=ri,column=cc).border=bd
    for cc in (3,4,5,7): ws.cell(row=ri,column=cc).alignment=ctr
    ws.cell(row=ri,column=6).number_format='0.0%'; ws.cell(row=ri,column=6).alignment=ctr; ws.cell(row=ri,column=7).number_format='#,##0'
ws.freeze_panes='C2'; W(ws,{'A':9,'B':24,'C':11,'D':17,'E':12,'F':12,'G':18})

# B4_Cross_Strain_Scans (no RGGMCI)
cols=['strain','CCTT_triggers','CGAD_chitinase','bldA_TTA_BGCs','resistance_T1','resistance_T2','FLBR_grade','FLBR_megasynth','UMED','EFLS_pairs','TFBS_total','QS_signals','NAPAA']
ws=NS('B4_Cross_Strain_Scans',cols)
for sid in SIDS:
    a=gene['scan_agg'][sid]
    ws.append([sid,a['CCTT_triggers'],a['CGAD_chitinase'],a['bldA_TTA_BGCs'],a['resistance_T1'],a['resistance_T2'],a['FLBR_grade'],a['FLBR_megasynth'],a['UMED'],a['EFLS_pairs'],a['TFBS_total'],a['QS_signals'],a['NAPAA']])
fillrows(ws,len(SIDS),13)
for i in range(2,2+len(SIDS)):
    for cc in range(2,14):
        if cc!=7: ws.cell(row=i,column=cc).font=blue; ws.cell(row=i,column=cc).alignment=ctr
ws.freeze_panes='B2'; W(ws,{'A':9,'B':13,'C':14,'D':13,'E':12,'F':12,'G':11,'H':13,'I':8,'J':11,'K':11,'L':11,'M':8})

# BGC_Scan_Profile
DOM=['NRPS_A','NRPS_C','NRPS_T_PCP','PKS_KS','PKS_AT','PKS_KR','PKS_DH','PKS_ER','TE_release','Transporter','Regulator','Oxidoreductase']
cols=['strain','BGC_ID','TTA_codons','TTA_cds','Resistance_Tier','UMED_Verdict','CCTT_Triggers','Total_Domains']+DOM
ws=NS('BGC_Scan_Profile',cols)
for r in deep['bgc_profile']:
    ws.append([r['sid'],r['bgc_id'],r['tta_codons'],r['tta_cds'],r['resistance_tier'],r['umed_verdict'],r['cctt_triggers'],r['total_domains']]+[r.get(d,0) for d in DOM])
fillrows(ws,len(deep['bgc_profile']),len(cols)); ws.freeze_panes='C2'; ws.auto_filter.ref=f"A1:{get_column_letter(len(cols))}{1+len(deep['bgc_profile'])}"
W(ws,{'A':9,'B':10,'C':11,'D':9,'E':24,'F':22,'G':28,'H':13})
for j in range(len(DOM)): ws.column_dimensions[get_column_letter(9+j)].width=11

# BGC_Domain_Architecture
ws=NS('BGC_Domain_Architecture',['strain','BGC_ID','Domain_Architecture'])
for r in gene['domain_arch']: ws.append([r['sid'],r['bgc_id'],r['architecture']])
fillrows(ws,len(gene['domain_arch']),3); ws.freeze_panes='A2'; ws.auto_filter.ref=f"A1:C{1+len(gene['domain_arch'])}"
W(ws,{'A':9,'B':14,'C':90})

# BGC_Class_Predictions
ws=NS('BGC_Class_Predictions',['strain','Contig','Module','Protocluster','Predicted_Products','Source'])
for r in deep['class_pred']: ws.append([r['sid'],r['contig'],r['module'],r['protocluster'],r['predicted_products'],r.get('provenance','bounded-json')])
fillrows(ws,len(deep['class_pred']),6); ws.freeze_panes='A2'; W(ws,{'A':9,'B':16,'C':16,'D':12,'E':40,'F':13})

# Gene_NRPS_PKS_Substrates
ws=NS('Gene_NRPS_PKS_Substrates',['strain','taxonomy','Contig','Locus_Tag','Domain_ID','Prediction_Field','Consensus_Substrate','Source'])
for r in gene['substrates']: ws.append([r['sid'],ORG[r['sid']],r['contig'],r['locus'],r['domain_id'],r['field'],r['substrate'],r.get('provenance','bounded-json')])
fillrows(ws,len(gene['substrates']),8); ws.freeze_panes='A2'; ws.auto_filter.ref=f"A1:H{1+len(gene['substrates'])}"
W(ws,{'A':9,'B':22,'C':16,'D':14,'E':40,'F':14,'G':18,'H':13})

# Gene_Active_Sites
ws=NS('Gene_Active_Sites',['strain','Contig','Locus_Tag','Domain_ID','Active_Site_Calls','Source'])
for r in deep['active_sites']: ws.append([r['sid'],r['contig'],r['locus'],r['domain_id'],r['active_site_calls'],r.get('provenance','bounded-json')])
fillrows(ws,len(deep['active_sites']),6); ws.freeze_panes='A2'; ws.auto_filter.ref=f"A1:F{1+len(deep['active_sites'])}"
W(ws,{'A':9,'B':16,'C':16,'D':42,'E':40,'F':13})

# Gene_RiPP_Cores
ws=NS('Gene_RiPP_Cores',['strain','taxonomy','Contig','RiPP_Family','Locus_Tag','Motif_Index','Core_Sequence','Source'])
for r in gene['ripp']: ws.append([r['sid'],ORG[r['sid']],r['contig'],r['family'],r['locus'],r['motif_index'],r['core'],r.get('provenance','bounded-json')])
fillrows(ws,len(gene['ripp']),8); ws.freeze_panes='A2'; W(ws,{'A':9,'B':22,'C':16,'D':16,'E':14,'F':11,'G':40,'H':13})

# Gene_Domain_Hits
ws=NS('Gene_Domain_Hits',['strain','Region_Key','Locus_Tag','Domain','Pfam_Acc','Evalue','Bitscore','Tier1_Diagnostic'])
for r in deep['domain_hits']: ws.append([r['sid'],r['region_key'],r['locus'],r['domain'],r['pfam'],r['evalue'],r['bitscore'],r['tier1']])
fillrows(ws,len(deep['domain_hits']),8); ws.freeze_panes='A2'; ws.auto_filter.ref=f"A1:H{1+len(deep['domain_hits'])}"
W(ws,{'A':9,'B':18,'C':16,'D':18,'E':12,'F':11,'G':10,'H':16})

# TFBS_Motifs
motifs=sorted({m for d in gene['tfbs'].values() for m in d})
cols=['strain','taxonomy']+motifs+['Total']; ws=NS('TFBS_Motifs',cols)
for ri,sid in enumerate(SIDS,2):
    ws.append([sid,ORG[sid]]+[gene['tfbs'][sid].get(m,0) for m in motifs])
    ws.cell(row=ri,column=2+len(motifs)+1,value=f'=SUM(C{ri}:{get_column_letter(2+len(motifs))}{ri})').font=black
    for cc in range(1,3+len(motifs)+1): ws.cell(row=ri,column=cc).border=bd
    for cc in range(3,3+len(motifs)): ws.cell(row=ri,column=cc).font=blue; ws.cell(row=ri,column=cc).alignment=ctr
    ws.cell(row=ri,column=1).font=base; ws.cell(row=ri,column=2).font=base; ws.cell(row=ri,column=2+len(motifs)+1).alignment=ctr
ws.freeze_panes='C2'; W(ws,{'A':9,'B':22})
for j,m in enumerate(motifs): ws.column_dimensions[get_column_letter(3+j)].width=max(8,len(m)+1)

# C1/C2 DAPR scaffold
for code,nm in [('C1_DAPR_Antibacterial','antibacterial'),('C2_DAPR_Antifungal','antifungal')]:
    ws=NS(code,['Rank','strain','BGC_ID','Product_Class','AN_Score','WL_Score','Rationale','KCB_Provenance'])
    for ri in range(2,7):
        for cc in range(1,9): ws.cell(row=ri,column=cc).border=bd; ws.cell(row=ri,column=cc).fill=PatternFill('solid',fgColor=SCAF)
    W(ws,{'A':6,'B':9,'C':12,'D':16,'E':10,'F':10,'G':40,'H':16})
    ws.cell(row=8,column=1,value=f'SCAFFOLD — ranked {nm} leads are a Sapote (LLM judgment-layer) output; fill after a scoring pass.').font=ital
    ws.merge_cells(start_row=8,start_column=1,end_row=8,end_column=7)

# D1_RGGMCI_All_Strains
ws=NS('D1_RGGMCI_All_Strains',['strain','Status','Ref_Records','ClusterBlast_Files','Pairs_Total','HIGH','MODERATE','LOW','Evidence_Rows','Note'])
for sid in SIDS:
    r=rgf[sid]; c=r['conf']
    hi=c.get('HIGH_RG_GMCI_RESCUE',0); mo=c.get('MODERATE_RG_GMCI_CANDIDATE',0); lo=c.get('LOW_SHARED_REFERENCE_SIGNAL',0)
    ws.append([sid,r['status'],r['ref_record_count'],r['clusterblast_txt_files'],r['n_pairs'],hi,mo,lo,r['n_evidence'],'ranked_pairs capped at 1000' if r['n_pairs']>=1000 else ''])
fillrows(ws,len(SIDS),10)
for i in range(2,2+len(SIDS)):
    for cc in (3,4,5,6,7,8,9): ws.cell(row=i,column=cc).font=blue; ws.cell(row=i,column=cc).alignment=ctr
ws.freeze_panes='B2'; W(ws,{'A':9,'B':8,'C':12,'D':16,'E':11,'F':8,'G':10,'H':8,'I':13,'J':22})

# D2_RGGMCI_Top_Pairs (all HIGH)
cols=['strain','Pair','BGC_a','Contig_a','Products_a','Edge_a','BGC_b','Contig_b','Products_b','Edge_b','Score','Confidence','Pair_Type','Avg_Min_Identity','Shared_Ref_Tokens','Shared_Product_Tokens']
ws=NS('D2_RGGMCI_Top_Pairs',cols); EDGEFRAG={'Edge','Full-contig'}; nr=0
for sid in SIDS:
    highs=[p for p in rgf[sid]['ranked_pairs'] if p.get('rggmci_confidence')=='HIGH_RG_GMCI_RESCUE']
    highs.sort(key=lambda x:-(x.get('rggmci_score') or 0))
    for p in highs:
        ea=p.get('edge_a',''); eb=p.get('edge_b','')
        pt='fragment_rescue' if (ea in EDGEFRAG or eb in EDGEFRAG) else 'interior_homology'
        ws.append([sid,p.get('pair',''),p.get('bgc_a',''),p.get('contig_a',''),jn(p.get('products_a'))[:40],ea,
            p.get('bgc_b',''),p.get('contig_b',''),jn(p.get('products_b'))[:40],eb,p.get('rggmci_score'),'HIGH',pt,
            p.get('avg_min_identity'),jn(p.get('shared_reference_type_tokens'))[:40],jn(p.get('shared_product_tokens'))[:40]]); nr+=1
fillrows(ws,nr,len(cols))
for i in range(2,2+nr):
    if ws.cell(row=i,column=13).value=='fragment_rescue': ws.cell(row=i,column=13).fill=PatternFill('solid',fgColor=RESC)
ws.freeze_panes='C2'; ws.auto_filter.ref=f'A1:{get_column_letter(len(cols))}{1+nr}'
W(ws,{'A':9,'B':16,'C':9,'D':16,'E':18,'F':11,'G':9,'H':16,'I':18,'J':11,'K':8,'L':10,'M':16,'N':14,'O':24,'P':24})

# A4_Completeness_Audit
ws=NS('A4_Completeness_Audit',['strain','In_Registry','Has_BGCs','In_Class_Matrix','TIGRFAM_Checked','Scans_Filled','RGGMCI_Run','DAPR_Filled','Pct_Core_Complete'])
for ri,sid in enumerate(SIDS,2):
    ws.cell(row=ri,column=1,value=sid).font=base
    ws.cell(row=ri,column=2,value=f'=IF(COUNTIF(A2_Strain_Registry!$A:$A,$A{ri})>0,"Y","N")').font=green
    ws.cell(row=ri,column=3,value=f'=IF(COUNTIF(B1_BGC_Master!$A:$A,$A{ri})>0,"Y","N")').font=green
    ws.cell(row=ri,column=4,value=f'=IF(COUNTIF(B2_Product_Class_Matrix!$A:$A,$A{ri})>0,"Y","N")').font=green
    ws.cell(row=ri,column=5,value=f'=IF(COUNTIF(TIGRFAM_Check!$A:$A,$A{ri})>0,"Y","N")').font=green
    ws.cell(row=ri,column=6,value=f'=IF(COUNTIF(B4_Cross_Strain_Scans!$A:$A,$A{ri})>0,"Y","N")').font=green
    ws.cell(row=ri,column=7,value=f'=IF(COUNTIF(D1_RGGMCI_All_Strains!$A:$A,$A{ri})>0,"Y","N")').font=green
    ws.cell(row=ri,column=8,value=f'=IF(COUNTIF(C1_DAPR_Antibacterial!$B:$B,$A{ri})>0,"Y","N")').font=green
    ws.cell(row=ri,column=9,value=f'=COUNTIF(B{ri}:G{ri},"Y")/6').font=black
    for cc in range(1,10): ws.cell(row=ri,column=cc).border=bd; ws.cell(row=ri,column=cc).alignment=ctr
    ws.cell(row=ri,column=9).number_format='0%'
ws.freeze_panes='B2'; W(ws,{'A':9,'B':12,'C':11,'D':15,'E':16,'F':13,'G':12,'H':12,'I':18})

# Cross_Strain_Compare
ws=wb.create_sheet('Cross_Strain_Compare'); ws.merge_cells(f'A1:{get_column_letter(1+len(SIDS))}1')
ws['A1']='Cross-Strain Comparison'; ws['A1'].font=tf; ws['A1'].fill=tfill; ws['A1'].alignment=ctr
ws.append(['Metric']+SIDS)
for cc in range(1,2+len(SIDS)):
    c=ws.cell(row=2,column=cc); c.font=hf; c.fill=hfill; c.alignment=ctr; c.border=bd
metrics=[('taxonomy',[f'=A2_Strain_Registry!B{2+i}' for i in range(len(SIDS))],None),
 ('Genome size (Mb)',[f'=A2_Strain_Registry!J{2+i}/1000000' for i in range(len(SIDS))],'0.00'),
 ('Contigs',[f'=A2_Strain_Registry!H{2+i}' for i in range(len(SIDS))],'#,##0'),
 ('N50',[f'=A2_Strain_Registry!I{2+i}' for i in range(len(SIDS))],'#,##0'),
 ('GC %',[f'=A2_Strain_Registry!K{2+i}' for i in range(len(SIDS))],'0.0'),
 ('Assembly grade',[f'=A2_Strain_Registry!O{2+i}' for i in range(len(SIDS))],None),
 ('Raw BGCs',[f'=A2_Strain_Registry!M{2+i}' for i in range(len(SIDS))],'#,##0'),
 ('Corrected BGCs',[f'=A2_Strain_Registry!N{2+i}' for i in range(len(SIDS))],'0.00'),
 ('Distinct product classes',[f'=B2_Product_Class_Matrix!{DISTINCT_COL}{2+i}' for i in range(len(SIDS))],'#,##0'),
 ('BGCs with KCB hit',[f'=B3_Known_Cluster_Matrix!D{2+i}' for i in range(len(SIDS))],'#,##0'),
 ('% BGCs with KCB',[f'=B3_Known_Cluster_Matrix!F{2+i}' for i in range(len(SIDS))],'0.0%'),
 ('TIGRFAM diagnostics',[f'=TIGRFAM_Check!I{2+i}' for i in range(len(SIDS))],'#,##0'),
 ('RG-GMCI HIGH pairs',[f'=D1_RGGMCI_All_Strains!F{2+i}' for i in range(len(SIDS))],'#,##0'),
 ('TFBS total',[f'=B4_Cross_Strain_Scans!K{2+i}' for i in range(len(SIDS))],'#,##0')]
r=3
for name,fs,fmt in metrics:
    ws.cell(row=r,column=1,value=name).font=boldb; ws.cell(row=r,column=1).border=bd
    for i,f in enumerate(fs):
        c=ws.cell(row=r,column=2+i,value=f); c.font=green; c.alignment=ctr; c.border=bd
        if fmt: c.number_format=fmt
    r+=1
ws.freeze_panes='B3'; W(ws,{'A':26})
for i in range(len(SIDS)): ws.column_dimensions[get_column_letter(2+i)].width=18

# TIGRFAM_Check
cols=['strain','taxonomy','Module_Hits','TIGR01454','TIGR03604','TIGR03828','TIGR04186','Diag_Present','Diag_Surfaced','GBK_TIGR03604','Parity']
ws=NS('TIGRFAM_Check',cols)
for ri,sid in enumerate(SIDS,2):
    t=tig[sid]; pr=t['present']
    ws.append([sid,ORG[sid],t['module'],pr.get('TIGR01454',0),pr.get('TIGR03604',0),pr.get('TIGR03828',0),pr.get('TIGR04186',0),None,t['surfaced'],t['gbk'],None])
    for cc in (3,4,5,6,7,9,10): ws.cell(row=ri,column=cc).font=blue; ws.cell(row=ri,column=cc).alignment=ctr
    ws.cell(row=ri,column=8,value=f'=SUM(D{ri}:G{ri})').font=black; ws.cell(row=ri,column=8).alignment=ctr
    p=ws.cell(row=ri,column=11,value=f'=IF(I{ri}=H{ri},"PASS","FAIL")'); p.font=black; p.alignment=ctr; p.fill=PatternFill('solid',fgColor=PASS)
    for cc in range(1,12): ws.cell(row=ri,column=cc).border=bd
    ws.cell(row=ri,column=1).font=base; ws.cell(row=ri,column=2).font=base
ws.freeze_panes='A2'; W(ws,{'A':9,'B':24,'C':11,'D':10,'E':10,'F':10,'G':10,'H':11,'I':12,'J':13,'K':8})

# Strain_Catalog
ws=NS('Strain_Catalog',['strain','taxonomy','Genus','WW_Accession','GCA_Accession','BioSample','Tested','Notes'])
# Per-strain Strain_Catalog notes, keyed by REAL strain ID. FIXED v9.7.308: was
# {'SID-XXX': 'Amycolatopsis — ansamycin (TIGR01454) candidate, untested'} — a scrub
# placeholder key that never matched any real strain, so the note was orphaned (note.get
# always returned ''). Emptied here (behavior identical) pending the real strain ID it belongs
# to; the note text is preserved below so the annotation is not lost.
_ORPHANED_STRAIN_NOTES_PENDING_MAPPING=['Amycolatopsis — ansamycin (TIGR01454) candidate, untested']
note={}
for s in catalog: ws.append([s['sid'],s.get('organism',''),(s.get('organism','') or ' ').split()[0],s.get('ww',''),s.get('gca','') or '',s.get('samn','') or '',None,note.get(s['sid'],'')])
for i in range(2,2+len(catalog)):
    ws.cell(row=i,column=7,value=f'=IF(COUNTIF(A2_Strain_Registry!$A:$A,A{i})>0,"done","pending")').font=green; ws.cell(row=i,column=7).alignment=ctr
    for cc in range(1,9): ws.cell(row=i,column=cc).border=bd
    for cc in (1,2,3,4,5,6,8): ws.cell(row=i,column=cc).font=base
ws.freeze_panes='A2'; ws.auto_filter.ref=f'A1:H{1+len(catalog)}'
W(ws,{'A':10,'B':42,'C':16,'D':16,'E':18,'F':16,'G':10,'H':44})

out=_OUT
atomic_save(wb, out)
emit('saved | sheets:',len(wb.sheetnames),'| strains:',len(SIDS),'| BGCs:',NB,'| classes:',len(classes),'| D2 pairs:',nr)
