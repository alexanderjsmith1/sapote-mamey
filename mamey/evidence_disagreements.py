"""Private offline review view over explicit, frozen evidence sources.

Reuses tool_database_reader for identity, BLAST parsing and source checks. No
semantic equivalence or contradiction is inferred from annotation keywords.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from collections import Counter
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from . import tool_database_reader as owner
from .exact_identity import exact_locus_display
from .tool_database_session import FrozenDatabaseSession,decode_retained_json

ADAPTER = {'nr':'blastp-nr-v1', 'ClusteredNR':'blastp-clustered-nr-v1', 'SwissProt':'blastp-swissprot-v2'}
CHANNELS = tuple(ADAPTER)
CEILING = 'Review candidates only. No automatic adjudication, scientific admission or release acceptance. Function, expression and activity remain unestablished.'

def compare_statements(statements):
    """Text is an inspection cue only; explicit opposite assertions need review.

    Structured assertions require a source locator, predicate, scope, controlled
    term and positive/negative polarity. No source adapter invents such assertions.
    Different positive terms alone cannot prove mutually exclusive biology.
    """
    out = []
    for i,a in enumerate(statements):
        for b in statements[i+1:]:
            if a['channel'] == b['channel']: continue
            if a.get('binding') != 'BOUND' or b.get('binding') != 'BOUND': continue
            x,y=a.get('assertion'),b.get('assertion')
            if x and y and all(x.get(k) and x.get(k)==y.get(k) for k in ('predicate','scope','term')) and x.get('polarity') in ('positive','negative') and y.get('polarity') in ('positive','negative') and x['polarity']!=y['polarity'] and x.get('source') and y.get('source'):
                rule='EXPLICIT_OPPOSED_STATEMENTS_REVIEW'
            elif a.get('resolution') != b.get('resolution'):
                rule='DIFFERING_RESOLUTION'
            elif a.get('statement','').strip() != b.get('statement','').strip():
                rule='TEXT_VARIATION_UNRESOLVED'
            else: rule='SAME_RETAINED_TEXT_NOT_FUNCTION_VALIDATION'
            out.append({'left':a['id'],'right':b['id'],'rule':rule,'hold':'Human review required; multifunctionality, homology transfer and source scope unresolved.'})
    return out

def _resolution(text):
    # This is an annotation-specificity label, never a biological classifier.
    return 'unspecified_annotation' if re.search(r'\b(hypothetical|uncharacterized|unknown function)\b',text,re.I) else 'source_named_hit_annotation'

def matches(g,b,hash_key='protein_sha256'):
    if not b or not g.get('protein_sha256') or b.get(hash_key)!=g['protein_sha256']: return False
    if b.get('locus_tag')!=g['locus_tag']: return False
    return all(k not in b or b[k]==g.get(k) for k in ('cds_start','cds_end','strand','strain','full_node','region','bgc_alias','exact_identity','assembly_source_sha256'))

class Explorer:
    def __init__(self,selection):
        self.selection_path=Path(selection).resolve()
        self.config=json.loads(self.selection_path.read_text(),object_pairs_hook=owner._unique_object)
        if self.config.get('schema')!='mamey.disagreement-selection/1' or not self.config.get('population'): raise ValueError('SELECTION_SCHEMA_OR_POPULATION_HOLD')
        if set(self.config['sources']) != {'census','nr','ClusteredNR','SwissProt','domain','MIBiG'}: raise ValueError('EXPLICIT_SIX_SOURCE_SELECTION_REQUIRED')
        contract=self.config.get('contract',{});cp=self.selection_path.parent/contract.get('path','')
        if not cp.is_file() or owner._digest(cp)!=contract.get('sha256'):raise ValueError('CURRENT50_CONTRACT_PIN_HOLD')
        self.contract_text=cp.read_text();self.contract_stamp=owner._stamp(cp);self.contract_path=cp
        self.section_requirements={int(n):v.strip() for n,v in re.findall(r'^\| (\d+) \| (.*?) \|$',self.contract_text,re.M)}
        if set(self.section_requirements)!=set(range(1,51)):raise ValueError('CURRENT50_SHAPE_HOLD')
        self.sources={}; self.connections={}; self.manifests={};self.stamps={}
        try:
            for name,s in self.config['sources'].items():
                root=Path(s['root']);root=(self.selection_path.parent/root).resolve()
                session=FrozenDatabaseSession(root,s['manifest'],expected_manifest_sha256=s['manifest_sha256'],expected_schema='antismash_reference_comparisons_candidate/1' if name=='MIBiG' else owner.SCHEMA,adapter=ADAPTER.get(name,'gene-census-v1' if name=='census' else 'manifest'))
                session.__enter__();self.connections[name]=session;self.manifests[name]=session.manifest
                self.sources[name]=session.receipt
            census_hash=self.sources['census']['sha256']
            for name in (*CHANNELS,'domain'):
                if self.manifests[name].get('census_sha256')!=census_hash:raise ValueError('MIXED_POPULATION_CENSUS_PIN_HOLD')
                metadata=self.connections[name].rows("SELECT value FROM metadata WHERE key='census_sha256'")
                if len(metadata)!=1 or metadata[0]['value']!=census_hash:raise ValueError('CENSUS_DEPENDENCY_METADATA_HOLD')
            self._roster()
        except Exception:
            self.close();raise

    def close(self):
        errors=[]
        for c in self.connections.values():
            try:c.close()
            except Exception as exc:errors.append(exc)
        if errors:raise errors[0]

    def check_stable(self,hashes=False):
        if owner._stamp(self.contract_path)!=self.contract_stamp or (hashes and owner._digest(self.contract_path)!=self.config['contract']['sha256']):raise ValueError('CONTRACT_CHANGED_HOLD')
        for session in self.connections.values():session.check(hashes=hashes)

    def _roster(self):
        c=self.connections['census']
        assemblies={r['strain']:r['source_sha256'] for r in c.rows('SELECT strain,source_sha256 FROM strain')}
        self.genes={};self.loci={r['locus_key']:dict(r) for r in c.iter_rows('SELECT * FROM locus ORDER BY locus_key')}
        if len(self.loci)!=c.rows('SELECT count(*) n FROM locus')[0]['n']:raise ValueError('DUPLICATE_LOCUS_HOLD')
        for l in self.loci.values():
            if exact_locus_display(l['strain'],l['full_node'],l['region'],l['bgc_alias'])!=l['exact_identity']:raise ValueError('IDENTITY_CONFLICT')
        for row in c.iter_rows('SELECT * FROM gene ORDER BY locus_key,gene_order'):
            g=dict(row);l=self.loci[g['locus_key']];g.update({k:l[k] for k in ('exact_identity','strain','full_node','region','bgc_alias')})
            g['assembly_source_sha256']=assemblies.get(g['strain'])
            g['id']=g['locus_key']+':'+str(g['gene_order']);g['channels']={};
            if g['id'] in self.genes:raise ValueError('DUPLICATE_GENE_IDENTITY_HOLD')
            self.genes[g['id']]=g
        census_counts=Counter(g['locus_key'] for g in self.genes.values())
        if any(census_counts[k]!=l['cds_count'] for k,l in self.loci.items()):raise ValueError('CENSUS_DENOMINATOR_HOLD')
        for name in CHANNELS:
            c=self.connections[name];swiss=name=='SwissProt'
            bindings={ (r['locus_key'],r['gene_order']):dict(r) for r in c.iter_rows('SELECT * FROM binding ORDER BY locus_key,gene_order')}
            if len(bindings)!=c.rows('SELECT count(*) n FROM binding')[0]['n']:raise ValueError('DUPLICATE_CHANNEL_BINDING_HOLD')
            proteins={r['query_sha256']:dict(r) for r in c.iter_rows('SELECT * FROM protein ORDER BY query_sha256')}
            for g in self.genes.values():
                b=bindings.get((g['locus_key'],g['gene_order']));p=proteins.get(g['protein_sha256'],{})
                bound=matches(g,b,'query_sha256') and (not swiss or b.get('assembly_source_sha256')==g['assembly_source_sha256'] and bool(g['assembly_source_sha256'])) and b['exact_identity']==g['exact_identity'] and b['binding_state'] in ('CENSUS_SEQUENCE_BOUND','SEQUENCE_BOUND_CURRENT_LOCUS_PROJECTION') and p.get('aa_length' if swiss else 'protein_length')==g['protein_length']
                g['channels'][name]=p.get('state' if swiss else 'availability_state','NO_VERIFIED_SEARCH') if bound else 'IDENTITY_OR_PROTEIN_BINDING_HOLD'
            del bindings,proteins
        for g in self.genes.values():
            g['index_rule']='MISSING_OR_HELD_CHANNEL' if any(x in ('NO_VERIFIED_SEARCH','IDENTITY_OR_PROTEIN_BINDING_HOLD','MISSING_OR_UNBOUND_PROTEIN_HOLD') for x in g['channels'].values()) else 'RECORDED_SEARCH_OUTCOMES'
        # Small in-memory ID projection; no new SQLite copy or added source index.
        mc=self.connections['MIBiG']
        files={r['id'] for r in mc.iter_rows("SELECT id FROM source_file WHERE channel='knownclusterblast' ORDER BY id")}
        self.reference_ids={};last=0;read=0
        while True:
            page=mc.rows('SELECT id,locus_key,gene_order,file_id FROM alignment WHERE id>? ORDER BY id LIMIT 1000',(last,))
            if not page:break
            for r in page:
                if r['file_id'] in files:self.reference_ids.setdefault((r['locus_key'],r['gene_order']),[]).append(r['id'])
            read+=len(page)
            if read>2000000:raise ValueError('REFERENCE_INDEX_ROW_BUDGET_HOLD')
            last=page[-1]['id']
        profiles={}
        for name,session in self.connections.items():
            rows=session.rows('SELECT * FROM section_profile')
            profiles[name]={'source_profiles':[r.get('profile_sha256') for r in rows],'matches_current_contract':any(r.get('profile_sha256')==self.config['contract']['sha256'] for r in rows),'mapping_ceiling':'Requirements are context, never section completion'}
        self.summary={'population':self.config['population'],'gene_occurrences':len(self.genes),'unique_proteins':len({g['protein_sha256'] for g in self.genes.values() if g['protein_sha256']}),'loci':len(self.loci),'strains':sorted({g['strain'] for g in self.genes.values()}),'index_rules':dict(Counter(g['index_rule'] for g in self.genes.values())),'denominator':'Exact frozen census gene occurrences; overlapping occurrences are not deduplicated. Search no-hit is not biological absence.','claim_ceiling':CEILING,'section_mapping':{'contract_sha256':self.config['contract']['sha256'],'source_profiles':profiles,'verified_requirements':{n:self.section_requirements[n] for n in (1,3,4,8,9,14,15,16,19,50)},'hold':'Review fields can inform these requirements; no completed section or evidence-index admission is emitted. Exact-region census does not include expanded boundary-context genes.'},'sources':self.sources}

    def search(self,query='',strain='',state='',offset=0):
        self.check_stable()
        rows=[g for g in self.genes.values() if (not strain or strain==g['strain']) and (not state or state==g['index_rule']) and query.casefold() in (' '.join([g['exact_identity'],g['locus_tag'] or '',g['product'],g['protein_sha256'] or ''])).casefold()]
        rows.sort(key=lambda g:(g['exact_identity'],g['gene_order']))
        return {'total':len(rows),'offset':offset,'limit':25,'rows':[{k:g[k] for k in ('id','exact_identity','locus_tag','gene_order','protein_sha256','channels','index_rule')} for g in rows[offset:offset+25]]}

    def _gene(self,gid):
        self.check_stable()
        if gid not in self.genes:raise ValueError('EXACT_GENE_NOT_FOUND')
        return self.genes[gid]

    def hits(self,gid,channel,search_id,offset=0):
        g=self._gene(gid)
        if channel not in CHANNELS or g['channels'][channel]=='IDENTITY_OR_PROTEIN_BINDING_HOLD':raise ValueError('CHANNEL_BINDING_HOLD')
        raw,total=self.connections[channel].hit_evidence(g['exact_identity'].split(' / '),g['gene_order'],search_id,limit=25,offset=offset)
        return {'rows':raw,'total':total,'offset':offset,'limit':25,'source':self.sources[channel],'denominator':'Source-retained hits in this one search; not all possible homologues. HSP values remain raw.','hold':'Query union coverage is source-reported; never reference coverage. Above-100 values are preserved, not validated.'}

    def detail(self,gid):
        g=self._gene(gid);l=self.loci[g['locus_key']];statements=[];channels={};review=[]
        for name in CHANNELS:
            state=g['channels'][name];ch={'state':state,'source':self.sources[name],'searches':[]};channels[name]=ch
            if state in ('IDENTITY_OR_PROTEIN_BINDING_HOLD','MISSING_OR_UNBOUND_PROTEIN_HOLD'):continue
            c=self.connections[name];swiss=name=='SwissProt'
            searches=c.inspect(g['exact_identity'].split(' / '),gene_order=g['gene_order'],view='searches')
            if searches.get('next_offset') is not None:raise ValueError('SEARCH_HISTORY_BUDGET_HOLD')
            for s in searches['records']:
                hits,total=c.hit_evidence(g['exact_identity'].split(' / '),g['gene_order'],s['search_id'],limit=1)
                item={'search':s,'retained_hits':total,'representative':hits[0] if hits else None,'selection_rule':'Lowest retained source rank within EACH search; no cross-search winner. All retained counterevidence available through hit pagination.'};ch['searches'].append(item)
                if hits:
                    for i,d in enumerate(hits[0].get('descriptions',[])):
                        text=d.get('title') or ''
                        if text:statements.append({'id':name+':'+str(s['search_id'])+':'+str(i),'channel':name,'statement':text,'binding':'BOUND','resolution':_resolution(text),'source_rank':hits[0]['source_rank'],'source':self.sources[name],'hold':'Homologue annotation; transfer to query not adjudicated.'})
        dc=self.connections['domain'];dgs=dc.rows('SELECT * FROM gene WHERE locus_key=? AND gene_order=?',(g['locus_key'],g['gene_order']));dg=dgs[0] if len(dgs)==1 else None
        dls=dc.rows('SELECT * FROM locus WHERE locus_key=?',(g['locus_key'],));dl=dls[0] if len(dls)==1 else None
        domain_bound=matches(g,dg) and dl and dl['exact_identity']==g['exact_identity'] and dl['source_member_sha256']==l['source_member_sha256']
        domains=[]
        if domain_bound:
            for row in dc.rows('SELECT f.*,d.domain_label,d.protein_start_raw,d.protein_end_raw,d.evalue_raw,d.score_raw,d.source_tool,d.source_database_version FROM feature f LEFT JOIN domain_summary d USING(locus_key,feature_order) WHERE f.locus_key=? ORDER BY feature_order',(g['locus_key'],)):
                r=dict(row)
                if g['locus_tag'] not in json.loads(r['explicit_gene_tags_json']):continue
                r['qualifiers']=decode_retained_json(r.pop('source_qualifiers_zlib'));domains.append(r)
                if r['binding_state']=='SOURCE_SEQUENCE_AND_GEOMETRY_BOUND':statements.append({'id':'domain:'+str(r['feature_order']),'channel':'domain','statement':r['domain_label'] or r['feature_type'],'binding':'BOUND','resolution':'partial_domain_or_module','source':self.sources['domain'],'hold':'Domain/module scope does not establish full protein function.'})
        channels['domain']={'state':dg['result_state'] if domain_bound else 'IDENTITY_OR_PROTEIN_BINDING_HOLD','records':domains,'source':self.sources['domain'],'denominator':{'protein_length_aa':g['protein_length'],'feature_scope':'Explicit source gene tags, exact protein and region source hash; original geometry holds retained'},'source_member':l['source_member'],'source_member_sha256':l['source_member_sha256']}
        mc=self.connections['MIBiG'];mgs=mc.rows('SELECT * FROM gene WHERE locus_key=? AND gene_order=?',(g['locus_key'],g['gene_order']));mg=mgs[0] if len(mgs)==1 else None;mls=mc.rows('SELECT * FROM locus WHERE locus_key=?',(g['locus_key'],));ml=mls[0] if len(mls)==1 else None
        mapped=matches(g,dict(mg) if mg else None) and ml and ml['exact_identity']==g['exact_identity'] and ml['source_member_sha256']==l['source_member_sha256']
        ids=self.reference_ids.get((g['locus_key'],g['gene_order']),[]) if mapped else []
        refs=[]
        if ids:
            placeholders=','.join('?' for _ in ids[:100])
            refs=mc.rows("SELECT a.*,f.member,f.sha256 source_file_sha256,f.archive_sha256,f.channel,r.reference_raw,r.metadata_json FROM alignment a CROSS JOIN source_file f ON f.id=a.file_id CROSS JOIN reference r ON r.id=a.reference_id WHERE a.id IN ("+placeholders+") ORDER BY a.id",ids[:100])
        total=len(ids)
        channels['MIBiG']={'state':'SOURCE_GENE_MAPPED_ALIGNMENT_PROOF_HELD' if refs else 'NO_RETAINED_KNOWNCLUSTERBLAST_ALIGNMENT' if mapped else 'IDENTITY_OR_PROTEIN_BINDING_HOLD','records':refs[:100],'total':total,'displayed':min(100,len(refs)),'source':self.sources['MIBiG'],'denominator':'Coverage denominator/formula not established by source TXT. No inferred recalculation.','hold':'KnownClusterBlast/MIBiG reference context only; no query alignment sequence proof. Excluded from functional disagreement comparison. Dedicated finalized current MIBiG extension not selected.'}
        if total>100:channels['MIBiG']['hold']+=' Display bounded to 100; remaining rows available in source reader.'
        review=compare_statements(statements)
        if any(s in ('NO_VERIFIED_SEARCH','IDENTITY_OR_PROTEIN_BINDING_HOLD') for s in g['channels'].values()):review.insert(0,{'rule':'MISSING_DATA_OR_BINDING_HOLD','hold':'Missing search evidence is not negative functional evidence.'})
        if any(s=='VERIFIED_NO_HIT' for s in g['channels'].values()):review.insert(0,{'rule':'RECORDED_NO_HIT_NOT_FUNCTIONAL_CONTRADICTION','hold':'Search settings and database scope remain relevant.'})
        return {'gene':g,'locus_context':l,'channels':channels,'statements':statements,'review_candidates':review,'denominator':{'gene_occurrences_in_locus':l['cds_count'],'query_protein_length_aa':g['protein_length']},'claim_ceiling':CEILING,'rule_scope':'Pair cues use each search lowest retained rank and bound domains. Not exhaustive adjudication of all retained hits; inspect counterevidence. No keyword contradiction rule.'}

    def references(self,gid,offset=0):
        g=self._gene(gid);context=self.detail(gid)['channels']['MIBiG']
        if context['state']=='IDENTITY_OR_PROTEIN_BINDING_HOLD':raise ValueError('REFERENCE_BINDING_HOLD')
        ids=self.reference_ids.get((g['locus_key'],g['gene_order']),[]);page=ids[offset:offset+25]
        rows=[]
        if page:
            rows=self.connections['MIBiG'].rows('SELECT a.*,f.member,f.sha256 source_file_sha256,r.reference_raw,r.metadata_json FROM alignment a CROSS JOIN source_file f ON f.id=a.file_id CROSS JOIN reference r ON r.id=a.reference_id WHERE a.id IN ('+','.join('?' for _ in page)+') ORDER BY a.id',page)
        return {'rows':rows,'total':len(ids),'offset':offset,'limit':25,'source':self.sources['MIBiG'],'hold':context['hold'],'denominator':context['denominator']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--selection',required=True,type=Path);p.add_argument('--port',type=int,default=8767);p.add_argument('--audit',type=Path)
    a=p.parse_args()
    if a.audit and (a.audit.exists() or a.audit.is_symlink()):p.error('AUDIT_OUTPUT_EXISTS_CHOOSE_ADDITIVE_PATH')
    ex=Explorer(a.selection)
    if a.audit:
        # Five deterministic real cases with distinct available source states.
        chosen=[]
        for predicate in (lambda g:all(x=='VERIFIED_HITS' for x in g['channels'].values()),lambda g:'VERIFIED_NO_HIT' in g['channels'].values(),lambda g:'NO_VERIFIED_SEARCH' in g['channels'].values(),lambda g:'VERIFIED_MIXED_OUTCOMES' in g['channels'].values(),lambda g:True):
            row=next((g for g in ex.genes.values() if predicate(g) and g['id'] not in chosen),None)
            if row:chosen.append(row['id'])
        records=[ex.detail(x) for x in chosen];ex.check_stable(hashes=True)
        a.audit.write_text(json.dumps({'summary':ex.summary,'five_records':records,'selected_ids':chosen,'status':'SOURCE_BOUND_ENGINEERING_REVIEW_ONLY'},indent=2));ex.close();return
    html=Path(__file__).with_name('evidence_disagreements.html').read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # Local-only; refuse cross-origin browser access and DNS rebinding.
            if self.headers.get('Host') not in (f'127.0.0.1:{a.port}',f'localhost:{a.port}'):
                self.send_error(403);return
            try:
                u=urlparse(self.path);q={k:v[0] for k,v in parse_qs(u.query).items()}
                ex.check_stable()
                if u.path=='/':body=html;kind='text/html; charset=utf-8'
                else:
                    if u.path=='/api/summary':out=ex.summary
                    elif u.path=='/api/search':out=ex.search(q.get('q',''),q.get('strain',''),q.get('state',''),max(0,int(q.get('offset',0))))
                    elif u.path=='/api/gene':out=ex.detail(q['id'])
                    elif u.path=='/api/hits':out=ex.hits(q['id'],q['channel'],int(q['search']),max(0,int(q.get('offset',0))))
                    elif u.path=='/api/references':out=ex.references(q['id'],max(0,int(q.get('offset',0))))
                    else:self.send_error(404);return
                    body=json.dumps(out,allow_nan=False).encode();kind='application/json'
                self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'");self.end_headers();self.wfile.write(body)
            except (ValueError,KeyError,sqlite3.Error) as e:
                self.send_response(422);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps({'hold':str(e)}).encode())
        def log_message(self,*args):pass
    try:
        server=HTTPServer(('127.0.0.1',a.port),Handler)
        print(f'Private local explorer: http://127.0.0.1:{a.port}',flush=True)
        server.serve_forever()
    finally:ex.close()

if __name__=='__main__':main()
