"""Build a private offline RG-GMCI review view using the retained semantic reader.
No extraction, scoring, reaction assignment or scientific admission occurs here.
"""
import argparse, hashlib, importlib.util, json, sqlite3, sys
from pathlib import Path
sys.dont_write_bytecode = True

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def identity(value):
    parts=value.split(' / ')
    if len(parts)!=4 or any(not p.strip() for p in parts):
        raise ValueError('Incomplete exact locus identity')
    return value

def eligible(p):
    return bool(p['shared_product_tokens']) and p['good_geometry_references']>0 and p['complementary_disjoint_refs']>0

def validate_partition(part, strain):
    im=part['input']['identity_map']; seen=set()
    for alias, value in im.items():
        bits=identity(value).split(' / ')
        if bits[0]!=strain or bits[3]!=alias or value in seen:raise ValueError('Wrong population or duplicate identity')
        seen.add(value)
    bgcs=part['input']['input_bgcs']
    if len({b['bgc_id'] for b in bgcs})!=len(bgcs):raise ValueError('Duplicate locus record')
    for b in bgcs:
        bits=im[b['bgc_id']].split(' / ')
        if b['contig']!=bits[1] or b['antismash_region']!=bits[2]:raise ValueError('Wrong assembly identity')
        if not 1<=b['start']<=b['end']<=b['contig_length']:raise ValueError('Boundary coordinate error')
    seen=set()
    for pair in part['result']['ranked_pairs']:
        key=tuple(sorted((pair['bgc_a'],pair['bgc_b'])))
        if key in seen or key[0]==key[1]:raise ValueError('Duplicate pair')
        seen.add(key)
        for side in ('a','b'):
            if pair['exact_identity_'+side]!=im[pair['bgc_'+side]]:raise ValueError('Pair identity mismatch')
        for field in ('good_geometry_references','complementary_disjoint_refs','supporting_references'):
            if not isinstance(pair[field],int) or pair[field]<0:raise ValueError('Unmeasured or invalid reference count')
            if pair[field]>pair['supporting_references']:raise ValueError('Reference denominator overflow')


def select(part, count=1):
    pairs=part['result']['ranked_pairs']
    candidates=[(i,p) for i,p in enumerate(pairs,1) if eligible(p)]
    return candidates[:count]

def clean(raw, im):
    if isinstance(raw,dict):return {k:clean(v,im) for k,v in raw.items()}
    if isinstance(raw,list):return [clean(v,im) for v in raw]
    if isinstance(raw,str):
        if raw in im:return im[raw]
        if '+' in raw and all(x in im for x in raw.split('+')):return ' ↔ '.join(im[x] for x in raw.split('+'))
    return raw

def build(args):
    root=args.source.resolve(); manifest=root/'RELEASE_MANIFEST.json'
    if sha(manifest)!=args.manifest_sha256:raise ValueError('Manifest hash mismatch')
    release=json.loads(manifest.read_text());db=(root/release['database']).resolve()
    if not db.is_relative_to(root):raise ValueError('Database outside source root')
    dbpin=release['database_sha256']
    if sha(db)!=dbpin:raise ValueError('Database hash mismatch')
    reader=root/'methods_and_receipts/read_rggmci_database.py'
    pin=next(f['sha256'] for f in release['files'] if f['path']=='methods_and_receipts/read_rggmci_database.py')
    if sha(reader)!=pin:raise ValueError('Reader hash mismatch')
    spec=importlib.util.spec_from_file_location('retained_rggmci_reader',reader);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
    c.execute('PRAGMA query_only=ON');c.execute('PRAGMA trusted_schema=OFF');c.execute('BEGIN')
    required={'strain_partition','locus','gene_context','reference_source','section_profile','section_relevance'}
    if not required.issubset({r[0] for r in c.execute("select name from sqlite_master where type='table'")}):raise ValueError('Schema missing required tables')
    profile=dict(c.execute('select * from section_profile').fetchone())
    if sha(args.contract)!=profile['profile_sha256']:raise ValueError('Current contract differs from retained profile')
    strains=[r[0] for r in c.execute('select strain from strain_partition order by strain')]
    if len(strains)!=45:raise ValueError('Expected explicit frozen45 population')
    selected=strains[:5] if args.pilot else strains
    if args.strain:
        if args.strain not in selected:raise ValueError('Requested strain outside bound population')
        selected=[args.strain]
    rows=[]; census=[];audit=[]
    for strain in selected:
        part=mod.read_partition(db,strain);validate_partition(part,strain);im=part['input']['identity_map']
        loci={r['bgc_id']:r for r in part['input']['input_bgcs']}
        picks=select(part)
        census.append(dict(strain=strain,available_pairs=len(part['result']['ranked_pairs']),eligible_pairs=sum(eligible(p) for p in part['result']['ranked_pairs']),displayed_pairs=len(picks),export_receipt=part['result'].get('export_receipt')))
        for rank,p in picks:
            a,b=p['bgc_a'],p['bgc_b'];ia,ib=identity(im[a]),identity(im[b])
            if p['exact_identity_a']!=ia or p['exact_identity_b']!=ib:raise ValueError('Identity conflict')
            ev=[e for e in part['result']['evidence_rows'] if {e['bgc_a'],e['bgc_b']}=={a,b}]
            bound=[]
            for ident in (ia,ib):
                loc=dict(c.execute('select * from locus where exact_identity=?',(ident,)).fetchone())
                genes=[dict(r) for r in c.execute('select gene_order,locus_tag,protein_sha256,protein_length,state from gene_context where locus_key=? order by gene_order',(loc['locus_key'],))]
                if len(genes)!=loc['cds_count'] or any(len(g['protein_sha256'] or '')!=64 for g in genes):raise ValueError('Protein roster binding error')
                refs=[dict(r) for r in c.execute('select * from reference_source where locus_key=?',(loc['locus_key'],))]
                bound.append(dict(locus=loc,reference_sources=refs,gene_context=genes))
            holds=['REACTION_DEFINITION_UNBOUND: no reviewed reaction assigned','PARTNER_FUNCTION_UNREVIEWED: shared class is annotation context','No nucleotide join, cooperation, production or activity established','Independent pathway or paralog remains an alternative']
            for k in ('acceptance_gate','junction_evidence_state','terminus_override_note'):
                if p.get(k):holds.append(k+': '+str(p[k]))
            rows.append(dict(focal=ia,partner=ib,strain=strain,rank=rank,shared_class=p['shared_product_tokens'],reaction='Unassigned — reviewed reaction definition and bound catalytic evidence required',machinery='Unreviewed; source product annotations: '+p['products_b'],focal_component='Unreviewed; source product annotations: '+p['products_a'],hold=holds,raw=clean(p,im),evidence=clean(ev,im),bound_sources=bound,boundary={side:{k:loci[alias].get(k) for k in ('edge_status','start','end','contig_length','overmerge_state','protocluster_count','architecture_rationale')} for side,alias in [('focal',a),('partner',b)]},denominator={'unit':'saved reference records per pair; not reactions or complete pathway genes','supporting_references':p.get('supporting_references'),'evidence_rows':len(ev),'available_ranked_pairs_in_partition':len(part['result']['ranked_pairs']),'displayed_pairs_in_partition':1},status='MACHINERY_REVIEW_QUEUE_NOT_MECHANISTIC_HYPOTHESIS'))
            audit.append(dict(focal=ia,partner=ib,identity_match=True,evidence_rows=len(ev),raw_pair_equal=rows[-1]['raw']==clean(p,im),source_count=sum(len(x['reference_sources']) for x in bound),reaction_assigned=False,holds=holds))
    c.close()
    if sha(db)!=dbpin or sha(manifest)!=args.manifest_sha256 or sha(reader)!=pin or sha(args.contract)!=profile['profile_sha256']:raise ValueError('Source drift')
    data=dict(population='frozen45',scope='First eligible saved rank per strain, at most 45 pairs. Eligibility is routing only: shared product token, positive good-geometry reference count and positive disjoint reference count. No partners accepted.',source={'database':str(db),'database_sha256':dbpin,'manifest':str(manifest),'manifest_sha256':args.manifest_sha256,'reader_sha256':pin,'contract_sha256':profile['profile_sha256'],'binding':release['binding']},sections={'10':'Fragment and boundary risks','29':'Cross-cluster hypotheses','37':'Partner/accessory proteins','43':'RG-GMCI cross-contig candidates','verification':'Current supplied contract hash equals stored exact50 profile; mapping is relevance only'},rows=rows,census=census,mechanistic_hypotheses=0)
    out=args.output.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be new or empty; preserve prior checkpoint')
    out.mkdir(parents=True,exist_ok=True)
    (out/'board_data.json').write_text(json.dumps(data,indent=2))
    template=Path(__file__).with_name('reaction_gap_board.html').read_text()
    (out/'index.html').write_text(template.replace('/*DATA*/',json.dumps(data).replace('<','\\u003c')))
    (out/'BUILD_RECEIPT.json').write_text(json.dumps({'source':data['source'],'population':'frozen45','partitions':len(selected),'displayed_pairs':len(rows),'audit':audit,'candidate_only':True},indent=2))
    print(json.dumps({'partitions':len(selected),'pairs':len(rows),'output':str(out)}))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--manifest-sha256',required=True);ap.add_argument('--contract',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--pilot',action='store_true');ap.add_argument('--strain');build(ap.parse_args())
