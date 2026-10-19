"""Bounded read-only local-source SQLite/FASTA parser; no HMM or coordinates inferred."""
import hashlib,math,re,sqlite3,json
from pathlib import Path
from contextlib import closing

COLUMNS=[('acc','TEXT'),('species','TEXT'),('ppser','INTEGER'),('fastaid','TEXT'),('aaseq','TEXT'),('ppstrand','INTEGER'),('testrand','INTEGER'),('pptedist','INTEGER'),('score','float')]
STAGES={'makeblastdb-nucl','makeblastdb-prot','blastp','blastn','prodigal-short'}
PRODIGAL_SCORE_HEADER='\t'.join(('Beg','End','Std','Total','CodPot','StrtSc','Codon','RBSMot','Spacer','RBSScr','UpsScr','TypeScr','GCCont'))


def contained(root,value):
    if not isinstance(value,str):raise ValueError('RAW_OUTPUT_PATH_INVALID')
    p=Path(value)
    if not p.is_absolute() or '..' in p.parts or root not in p.parents:raise ValueError('RAW_OUTPUT_OUTSIDE_RUN')
    for ancestor in [p]+list(p.parents):
        if ancestor==root:break
        if ancestor.is_symlink():raise ValueError('RAW_OUTPUT_SYMLINK_REFUSED')
    return p


def fasta(text):
    records={};key=None;parts=[]
    for line in text.splitlines()+['>END']:
        if line.startswith('>'):
            if key is not None:
                seq=''.join(parts)
                if key in records or not re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWY]+',seq):raise ValueError('RAW_FASTA_DUPLICATE_OR_SEQUENCE_INVALID')
                records[key]=seq
            header=line[1:].split();key=header[0] if header else None;parts=[]
            if not key:raise ValueError('RAW_FASTA_ID_REQUIRED')
        elif line.strip():
            if key is None:raise ValueError('RAW_FASTA_HEADER_REQUIRED')
            parts.append(line.strip())
    return records


def stage_inventory(api,inner,bound,sources):
    temp=inner/'temp';starts=sorted(temp.glob('*.started.json'));terminals=sorted(temp.glob('*.terminal.json'))
    if len(starts)>8 or len(terminals)>8:raise ValueError('RAW_STAGE_ROSTER_TOO_LARGE')
    found={};incomplete=[]
    if set(x.name.removesuffix('.started.json') for x in starts)!=set(x.name.removesuffix('.terminal.json') for x in terminals):incomplete.append('STARTED_TERMINAL_ROSTER_MISMATCH')
    for path in starts:
        started=api['json_input'](contained(inner,str(path)),sources);end=path.with_name(path.name.removesuffix('.started.json')+'.terminal.json')
        if not end.exists():continue
        terminal=api['json_input'](contained(inner,str(end)),sources);terminal_sha=sources[-1]['sha256']
        if not isinstance(started,dict) or not isinstance(terminal,dict):raise ValueError('RAW_STAGE_RECEIPT_INVALID')
        stage=terminal.get('stage')
        if not isinstance(stage,str) or stage not in STAGES or stage in found:raise ValueError('RAW_STAGE_DUPLICATE_OR_UNKNOWN')
        keys=('schema','stage','argv','stdout','stderr','contract','validation_scope')
        if any(started.get(k)!=terminal.get(k) for k in keys) or started.get('schema')!='ripper-local-stage-review-v1' or started.get('state')!='STARTED' or started.get('validation_scope')!='LOCAL_SHAPE_RULES_NATIVE_WORKFLOW_UNVERIFIED':raise ValueError('RAW_STAGE_STARTED_TERMINAL_MISMATCH')
        if terminal.get('state')!='EXIT_ZERO_OUTPUT_OBSERVED_UNVERIFIED' or type(terminal.get('raw_status')) is not int or terminal['raw_status']!=0:raise ValueError('RAW_STAGE_FAILED_OR_UNRESOLVED')
        argv=terminal.get('argv');contract=terminal.get('contract');validation=terminal.get('validation')
        if not isinstance(argv,list) or not argv or any(not isinstance(x,str) for x in argv) or not isinstance(contract,dict) or not isinstance(validation,dict):raise ValueError('RAW_STAGE_CONTRACT_INVALID')
        for key in ('stdout','stderr'):
            p=contained(inner,terminal.get(key));sources.append(api['binding'](p,api['load_bytes'](p)))
        dbprefix=str(inner/'blastdb'/Path(bound['genbank']['path']).name.split('.')[0])
        if stage.startswith('makeblastdb-'):
            kind=stage.removeprefix('makeblastdb-');suffixes=('nhr','nin','nsq') if kind=='nucl' else ('phr','pin','psq')
            inp=contained(inner,argv[2]) if len(argv)==9 else None
            expected=['makeblastdb','-in',str(inp),'-title',Path(bound['genbank']['path']).name.split('.')[0],'-dbtype',kind,'-out',dbprefix]
            if argv!=expected or contract!={'kind':'blastdb_'+kind,'prefix':dbprefix}:raise ValueError('RAW_STAGE_ARGV_OR_CONTRACT_MISMATCH')
            paths=[Path(dbprefix+'.'+x) for x in suffixes]
        else:
            output=contained(inner,contract.get('path'));paths=[output]
            if stage=='blastp':
                expected=['blastp','-query',bound['query_fasta']['path'],'-db',dbprefix,'-out',str(output),'-evalue','1e-3'];kind='blastp_pairwise'
            elif stage=='blastn':
                q=contained(inner,argv[2]) if len(argv)==13 else None;subject=contained(inner,argv[4]) if len(argv)==13 else None
                expected=['blastn','-query',str(q),'-subject',str(subject),'-task','megablast','-out',str(output),'-outfmt','6','-dust','no'];kind='blastn_tsv'
            else:
                inp=contained(inner,argv[6]) if len(argv)==9 else None
                expected=[bound['prodigal_short']['path'],'-p','meta','-f','gff','-i',str(inp),'-s',str(output)];kind='prodigal_scores'
            if argv!=expected or contract!={'kind':kind,'path':str(output)}:raise ValueError('RAW_STAGE_ARGV_OR_CONTRACT_MISMATCH')
        outputs=terminal.get('outputs')
        if not isinstance(outputs,list) or len(outputs)!=len(paths) or any(not isinstance(x,dict) for x in outputs):raise ValueError('RAW_STAGE_OUTPUT_ROSTER_INVALID')
        captured={}
        for p,item in zip(paths,outputs):
            raw=api['load_bytes'](contained(inner,str(p)));b=api['binding'](p,raw);sources.append(b);captured[str(p)]=raw
            if stage.startswith('makeblastdb-') and not raw:raise ValueError('RAW_BLAST_DATABASE_EMPTY')
            if item!={'path':str(p),'bytes':len(raw),'sha256':b['sha256']}:raise ValueError('RAW_STAGE_OUTPUT_DIGEST_MISMATCH')
        if stage=='blastp':
            text=captured[str(paths[0])].decode();nohit=bool(re.search(r'No hits found',text,re.I));hit=bool(re.search(r'Score\s*=',text))
            if not re.search(r'^BLASTP\b',text,re.M) or not re.search(r'^Query=\s*\S',text,re.M) or 'Database:' not in text or nohit==hit:raise ValueError('RAW_BLASTP_DECLARATION_AMBIGUOUS')
            expected='NO_HIT_DECLARED_UNATTESTED' if nohit else 'HITS_DECLARED_UNBOUND'
            if validation.get('outcome')!=expected:raise ValueError('RAW_BLASTP_DECLARATION_MISMATCH')
        elif stage in {'blastn','prodigal-short'}:
            text=captured[str(paths[0])].decode();data=[x for x in text.splitlines() if x.strip() and not x.lstrip().startswith('#')]
            if stage=='prodigal-short' and not text:raise ValueError('RAW_PRODIGAL_EMPTY_UNRESOLVED')
            if stage=='prodigal-short' and data and data[0]==PRODIGAL_SCORE_HEADER:data=data[1:]
            for line in data:
                fields=line.split('\t')
                if stage=='blastn':
                    if len(fields)!=12 or not fields[0] or not fields[1]:raise ValueError('RAW_BLASTN_ROW_INVALID')
                    try:numbers=[float(x) for x in fields[2:]]
                    except ValueError as exc:raise ValueError('RAW_BLASTN_ROW_INVALID') from exc
                    if any(not math.isfinite(x) or x<0 for x in numbers) or numbers[0]>100 or numbers[1]<=0 or any(not re.fullmatch(r'[1-9][0-9]*',x) for x in fields[6:10]):raise ValueError('RAW_BLASTN_ROW_INVALID')
                else:
                    if len(fields)<4 or not re.fullmatch(r'[1-9][0-9]*',fields[0]) or not re.fullmatch(r'[1-9][0-9]*',fields[1]) or int(fields[1])<int(fields[0]) or fields[2] not in ('+','-'):raise ValueError('RAW_PRODIGAL_ROW_INVALID')
                    try:score=float(fields[3])
                    except ValueError as exc:raise ValueError('RAW_PRODIGAL_ROW_INVALID') from exc
                    if not math.isfinite(score):raise ValueError('RAW_PRODIGAL_ROW_INVALID')
            expected=('ALIGNMENT_ROWS_SHAPE_OBSERVED_UNBOUND' if data else 'NO_ROWS_OBSERVED_COORDINATE_HOLD') if stage=='blastn' else ('SCORE_ROWS_SHAPE_OBSERVED_UNBOUND' if data else 'NO_SCORE_ROWS_REPORTED_UNVERIFIED')
            if validation.get('outcome')!=expected:raise ValueError('RAW_STAGE_ROW_OUTCOME_MISMATCH')
            if stage=='blastn' and not data:incomplete.append('TE_COORDINATE_STAGE_NO_ROWS')
        found[stage]=dict(outcome=validation.get('outcome'),terminal_sha256=terminal_sha,terminal_path=str(end))
    return found,incomplete


def source_declaration(api,inner,bound,sources,stages,nohit,count):
    path=contained(inner,str(inner/'DISCOVERY.json'))
    if not path.is_file():return {'status':'MISSING_REQUIRED_SOURCE_DECLARATION'}
    raw=api['load_bytes'](path)
    if len(raw)>1024**2:raise ValueError('RAW_N3_DECLARATION_TOO_LARGE')
    b=api['binding'](path,raw);sources.append(b);data=json.loads(raw.decode())
    qualifications={'schema':'ripper-local-discovery-review-v1','validation_scope':'LOCAL_DECLARATION_NATIVE_EXECUTION_AND_FORMATS_UNATTESTED','evidence_channel':'RAW_DISCOVERY_NOT_HMM_MERGED_TABLE','completion':'NORMAL_SCRIPT_END_ONLY_NOT_INDEPENDENT_PROCESS_ATTESTATION','candidate_bgc_membership':'UNVERIFIED'}
    if not isinstance(data,dict) or any(data.get(k)!=v for k,v in qualifications.items()) or data.get('biological_absence_inferred') is not False:raise ValueError('RAW_N3_DECLARATION_QUALIFICATION_INVALID')
    expected='NO_TE_HITS_DECLARED_UNATTESTED' if nohit else 'TE_MATCH_WITH_ROWS_UNATTESTED' if count else 'TE_MATCH_NO_CANDIDATE_ROWS_UNATTESTED'
    if data.get('state')!=expected or type(data.get('candidate_rows_declared')) is not int or data['candidate_rows_declared']!=count or type(data.get('te_matched_declared')) is not bool or data['te_matched_declared']!=bool(not nohit):raise ValueError('RAW_N3_DECLARATION_OUTCOME_CONTRADICTION')
    roster=data.get('stage_receipts')
    if not isinstance(roster,list) or any(not isinstance(x,str) for x in roster) or len(roster)!=len(set(roster)) or sorted(roster)!=sorted(x['terminal_path'] for x in stages.values()):raise ValueError('RAW_N3_DECLARATION_STAGE_ROSTER_MISMATCH')
    wanted={}
    for role,key in {'source':'upstream_source','config':'config','query_fasta':'query_fasta','genbank':'genbank'}.items():
        entry=bound.get(key)
        if not isinstance(entry,dict) or any(k not in entry for k in ('path','bytes','sha256')):raise ValueError('RAW_N3_EXPLICIT_INPUT_BINDINGS_REQUIRED')
        wanted[role]={k:entry[k] for k in ('path','bytes','sha256')}
    # Compare declaration fields only. Never follow external locators from this receipt.
    if data.get('inputs')!=wanted:raise ValueError('RAW_N3_DECLARATION_INPUT_BINDING_MISMATCH')
    return dict(status='MATCHED_UNATTESTED_SOURCE_DECLARATION',state=expected,sha256=b['sha256'],candidate_rows_declared=count,process_attestation='NOT_SUPPLIED_BY_SOURCE_DECLARATION_SEE_SEPARATE_LIFECYCLE')

def parse_discovery(api,inner,bound,contract):
    inner=Path(inner).resolve();sources=[];table=contract['table']
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',table):raise ValueError('RAW_SQL_TABLE_INVALID')
    db=contained(inner,str(inner/'sqlite/ripper.sqlite3'));raw=api['load_bytes'](db);sources.append(api['binding'](db,raw))
    if not raw.startswith(b'SQLite format 3\x00'):raise ValueError('RAW_SQLITE_FORMAT_REQUIRED')
    if any(Path(str(db)+suffix).exists() for suffix in ('-wal','-journal','-shm')):raise ValueError('RAW_SQLITE_LIVE_SIDECAR_REFUSED')
    try:
        if not hasattr(sqlite3.Connection,'deserialize'):raise ValueError('RAW_SQLITE_SNAPSHOT_DEPENDENCY_UNAVAILABLE')
        with closing(sqlite3.connect(':memory:',timeout=1)) as connection:
            connection.deserialize(raw)
            connection.execute('PRAGMA temp_store=MEMORY')
            connection.execute('PRAGMA query_only=ON');connection.execute('PRAGMA trusted_schema=OFF')
            schema=connection.execute('SELECT type,sql FROM sqlite_master WHERE name=?',(table,)).fetchall()
            if len(schema)!=1 or schema[0][0]!='table' or not isinstance(schema[0][1],str) or 'VIRTUAL' in schema[0][1].upper():raise ValueError('RAW_SQLITE_PLAIN_TABLE_REQUIRED')
            cols=connection.execute('PRAGMA table_info("'+table+'")').fetchall()
            if [(x[1],x[2].upper()) for x in cols]!=[(x,y.upper()) for x,y in COLUMNS]:raise ValueError('RAW_SQLITE_EXACT_COLUMNS_REQUIRED')
            indexes=connection.execute('PRAGMA index_list("'+table+'")').fetchall()
            unique=False
            for index in indexes:
                if index[2] and not index[4]:
                    info=connection.execute('PRAGMA index_info("'+index[1].replace('"','""')+'")').fetchall()
                    unique |= [x[2] for x in info]==['acc','ppser']
            if not unique:raise ValueError('RAW_SQLITE_UNIQUE_IDENTITY_REQUIRED')
            rows=connection.execute('SELECT '+','.join(x for x,y in COLUMNS)+' FROM "'+table+'" ORDER BY acc,ppser LIMIT 10001').fetchall()
            if len(rows)>10000:raise ValueError('RAW_CANDIDATE_ROSTER_TOO_LARGE')
    except sqlite3.Error as exc:raise ValueError('RAW_SQLITE_READ_FAILED: '+str(exc)) from exc
    candidates=[];seen=set()
    for row in rows:
        acc,organism,serial,identifier,seq,ppstrand,testrand,distance,score=row
        if not isinstance(acc,str) or not re.fullmatch(r'[A-Za-z0-9_.]+',acc) or type(serial) is not int or serial<1 or identifier!=acc+'_'+str(serial) or identifier in seen:raise ValueError('RAW_CANDIDATE_IDENTITY_INVALID')
        if not isinstance(seq,str) or not re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWY]+',seq) or not contract['config']['min_peptide_length']<=len(seq)<=contract['config']['max_peptide_length']:raise ValueError('RAW_CANDIDATE_SEQUENCE_INVALID')
        if type(ppstrand) is not int or ppstrand not in (-1,1) or type(testrand) is not int or testrand not in (-1,1) or type(distance) is not int or distance<0 or not isinstance(score,(int,float)) or not math.isfinite(score) or not isinstance(organism,str):raise ValueError('RAW_CANDIDATE_RAW_FIELDS_INVALID')
        seen.add(identifier);candidates.append(dict(enzyme_accession=acc,peptide_id=identifier,sequence=seq,channel='distant' if re.fullmatch(r'9[0-9]{3,}',str(serial)) else 'main',source_fields=dict(zip((x for x,y in COLUMNS),row)),candidate_membership='UNVERIFIED',coordinate_status='ABSENT_PRODUCER_MAPPING',hmm_annotation='NOT_RUN'))
    stages,incomplete=stage_inventory(api,inner,bound,sources);base={'makeblastdb-nucl','makeblastdb-prot','blastp'};nohit=stages.get('blastp',{}).get('outcome')=='NO_HIT_DECLARED_UNATTESTED'
    expected=base if nohit else STAGES
    if set(stages)!=expected:incomplete.append('EXACT_STAGE_COVERAGE_UNRESOLVED')
    stem=Path(bound['genbank']['path']).stem;faa=inner/'output'/(stem+'_rip.faa');gbk=inner/'output'/(stem+'_rip.gbk')
    if faa.exists():
        content=api['load_bytes'](contained(inner,str(faa)));sources.append(api['binding'](faa,content));actual=fasta(content.decode())
        if actual!={x['peptide_id']:x['sequence'] for x in candidates}:raise ValueError('RAW_SQLITE_FASTA_MISMATCH')
    elif candidates:incomplete.append('CANDIDATE_FASTA_EXPORT_MISSING')
    if not nohit:
        if not gbk.is_file():incomplete.append('GENBANK_EXPORT_MISSING')
        else:
            content=api['load_bytes'](contained(inner,str(gbk)));sources.append(api['binding'](gbk,content))
            if not content.startswith(b'LOCUS') or len(re.findall(rb'^//\s*$',content,re.M))!=1:raise ValueError('RAW_GENBANK_EXPORT_SHAPE_INVALID')
    elif candidates or faa.exists() or gbk.exists():raise ValueError('RAW_NO_HIT_EXPORT_CONTRADICTION')
    declaration=source_declaration(api,inner,bound,sources,stages,nohit,len(candidates)) if contract.get('requires_discovery_declaration') else {'status':'NOT_REQUIRED_HISTORICAL_Q3_INTERFACE'}
    if declaration['status']=='MISSING_REQUIRED_SOURCE_DECLARATION':incomplete.append('N3_DISCOVERY_DECLARATION_MISSING')
    mismatch=any(x['enzyme_accession']!=contract['expected_subject'] for x in candidates)
    status='AMBIGUOUS' if incomplete or mismatch else 'NO_HIT' if nohit else 'SUCCESS_UNBOUND' if candidates else 'NO_RETAINED_CANDIDATES'
    for b in sources:
        if api['binding'](b['path'],api['load_bytes'](b['path']))!=b:raise ValueError('RAW_OUTPUT_CHANGED_DURING_PARSE')
    return dict(schema_version='ripper-raw-discovery/1',status=status,outcome='INCOMPLETE_OR_SUBJECT_CONTEXT_UNRESOLVED' if status=='AMBIGUOUS' else 'NO_BLASTP_HIT_DECLARED_DISCOVERY_SCOPE' if nohit else 'RAW_SQLITE_FASTA_ROWS_ONLY',candidate_count=None if status=='AMBIGUOUS' else len(candidates),retained_raw_candidate_count=len(candidates),candidates=candidates,sources=sources,stages=stages,source_declaration=declaration,incomplete=incomplete,subject_context_mismatch=mismatch,hmm_annotation='NOT_RUN_SEPARATE_STAGE',candidate_membership='UNVERIFIED',coordinate_provenance='ABSENT_PRODUCER_MAPPING',biological_absence_inferred=False,scope='source-documented raw discovery only; stage/model/BLAST biological validation not inferred')
