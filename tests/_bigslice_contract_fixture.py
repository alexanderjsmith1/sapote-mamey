"""Independent tiny metadata databases/fake child; no BiG-SLiCE or biological search."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import zipfile
from types import SimpleNamespace
from tests._python_fixture_launcher import write_python_fixture

MODEL_DDL = '''
CREATE TABLE schema(ver TEXT); INSERT INTO schema VALUES('1.0.1');
CREATE TABLE run(id INTEGER PRIMARY KEY,status INTEGER,hmm_db_id INTEGER,prog_params TEXT);
CREATE TABLE hmm_db(id INTEGER PRIMARY KEY,md5_biosyn_pfam TEXT,md5_sub_pfam TEXT);
CREATE TABLE clustering(id INTEGER PRIMARY KEY,run_id INTEGER,clustering_method TEXT,num_centroids INTEGER,threshold REAL,random_seed INTEGER);
CREATE TABLE gcf(id INTEGER PRIMARY KEY,id_in_run INTEGER,clustering_id INTEGER);
CREATE TABLE bgc(id INTEGER PRIMARY KEY,orig_folder TEXT,orig_filename TEXT,length_nt INTEGER);
CREATE TABLE run_bgc_status(bgc_id INTEGER,run_id INTEGER,status INTEGER);
CREATE TABLE gcf_membership(bgc_id INTEGER,gcf_id INTEGER,rank INTEGER,membership_value REAL);
INSERT INTO hmm_db VALUES(1,'11111111111111111111111111111111','22222222222222222222222222222222');
INSERT INTO run VALUES(3,7,1,'--threshold 0.4');
INSERT INTO clustering VALUES(11,3,'birch',2,0.4,123);
INSERT INTO gcf VALUES(101,1,11); INSERT INTO gcf VALUES(102,2,11);
INSERT INTO run VALUES(8,7,1,'--threshold 0.6');
INSERT INTO clustering VALUES(22,8,'birch',1,0.6,456);
INSERT INTO gcf VALUES(202,1,22);
'''
QUERY_DDL = '''
CREATE TABLE schema(ver TEXT,parent_schema_ver TEXT); INSERT INTO schema VALUES('1.0.1','1.0.1');
CREATE TABLE bgc(id INTEGER PRIMARY KEY,orig_folder TEXT,orig_filename TEXT,length_nt INTEGER);
CREATE TABLE gcf_membership(bgc_id INTEGER,gcf_id INTEGER,rank INTEGER,membership_value REAL);
'''
REPORT_DDL = '''
CREATE TABLE reports(id INTEGER PRIMARY KEY,type TEXT,name TEXT,creation_date TEXT);
CREATE TABLE reports_run(report_id INTEGER,run_id INTEGER);
'''
FAKE_CHILD = r'''
from pathlib import Path
import json, sqlite3, shutil, sys
args=sys.argv[1:]
root=Path(__file__).parent.parent
control=json.loads((root/'control.json').read_text())
if '--version' in args:
    # Upstream rewrites argv, losing a supplied --program_db_folder, then tries
    # entry-adjacent bigslice-models; its outer main can still exit zero.
    default=Path(__file__).parent/'bigslice-models'
    if not (default/'biosynthetic_pfams/biopfam.md5sum').is_file():
        print("Can't find HMM model libraries!");print('BiG-SLiCE run failed.');sys.exit(0)
    print('BiG-SLiCE version 2.0.0');sys.exit(0)
if '--help' in args:
    print(control.get('help_text','usage: bigslice <output_folder_path>\n[ Version 2.0.0 ]\nBiosynthetic Gene clusters - Super Linear Clustering Engine'))
    sys.exit(0)
(root/'last_argv.json').write_text(json.dumps(args))
mode=control.get('mode','success')
if mode=='nonzero':
    print('synthetic diagnostic retained');sys.exit(7)
def val(flag):return args[args.index(flag)+1]
if '--query' in args:
    inp=Path(val('--query'));work=Path(args[args.index('--query')+2])
    index=work/'reports/reports.db';index.parent.mkdir(parents=True,exist_ok=True)
    if not index.exists():
        with sqlite3.connect(index) as db:db.executescript(control['report_ddl'])
    with sqlite3.connect(index) as db:
        rid=db.execute("SELECT coalesce(max(id),0)+1 FROM reports").fetchone()[0]
        name=val('--query_name')
        db.execute('INSERT INTO reports VALUES(?,?,?,?)',(rid,'query',name,'2000-01-01'))
        run=int(val('--run_id'))+(1 if mode=='wrong_run' else 0)
        db.execute('INSERT INTO reports_run VALUES(?,?)',(rid,run))
    if mode=='row_only':
        print('BiG-SLiCE run failed.');sys.exit(0)
    dest=work/'reports'/str(rid)/'data.db';dest.parent.mkdir()
    with sqlite3.connect(dest) as db:
        db.executescript(control['query_ddl'])
        for i,p in enumerate(sorted(inp.rglob('*.gbk')),1):
            db.execute('INSERT INTO bgc VALUES(?,?,?,100)',(i,str(p.parent),p.name))
            for rank in range(int(val('--n_ranks'))):
                db.execute('INSERT INTO gcf_membership VALUES(?,?,?,?)',(i,101+rank,rank,0.25+rank*0.5))
            if mode=='duplicate_rank':db.execute('INSERT INTO gcf_membership VALUES(?,102,0,0.5)',(i,))
            if mode=='wrong_gcf':db.execute('UPDATE gcf_membership SET gcf_id=202 WHERE bgc_id=?',(i,))
    if mode=='mutate_model':
        with sqlite3.connect(work/'result/data.db') as db:db.execute("UPDATE run SET prog_params='changed' WHERE id=3")
else:
    inp=Path(val('-i'))/'cohort';dest=Path(args[args.index('-i')+2])
    if dest.exists():sys.exit(9)
    (dest/'result').mkdir(parents=True)
    shutil.copyfile(control['model_seed'],dest/'result/data.db')
    with sqlite3.connect(dest/'result/data.db') as db:
        db.execute('DELETE FROM run WHERE id=8');db.execute('DELETE FROM clustering WHERE id=22');db.execute('DELETE FROM gcf WHERE id=202')
        db.execute('UPDATE clustering SET threshold=? WHERE id=11',(float(val('--threshold')),))
        if mode=='cluster_wrong_threshold':db.execute('UPDATE clustering SET threshold=0.9 WHERE id=11')
        if mode=='cluster_wrong_method':db.execute("UPDATE clustering SET clustering_method='foreign' WHERE id=11")
        for i,p in enumerate(sorted(inp.glob('*.gbk')),1):
            db.execute('INSERT INTO bgc VALUES(?,?,?,100)',(i,'cohort',p.name))
            db.execute('INSERT INTO run_bgc_status VALUES(?,3,7)',(i,))
            db.execute('INSERT INTO gcf_membership VALUES(?,101,0,0.25)',(i,))
print('synthetic metadata child complete')
'''


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2)+'\n')


def adapter_module():
    source=Path(__file__).resolve().parents[1]/'tools/bigslice_query.py'
    spec=importlib.util.spec_from_file_location('bigslice_contract_subject',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def panel(tmp_path, contigs=('CP000001.1',), strain='Streptomyces_example_Type'):
    root=tmp_path;inp=root/'input';inp.mkdir();rows=[]
    records=[];source=root/'source.zip'
    with zipfile.ZipFile(source,'w',compression=zipfile.ZIP_STORED) as archive:
        for i,contig in enumerate(contigs,1):
            name=f'object{i}.region001.gbk'
            data=(f'LOCUS       {contig} 100 bp DNA UNK 01-JAN-1980\nVERSION     {contig}\n'
                  'FEATURES             Location/Qualifiers\n     region          1..100\n                     /region_number="1"\nORIGIN\n        1 '+('n'*100)+'\n//\n').encode()
            (inp/name).write_bytes(data);archive.writestr(name,data)
            normalized=contig.split('.')[0] if contig.startswith('NODE_') else contig
            record={'contig':contig,'node_id':normalized,'antismash_region':'region001','bgc_id':f'BGC{i:03d}','source_gbk':name}
            records.append(record)
            rows.append({'relative_path':name,'bytes':str(len(data)),'sha256':hashlib.sha256(data).hexdigest(),'strain':strain,'full_contig':contig,
                         'region':'region001','bgc_alias':f'BGC{i:03d}','inventory_row_sha256':hashlib.sha256(canonical(record)).hexdigest(),'source_member':name})
    manifest=root/'manifest.json';write_json(manifest,{'strain_id':strain,'input_zip_sha256':sha(source),'bgcs':records})
    for row in rows:
        row.update(manifest_path=str(manifest),manifest_sha256=sha(manifest),source_zip=str(source),source_zip_sha256=sha(source))
    crosswalk=root/'identity.tsv'
    def save_rows():
        with crosswalk.open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(rows[0]),delimiter='\t');writer.writeheader();writer.writerows(rows)
    save_rows()
    work=root/'working';(work/'result/cache').mkdir(parents=True)
    model=work/'result/data.db'
    with sqlite3.connect(model) as db:db.executescript(MODEL_DDL)
    model_profile=root/'model_profile.json'
    write_json(model_profile,{'schema':'bigslice-model-profile:v1','profile':'bigslice-2.0.0-schema-1.0.1','model_sha256':sha(model),'run_id':3,
                              'normalization':'l2','review_status':'ADMITTED_BY_OPERATOR','provenance':'independent synthetic metadata fixture'})
    runtime=root/'runtime';runtime.mkdir()
    launcher=write_python_fixture(runtime/'fake-bigslice',FAKE_CHILD)
    binary=runtime/'source'/'bigslice';binary.parent.mkdir();binary.write_bytes((runtime/'fake-bigslice.fixture.py').read_bytes())
    seed=root/'model_seed.db';seed.write_bytes(model.read_bytes())
    write_json(runtime/'control.json',{'report_ddl':REPORT_DDL,'query_ddl':QUERY_DDL,'model_seed':str(seed),'mode':'success'})
    names=['bigslice','modules/data/schema.sql','modules/data/schema_query_mode.sql','modules/data/schema_reports_index.sql','modules/data/bgc.py','modules/clustering/membership.py']
    files=[]
    for name in names:
        p=runtime/'source'/name;p.parent.mkdir(parents=True,exist_ok=True)
        if name!='bigslice':p.write_text('synthetic source binding only\n')
        files.append({'relative_path':name,'sha256':sha(p)})
    admission=root/'runtime_manifest.json'
    write_json(admission,{'schema':'bigslice-runtime-admission:v1','profile':'bigslice-2.0.0-schema-1.0.1','version':'2.0.0','source_pin':'SYNTHETIC-NO-EXTERNAL-TOOL',
                         'review_status':'ADMITTED_BY_OPERATOR','distribution':{'name':'bigslice','mode':'source-tree','version':None},'interpreter_path':sys.executable,'interpreter_sha256':sha(Path(sys.executable).resolve()),'executable_sha256':sha(binary),'source_root':str(runtime/'source'),'source_files':files})
    hmm=root/'hmm'
    for name,value in [('biosynthetic_pfams/biopfam.md5sum','1'*32),('sub_pfams/corepfam.md5sum','2'*32)]:
        p=hmm/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value+'\n')
    out=root/'export'
    common=['--input',str(inp),'--identity-tsv',str(crosswalk),'--out',str(out),'--write-root',str(root),'--n-ranks','1','--threads','1']
    native=['--bigslice',str(binary),'--runtime-manifest',str(admission),'--program-db-folder',str(hmm)]
    query=['query',*common,*native,'--working-model',str(work),'--model-run-id','3','--model-profile',str(model_profile),'--allow-model-write']
    read=['read',*common,'--model-db',str(model),'--model-run-id','3','--model-profile',str(model_profile)]
    cluster=['cluster',*common,*native]
    return SimpleNamespace(**locals())


def control(case, mode):
    p=case.runtime/'control.json';data=json.loads(p.read_text());data['mode']=mode;write_json(p,data)


def state(case):
    return json.loads((case.out/'RUN_STATE.json').read_text())


def exported(case):
    with (case.out/'bigslice_assignment.tsv').open() as handle:return list(csv.DictReader(handle,delimiter='\t'))


def fake_watch(command, *, cwd, log, env, **policy):
    # Execute the independent tiny fake child, not a fake adapter-result dictionary.
    with log.open('x') as handle:
        child=subprocess.run(command,cwd=cwd,env=env,stdout=handle,stderr=subprocess.STDOUT,timeout=10)
    return {'argv':command,'cwd':str(cwd),'exit_code':child.returncode,'stop_reason':None,'log':str(log),'policy':policy}


def seed_query(case, names=None, memberships=None, report_id=4):
    index=case.work/'reports/reports.db';index.parent.mkdir(exist_ok=True)
    with sqlite3.connect(index) as db:
        db.executescript(REPORT_DDL)
        db.execute('INSERT INTO reports VALUES(?,\'query\',\'selected-query\',\'2000-01-01\')',(report_id,))
        db.execute('INSERT INTO reports_run VALUES(?,3)',(report_id,))
        db.execute("INSERT INTO reports VALUES(9,'query','unrelated','2000-01-02')")
        db.execute('INSERT INTO reports_run VALUES(9,8)')
    qdb=case.work/'reports'/str(report_id)/'data.db';qdb.parent.mkdir()
    with sqlite3.connect(qdb) as db:
        db.executescript(QUERY_DDL)
        for i,name in enumerate(names or [r['relative_path'] for r in case.rows],1):
            p=case.inp/name
            db.execute('INSERT INTO bgc VALUES(?,?,?,100)',(i,str(p.parent),p.name))
        for m in memberships or [(i,101,0,0.25) for i in range(1,len(case.rows)+1)]:
            db.execute('INSERT INTO gcf_membership VALUES(?,?,?,?)',m)
    receipt=close_seed_receipt(case,qdb,index)
    return [*case.read,'--query-db',str(qdb),'--reports-db',str(index),'--report-id',str(report_id),'--query-name','selected-query','--query-receipt',str(receipt)],qdb,index


def close_seed_receipt(case,qdb,index):
    # Independently declared synthetic producer artifacts, not adapter output.
    # Tests may construct intentionally malformed but hash-closed DB input to
    # reach schema/membership gates; actual tampering is tested separately.
    def bound(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}
    scope={'run_id':3,'status':7,'prog_params':'--threshold 0.4','hmm_db_id':1,'clustering_id':11,'clustering_method':'birch',
           'num_centroids':2,'threshold':0.4,'random_seed':123,'md5_biosyn_pfam':'1'*32,'md5_sub_pfam':'2'*32,
           'families':[{'id':101,'id_in_run':1},{'id':102,'id_in_run':2}],'model':bound(case.model),
           'normalization':'l2','profile':'bigslice-2.0.0-schema-1.0.1'}
    root=case.root/'producer';root.mkdir(exist_ok=True);rid=int(qdb.parent.name);attempt='independently-declared-synthetic-producer'
    manifest={'schema':'mamey-bigslice-attempt:v1','status':'PLANNED','mode':'query','release':'PRIVATE','attempt_id':attempt,
              'working_model':str(case.work),'model_scope':scope,'immutable_bindings':[scope['model']],'selected_inputs':case.rows}
    denominator={'selected_inputs':len(case.rows),'parsed_bgcs':len(case.rows),'membership_rows':len(case.rows),'excluded':0}
    result={'schema':'mamey-bigslice-selected-result:v1','model_scope':scope,'report_id':rid,'query_db':bound(qdb),'denominator':denominator,
            'query_provenance':{'schema':'bigslice-query-provenance:v1','query_name':'selected-query',
             'report_row':{'id':rid,'type':'query','name':'selected-query','creation_date':'2000-01-01'},'run_link':{'report_id':rid,'run_id':3}}}
    write_json(root/'RUN_MANIFEST.json',manifest);write_json(root/'SELECTED_RESULT.json',result)
    write_json(root/'RUN_STATE.json',{'schema':'mamey-bigslice-attempt:v1','status':'COMPLETE','mode':'query','release':'PRIVATE','attempt_id':attempt,
               'denominator':denominator,'result_sha256':sha(root/'SELECTED_RESULT.json'),'manifest_sha256':sha(root/'RUN_MANIFEST.json')})
    return root/'SELECTED_RESULT.json'
