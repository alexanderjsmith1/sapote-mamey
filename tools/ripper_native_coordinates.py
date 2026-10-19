"""Native retained-artifact coordinate evaluation; no merged-evidence relabelling."""
import hashlib,io,json,math,re,sqlite3,sys
from pathlib import Path
from contextlib import closing

SOURCE_SHA='0b92227d09bb033074ec70379ef27c4767e2ab30c7e478e76e71c3abc13be0f3'
HEADER='Beg End Std Total CodPot StrtSc Codon RBSMot Spacer RBSScr UpsScr TypeScr GCCont'.split()
ROLES=set('raw faa score window genbank query stage terminal provenance source config reconstruction profile queries sqlite exported_genbank prodigal_stage_started lifecycle_launch'.split())

def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def require(condition,code):
    if not condition:raise ValueError('NATIVE_COORDINATE_'+code)

def fasta_records(text):
    records={};key=None
    for number,line in enumerate(text.splitlines(),1):
        if line.startswith('>'):
            fields=line[1:].split(None,1);require(len(fields)==2,'FASTA_DESCRIPTION_REQUIRED')
            key=fields[0];require(key not in records,'FASTA_DUPLICATE_ID')
            records[key]={'sequence':'','description':fields[1],'line':line,'line_1based':number}
        elif line.strip():
            require(key is not None,'FASTA_HEADER_REQUIRED');records[key]['sequence']+=line.strip()
    return records

def note_fields(description):
    values={}
    for part in description.split(';'):
        require(':' in part,'NOTE_FIELD_INVALID');key,value=(x.strip() for x in part.split(':',1))
        require(key not in values and value,'NOTE_FIELD_DUPLICATE_OR_EMPTY');values[key]=value
    require(set(values)==set(HEADER)|{'SameStrand','ShaHex'},'NOTE_FIELD_ROSTER')
    require(all(re.fullmatch(r'[1-9][0-9]*',values[k]) for k in ('Beg','End')) and values['Std'] in ('1','-1') and values['SameStrand'] in ('0','1'),'NOTE_GEOMETRY_INVALID')
    for key in ('Total','CodPot','StrtSc','RBSScr','UpsScr','TypeScr','GCCont'):
        try:value=float(values[key])
        except ValueError as exc:raise ValueError('NATIVE_COORDINATE_NOTE_NUMBER_INVALID') from exc
        require(math.isfinite(value),'NOTE_NUMBER_INVALID')
    require(values['ShaHex']==hashlib.sha1('_'.join(values[k] for k in ('Beg','End','Std')).encode()).hexdigest(),'GEOMETRY_NOTE_HASH_MISMATCH')
    return values

def score_rows(text):
    result=[];header_seen=False;data_seen=False;model_table=None
    for number,line in enumerate(text.splitlines(),1):
        if not line.strip():continue
        if line.lstrip().startswith('#'):
            table=re.search(r'(?:^|;)transl_table=(\d+)',line)
            if table:model_table=int(table[1])
            continue
        fields=line.split('\t')
        if fields==HEADER:
            require(not header_seen and not data_seen,'SCORE_HEADER_DUPLICATE_OR_MISPLACED');header_seen=True;continue
        require(header_seen and len(fields)==13 and all(re.fullmatch(r'[1-9][0-9]*',x) for x in fields[:2]) and int(fields[1])>=int(fields[0]) and fields[2] in ('+','-'),'SCORE_DIALECT_INVALID')
        for index in (3,4,5,9,10,11,12):
            try:number_value=float(fields[index])
            except ValueError as exc:raise ValueError('NATIVE_COORDINATE_SCORE_NUMBER_INVALID') from exc
            require(math.isfinite(number_value),'SCORE_NUMBER_INVALID')
        result.append(dict(fields=dict(zip(HEADER,fields)),line_1based=number,line_sha256=sha(line.encode()),strand=1 if fields[2]=='+' else -1));data_seen=True
    require(header_seen,'SCORE_HEADER_REQUIRED');return result,model_table

def matching_scores(note,rows,reward,te_strand):
    selected=[];strand=int(note['Std'])
    for row in rows:
        fields=row['fields']
        if (fields['Beg'],fields['End'],row['strand'])!=(note['Beg'],note['End'],strand):continue
        if not math.isclose(float(fields['Total'])+(reward if strand==te_strand else 0),float(note['Total']),rel_tol=0,abs_tol=1e-9):continue
        if any(fields[k]!=note[k] for k in HEADER if k not in ('Std','Total')):continue
        selected.append(row)
    return selected

def translated_interval(dna,strand,codon):
    require(type(strand) is int and strand in (-1,1),'INTEGER_STRAND_REQUIRED')
    require(len(dna)>0 and len(dna)%3==0,'NONTRIPLET_INTERVAL_REFUSED')
    if strand==-1:dna=dna.reverse_complement()
    text=str(dna).upper();require(re.fullmatch('[ACGT]+',text),'UNAMBIGUOUS_INTERVAL_DNA_REQUIRED')
    require(codon=='Edge' or codon==text[:3],'START_CODON_METADATA_MISMATCH')
    unadjusted=str(dna.translate(table=1));translated=unadjusted;transformations=[]
    if translated.endswith('*'):translated=translated[:-1];transformations.append('terminal_stop_removed')
    if translated.startswith(('V','L')):translated='M'+translated[1:];transformations.append('initial_V_or_L_to_M_without_coordinate_shift')
    return text,unadjusted,translated,transformations

def sqlite_rows(raw,table,columns):
    try:
        with closing(sqlite3.connect(':memory:')) as connection:
            connection.deserialize(raw);connection.execute('PRAGMA trusted_schema=OFF');connection.execute('PRAGMA query_only=ON');connection.execute('PRAGMA temp_store=MEMORY')
            schema=connection.execute('SELECT type,sql FROM sqlite_master WHERE name=?',(table,)).fetchall()
            require(len(schema)==1 and schema[0][0]=='table' and isinstance(schema[0][1],str) and 'VIRTUAL' not in schema[0][1].upper(),'SQL_PLAIN_TABLE_REQUIRED')
            require([(x[1],x[2].upper()) for x in connection.execute('PRAGMA table_info("'+table+'")')]==[(x,y.upper()) for x,y in columns],'SQL_COLUMNS_MISMATCH')
            return connection.execute('SELECT '+','.join(k for k,v in columns)+' FROM "'+table+'" ORDER BY acc,ppser LIMIT 10001').fetchall()
    except sqlite3.Error as exc:raise ValueError('NATIVE_COORDINATE_SQLITE_READ_REFUSED') from exc

def native_coordinates(api,packet_path,supplied,out,control_path=None):
    sources=[];packet=api['json_input'](packet_path,sources)
    require(isinstance(packet,dict) and packet.get('schema')=='ripper-native-coordinate-reconstruction/1','PACKET_SCHEMA_INVALID')
    qualifiers={'status':'EXACT_RETAINED_ARTIFACT_RECONSTRUCTION_ONLY','mapping_origin':'derived_from_retained_native_artifacts','native_evidence_kind':'local_adapter_observed_native','upstream_execution':'EXECUTED_NATIVE_LOCAL_ADAPTER_OBSERVED','original_raw_coordinate_provenance':'ABSENT_PRODUCER_MAPPING','producer_authentication':'CONTENT_BINDINGS_ONLY_NOT_AUTHENTICATED_PRODUCER','candidate_membership':'UNVERIFIED','hmm_annotation':'NOT_RUN','biology':'UNASSESSED'}
    require(all(packet.get(k)==v for k,v in qualifiers.items()) and packet.get('instrumented_producer_sidecar') is False,'PACKET_QUALIFICATION_PROMOTION')
    bindings=packet.get('bindings');require(isinstance(bindings,dict) and set(bindings)==ROLES,'EXPLICIT_BINDING_ROSTER_REQUIRED')
    require(all(isinstance(x,dict) and set(x)=={'path','bytes','sha256'} and isinstance(x['path'],str) and type(x['bytes']) is int and isinstance(x['sha256'],str) for x in bindings.values()),'BINDING_SHAPE_INVALID')
    bound=api['owned_module']('ripper_run_binding').files(api,{k:v['sha256'] for k,v in bindings.items()},supplied,sources)
    require(bound==bindings,'EXPLICIT_FILE_BINDING_MISMATCH')
    payload={role:api['load_bytes'](entry['path']) for role,entry in bound.items()}
    require(all(api['binding'](bound[k]['path'],raw)==bound[k] for k,raw in payload.items()),'INPUT_GENERATION_CHANGED')
    inspection=api['owned_module']('ripper_native_result').native_result(api,bound['terminal']['path'],bound['raw']['path'],None,control_path)
    for entry in inspection['sources']:
        if entry not in sources:sources.append(entry)
    require(inspection['terminal_status']=='SUCCESS_UNBOUND','RETAINED_NATIVE_CANDIDATES_REQUIRED')
    terminal=json.loads(payload['terminal']);raw=json.loads(payload['raw']);rows=packet.get('rows');count=raw['candidate_count']
    require(type(packet.get('candidate_count')) is int and packet['candidate_count']==count and isinstance(rows,list) and len(rows)==count,'EXACT_CANDIDATE_DENOMINATOR_REQUIRED')
    require(isinstance(terminal.get('files'),dict) and isinstance(terminal.get('adaptation'),dict) and isinstance(terminal.get('retained_outputs'),dict),'TERMINAL_BINDING_OBJECTS_REQUIRED')
    for key in ('genbank','query_fasta','upstream_source','config','queries','prodigal_short'):
        entry=terminal['files'].get(key);require(isinstance(entry,dict) and all(k in entry for k in ('path','bytes','sha256')),'TERMINAL_FILE_ROLE_REQUIRED_'+key)
    require(all(isinstance(v,dict) and all(k in v for k in ('path','bytes','sha256')) for v in terminal['retained_outputs'].values()),'TERMINAL_OUTPUT_BINDING_SHAPE')
    require(bound['source']['sha256']==SOURCE_SHA,'SOURCE_POLICY_UNREVIEWED')
    for role,key in {'genbank':'genbank','query':'query_fasta','source':'upstream_source','config':'config','queries':'queries'}.items():
        require(bound[role]=={k:terminal['files'][key][k] for k in ('path','bytes','sha256')},'TERMINAL_INPUT_BINDING_MISMATCH_'+role)
    require(bound['profile']['sha256']==terminal['adaptation'].get('artifact_sha256'),'NATIVE_PROFILE_MISMATCH')
    retained={v['path']:v for v in terminal['retained_outputs'].values()}
    for role in ('raw','faa','score','window','stage','sqlite','exported_genbank','prodigal_stage_started'):
        require(retained.get(bound[role]['path'])==bound[role],'RETAINED_OUTPUT_BINDING_MISMATCH_'+role)
    launch=json.loads(payload['lifecycle_launch']);require(isinstance(launch,dict) and launch.get('pid')==terminal.get('pid') and launch.get('argv')==terminal.get('argv') and launch.get('upstream_execution')==terminal['upstream_execution'],'LAUNCH_CONTEXT_MISMATCH')
    stage=json.loads(payload['stage']);started=json.loads(payload['prodigal_stage_started'])
    require(isinstance(stage,dict) and isinstance(started,dict) and stage.get('stage')=='prodigal-short' and type(stage.get('raw_status')) is int and stage['raw_status']==0 and stage.get('state')=='EXIT_ZERO_OUTPUT_OBSERVED_UNVERIFIED','PRODIGAL_STAGE_REQUIRED')
    require(all(started.get(k)==stage.get(k) for k in ('schema','stage','argv','stdout','stderr','contract','validation_scope')) and started.get('state')=='STARTED','PAIRED_STAGE_MISMATCH')
    require(stage.get('argv')==[terminal['files']['prodigal_short']['path'],'-p','meta','-f','gff','-i',bound['window']['path'],'-s',bound['score']['path']] and stage.get('contract')=={'kind':'prodigal_scores','path':bound['score']['path']} and stage.get('outputs')==[bound['score']],'STAGE_INPUT_OUTPUT_MISMATCH')
    require(packet.get('source_stage')=={'stage':'prodigal-short','terminal_sha256':bound['stage']['sha256'],'score_sha256':bound['score']['sha256'],'window_sha256':bound['window']['sha256']},'SOURCE_STAGE_PACKET_MISMATCH')
    table=terminal['native_contract'].get('table');require(isinstance(table,str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',table),'SQL_TABLE_INVALID')
    require(hasattr(sqlite3.Connection,'deserialize'),'SQLITE_SNAPSHOT_DEPENDENCY_REQUIRED')
    columns=api['owned_module']('ripper_raw_discovery').COLUMNS
    sqlrows=sqlite_rows(payload['sqlite'],table,columns)
    require(len(sqlrows)==count,'SQL_ROW_DENOMINATOR_MISMATCH');sqlmap={row[3]:dict(zip((k for k,v in columns),row)) for row in sqlrows};require(len(sqlmap)==count,'SQL_IDENTITY_DUPLICATE')
    candidates={c['peptide_id']:c for c in raw['candidates']};require(all(sqlmap.get(k)==v['source_fields'] for k,v in candidates.items()),'RAW_SQL_ROW_MISMATCH')
    context=api['queries_input'](bound['queries']['path'],sources);require(len(context)==1 and packet.get('declared_query_context')==context[0],'QUERY_CONTEXT_MISMATCH')
    semantic=api['validate_local_semantics'](payload['genbank'].decode(),payload['query'].decode(),context[0]);coords=api['owned_module']('ripper_coordinate_binding')
    if semantic.get('status')=='HOLD_DEPENDENCY_UNAVAILABLE':raise ValueError('NATIVE_COORDINATE_RICH_PARSER_DEPENDENCY_REQUIRED')
    require(semantic.get('status')=='PASS_INPUT_BINDING_ONLY' and semantic.get('query_relation')=='EXACT_SEQUENCE_SELF_MATCH_ONLY','SEMANTIC_INPUT_BINDING_REQUIRED')
    try:reader=coords.rich_coordinate_reader()
    except (RuntimeError,OSError) as exc:raise ValueError('NATIVE_COORDINATE_RICH_PARSER_DEPENDENCY_REQUIRED') from exc
    record=reader.read(io.StringIO(payload['genbank'].decode()),'genbank');source_nt=str(record.seq).upper();source_nt_sha=sha(source_nt.encode());subject=semantic['selected_subject_cds'];subject_sha=coords.subject_digest(bound['genbank']['sha256'],record.id,subject)
    header_fields={}
    for line in payload['genbank'].decode().splitlines():
        if line.startswith(('LOCUS ','ACCESSION ','VERSION ')):header_fields[line.split()[0]]=line.split()[1]
    require(packet.get('source_record')=={'biopython_id':record.id,'header_fields':header_fields,'source_genbank_sha256':bound['genbank']['sha256'],'length':len(record),'uppercase_nt_sha256':source_nt_sha},'ORIGINAL_RECORD_IDENTITY_MISMATCH')
    require(packet.get('selected_subject_cds')==subject and packet.get('selected_subject_cds_sha256')==subject_sha and packet.get('query_relation')==semantic['query_relation'],'SELECTED_SUBJECT_CDS_MISMATCH')
    window_lines=payload['window'].decode().splitlines();require(window_lines and window_lines[0].startswith('>') and sum(x.startswith('>') for x in window_lines)==1,'SINGLE_WINDOW_REQUIRED')
    parts=window_lines[0][1:].strip().rsplit(None,2);require(len(parts)==3 and parts[0]==bound['genbank']['path'] and all(re.fullmatch(r'[1-9][0-9]*',x) for x in parts[1:]),'WINDOW_SOURCE_HEADER_MISMATCH')
    ws,we=map(int,parts[1:]);window_nt=''.join(window_lines[1:]).upper();require(1<=ws<=we<=len(record) and source_nt[ws-1:we]==window_nt and re.fullmatch('[ACGT]+',window_nt),'WINDOW_ORIGIN_SEQUENCE_MISMATCH')
    window={'status':'BOUND_HEADER_INTERVAL_AND_SEQUENCE_CONSISTENT','start_1based':ws,'end_inclusive':we,'source_orientation':1,'window_nt_sha256':sha(window_nt.encode()),'origin_authentication':'RETAINED_DECLARATION_ONLY_NOT_INSTRUMENTED_PRODUCER'};require(packet.get('window')==window,'WINDOW_PACKET_MISMATCH')
    fasta=fasta_records(payload['faa'].decode());require(set(fasta)==set(candidates),'RAW_FASTA_ROSTER_MISMATCH');scores,model_table=score_rows(payload['score'].decode());conf={}
    for line in payload['config'].decode().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key,value=line.split(None,1);require(key not in conf,'CONFIG_DUPLICATE');conf[key]=value
    reward=float(conf.get('sameStrandReward','5'));require(math.isfinite(reward),'FINITE_REWARD_REQUIRED')
    require(packet.get('translation')=={'candidate_table':1,'selected_CDS_declared_table':subject['translation_table'],'prodigal_model_table_declared':model_table,'complete_ORF_claim':'NOT_MADE'},'TRANSLATION_POLICY_MISMATCH')
    seen=set();assessments=[]
    for row in rows:
        require(isinstance(row,dict),'ROW_OBJECT_REQUIRED');identifier=row.get('FastaID');require(isinstance(identifier,str) and identifier in candidates and identifier not in seen,'CANONICAL_ROW_IDENTITY_DUPLICATE_OR_UNKNOWN');seen.add(identifier);c=candidates[identifier];fields=c['source_fields'];seq=c['sequence'];fasta_row=fasta[identifier]
        require(row.get('enzyme_accession')==c['enzyme_accession'] and row.get('PPSerial')==str(fields['ppser']) and row.get('sequence_sha256')==sha(seq.encode()) and row.get('raw_sqlite_row_content_sha256')==digest(fields),'CANONICAL_ROW_HASH_MISMATCH')
        require(row.get('candidate_membership')=='UNVERIFIED' and row.get('producer_mapping')=='ABSENT_DIRECT_INSTRUMENTED_OUTPUT' and row.get('mapping_origin')=='RETAINED_ARTIFACT_RECONSTRUCTION' and row.get('qualification')=='COORDINATE_AND_SEQUENCE_CONSISTENCY_ONLY' and row.get('complete_ORF_claim')=='NOT_MADE' and row.get('nucleotide_interval_adjustment')=='NONE','ROW_QUALIFICATION_PROMOTION')
        require(row.get('status')=='EXACT_ROW_INTERVAL_TRANSLATION_RECONSTRUCTED' and row.get('source_record_id')==record.id and row.get('source_genbank_sha256')==bound['genbank']['sha256'] and row.get('source_record_nt_sha256')==source_nt_sha and row.get('selected_subject_cds_sha256')==subject_sha and row.get('window_origin')==window,'ROW_SOURCE_CONTEXT_MISMATCH')
        require(fasta_row['sequence']==seq and row.get('fasta_header_binding')=={'line_1based':fasta_row['line_1based'],'header_line_sha256':sha(fasta_row['line'].encode()),'digest_convention':'UTF8 completeheaderincluding >, withoutnewline','fasta_file_sha256':bound['faa']['sha256']},'FASTA_HEADER_SEQUENCE_BINDING_MISMATCH')
        note=note_fields(fasta_row['description']);beg,end,strand=int(note['Beg']),int(note['End']),int(note['Std']);require(type(fields['ppstrand']) is int and type(fields['testrand']) is int and fields['ppstrand']==strand and fields['testrand'] in (-1,1) and note['SameStrand']==str(int(strand==fields['testrand'])),'ROW_STRAND_MISMATCH')
        require(type(fields.get('score')) in (int,float) and math.isfinite(fields['score']),'RAW_SCORE_NUMBER_INVALID')
        require(math.isclose(float(fields['score']),float(note['Total']),rel_tol=0,abs_tol=1e-9) and row.get('same_strand_reward')==reward and row.get('score_numeric_absolute_tolerance')==1e-9,'ROW_SCORE_POLICY_MISMATCH')
        matches=matching_scores(note,scores,reward,fields['testrand']);require(len(matches)==1,'SCORE_ROW_NOT_UNIQUE');selected=matches[0]
        require(row.get('score_row')=={k:selected[k] for k in ('line_1based','line_sha256')} and row.get('score_file_sha256')==bound['score']['sha256'],'SCORE_ROW_CONTENT_BINDING_MISMATCH')
        require(1<=beg<=end<=len(window_nt),'LOCAL_INTERVAL_OUT_OF_RANGE');start,end0=ws+beg-2,ws+end-1
        require(isinstance(row.get('local_interval'),dict) and isinstance(row.get('original_interval'),dict) and all(type(row['local_interval'].get(k)) is int for k in ('start_1based','end_inclusive')) and all(type(row['original_interval'].get(k)) is int for k in ('start_0based','end_exclusive','strand')),'INTEGER_GEOMETRY_REQUIRED')
        require(row.get('local_interval')=={'start_1based':beg,'end_inclusive':end} and row.get('original_interval')=={'start_0based':start,'end_exclusive':end0,'strand':strand},'INTERVAL_CONVERSION_OR_STRAND_MISMATCH')
        dna=record.seq[start:end0];require(str(dna).upper()==window_nt[beg-1:end],'WINDOW_INTERVAL_SEQUENCE_MISMATCH')
        dna_text,unadjusted,translated,transformations=translated_interval(dna,strand,note['Codon'])
        require(translated==seq and row.get('translation_table')==1 and row.get('translation_transformations')==transformations and row.get('oriented_dna_sha256')==sha(dna_text.encode()) and row.get('unadjusted_translation_sha256')==sha(unadjusted.encode()),'SOURCE_TRANSLATION_POLICY_MISMATCH')
        require(row.get('start_codon_metadata')==note['Codon'] and row.get('observed_start_codon')==dna_text[:3] and row.get('edge_declared') is (note['Codon']=='Edge') and row.get('geometry_sha1')==note['ShaHex'],'START_OR_GEOMETRY_METADATA_MISMATCH')
        require(row.get('serial_counter_regime')==c['channel'],'SERIAL_COUNTER_REGIME_MISMATCH')
        assessments.append(dict(peptide_id=identifier,enzyme_accession=c['enzyme_accession'],PPSerial=str(fields['ppser']),status='RECONSTRUCTED_SEQUENCE_COORDINATES_UNATTESTED',start_0based=start,end_exclusive=end0,strand=strand,sequence_sha256=sha(seq.encode()),score_row=row['score_row'],translation_table=1,translation_transformations=transformations,mapping_origin='derived_from_retained_native_artifacts',instrumented_producer_sidecar=False,candidate_membership='UNVERIFIED',hmm_annotation='NOT_RUN'))
    require(seen==set(candidates),'EXACT_CANDIDATE_ROSTER_REQUIRED')
    code_bindings={}
    for name in ('ripper_adapter.py','ripper_native_result.py','ripper_native_coordinates.py','ripper_coordinate_binding.py','ripper_raw_discovery.py','ripper_run_binding.py'):
        path=Path(__file__).with_name(name);entry=api['binding'](path,api['load_bytes'](path));sources.append(entry);code_bindings[name]=entry['sha256']
    data=dict(schema_version='ripper-native-coordinate-binding/1',import_status='RETAINED_NATIVE_COORDINATES_EVALUATED',evidence_kind='local_adapter_observed_native',upstream_execution='EXECUTED_NATIVE_LOCAL_ADAPTER_OBSERVED',raw_candidate_count=count,evaluated_candidate_count=len(assessments),assessments=assessments,source_record_id=record.id,selected_subject_cds_sha256=subject_sha,source_raw_coordinate_provenance='ABSENT_PRODUCER_MAPPING',coordinate_evidence_origin='derived_from_retained_native_artifacts',producer_authentication='CONTENT_BINDINGS_ONLY_NOT_AUTHENTICATED_PRODUCER',instrumented_producer_sidecar=False,candidate_membership='UNVERIFIED',hmm_annotation='NOT_RUN_SEPARATE_STAGE',biology='UNASSESSED',canonical_import='NOT_ADMITTED',biological_absence_inferred=False,source_input_nature=packet.get('source_input_nature'),sources=sources,holds=['HOLD_INSTRUMENTED_PRODUCER_ORIGIN','HOLD_BGC_MEMBERSHIP','HOLD_HMM_ANNOTATION_NOT_RUN','HOLD_CANONICAL_IMPORT'],scope='Retrospective native row/window/score/sequence coordinate consistency only; no merged-evidence relabelling, BGC membership, biological validation or new native execution')
    data['software']={'consumer':'ripper_native_coordinates/1','python':sys.version,'biopython':semantic.get('version'),'sqlite':sqlite3.sqlite_version,'code_sha256':code_bindings,'source_policy_sha256':SOURCE_SHA,'parameters':{'candidate_translation_table':1,'score_absolute_tolerance':1e-9,'same_strand_reward':reward,'nucleotide_interval_shift':False,'nontriplet_policy':'REFUSED'}}
    data['exported_genbank_usage']='HASH_BOUND_ONLY_NOT_COMPLETE_COORDINATE_PRODUCER'
    data['reconstruction_and_provenance_usage']='HASH_BOUND_ADDITIVE_METADATA; independent row checks use originalrecord/window/FASTA/score/SQLite/stage'
    api['publish'](out,{'NATIVE_COORDINATE_BINDING.json':data},sources);return data
