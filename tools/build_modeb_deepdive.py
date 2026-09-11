#!/usr/bin/env python3
"""build_modeb_deepdive.py — gene-by-gene Mode B deep dives (Sapote deliverable).

For each target BGC, assembles a structured §1–§8 deep dive from the banked gene-level data: domain
architecture (bgc_profile), active-site/specificity calls (active_sites), the ordered gene inventory
(class_pred predicted_products), KCB anchor + size + edge (bgc_data), and strain regulatory context (tfbs).

Claim-safety: every statement is class-level and KCB-anchored (similarity, not identification); bioactivity metadata is
optional strain-level context, never asserted per BGC; markers/coupling are candidate evidence. The verdict
reflects whether the gene-by-gene biosynthetic logic supports the anchor's class, not a compound ID.

Usage: python tools/build_modeb_deepdive.py --banked-dir cohort --out analysis/ModeB_DeepDives.md [--targets SID-XXX:BGC024,...]
Default targets = the six Class-A leads.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, json, sys


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text
from mamey.id_resolver import resolver_rows, resolver_md

DEFAULT=[('SID-XXX','BGC024'),('SID-XXX','BGC032'),('SID-XXX','BGC037'),('SID-XXX','BGC059'),('SID-XXX','BGC014'),('SID-XXX','BGC067')]


def _count_verdicts(targets, vmap):
    """§8-verdict counts for the run summary line. Must use the SAME default ('CONFIRM' when a
    target has no row in modeb_verdicts.csv) that the card body and section-header grouping in
    main() already apply (`st=(v or {}).get('status','CONFIRM')`) -- otherwise a --targets-only
    invocation with no modeb_verdicts.csv (vmap == {}) prints "0 CONFIRM, 0 DOWNGRADE, 0 DROP"
    while every card in the document it just wrote literally renders "Verdict — CONFIRM": the
    printed summary silently contradicts its own output. BC2-408."""
    nc = nd = nr = 0
    for t in targets:
        st = (vmap.get(t) or {}).get('status', 'CONFIRM')
        if st == 'CONFIRM':
            nc += 1
        elif st == 'DOWNGRADE':
            nd += 1
        elif st == 'DROP':
            nr += 1
    return nc, nd, nr


CATS=[
 ('Core biosynthesis', ['polyketide synthase','ketosynthase','beta-ketoacyl','3-oxoacyl-acp','acyl carrier','acyltransferase domain','non-ribosomal peptide','amp-binding','condensation','pks','nrps','crotonyl-coa carboxylase','enterobactin synthetase']),
 ('Tailoring / decoration', ['cytochrome p450','halogenase','methyltransferase','glycosyltransferase','sdr family','short-chain dehydrogenase','monooxygenase','oxygenase','reductase','hydroxylase','epimerase','dehydratase','aminotransferase','oxidoreductase','dioxygenase','flavin','sulfotransferase','zinc-binding dehydrogenase','cyclase']),
 ('Sugar / precursor supply', ['dtdp','ndp-hexose','thymidylyltransferase','glucose-1-phosphate','dtdp-glucose','rfba','deoxy','rhamnose','nad-dependent epimerase','gdp-mannose','citramalate','asparagine synth']),
 ('Regulation', ['regulator','sigma factor','sigma-70','response regulator','histidine kinase','helix-turn-helix','winged helix','lysr','tetr','marr','luxr','arac','anti-sigma','antar','spoiie','wyl domain','protein kinase']),
 ('Resistance / transport', ['transporter','abc transporter','mfs transporter','permease','resistance','efflux','bleomycin resistance','substrate-binding']),
]

def categorize(products):
    genes=[g.strip() for g in (products or '').replace('\n',' ').split(';') if g.strip()]
    out={c:[] for c,_ in CATS}; other=[]
    for g in genes:
        gl=g.lower(); placed=False
        for c,kws in CATS:
            if any(k in gl for k in kws): out[c].append(g); placed=True; break
        if not placed and len(g)<60 and 'hypothetical' not in gl and 'duf' not in gl and 'domain-containing' not in gl:
            other.append(g)
    return out, other, len(genes)

EXTENDER={'mal':'malonyl','mmal':'methylmalonyl','emal':'ethylmalonyl','mxmal':'methoxymalonyl','Malonyl-CoA':'malonyl','Methylmalonyl-CoA':'methylmalonyl','Ethylmalonyl-CoA':'ethylmalonyl','Methoxymalonyl-ACP':'methoxymalonyl'}
PROTEINOGENIC={'Ala','Arg','Asn','Asp','Cys','Gln','Glu','Gly','His','Ile','Leu','Lys','Met','Phe','Pro','Ser','Thr','Trp','Tyr','Val'}
NONPROT={'Orn','Dab','bAla','Pip','Hpg','Dhpg','Aad','Sal','Pgl','Hty','Cit','Kyn'}
RARE_NOTE={'ethylmalonyl':'ethyl branch (crotonyl-CoA carboxylase/reductase)','methoxymalonyl':'methoxy branch (rare extender)',
 'Hpg':'4-hydroxyphenylglycine — aromatic, glycopeptide/vancomycin-type unit','Dhpg':'3,5-dihydroxyphenylglycine — glycopeptide unit',
 'Orn':'ornithine (non-proteinogenic)','Dab':'2,4-diaminobutyrate','Pip':'pipecolate','Sal':'salicylate starter (siderophore-type)','bAla':'β-alanine'}

def parse_specificity(sid, contig, region, asites, sub):
    from collections import Counter
    # AT catalytic + specificity calls on the BGC's contig
    AT=[a for a in asites if a['sid']==sid and a.get('contig')==contig]
    at=Counter(); ks_active=False
    for a in AT:
        c=a.get('active_site_calls','').lower()
        if 'histidines: true' in c: ks_active=True
        if 'methylmalonyl-coa specific' in c: at['methylmalonyl']+=1
        elif 'malonyl-coa specific' in c: at['malonyl']+=1
        elif 'neither' in c: at['neither']+=1
        elif 'inconclusive' in c: at['inconclusive']+=1
    # on-BGC substrate consensus (accurate but sparse when fragmented)
    on=[s for s in sub if s['sid']==sid and s.get('contig')==contig and s.get('locus')==region and s.get('field')=='substrate consensus']
    # strain-level extender + AA pools (context; fragmentation scatters per-module attribution)
    ext=Counter(); aa=Counter()
    for s in sub:
        if s['sid']==sid and s.get('field')=='substrate consensus':
            v=s['substrate']
            if v in EXTENDER: ext[EXTENDER[v]]+=1
            elif v in PROTEINOGENIC or v in NONPROT: aa[v]+=1
    return at, ks_active, on, ext, aa

def module_logic(p, cls=''):
    ks=p.get('PKS_KS',0); at=p.get('PKS_AT',0); kr=p.get('PKS_KR',0); dh=p.get('PKS_DH',0); er=p.get('PKS_ER',0)
    c=p.get('NRPS_C',0); a=p.get('NRPS_A',0); pcp=p.get('NRPS_T_PCP',0)
    cl=cls.lower(); bits=[]
    aromatic = ('t2pks' in cl or 'hr-t2pks' in cl)
    transat = ('transat-pks' in cl)
    if ks:
        if aromatic:
            bits.append(f"{ks} ketosynthase (KS) domains in an **iterative aromatic (type II) PKS** context (minimal KSα/KSβ/CLF re-used across cycles; no per-module AT — decoration is supplied by tailoring enzymes, §4)")
        elif transat:
            bits.append(f"{ks} KS + {at} AT — **trans-AT modular PKS** (AT supplied in trans; AT count < KS is expected); reductive loop depth {kr} KR / {dh} DH / {er} ER")
        else:
            mode = 'trans-AT-like (AT < KS)' if at and at<ks-1 else 'cis-AT modular'
            bits.append(f"{ks} KS + {at} AT → ~{max(ks,at)} extension cycles, {mode} PKS; reductive loop depth {kr} KR / {dh} DH / {er} ER")
    if c or a:
        if a>=2 and c>=2 and pcp>=1:
            bits.append(f"{c} condensation (C) + {a} adenylation (A) + {pcp} PCP → a genuine NRPS module set (~{max(c,a)} amino-acid incorporations)")
        else:
            bits.append(f"{c} C / {a} A / {pcp} PCP domains — sub-modular (likely standalone C/A or a single hybrid module, not a full NRPS line)")
    if ks and a>=2 and pcp>=1 and not aromatic:
        bits.append("co-occurring modular PKS and NRPS → **hybrid PKS-NRPS assembly line**")
    return bits

def deepdive(sid,bid,brec,prof,asites,cpred,tfbs,rescue,sub,coupling=None,verdict=None):
    b=brec.get((sid,bid),{}); p=prof.get((sid,bid),{})
    contig=b.get('contig')
    AS=[a for a in asites if a['sid']==sid and a.get('contig')==contig]
    CP=[c for c in cpred if c['sid']==sid and c.get('contig')==contig]
    products=' ; '.join(c.get('predicted_products','') for c in CP)
    cats, other, ngenes = categorize(products)
    reg=tfbs.get(sid,{})
    cset=(coupling or {}).get(sid,{}).get(bid,[]) if coupling else []
    incluster_sarp=('SARP' in cset)
    status=(verdict or {}).get('status','CONFIRM'); vnote=(verdict or {}).get('note',''); vclass=(verdict or {}).get('modeb_class','')
    L=[]
    L.append(f"## {sid} / {bid} — {b.get('closest_kcb_product','?')}  ·  **{status}**" + (f" ({vclass})" if vclass else "") + "\n")
    # §1 identity
    L.append(f"**§1 · Identity & anchor.** antiSMASH class `{b.get('products','')}`; KCB anchor *{b.get('closest_kcb_product','?')}* "
             f"(closest MIBiG {b.get('closest_mibig','?')}); region {b.get('region','?')} on contig {contig}; "
             f"{b.get('length_kb','?')} kb; edge status **{b.get('edge_status','?')}**. The anchor is a similarity hypothesis, not an identification.")
    # §2 architecture
    bits=module_logic(p, b.get('products',''))
    L.append(f"\n**§2 · Assembly-line architecture.** {p.get('total_domains','?')} biosynthetic domains total. "
             + (' '.join('• '+x for x in bits) if bits else 'No modular PKS/NRPS core resolved.'))
    # §3 substrate & active-site specificity
    at, ks_active, on, ext, aa = parse_specificity(sid, contig, b.get('region'), asites, sub)
    s3=[]
    if ext:
        extstr=', '.join(f"{n}× {u}" for u,n in ext.most_common())
        branch='methyl/ethyl-branched' if (ext.get('methylmalonyl') or ext.get('ethylmalonyl')) else 'unbranched (all-malonyl)'
        s3.append(f"PKS extender pool (strain-resolved): {extstr} → {branch} polyketide backbone")
    if aa:
        nonp=[a_ for a_ in aa if a_ in NONPROT]
        aastr=', '.join(f"{a_}×{aa[a_]}" for a_,_ in aa.most_common(8))
        s3.append(f"NRPS A-domain substrate pool: {aastr}" + (f"; non-proteinogenic: {', '.join(nonp)}" if nonp else ''))
    if at:
        s3.append(f"AT specificity calls on-contig: {dict(at)}")
    if ks_active: s3.append("KS catalytic histidines present (active condensation)")
    # diagnostic rare units
    flags=[RARE_NOTE[u] for u in list(ext)+list(aa) if u in RARE_NOTE]
    if flags: s3.append("**diagnostic units:** " + '; '.join(sorted(set(flags))))
    note=" *(fragmentation scatters the per-module ladder across contigs, so units are strain-resolved, not per-module assigned; on-BGC consensus calls resolved: %d)*" % len(on)
    L.append("\n**§3 · Substrate & active-site specificity.** " + ('. '.join(s3) if s3 else 'no substrate/active-site calls recovered offline') + '.' + note)
    # §4 tailoring
    def show(cat,lim=10):
        items=cats.get(cat,[]); 
        return (', '.join(sorted(set(items))[:lim]) + (f' (+{len(set(items))-lim} more)' if len(set(items))>lim else '')) if items else '—'
    L.append(f"\n**§4 · Tailoring / decoration.** {show('Tailoring / decoration')}")
    L.append(f"\n**§5 · Sugar / precursor supply.** {show('Sugar / precursor supply')}")
    # §6 regulation
    L.append(f"\n**§6 · Regulation.** In-cluster: {show('Regulation',8)}. Strain TFBS context: "
             f"GBL/AdpA {reg.get('GBL_AdpA_like','?')}, DasR {reg.get('DasR_like_palindrome','?')}, "
             f"BldD {reg.get('BldD_like','?')}. **In-cluster coupling (tfbs_coupling): SARP/BTAD {'present' if incluster_sarp else 'absent'}** "
             f"(pathway-specific activator — the actionable Class-A signal){'; co-regulators: '+', '.join(x for x in cset if x!='SARP') if cset else ''}. "
             f"bldA/TTA-dependent CDS in cluster: {p.get('tta_cds','?')}.")
    # §7 resistance/transport + fragmentation
    rt=p.get('resistance_tier','')
    rtnote={'T1':'source-derived self-protection (diagnostic of a genuine, expressed pathway)','T2':'resistance-like, source-derived',
            'T3':'transporter-only routing (weaker self-resistance signal)','NU':'no source-derived resistance detected'}.get(rt[:2],'—')
    rsc=rescue.get(sid,{})
    L.append(f"\n**§7 · Resistance, transport & assembly context.** Resistance tier **{rt[:48]}** — {rtnote}. "
             f"Transport/resistance genes: {show('Resistance / transport',6)}. "
             f"Assembly: {rsc.get('contigs','?')} contigs, fragmentation {rsc.get('frag','?')}%, rescue tier {rsc.get('tier','?')} "
             f"({'edge-truncated — true cluster larger; re-sequencing target' if b.get('edge_status')=='Edge' else 'megasynthase may span contig boundaries' if (rsc.get('contigs') or 0)>200 else 'well-assembled'}).")
    # §8 verdict — reflects the actual Mode B status (CONFIRM / DOWNGRADE / DROP)
    ks=p.get('PKS_KS',0); cc=p.get('NRPS_C',0); td=p.get('total_domains',0)
    if status=='DROP':
        L.append(f"\n**§8 · Verdict — DROP.** Gene-level basis for rejection: *{vnote}*. "
                 f"The architecture here ({td} domains, {ks} KS / {cc} C) does **not** support the {b.get('closest_kcb_product','?').split('/')[0]} anchor's class — "
                 f"the KCB hit is a partial / whole-genome similarity, not a matching biosynthetic locus. The framework correctly says *no*: "
                 f"a similarity anchor without the diagnostic machinery at the locus is insufficient.\n")
    elif status=='DOWNGRADE':
        L.append(f"\n**§8 · Verdict — DOWNGRADE.** *{vnote}*. The locus is real but reclassified ({vclass}); retained as genomic "
                 f"context (cell-envelope / primary-adjacent), **not** promoted as a diffusible small-molecule lead. "
                 f"Resistance tier {(p.get('resistance_tier') or '')[:30]}.\n")
    else:
        rt2={'T1':'source-derived self-protection','T2':'resistance-like self-protection','T3':'transporter-only routing','NU':'no source-derived resistance'}.get((p.get('resistance_tier') or 'NU')[:2],'-')
        L.append(f"\n**§8 · Verdict — CONFIRM (class-level).** Gene-by-gene logic ({ks} KS / {cc} C, tailoring + "
                 f"{('SARP-coupled' if incluster_sarp else 'regulator-bearing (no in-cluster SARP)')}, {rt2}) supports a genuine, expressed "
                 f"{b.get('products','').split(';')[0]} pathway in the *{b.get('closest_kcb_product','?').split('/')[0]}* family ({vclass or 'class-level'}). "
f"Class-level hypothesis only; bioactivity metadata may be `NOT_SUPPLIED` and is not asserted for this BGC. "
                 f"Next: HMMER/BLAST the core + {('halogenase' if 'HAL' in (p.get('cctt_triggers') or '') else 'tailoring')} genes"
                 f"{'; re-sequence to resolve fragmentation' if (b.get('edge_status')=='Edge' or (rescue.get(sid,{}).get('contigs') or 0)>200) else ''}.\n")
    return '\n'.join(L)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--banked-dir', default='cohort'); ap.add_argument('--out', default='ModeB_DeepDives.md')
    ap.add_argument('--targets', default=None); ap.add_argument('--workbook', default=None)
    a=ap.parse_args()
    bgc=_read_json(os.path.join(a.banked_dir,'bgc_data.json')); brec={(b['sid'],b['bgc_id']):b for b in bgc['bgcs']}
    import os.path as _op
    # W6: deep_data.json / gene_data.json are enrichment; degrade gracefully so a single-strain package
    # (bgc_data.json only) still produces a deep-dive (without the deep/TFBS layers).
    _dp=os.path.join(a.banked_dir,'deep_data.json')
    deep=_read_json(_dp) if _op.exists(_dp) else {'bgc_profile':[]}
    prof={(p['sid'],p['bgc_id']):p for p in deep.get('bgc_profile',[])}
    _gp=os.path.join(a.banked_dir,'gene_data.json')
    gene=_read_json(_gp) if _op.exists(_gp) else {}; tfbs=gene.get('tfbs',{})
    coupling=_read_json(_op.join(a.banked_dir,'tfbs_coupling.json')) if _op.exists(_op.join(a.banked_dir,'tfbs_coupling.json')) else {}
    # rescue context
    # build rescue dict from workbook Fragment_Rescue_Tiers if available, else proxy from bgc_data contigs
    rescue={}
    if a.workbook and os.path.exists(a.workbook):
        try:
            import openpyxl
            wb=openpyxl.load_workbook(a.workbook, read_only=True)
            if 'Fragment_Rescue_Tiers' in wb.sheetnames:
                rows=list(wb['Fragment_Rescue_Tiers'].iter_rows(values_only=True)); h=list(rows[0]); ix={c:i for i,c in enumerate(h)}
                for r in rows[1:]:
                    if r[ix['strain']]: rescue[r[ix['strain']]]={'contigs':r[ix['Contigs']],'frag':r[ix['Frag_Loss']],'tier':r[ix['Tier']]}
        except Exception as e:
            emit(f"  [warn] workbook rescue read failed: {e}")
    if not rescue:
        sc={}
        for b in bgc['bgcs']: sc.setdefault(b['sid'],set()).add(b.get('contig'))
        for sid in sc: rescue[sid]={'contigs':len(sc[sid]),'frag':'?','tier':'?'}
    targets=DEFAULT; vmap={}
    vpath=os.path.join(a.banked_dir,'modeb_verdicts.csv')
    if os.path.exists(vpath):
        import csv as _csv
        for r in _csv.DictReader(open(vpath)):
            vmap[(r['strain'],r['bgc'])]={'status':r['status'],'modeb_class':r.get('modeb_class',''),'note':r.get('note','')}
    if a.targets:
        targets=[tuple(t.split(':')) for t in a.targets.split(',')]
    elif vmap:
        order={'CONFIRM':0,'DOWNGRADE':1,'DROP':2}
        targets=sorted(vmap.keys(), key=lambda k:(order.get(vmap[k]['status'],3), k[0]))
    # --- completeness guard: never emit mismatched placeholder cards on incomplete input ---
    if not a.targets and not vmap:
        sys.exit("build_modeb_deepdive: no --targets and no modeb_verdicts.csv in '%s'.\n"
                 "  Refusing to fall back to the built-in SID target list (that yields\n"
                 "  mismatched all-'?' cards on a strain those SIDs do not belong to).\n"
                 "  Provide --targets SID:BGC[,SID:BGC...] or run the Mode B verdict step first." % a.banked_dir)
    _missing=[t for t in targets if t not in brec]
    if _missing:
        sys.stderr.write("  [warn] %d target(s) absent from banked records, skipped: %s\n" % (len(_missing), _missing[:5]))
    targets=[t for t in targets if t in brec]
    if not targets:
        sys.exit("build_modeb_deepdive: no requested target matches a banked BGC record; nothing to render.")
    head=("# Mode B gene-by-gene deep dives — full verdict set\n\n"
          "*Sapote deliverable. Each dive reads the banked gene-level data (domain architecture, active-site calls, "
          "ordered gene inventory, regulatory context). All statements are class-level and KCB-anchored (similarity, "
"not identification); bioactivity metadata is optional strain-level context; markers/coupling are candidate evidence "
          "pending HMMER/BLAST. CONFIRM = gene logic supports the anchor's class; DOWNGRADE = real locus, reclassified, "
          "not a diffusible lead; DROP = anchor's class not supported at the locus (the framework saying no).*\n\n---\n\n")
    body=[]; last=None
    for sid,bid in targets:
        v=vmap.get((sid,bid)); st=(v or {}).get('status','CONFIRM')
        if st!=last:
            _desc={'CONFIRM':'gene logic supports the anchor class','DOWNGRADE':'real locus, reclassified','DROP':'anchor class NOT supported at the locus'}.get(st,'')
            body.append(f"\n# {st}S — {_desc}\n"); last=st
        body.append(deepdive(sid,bid,brec,prof,deep.get('active_sites',{}),deep.get('class_pred',{}),tfbs,rescue,gene.get('substrates',[]),coupling,v))
    head = head + "## ID resolver\n\n" + resolver_md(resolver_rows([brec[t] for t in targets if t in brec])) + "\n\n"
    atomic_write_text(a.out, head+'\n\n---\n\n'.join(body))
    # BC2-408: count with the SAME 'CONFIRM' default the card body/section-header grouping above
    # already uses (line ~251's `st=(v or {}).get('status','CONFIRM')`) -- see _count_verdicts.
    nc, nd, nr = _count_verdicts(targets, vmap)
    emit(f"  wrote {len(targets)} Mode B deep dives ({nc} CONFIRM, {nd} DOWNGRADE, {nr} DROP) -> {a.out}")

if __name__=='__main__': main()
