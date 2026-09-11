"""Portable extraction of saved package scan context. Never execute a scan.

Requires the bundled mamey.scan_channel_alias owner. Inputs and output are explicit.
SQLite output is exclusive-create. No sequences or large alias payloads are copied.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, re, sqlite3, zlib
from pathlib import Path
from urllib.parse import quote
import sys
if __package__ in (None, ''):
    _bundle_root=Path(__file__).resolve().parents[1]
    if (_bundle_root/'mamey').is_dir():sys.path.insert(0,str(_bundle_root))
from mamey.scan_channel_alias import load_bound_scan_manifest, _validated_alias_target
from mamey.exact_identity import exact_locus_display
from mamey.tool_database_reader import _no_sidecars
from mamey import scan_channel_alias, exact_identity, __version__, BUNDLE_VERSION

SCHEMA='current_package_scan_states/1'
CHANNEL_MAP={'domain_architecture':'domain','antismash_structured':'domain','mibig_per_gene':'mibig','clusterblast_genes':'clusterblast','rggmci':'rggmci'}
EXPECTED=('chitinase','tfbs','blda_tta','regulators','transporters','resistance','cctt','flbr','cassettes','umed','efls','domain_architecture','resistance_tiers','wetlab_rows','qs_signals','glycosylation_arms','per_bgc_dss','rggmci','primary_metabolism','misanchor_guards','concordance_per_bgc','clusterblast_genes','mibig_per_gene','antismash_structured','functional_profiles','pks_ks_scan')
MAX_FILE=64*1024*1024

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def strict(raw):
    def pairs(rows):
        out={}
        for k,v in rows:
            if k in out:raise ValueError('DUPLICATE_JSON_KEY_HOLD')
            out[k]=v
        return out
    def nonfinite(_):raise ValueError('NONFINITE_JSON_HOLD')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)

def js(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)

def read_file(root, name):
    p=_validated_alias_target(root,name)
    if not p.is_file() or p.stat().st_size>MAX_FILE:raise ValueError('SOURCE_SIZE_OR_MISSING_HOLD')
    raw=p.read_bytes()
    if len(raw)>MAX_FILE:raise ValueError('SOURCE_SIZE_HOLD')
    return p,raw,hashlib.sha256(raw).hexdigest()

def snapshot(package):
    """Strictly precheck exact bytes, then reuse the established alias owner."""
    package=Path(package)
    if package.is_symlink():raise ValueError('SYMLINK_PACKAGE_HOLD')
    package=package.resolve(strict=True)
    _,raw,mh=read_file(package,'manifest.json');original=strict(raw)
    if not isinstance(original,dict):raise ValueError('MANIFEST_OBJECT_HOLD')
    listed={}
    for row in original.get('files',[]):
        name=row.get('path')
        if not isinstance(name,str) or name in listed:raise ValueError('DUPLICATE_OR_INVALID_LISTED_FILE_HOLD')
        _validated_alias_target(package,name);listed[name]=row
    consumed={'manifest.json':(mh,len(raw),'SELECTED_MANIFEST_HASH_NOT_RELEASE_SIGNATURE')}
    for v in (original.get('source_scans') or {}).values():
        if isinstance(v,dict) and ('alias_of' in v or v.get('schema')=='source_scan_channel_alias_v1'):
            _,b,h=read_file(package,v.get('alias_of'));strict(b)
            consumed[v['alias_of']]=(h,len(b),'')
    m,sources,loaded_sha=load_bound_scan_manifest(package/'manifest.json')
    if loaded_sha!=mh:raise ValueError('MANIFEST_CHANGED_HOLD')
    for src in sources.values():
        if src['sha256'] not in {x[0] for x in consumed.values()}:raise ValueError('ALIAS_CHANGED_HOLD')
    sid=m.get('strain_id')
    if not isinstance(sid,str) or not sid.strip():raise ValueError('STRAIN_IDENTITY_HOLD')
    aux={}
    for suffix in ('_1_intake.json','_gene_by_gene_all_bgcs.csv','_proteins.faa'):
        candidates=[n for n in listed if n.endswith(suffix)]
        if len(candidates)>1:raise ValueError('AMBIGUOUS_AUX_SOURCE_HOLD')
        if candidates:
            name=candidates[0];_,b,h=read_file(package,name);consumed[name]=(h,len(b),'');aux[suffix]=(name,b)
    for name in ('gate_validation.json','commit_receipt.json'):
        if (package/name).exists():
            _,b,h=read_file(package,name);strict(b);consumed[name]=(h,len(b),'');aux[name]=(name,b)
    states={}
    for name,(h,size,state) in consumed.items():
        if name=='manifest.json':states[name]=state;continue
        expected=listed.get(name)
        if expected is None:states[name]='HASHED_CURRENT_BYTES_NOT_MANIFEST_LISTED'
        elif expected.get('sha256')!=h or expected.get('bytes')!=size:
            if name in ('gate_validation.json','commit_receipt.json'):states[name]='SAVED_RECEIPT_MANIFEST_MISMATCH_HOLD_NOT_VALIDATION_AUTHORITY'
            else:raise ValueError('MANIFEST_FILE_HASH_OR_SIZE_MISMATCH_HOLD')
        else:states[name]='MANIFEST_LISTED_BYTES_VERIFIED'
    identities={}
    for b in m.get('bgcs',[]):
        ident=(sid,b.get('contig'),b.get('antismash_region'),b.get('bgc_id'))
        if any(not isinstance(x,str) or not x.strip() for x in ident):raise ValueError('INCOMPLETE_LOCUS_IDENTITY_HOLD')
        display=exact_locus_display(*ident)
        if ident[-1] in identities:raise ValueError('AMBIGUOUS_PACKAGE_ALIAS_HOLD')
        if type(b.get('start')) is not int or type(b.get('end')) is not int or b['start']<0 or b['end']<=b['start']:raise ValueError('LOCUS_COORDINATE_HOLD')
        identities[ident[-1]]=(ident,display,b)
    if not identities:raise ValueError('EMPTY_LOCUS_ROSTER_HOLD')
    for b in m.get('bgc_crosswalk',[]):
        target=identities.get(b.get('bgc_id'))
        if target is None or (b.get('contig'),b.get('antismash_region'),b.get('start'),b.get('end')) != (target[0][1],target[0][2],target[2]['start'],target[2]['end']):raise ValueError('CROSSWALK_IDENTITY_CONFLICT_HOLD')
    genes=collections.defaultdict(list);proteins=collections.defaultdict(list)
    if '_proteins.faa' in aux:
        tag=alias=None;seq=[]
        def save():
            if tag is not None:
                aa=''.join(seq).upper();proteins[(alias,tag)].append((hashlib.sha256(aa.encode()).hexdigest(),len(aa)))
        for line in aux['_proteins.faa'][1].decode().splitlines():
            if line.startswith('>'):
                save();head=line[1:].split();tag=head[0] if head else None
                matches=[x[4:] for x in head[1:] if x.startswith('bgc=')];alias=matches[0] if len(matches)==1 else None;seq=[]
            else:seq.append(''.join(line.split()))
        save()
    if '_gene_by_gene_all_bgcs.csv' in aux:
        import io
        reader=csv.DictReader(io.StringIO(aux['_gene_by_gene_all_bgcs.csv'][1].decode('utf-8-sig')))
        required={'strain','contig','region','bgc_id','locus_tag','cds_start','cds_end','strand','aa_length'}
        if not required<=set(reader.fieldnames or []):raise ValueError('GENE_CSV_SCHEMA_HOLD')
        for row in reader:
            target=identities.get(row['bgc_id'])
            if target is None or (row['strain'],row['contig'],row['region'],row['bgc_id'])!=target[0]:raise ValueError('GENE_LOCUS_IDENTITY_HOLD')
            options=proteins.get((row['bgc_id'],row['locus_tag']),[])
            state='PROTEIN_HASH_UNAVAILABLE_HOLD';ph=None;length=None
            if len(options)==1:
                ph,length=options[0];state='PACKAGE_PROTEIN_HASH_RECORDED_NOT_FROZEN_ADMISSION'
                if int(row['aa_length'])!=length:state='PROTEIN_LENGTH_CONFLICT_HOLD'
            elif len(options)>1:state='AMBIGUOUS_PROTEIN_OCCURRENCE_HOLD'
            strand={'+':1,'-':-1,'1':1,'-1':-1}.get(row['strand'])
            genes[row['bgc_id']].append(dict(locus_tag=row['locus_tag'],protein_sha256=ph,protein_length=length,cds_start=int(row['cds_start']),cds_end=int(row['cds_end']),strand=strand,state=state,membership=row.get('boundary_flag','UNSPECIFIED'),source_fields={k:row.get(k) for k in ('assembly_locator','source_gbk','source_line_locator','bgc_start','bgc_end','edge_core_overlap')}))
    for name,(h,_,_) in consumed.items():
        if sha(package/name)!=h:raise ValueError('SOURCE_CHANGED_DURING_READ_HOLD')
    return dict(root=package,manifest=m,original=original,manifest_sha256=mh,sources=sources,consumed=consumed,integrity=states,identities=identities,genes=genes,aux=aux)

def signal_value(channel,payload,alias):
    if payload is None:return 'MISSING_CHANNEL_NOT_NEGATIVE',None,''
    if not isinstance(payload,dict):return 'UNSUPPORTED_CHANNEL_SHAPE_HOLD',None,''
    if channel in ('concordance_per_bgc','functional_profiles'):
        return ('RECORDED_LOCUS_RESULT_NOT_ADMITTED',payload[alias],'/'+quote(alias,safe='')) if alias in payload else ('UNRECORDED_LOCUS_NOT_NEGATIVE',None,'')
    if isinstance(payload.get('per_bgc'),dict):
        return ('RECORDED_LOCUS_RESULT_NOT_ADMITTED',payload['per_bgc'][alias],'/per_bgc/'+quote(alias,safe='')) if alias in payload['per_bgc'] else ('UNRECORDED_LOCUS_NOT_NEGATIVE',None,'')
    if isinstance(payload.get('bgc_coupling'),dict) and alias in payload['bgc_coupling']:
        return 'RECORDED_LOCUS_COUPLING_NOT_ADMITTED',payload['bgc_coupling'][alias],'/bgc_coupling/'+quote(alias,safe='')
    return 'PACKAGE_SCOPED_NOT_PROJECTED',None,''

def build(packages, output, census=None, census_sha=None, profile_db=None, profile_sha=None, resume=False):
    output=Path(output)
    if (census is None)!=(census_sha is None) or (profile_db is None)!=(profile_sha is None):raise ValueError('DEPENDENCY_PATH_AND_HASH_REQUIRED_TOGETHER')
    existing=output.exists()
    if existing and not resume:raise ValueError('OUTPUT_ALREADY_EXISTS')
    packages=sorted(map(Path,packages),key=lambda p:str(p.resolve()))
    planned={str(p.resolve()):sha(p/'manifest.json') for p in packages}
    if len(planned)!=len(packages) or len(set(planned.values()))!=len(packages):raise ValueError('DUPLICATE_PACKAGE_MANIFEST_HOLD')
    dependency_pins={'producer_sha256':sha(Path(__file__)),'frozen_census_sha256':census_sha or 'NOT_PROVIDED','profile_database_sha256':profile_sha or 'NOT_PROVIDED','planned_manifest_sha256':js(sorted(planned.values()))}
    dependency_pins.update(alias_owner_sha256=sha(Path(scan_channel_alias.__file__)),identity_owner_sha256=sha(Path(exact_identity.__file__)),engine_version=__version__,bundle_version=BUNDLE_VERSION)
    cen=None
    if census:
        census=Path(census)
        _no_sidecars(census)
        if not census_sha or sha(census)!=census_sha:raise ValueError('CENSUS_HASH_HOLD')
        cen=sqlite3.connect(census.resolve().as_uri()+'?mode=ro',uri=True);cen.row_factory=sqlite3.Row
    output.parent.mkdir(parents=True,exist_ok=True)
    if not existing:
        with output.open('xb'):pass
    else:_no_sidecars(output)
    db=sqlite3.connect(output);db.execute('PRAGMA journal_mode=MEMORY');db.execute('PRAGMA foreign_keys=ON')
    if not existing:db.executescript('''
    CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE package(package_id TEXT PRIMARY KEY,source_locator TEXT,manifest_sha256 TEXT,strain TEXT,input_zip_sha256 TEXT,bundle_version TEXT,engine_version TEXT,recorded_status TEXT,context_json TEXT);
    CREATE TABLE source_file(package_id TEXT REFERENCES package,name TEXT,sha256 TEXT,bytes INTEGER,integrity TEXT,PRIMARY KEY(package_id,name));
    CREATE TABLE locus(locus_key TEXT PRIMARY KEY,package_id TEXT REFERENCES package,strain TEXT,full_node TEXT,region TEXT,bgc_alias TEXT,exact_identity TEXT,region_start INTEGER,region_end INTEGER,frozen_binding_state TEXT,frozen_context_json TEXT,guards_json TEXT);
    CREATE INDEX locus_identity ON locus(strain,full_node,region,bgc_alias);
    CREATE TABLE gene(locus_key TEXT REFERENCES locus,gene_order INTEGER,locus_tag TEXT,protein_sha256 TEXT,protein_length INTEGER,cds_start INTEGER,cds_end INTEGER,strand INTEGER,membership TEXT,state TEXT,source_fields_json TEXT,PRIMARY KEY(locus_key,gene_order));
    CREATE TABLE signal(locus_key TEXT REFERENCES locus,channel TEXT,state TEXT,saved_status TEXT,source_locator TEXT,source_sha256 TEXT,raw_zlib BLOB,raw_sha256 TEXT,compatible_channel TEXT,evidence_index_state TEXT,PRIMARY KEY(locus_key,channel));
    CREATE TABLE package_signal(package_id TEXT REFERENCES package,channel TEXT,source_locator TEXT,source_sha256 TEXT,summary_json TEXT,PRIMARY KEY(package_id,channel));
    CREATE TABLE section_profile(profile_sha256 TEXT,bundle_version TEXT,code_zip_sha256 TEXT,member TEXT,contract_text TEXT);
    CREATE TABLE section_relevance(section_number INTEGER PRIMARY KEY,profile_sha256 TEXT,requirement TEXT,relation TEXT,limits TEXT);
    ''')
    if existing:
        recorded=dict(db.execute('SELECT key,value FROM metadata'))
        if any(recorded.get(k)!=v for k,v in dependency_pins.items()):raise ValueError('RESUME_DEPENDENCY_OR_POPULATION_CHANGED_HOLD')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('RESUME_DATABASE_INTEGRITY_HOLD')
    else:
        db.executemany('INSERT INTO metadata VALUES (?,?)',dict(channel='current_package_scan_states',schema_version='0.1.0',scope='Saved package occurrences, variants retained; no new scans or automatic cohort selection',scientific_admission='NOT_PERFORMED',source_binding='Consumed file hashes checked against manifest when listed. Saved gate result is not independently rerun. Source archive identity is recorded, not reopened.',**dependency_pins).items())
        db.commit()
    receipts=[]
    for package in packages:
        prior_pid=planned[str(package.resolve())]
        if existing and db.execute('SELECT count(*) FROM package WHERE package_id=?',(prior_pid,)).fetchone()[0]:
            for name,h,size in db.execute('SELECT name,sha256,bytes FROM source_file WHERE package_id=?',(prior_pid,)):
                p,raw,current=read_file(package,name)
                if current!=h or len(raw)!=size:raise ValueError('RESUME_SOURCE_CHANGED_HOLD')
            receipts.append(dict(package_id=prior_pid,path=str(package),state='VERIFIED_COMMITTED_PARTITION_REUSED'))
            continue
        s=snapshot(package);m=s['manifest'];pid=s['manifest_sha256']
        if pid!=prior_pid:raise ValueError('SOURCE_MANIFEST_CHANGED_HOLD')
        context={k:m.get(k) for k in ('taxonomy','source','source_provenance','source_provenance_note','analysis_date','mode','scan_status','missingness','issues','package_status','terminal_status','claim_safety_status','reporting_features','antismash_profile')}
        context['taxonomy_method']='PACKAGE_SUPPLIED_TEXT_NOT_INDEPENDENT_CLASSIFICATION';context['bioactivity_or_blda_control_validation']='NOT_PERFORMED'
        for k in ('_1_intake.json','gate_validation.json','commit_receipt.json'):
            if k in s['aux']:context[k]=strict(s['aux'][k][1])
        db.execute('INSERT INTO package VALUES (?,?,?,?,?,?,?,?,?)',(pid,'package-manifest://'+pid,pid,m['strain_id'],m.get('input_zip_sha256'),m.get('bundle_version'),m.get('workflow_version'),str(m.get('terminal_status')),js(context)))
        db.executemany('INSERT INTO source_file VALUES (?,?,?,?,?)',[(pid,n,h,size,s['integrity'][n]) for n,(h,size,_) in s['consumed'].items()])
        scans=m.get('source_scans') or {};channels=sorted(set(EXPECTED)|set(scans))
        for ch in channels:
            value=scans.get(ch);src=s['sources'].get(ch,{'locator':'package://manifest.json','sha256':pid,'pointer':'/source_scans/'+ch})
            summary={k:v for k,v in (value.items() if isinstance(value,dict) else []) if not isinstance(v,(dict,list))}
            summary['retained_source_fields']=list(value) if isinstance(value,dict) else []
            summary['large_payload_policy']='Complete source remains in hash-pinned package; gene-hit/domain/reference payloads not copied.'
            db.execute('INSERT INTO package_signal VALUES (?,?,?,?,?)',(pid,ch,src['locator']+'#'+src['pointer'],src['sha256'],js(summary)))
        for alias,(ident,display,b) in s['identities'].items():
            key=hashlib.sha256(js([pid,*ident]).encode()).hexdigest();gg=s['genes'].get(alias,[])
            frozen=[];binding='FROZEN_CENSUS_NOT_PROVIDED'
            if cen:
                rows=list(cen.execute('SELECT * FROM locus WHERE strain=? AND full_node=? AND region=? AND bgc_alias=?',ident))
                binding='NO_EXACT_FROZEN_LOCUS_MATCH_HOLD' if not rows else 'FROZEN_COMPARISON_CONTEXT_ONLY'
                for f in rows:
                    fm=dict(f);source=cen.execute('SELECT source_sha256 FROM strain WHERE strain=?',(ident[0],)).fetchall()
                    source_match=any(r[0]==m.get('input_zip_sha256') for r in source)
                    old=list(cen.execute('SELECT locus_tag,protein_sha256,cds_start,cds_end,strand FROM gene WHERE locus_key=?',(f['locus_key'],)))
                    current=[(g['locus_tag'],g['protein_sha256'],g['cds_start'],g['cds_end'],g['strand']) for g in gg]
                    roster=collections.Counter(map(tuple,old))==collections.Counter(current)
                    frozen.append(dict(locus_key=f['locus_key'],exact_identity=f['exact_identity'],source_archive_sha_agrees=source_match,frozen_start=f['region_start_1based'],frozen_end=f['region_end_1based'],raw_coordinate_equal=(b['start'],b['end'])==(f['region_start_1based'],f['region_end_1based']),one_based_vs_zero_based_candidate=(b['start']+1,b['end'])==(f['region_start_1based'],f['region_end_1based']),full_gene_tuple_multiset_equal=roster,frozen_gene_count=len(old),package_gene_count=len(gg),state='COMPARISON_ONLY_NOT_ADMISSION'))
            guards={k:v for k,v in b.items() if any(w in k.lower() for w in ('guard','misanchor','primary_metabolism','edge_status','confidence'))}
            db.execute('INSERT INTO locus VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(key,pid,*ident,display,b['start'],b['end'],binding,js(frozen),js(guards)))
            for order,g in enumerate(gg):db.execute('INSERT INTO gene VALUES (?,?,?,?,?,?,?,?,?,?,?)',(key,order,g['locus_tag'],g['protein_sha256'],g['protein_length'],g['cds_start'],g['cds_end'],g['strand'],g['membership'],g['state'],js(g['source_fields'])))
            for ch in channels:
                value=scans.get(ch);state,raw,pointer=signal_value(ch,value,alias);src=s['sources'].get(ch,{'locator':'package://manifest.json','sha256':pid,'pointer':'/source_scans/'+ch})
                saved_status=value.get('status') if isinstance(value,dict) else None
                if isinstance(raw,dict):saved_status=raw.get('verdict',raw.get('status',saved_status))
                encoded=js(raw).encode()
                db.execute('INSERT INTO signal VALUES (?,?,?,?,?,?,?,?,?,?)',(key,ch,state,js(saved_status),src['locator']+'#'+src['pointer']+pointer,src['sha256'],zlib.compress(encoded),hashlib.sha256(encoded).hexdigest(),CHANNEL_MAP.get(ch),'UNBOUND' if ch in CHANNEL_MAP else 'UNSUPPORTED_CHANNEL_NOT_COERCED'))
        receipts.append(dict(package_id=pid,path=str(s['root']),loci=len(s['identities']),genes=sum(map(len,s['genes'].values())),consumed_files=len(s['consumed']),integrity=dict(collections.Counter(s['integrity'].values()))))
        db.commit()
    if profile_db:
        profile_db=Path(profile_db)
        _no_sidecars(profile_db)
        if not profile_sha or sha(profile_db)!=profile_sha:raise ValueError('PROFILE_DATABASE_HASH_HOLD')
        pc=sqlite3.connect(profile_db.resolve().as_uri()+'?mode=ro',uri=True)
        profile=pc.execute('SELECT * FROM section_profile').fetchone()
        prior_profiles=db.execute('SELECT * FROM section_profile').fetchall()
        if prior_profiles and prior_profiles!=[tuple(profile)]:raise ValueError('RESUME_PROFILE_CONTENT_HOLD')
        if not prior_profiles:db.execute('INSERT INTO section_profile VALUES (?,?,?,?,?)',tuple(profile))
        direct={1,2,3,4,7,8,9,11,14,15,18,19,20,23,24,26,28,31,36,46,49,50}
        for n,ph,req in pc.execute('SELECT section_number,profile_sha256,requirement FROM section_relevance ORDER BY section_number'):
            row=(n,ph,req,'SAVED_CONTEXT_OR_TYPED_HOLD_ONLY' if n in direct else 'NO_DIRECT_SUPPORT','No section satisfied by scan states alone. Saved verdicts, applicability and missingness are not biological validation.')
            existing_row=db.execute('SELECT * FROM section_relevance WHERE section_number=?',(n,)).fetchone()
            if existing_row and existing_row!=row:raise ValueError('RESUME_SECTION_CONTENT_HOLD')
            if not existing_row:db.execute('INSERT INTO section_relevance VALUES (?,?,?,?,?)',row)
        pc.close()
        if sha(profile_db)!=profile_sha:raise ValueError('PROFILE_DATABASE_CHANGED_HOLD')
    if cen:
        cen.close()
        if sha(census)!=census_sha:raise ValueError('CENSUS_CHANGED_HOLD')
    if any(sha(Path(p)/'manifest.json')!=h for p,h in planned.items()):raise ValueError('SOURCE_CHANGED_DURING_BUILD_HOLD')
    db.commit();assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not db.execute('PRAGMA foreign_key_check').fetchall()
    counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('package','locus','gene','signal','source_file','section_relevance')};db.close()
    return dict(schema=SCHEMA,database_sha256=sha(output),bytes=output.stat().st_size,counts=counts,packages=receipts,computation='NONE_SAVED_RESULTS_ONLY',acceptance='NOT_PERFORMED')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',action='append',required=True);p.add_argument('--output',required=True);p.add_argument('--census');p.add_argument('--census-sha256');p.add_argument('--profile-db');p.add_argument('--profile-sha256');p.add_argument('--resume',action='store_true');a=p.parse_args()
    print(json.dumps(build(a.package,a.output,a.census,a.census_sha256,a.profile_db,a.profile_sha256,a.resume),indent=2))

if __name__=='__main__':main()
