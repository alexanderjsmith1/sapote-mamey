"""Candidate adapter: selected database packet -> partial governed section document.

Uses the existing Sapote Markdown model. Never emits a full-card readiness claim.
No database reader, discovery, scoring or biological interpretation lives here.
"""
import collections,hashlib,html,json,re
from .sapote_markdown import parse_text,validate_model

PROFILE='1a27a5070b062bfe671721790f4e56c82028ff4fbd74d53478b932fec8a466a7'
SECTIONS={4:'Gene overview',7:'Transport, resistance and regulation evidence',27:'Self-resistance evidence and holds',31:'Source census',38:'Efflux and transporter evidence',42:'Mobile-context evidence',50:'Complete exact-region gene evidence ledger'}

def validate_packet(packet):
    """Check internal joins in an externally source-verified packet.

    This is not a DB reader or a source authenticator. Provenance declarations
    and row digests are unverified assertions here; caller must verify the packet
    bytes against an independently trusted source-audit receipt before use.
    """
    if packet.get('schema')!='modeb_selected_locus_packet/0.1' or packet.get('profile_sha256')!=PROFILE:raise ValueError('PACKET_PROFILE_MISMATCH')
    identity=packet.get('identity','');parts=identity.split(' / ')
    if len(parts)!=4 or any(not v for v in parts):raise ValueError('COMPLETE_IDENTITY_REQUIRED')
    locus=packet['locus']
    if [locus[k] for k in ['strain','full_node','region','bgc_alias']]!=parts:raise ValueError('LOCUS_IDENTITY_MISMATCH')
    genes=packet['exact_genes'];n=packet['expected_exact_genes']
    if type(n) is not int or n<1 or len(genes)!=n or locus['cds_count']!=n:raise ValueError('EXACT_ROSTER_COUNT_MISMATCH')
    if [x['gene_order'] for x in genes]!=list(range(1,n+1)):raise ValueError('EXACT_ROSTER_ORDER_MISMATCH')
    records=packet['records'];sources=packet['source_releases']
    def record(rid,database=None,tables=None):
        if rid not in records:raise ValueError('UNRESOLVED_PROVENANCE')
        r=records[rid]
        if database is not None and r['database_key']!=database:raise ValueError('RECORD_CHANNEL_OR_TOOL_MISMATCH')
        if tables is not None and r['table'] not in tables:raise ValueError('RECORD_TABLE_MISMATCH')
        if r['database_key'] not in sources:raise ValueError('SOURCE_RELEASE_MISSING')
        if set(r['fields'])!=set(r['field_provenance']):raise ValueError('FIELD_PROVENANCE_COVERAGE_MISMATCH')
        for value in r['field_provenance'].values():
            if value['database_sha256']!=sources[r['database_key']]['database_sha256']:raise ValueError('SOURCE_PIN_MISMATCH')
        return r['fields']
    def equal(row,expected,code):
        if any(key not in row or row[key]!=value for key,value in expected.items()):raise ValueError(code)
    def gene_row(row,g,code):
        equal(row,{k:g[k] for k in ['locus_key','gene_order','locus_tag','protein_sha256']},code)
        if 'membership' in row and row['membership']!='EXACT_REGION':raise ValueError(code)
        for field,canonical in [('cds_start','cds_start'),('start','cds_start'),('cds_end','cds_end'),('end','cds_end'),('strand','strand'),('protein_length','protein_length')]:
            if field in row and row[field]!=g[canonical]:raise ValueError(code)
    tool_tables={'antismash_gbk_domains':'gene','mamey_regulator_keywords':'gene','mamey_transporters_keywords':'gene','mamey_resistance_keywords':'gene','mamey_chitinase_keywords':'gene','tta_source_codon_counts':'gene','mamey_cassette_coupling':'gene','mamey_resistance_tiers':'context_gene','CCTT_EXISTING':'gene','UMED_EXISTING':'gene'}
    exact_tags=set()
    for gene in genes:
        if gene['identity']!=identity or gene['membership']!='EXACT_REGION':raise ValueError('GENE_SCOPE_MISMATCH')
        g=record(gene['census'],'antismash_gene_census',{'gene'})
        equal(g,{'gene_order':gene['gene_order'],'locus_tag':gene['locus_tag'],'locus_key':locus['locus_key'],'membership':'EXACT_REGION'},'GENE_CENSUS_MISMATCH')
        if g['locus_tag'] in exact_tags:raise ValueError('DUPLICATE_EXACT_GENE')
        exact_tags.add(g['locus_tag']);query=g['protein_sha256']
        for key in ['blastp_nr','blastp_clustered_nr','blastp_swissprot']:
            channel=gene['channels'][key];binding=record(channel['binding'],key,{'binding'});protein=record(channel['protein'],key,{'protein'})
            equal(binding,{'query_sha256':query,'exact_identity':identity,'gene_order':gene['gene_order'],'locus_key':locus['locus_key'],'locus_tag':g['locus_tag'],'strain':parts[0],'full_node':parts[1],'region':parts[2],'bgc_alias':parts[3]},'CHANNEL_QUERY_BINDING_MISMATCH')
            equal(protein,{'query_sha256':query},'PROTEIN_QUERY_BINDING_MISMATCH')
            length_key='aa_length' if key=='blastp_swissprot' else 'protein_length'
            equal(protein,{length_key:g['protein_length']},'PROTEIN_LENGTH_MISMATCH')
            if channel['state'] not in {'VERIFIED_HITS','VERIFIED_NO_HIT','VERIFIED_MIXED_OUTCOMES','NO_VERIFIED_SEARCH'} or protein.get('state',protein.get('availability_state'))!=channel['state']:raise ValueError('CHANNEL_STATE_MISMATCH')
            receipts=[(records[rid]['table'] if rid in records else None,record(rid,key,{'outcome'} if key=='blastp_swissprot' else {'search','source_xml'})) for rid in channel['search_receipts']]
            if key=='blastp_swissprot':
                for _,outcome in receipts:
                    equal(outcome,{'query_sha256':query},'SEARCH_QUERY_BINDING_MISMATCH')
                    count=outcome.get('hit_count')
                    if type(count) is not int or count<0:raise ValueError('OUTCOME_HIT_COUNT_INVALID')
                    expected='HITS_UNDER_RECORDED_SETTINGS' if count else 'NO_HIT_UNDER_RECORDED_SETTINGS_NOT_BIOLOGICAL_ABSENCE'
                    equal(outcome,{'observation':expected},'OUTCOME_OBSERVATION_CONTRADICTION')
                # The explicit source _query_key row is required for hit-pack IDs.
                qref=channel.get('query_key')
                qrow=record(qref,key,{'_query_key'}) if qref is not None else None
                if qrow is not None:equal(qrow,{'query_sha256':query},'HIT_QUERY_KEY_MISMATCH')
                for rid in channel['selected_hits']:
                    hit=record(rid,key,{'_hit_pack'})
                    if qrow is None:raise ValueError('HIT_QUERY_KEY_REQUIRED')
                    equal(hit,{'query_id':qrow['id']},'HIT_SEARCH_BINDING_MISMATCH')
                    if not any(row.get('hit_count',0)>0 for _,row in receipts):raise ValueError('HIT_OUTCOME_BINDING_MISMATCH')
            else:
                searches={};xmls={}
                for table,row in receipts:
                    target=searches if table=='search' else xmls
                    if row['id'] in target and target[row['id']]!=row:raise ValueError('DUPLICATE_SEARCH_RECEIPT_CONFLICT')
                    target[row['id']]=row
                    if table=='search':equal(row,{'query_sha256':query},'SEARCH_QUERY_BINDING_MISMATCH')
                    else:equal(row,{'channel':'ncbi_nr' if key=='blastp_nr' else 'ncbi_clustered_nr'},'SOURCE_XML_CHANNEL_MISMATCH')
                if set(xmls)!={row['xml_id'] for row in searches.values()}:raise ValueError('SEARCH_XML_BINDING_MISMATCH')
                selected_searches=set()
                for rid in channel['selected_hits']:
                    hit=record(rid,key,{'hit'})
                    if hit.get('search_id') not in searches:raise ValueError('HIT_SEARCH_BINDING_MISMATCH')
                    if searches[hit['search_id']].get('observation')!='HITS_UNDER_RECORDED_SETTINGS':raise ValueError('HIT_SEARCH_OBSERVATION_CONTRADICTION')
                    selected_searches.add(hit['search_id'])
                if selected_searches!={sid for sid,row in searches.items() if row.get('observation')=='HITS_UNDER_RECORDED_SETTINGS'}:raise ValueError('HIT_SEARCH_REPRESENTATIVE_REQUIRED')
            if channel['state']=='NO_VERIFIED_SEARCH' and (receipts or channel['selected_hits']):raise ValueError('CHANNEL_SEARCH_STATE_MISMATCH')
            if channel['state']!='NO_VERIFIED_SEARCH' and not receipts:raise ValueError('CHANNEL_SEARCH_RECEIPT_REQUIRED')
            observations={row.get('observation') for table,row in receipts if table in {'search','outcome'}}
            hit_observation='HITS_UNDER_RECORDED_SETTINGS';nohit_observation='NO_HIT_UNDER_RECORDED_SETTINGS_NOT_BIOLOGICAL_ABSENCE'
            states={frozenset():'NO_VERIFIED_SEARCH',frozenset({hit_observation}):'VERIFIED_HITS',frozenset({nohit_observation}):'VERIFIED_NO_HIT',frozenset({hit_observation,nohit_observation}):'VERIFIED_MIXED_OUTCOMES'}
            expected_state=states.get(frozenset(observations))
            if expected_state is None:raise ValueError('UNSUPPORTED_SEARCH_OBSERVATION')
            if channel['state']!=expected_state:raise ValueError('CHANNEL_HISTORY_STATE_MISMATCH')
            if (hit_observation in observations)!=bool(channel['selected_hits']):raise ValueError('CHANNEL_HIT_STATE_MISMATCH')
        for key,refs in gene['tools'].items():
            if key not in tool_tables:raise ValueError('UNSUPPORTED_GENE_TOOL')
            for rid in refs if isinstance(refs,list) else [refs]:gene_row(record(rid,key,{tool_tables[key]}),g,'TOOL_GENE_BINDING_MISMATCH')
    context_tables={'mamey_cassette_coupling':'gene','mamey_resistance_tiers':'context_gene','CCTT_EXISTING':'gene','UMED_EXISTING':'gene'}
    context_tags=set()
    for context in packet['context_genes']:
        if context['identity']!=identity or context['membership']!='BOUNDARY_CONTEXT':raise ValueError('CONTEXT_SCOPE_MISMATCH')
        if context['locus_tag'] in exact_tags|context_tags:raise ValueError('CONTEXT_GENE_OVERLAP')
        context_tags.add(context['locus_tag'])
        if not context['sources']:raise ValueError('CONTEXT_PROVENANCE_REQUIRED')
        for rid in context['sources']:
            row=record(rid);key=records[rid]['database_key']
            if key not in context_tables or records[rid]['table']!=context_tables[key]:raise ValueError('CONTEXT_SOURCE_TYPE_MISMATCH')
            equal(row,{'locus_key':locus['locus_key'],'locus_tag':context['locus_tag'],'protein_sha256':context['protein_sha256'],'gene_order':None,'strand':context['strand']},'CONTEXT_GENE_BINDING_MISMATCH')
            if row.get('membership') not in {'BOUNDARY_CONTEXT','BOUNDARY_CONTEXT_10KB'}:raise ValueError('CONTEXT_SOURCE_MEMBERSHIP_MISMATCH')
            start='cds_start' if 'cds_start' in row else 'start';end='cds_end' if 'cds_end' in row else 'end'
            equal(row,{start:context['start'],end:context['end']},'CONTEXT_GEOMETRY_MISMATCH')
    return packet

def render_packet_sections(packet,*,packet_locator,manifest_locator):
    validate_packet(packet);identity=packet['identity'];records=packet['records']
    def fields(rid):return records[rid]['fields']
    def clean(x):return str(x if x is not None else 'not reported').replace('|','¦').replace('\n',' ').replace('<','‹').replace('>','›')
    def table(tid,heads,rows):
        rows=list(rows)
        if not rows:return 'No rows in this bounded source selection; not biological absence.\n'
        return '<!-- sapote:table id="'+tid+'" layout="'+('landscape' if len(heads)>6 else 'auto')+'" -->\n|'+'|'.join(heads)+'|\n|'+'|'.join('---' for _ in heads)+'|\n'+'\n'.join('|'+'|'.join(clean(x) for x in row)+'|' for row in rows)+'\n'
    def citation(rid):return 'record:'+rid
    def qualifier(g):return fields(g['tools']['antismash_gbk_domains']).get('source_qualifiers_zlib',{})
    genes=packet['exact_genes'];n=len(genes);locus=packet['locus']
    kinds=collections.Counter(tuple(qualifier(g).get('gene_kind',[])) or ('UNANNOTATED',) for g in genes)
    feature_rows=[fields(x['feature']) for x in packet['features']];feature_counts=collections.Counter(x['feature_type'] for x in feature_rows)
    modules=[x for x in feature_rows if x['feature_type']=='aSModule'];module_genes=sorted({tag for x in modules for tag in json.loads(x['explicit_gene_tags_json'])})
    sections={}
    sections[4]=f'The frozen source region spans {locus["region_start_1based"]:,}–{locus["region_end_1based"]:,} on the full contig ({locus["region_nt"]:,} nt). It contains {n} exact-region CDS. Source product labels are {locus["products_json"]}; these labels do not establish one coherent pathway or a produced compound.\n\n'+table('gene-kinds',['antiSMASH gene_kind','Exact-region genes'],[(', '.join(k),v) for k,v in sorted(kinds.items())])+f'All {n} exact genes appear in §50. {len(packet["context_genes"])} distinct context CDS from the retained source-defined windows are listed separately. Conditional pathway order, functional review and core-versus-neighbor adjudication remain holds.\n'
    keyword_keys={'regulator':'mamey_regulator_keywords','transporter':'mamey_transporters_keywords','resistance':'mamey_resistance_keywords'}
    def matches(key):return [(g,fields(g['tools'][key]),g['tools'][key]) for g in genes if json.loads(fields(g['tools'][key]).get('groups_json','[]'))]
    counts={label:len(matches(key)) for label,key in keyword_keys.items()}
    sections[7]=f'Exact-region annotation-pattern matches: {counts["regulator"]} regulator, {counts["transporter"]} transporter and {counts["resistance"]} resistance-keyword rows. These are overlapping evidence categories, not validated functions. Regulatory targets, transport direction and substrate specificity are not supplied by these counts.\n\n'+table('regulator-evidence',['Exact locus / gene','Source groups','Preserved state','Provenance'],[(identity+' / '+g['locus_tag'],r['groups_json'],r['state'],citation(ref)) for g,r,ref in matches(keyword_keys['regulator'])])
    tierids=[rid for rid in packet['tool_records']['mamey_resistance_tiers'] if records[rid]['table']=='tier'];tier=fields(tierids[0]) if tierids else {};owner=json.loads(tier.get('owner_json','{}'))
    sections[27]='The saved algorithm reports '+clean(owner.get('tier','NOT_AVAILABLE'))+' with confidence '+clean(owner.get('confidence','NOT_REPORTED'))+'. Its retained rationale is: '+clean(owner.get('rationale','not supplied'))+'.\n\nSelf-resistance is unresolved: the packet contains no focal resistance phenotype, target-protection assay, or demonstrated coupling to a produced metabolite. The source routing tier is not promoted to mechanism.\n\n'+table('resistance-tier',['Source field','Retained value'],[(k,v) for k,v in owner.items()])+('Provenance: '+citation(tierids[0])+'.\n' if tierids else '')
    sections[31]=table('census',['Object counted','Count','Counting rule'],[('Exact-region CDS',n,'Census gene rows; all included'),('PFAM_domain feature instances',feature_counts['PFAM_domain'],'Source feature_type, no deduplication with aSDomain'),('aSDomain feature instances',feature_counts['aSDomain'],'Source feature_type'),('aSModule objects',len(modules),'Source module feature rows'),('Module-bearing proteins',len(module_genes),'Distinct explicitly bound gene tags on module records'),('Source modules carrying complete flag',sum('complete' in x['source_qualifiers_zlib'] for x in modules),'Source qualifier presence, not independent functional completeness'),('Source context CDS',len(packet['context_genes']),f'Union of source-defined windows; excluded from exact {n} denominator')])+ 'Domain instances, module objects and module-bearing proteins are separate counts. The module-bearing gene tags are '+', '.join(module_genes)+'. No domain/module list is inferred from a keyword count.\n'
    sections[38]='Transporter annotations prioritize review of export/import hypotheses. They do not establish efflux, drug substrate, resistance or an operon. The full retained matching groups are below.\n\n'+table('transporter-evidence',['Exact locus / gene','Groups','Preserved state','Provenance'],[(identity+' / '+g['locus_tag'],r['groups_json'],r['state'],citation(ref)) for g,r,ref in matches(keyword_keys['transporter'])])
    mobile=[]
    for g in genes:
        for rid in g['tools'].get('mamey_resistance_tiers',[]):
            r=fields(rid);groups=json.loads(r.get('groups_json','{}'))
            if groups.get('mobile'):mobile.append((identity+' / '+g['locus_tag'],groups['mobile'],r['state'],citation(rid)))
    sections[42]='Saved mobile-context guard: '+clean(owner.get('hgt_guard','NOT_REPORTED'))+'. This is the algorithm’s bounded annotation-pattern result, not proof that transfer did not occur. Genomic composition baseline, evolutionary comparison and nucleotide-level transfer tests are not in this packet.\n\n'+table('mobile-evidence',['Exact locus / gene','Mobile groups','State','Provenance'],mobile)
    bytag=collections.defaultdict(list)
    for row in feature_rows:
        if row['feature_type']=='aSModule':continue
        q=row['source_qualifiers_zlib'];label=', '.join(q.get('aSDomain',q.get('description',[])))
        for tag in json.loads(row['explicit_gene_tags_json']):bytag[tag].append(label)
    def channel_text(channel):
        out=channel['state']
        if not channel['selected_hits']:return out+'; no named hit selected. A missing verified search is not a no-hit result.'
        rid=channel['selected_hits'][0];r=fields(rid);ev=r.get('all_evidence_zlib',r.get('selected_hit',{}));desc=ev.get('descriptions',[{}])[0];hsp=ev.get('hsps',[{}])[0]
        title=r.get('title') or desc.get('title','not retained');acc=r.get('accession') or desc.get('accession','not retained');cols=hsp.get('alignment_columns');ident=hsp.get('identity_count');positive=hsp.get('positive_count')
        metric=f'identity {ident}/{cols}; positives {positive}/{cols}; query-union coverage {ev.get("query_union_coverage_pct","NR")}; first-HSP qcov {hsp.get("query_coverage_pct","NR")}; evalue {hsp.get("evalue","NR")}'
        return out+'; '+str(acc)+' — '+title+'; '+metric+f'; displayed 1 of {len(channel["selected_hits"])} source-search representatives; '+citation(rid)
    ledger=[]
    for g in genes:
        c=fields(g['census']);q=qualifier(g);annotation='gene_kind='+','.join(q.get('gene_kind',[]))+'; '+ '; '.join(q.get('gene_functions',q.get('product',[])))+'; domains='+', '.join(bytag[g['locus_tag']])
        states='; '.join(label+': '+fields(g['tools'][key])['groups_json'] for label,key in keyword_keys.items())
        ledger.append([identity+' / '+g['locus_tag'],f'{c["cds_start"]}–{c["cds_end"]}; strand {c["strand"]}; {c["protein_length"]} aa; SHA256 {c["protein_sha256"]}',annotation,*[channel_text(g['channels'][k]) for k in ['blastp_nr','blastp_clustered_nr','blastp_swissprot']],states,citation(g['census'])])
    sections[50]=f'Exactly {n} exact-region rows, ordered by the bound census. Subject titles remain subject descriptions. Each channel displays the first retained source-search representative; all per-search representatives and receipt rows selected into this packet remain inspectable through provenance. No raw coverage is capped.\n\n'+table('exact-gene-ledger',['Exact locus / gene','Geometry and sequence binding','Source annotation and domains','NCBI nr','ClusteredNR','Local Swiss-Prot','Annotation-pattern groups','Census provenance'],ledger)+'\n### Separate boundary-context rows\n\n'+table('context-ledger',['Exact locus / context gene','Geometry','Protein SHA256','Source rows'],[(identity+' / '+x['locus_tag'],f'{x["start"]}–{x["end"]}; strand {x["strand"]}',x['protein_sha256'],'; '.join(citation(r) for r in x['sources'])) for x in packet['context_genes']])
    front={'schema_version':'sapote-markdown-1.0','document_type':'analysis_report','title':'Database-backed section prototype — '+identity,'subtitle':'Partial section prototype; not a complete Mode B card','audience':'Scientific owner review','authority':'Source-bound prototype; no scientific acceptance','render_profile':'scientific_report','claim_safety_footer':'Source-bound observations only. No product, activity, self-resistance or scientific acceptance claim.','exact_locus':dict(zip(['strain','node_or_contig','region','bgc_alias'],identity.split(' / '))),'source_manifest':manifest_locator}
    # JSON is a YAML subset accepted by the existing governed parser.
    out=['---',json.dumps(front,ensure_ascii=False),'---','# '+front['title'],'','> [HOLD] Partial section prototype','> Only §4, §7, §27, §31, §38, §42 and §50 are populated as evidence-bearing prototypes. Scientific interpretation remains held.','',f'Evidence packet: {packet_locator}. Frozen source manifest: {manifest_locator}.','', '## Current 50-section profile coverage','']
    req={}
    for refs in packet['section_source_records'].values():
        for ref in refs:
            row=fields(ref)
            if row.get('profile_sha256')==PROFILE:
                number=row.get('section_number',row.get('section',row.get('number')))
                if isinstance(number,int):req.setdefault(number,row.get('requirement',''))
    out.append(table('profile-coverage',['Section','Current requirement','Prototype disposition'],[(i,req.get(i,'Requirement binding unavailable'), 'SOURCE-BOUND PARTIAL PROTOTYPE; scientific adjudication held' if i in SECTIONS else 'NOT AUTHORED; relevant inputs may exist, but functional/citation review not performed') for i in range(1,51)]))
    for num,title in SECTIONS.items():out.extend(['## §'+str(num)+' '+title,'',sections[num],''])
    out.extend(['## Interface and remaining holds','', 'The current50 contract is preserved as coverage metadata. The legacy document mode_b_card validator requires48 headings, so this partial prototype deliberately uses the existing analysis_report schema. It does not claim a full-card structure or publication pass.','', 'Reference comparisons retain raw values and metric holds in the packet. RG-GMCI and BiG-SCAPE source rows are context only; no physical join, phylogeny or gene-specific family inference is made.','', 'External domain-prevalence snapshots require independent selection and host-provenance reconciliation before comparison with the governed cohort.',''])
    return '\n'.join(out)

def render_model_html(model):
    """Basic preview of the existing canonical block model, with full cell contents."""
    validate_model(model).raise_for_errors();escape=lambda x:html.escape(str(x))
    blocks=[]
    for block in model.blocks:
        d=block.data
        if block.kind=='heading':blocks.append(f'<h{d["level"]}>{escape(d["text"])}</h{d["level"]}>')
        elif block.kind=='paragraph':blocks.append('<p>'+escape(d['text'])+'</p>')
        elif block.kind=='callout':blocks.append('<aside><strong>'+escape(d['title'])+'</strong><p>'+escape(d['text'])+'</p></aside>')
        elif block.kind=='table':
            rows=d['rows'];content='<thead><tr>'+''.join('<th>'+escape(x)+'</th>' for x in rows[0])+'</tr></thead><tbody>'
            for row in rows[1:]:content+='<tr>'+''.join('<td>'+escape(x)+'</td>' for x in row)+'</tr>'
            blocks.append('<div class="table-scroll"><table id="'+escape(d['id'])+'">'+content+'</tbody></table></div>')
        elif block.kind=='list':blocks.append('<ul>'+''.join('<li>'+escape(x)+'</li>' for x in d['items'])+'</ul>')
        elif block.kind=='rule':blocks.append('<hr>')
        else:raise ValueError('UNSUPPORTED_PREVIEW_BLOCK:'+block.kind)
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(model.meta.title)+'</title><style>body{font:16px/1.55 system-ui;color:#18384b;background:#faf9f5;margin:32px auto;max-width:1500px;padding:0 24px}h1{font-size:27px;overflow-wrap:anywhere}h2{padding-top:20px;color:#075f6e}aside{background:#fff0ca;border-left:5px solid #b78126;padding:15px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px;vertical-align:top;text-align:left;border:1px solid #ced8d9;overflow-wrap:anywhere}th{background:#dbecee;position:sticky;top:0}tr:nth-child(even){background:#f0f4f3}.table-scroll{overflow-x:auto;margin:20px 0}#exact-gene-ledger{min-width:1800px;table-layout:fixed}#exact-gene-ledger td{font-size:12px}p{max-width:1100px}footer{padding:30px;background:#e4efee}</style>'+''.join(blocks)+'<footer>'+escape(model.meta.claim_safety_footer)+'</footer></html>'
