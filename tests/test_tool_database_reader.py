"""Generic static SQLite fixtures; no external evidence or user-specific paths."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import zlib

import pytest
from mamey import tool_database_reader as reader

ID = ("TEST-1", "contig_complete_001", "region001", "cluster001")
DISPLAY = " / ".join(ID)


def fixture_db(root, keyword=False, rows=3):
    root.mkdir(parents=True, exist_ok=True)
    db = root / "evidence.sqlite"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE locus(locus_key TEXT,strain TEXT,full_node TEXT,region TEXT,bgc_alias TEXT,exact_identity TEXT)")
    extra = ",state TEXT,groups_json TEXT" if keyword else ",cds_start INTEGER,cds_end INTEGER,strand INTEGER,membership TEXT,product TEXT,hold TEXT"
    c.execute("CREATE TABLE gene(locus_key TEXT,gene_order INTEGER,locus_tag TEXT,protein_sha256 TEXT,protein_length INTEGER" + extra + ")")
    c.execute("CREATE TABLE section_profile(profile_sha256 TEXT,bundle_version TEXT)")
    c.execute("INSERT INTO section_profile VALUES(?,?)", ("f" * 64, "9.7.412"))
    c.execute("INSERT INTO locus VALUES(?,?,?,?,?,?)", ("key", *ID, DISPLAY))
    for i in range(rows):
        values = ("key", i, "gene"+str(i), "a"*64, 10)
        values += ("HELD_SOURCE_ROW", "[]") if keyword else (1,30,1,"EXACT_REGION","fixture","SOURCE_HOLD")
        c.execute("INSERT INTO gene VALUES("+",".join("?" for _ in values)+")",values)
    c.commit();c.close()
    update_manifest(root, keyword)
    return root


def update_manifest(root, keyword=False):
    db=root/"evidence.sqlite"
    m={"schema":reader.SCHEMA,"version":"0.1.0" if keyword else "0.1.1","database":db.name,
       "database_sha256":hashlib.sha256(db.read_bytes()).hexdigest(),"bytes":db.stat().st_size,
       "status":"CANDIDATE_HELD","counts":{"declared_only":999}}
    if keyword:m["channel"]="mamey_regulator_keywords"
    (root/"RELEASE_MANIFEST.json").write_text(json.dumps(m))


def inspect(root, **kw):
    return reader.inspect_tool_database(root,"RELEASE_MANIFEST.json",**kw)


def test_readonly_metadata_and_exact_locus_pagination(tmp_path):
    fixture_db(tmp_path)
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    a=inspect(tmp_path,adapter="gene-census-v1",identity=ID,limit=2)
    b=inspect(tmp_path,adapter="gene-census-v1",identity=ID,limit=2,offset=2)
    assert a["results"]["total_records"]==3 and a["results"]["next_offset"]==2
    assert len(b["results"]["records"])==1 and b["results"]["next_offset"] is None
    assert all(x["exact_identity"]==DISPLAY and x["hold"]=="SOURCE_HOLD" for x in a["results"]["records"])
    assert a["declared_coverage_not_recomputed"]["counts"]=={"declared_only":999}
    assert a["results"]["observed_counts"]=={"loci":1,"genes":3}
    assert a["scientific_admission"]=="NOT_PERFORMED"
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}


def test_keyword_and_all_four_channels(tmp_path):
    fixture_db(tmp_path,True)
    for channel in reader.KEYWORD_CHANNELS:
        p=tmp_path/"RELEASE_MANIFEST.json";m=json.loads(p.read_text());m["channel"]=channel;p.write_text(json.dumps(m))
        result=inspect(tmp_path,adapter="keyword-gene-v1",identity=ID)
        assert result["results"]["observed_state_counts"]==[{"state":"HELD_SOURCE_ROW","rows":3}]
        assert result["results"]["records"][0]["state"]=="HELD_SOURCE_ROW"


def test_manifest_generic_does_not_claim_result_support(tmp_path):
    fixture_db(tmp_path)
    r=inspect(tmp_path,identity=ID)
    assert r["results"]["state"]=="RESULT_ADAPTER_NOT_SELECTED"
    assert r["results"]["locus_query_state"]=="NOT_SUPPORTED"
    assert "records" not in r["results"]


def test_missing_and_conflicting_identity(tmp_path):
    fixture_db(tmp_path)
    r=inspect(tmp_path,adapter="gene-census-v1",identity=(*ID[:3],"other"))
    assert r["results"]["locus_query_state"].startswith("LOCUS_NOT_FOUND")
    c=sqlite3.connect(tmp_path/"evidence.sqlite");c.execute("UPDATE locus SET exact_identity='wrong'");c.commit();c.close();update_manifest(tmp_path)
    assert inspect(tmp_path,adapter="gene-census-v1",identity=ID)["results"]["locus_query_state"]=="HELD_IDENTITY_CONFLICT"


@pytest.mark.parametrize("sql,state",[
    ("INSERT INTO locus SELECT * FROM locus","HELD_IDENTITY_CONFLICT"),
    ("INSERT INTO gene SELECT * FROM gene LIMIT 1","HELD_DUPLICATE_OR_NULL_GENE_ORDER"),
    ("DELETE FROM gene","LOCUS_PRESENT_NO_GENE_ROWS_HELD"),
])
def test_duplicate_or_empty_rows_held(tmp_path,sql,state):
    fixture_db(tmp_path);c=sqlite3.connect(tmp_path/"evidence.sqlite");c.execute(sql);c.commit();c.close();update_manifest(tmp_path)
    assert inspect(tmp_path,adapter="gene-census-v1",identity=ID)["results"]["locus_query_state"]==state


@pytest.mark.parametrize("kwargs,code",[
    ({"limit":0},"INVALID_PAGINATION"),({"limit":1001},"INVALID_PAGINATION"),
    ({"offset":-1},"INVALID_PAGINATION"),({"limit":True},"INVALID_PAGINATION"),
    ({"identity":("TEST-1","NODE_1","region001","cluster001")},"COMPLETE_EXACT_IDENTITY_REQUIRED"),
    ({"identity":("TEST-1","contig",None,"cluster001")},"COMPLETE_EXACT_IDENTITY_REQUIRED"),
    ({"identity":("only",)},"COMPLETE_EXACT_IDENTITY_REQUIRED"),
    ({"adapter":"unknown"},"UNSUPPORTED_ADAPTER"),
    ({"adapter":"keyword-gene-v1"},"ADAPTER_MANIFEST_VARIANT_MISMATCH"),
    ({"expected_manifest_sha256":"0"*64},"MANIFEST_HASH_MISMATCH"),
])
def test_argument_refusals(tmp_path,kwargs,code):
    fixture_db(tmp_path)
    with pytest.raises(reader.ToolDatabaseInspectionError,match=code):inspect(tmp_path,**kwargs)


@pytest.mark.parametrize("field,value,code",[
    ("database","../outside.sqlite","UNSAFE_RELATIVE_LOCATOR"),
    ("database","C:\\outside.sqlite","UNSAFE_RELATIVE_LOCATOR"),
    ("database","/outside.sqlite","UNSAFE_RELATIVE_LOCATOR"),
    ("bytes",True,"INVALID_DATABASE_HASH_OR_SIZE"),
    ("bytes",200,"DATABASE_SIZE_MISMATCH"),
    ("database_sha256","0"*64,"DATABASE_HASH_MISMATCH"),
    ("schema","unknown/1","UNSUPPORTED_MANIFEST_SCHEMA"),
    ("files",[],"MANIFEST_DATABASE_ENTRY_CONFLICT"),
])
def test_manifest_refusals(tmp_path,field,value,code):
    fixture_db(tmp_path);p=tmp_path/"RELEASE_MANIFEST.json";m=json.loads(p.read_text());m[field]=value;p.write_text(json.dumps(m))
    with pytest.raises(reader.ToolDatabaseInspectionError,match=code):inspect(tmp_path)


def test_duplicate_json_keys_and_missing_path(tmp_path):
    fixture_db(tmp_path);(tmp_path/"RELEASE_MANIFEST.json").write_text('{"schema":"a","schema":"b"}')
    with pytest.raises(reader.ToolDatabaseInspectionError,match="DUPLICATE_MANIFEST_KEY"):inspect(tmp_path)
    with pytest.raises(reader.ToolDatabaseInspectionError,match="INPUT_UNREADABLE_OR_MALFORMED"):inspect(tmp_path/"absent")
    assert not (tmp_path/"absent").exists()


@pytest.mark.parametrize("suffix",["-wal","-shm","-journal"])
def test_sidecars_refused(tmp_path,suffix):
    fixture_db(tmp_path);(tmp_path/("evidence.sqlite"+suffix)).write_bytes(b"held")
    with pytest.raises(reader.ToolDatabaseInspectionError,match="LIVE_OR_JOURNALED_DATABASE_REFUSED"):inspect(tmp_path)


def test_schema_views_refused(tmp_path):
    fixture_db(tmp_path);c=sqlite3.connect(tmp_path/"evidence.sqlite");c.execute("ALTER TABLE gene RENAME TO hidden_gene");c.execute("CREATE VIEW gene AS SELECT * FROM hidden_gene");c.commit();c.close();update_manifest(tmp_path)
    with pytest.raises(reader.ToolDatabaseInspectionError,match="ADAPTER_TABLE_SHAPE_MISMATCH"):inspect(tmp_path,adapter="gene-census-v1")


def test_symlink_refused(tmp_path):
    fixture_db(tmp_path);p=tmp_path/"link.json"
    try:p.symlink_to(tmp_path/"RELEASE_MANIFEST.json")
    except (OSError,NotImplementedError):pytest.skip("symlink creation unavailable on this platform")
    with pytest.raises(reader.ToolDatabaseInspectionError,match="SYMLINK_INPUT_REFUSED"):
        reader.inspect_tool_database(tmp_path,"link.json")


def test_read_transaction_enforces_no_write_and_checks_drift(tmp_path,monkeypatch):
    fixture_db(tmp_path);original=reader._adapter_report
    def adversarial(c,*args):
        with pytest.raises(sqlite3.OperationalError):c.execute("DELETE FROM gene")
        p=tmp_path/"RELEASE_MANIFEST.json";p.write_text(p.read_text()+" ")
        return original(c,*args)
    monkeypatch.setattr(reader,"_adapter_report",adversarial)
    with pytest.raises(reader.ToolDatabaseInspectionError,match="INPUT_CHANGED_DURING_INSPECTION"):inspect(tmp_path)


def test_pagination_beyond1000_and_manifest_pin(tmp_path):
    fixture_db(tmp_path,rows=1002);h=hashlib.sha256((tmp_path/"RELEASE_MANIFEST.json").read_bytes()).hexdigest()
    r=inspect(tmp_path,adapter="gene-census-v1",identity=ID,offset=1000,expected_manifest_sha256=h)
    assert len(r["results"]["records"])==2 and r["manifest_trust"]=="EXPECTED_HASH_MATCHED"


def test_wal_header_refused_without_sidecars(tmp_path):
    fixture_db(tmp_path);c=sqlite3.connect(tmp_path/"evidence.sqlite")
    c.execute("PRAGMA journal_mode=WAL");c.close();update_manifest(tmp_path)
    with pytest.raises(reader.ToolDatabaseInspectionError,match="WAL_OR_UNSUPPORTED_SQLITE_FORMAT"):inspect(tmp_path)


def test_cooperative_writer_cannot_commit_during_read(tmp_path,monkeypatch):
    fixture_db(tmp_path);original=reader._adapter_report
    def probe(c,*args):
        other=sqlite3.connect(tmp_path/"evidence.sqlite",timeout=0.01)
        try:
            other.execute("UPDATE gene SET product='changed'")
            with pytest.raises(sqlite3.OperationalError):other.commit()
        finally:other.rollback();other.close()
        return original(c,*args)
    monkeypatch.setattr(reader,"_adapter_report",probe)
    result=inspect(tmp_path,adapter="gene-census-v1",identity=ID)
    assert result["results"]["records"][0]["product"]=="fixture"


def test_unserializable_result_is_typed_hold(tmp_path):
    fixture_db(tmp_path);c=sqlite3.connect(tmp_path/"evidence.sqlite")
    c.execute("UPDATE gene SET product=?",(b'blob',));c.commit();c.close();update_manifest(tmp_path)
    with pytest.raises(reader.ToolDatabaseInspectionError,match="UNSUPPORTED_RESULT_VALUE"):
        inspect(tmp_path,adapter="gene-census-v1",identity=ID)


def test_cli_success_failure_help_and_no_write_mode(tmp_path):
    fixture_db(tmp_path/"inputs")
    code=Path(__file__).resolve().parents[1]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",MPLCONFIGDIR=str(tmp_path/"mpl"))
    base=[sys.executable,"-B",str(code/"mamey_run.py"),"tool-database-inspect"]
    def run(args):return subprocess.run(base+args,cwd=tmp_path,env=env,capture_output=True,text=True)
    out=run(["--root",str(tmp_path/"inputs"),"--manifest","RELEASE_MANIFEST.json","--adapter","gene-census-v1","--locus",*ID,"--limit","1"])
    assert out.returncode==0,out.stderr
    assert json.loads(out.stdout)["results"]["returned_records"]==1
    bad=run(["--root",str(tmp_path/"absent"),"--manifest","RELEASE_MANIFEST.json"])
    assert bad.returncode==2 and json.loads(bad.stdout)["status"]=="HELD"
    assert run(["--help"]).returncode==0
    assert run(["--sql","DELETE FROM gene"]).returncode!=0
    assert run(["--write"]).returncode!=0


def blastp_fixture(root, adapter="blastp-nr-v1", hsps=3):
    root.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(root/"evidence.sqlite")
    c.execute("PRAGMA journal_mode=MEMORY")
    swiss=adapter=="blastp-swissprot-v2"
    c.executescript('''
    CREATE TABLE metadata(key TEXT,value TEXT);
    CREATE TABLE partition(locus_key TEXT,exact_identity TEXT,gene_count INTEGER);
    CREATE TABLE binding(locus_key TEXT,gene_order INTEGER,locus_tag TEXT,query_sha256 TEXT,binding_state TEXT,strain TEXT,full_node TEXT,region TEXT,bgc_alias TEXT,exact_identity TEXT);
    ''')
    channel,version=reader.BLASTP_ADAPTERS[adapter]
    c.executemany("INSERT INTO metadata VALUES (?,?)",[("channel",channel),("schema_version",version)])
    c.execute("INSERT INTO partition VALUES (?,?,?)",("key",DISPLAY,4))
    for n,q in enumerate(("a"*64,"b"*64,"c"*64,None)):
        c.execute("INSERT INTO binding VALUES (?,?,?,?,?,?,?,?,?,?)",("key",n,"gene"+str(n),q,"CENSUS_SEQUENCE_BOUND",*ID,DISPLAY))
    evidence={"source_rank":1,"subject_length":200,"descriptions":[{"accession":"EXAMPLE","title":"recorded subject description"}],"hsps":[{"hsp_number":n+1,"alignment_columns":100,"identity_count":91,"positive_count":97,"query_from":1,"query_to":100,"evalue":1e-20,"bitscore":50,"extra_preserved":"yes"} for n in range(hsps)],"query_union_coverage_pct":50,"annotation_authority":"SUBJECT_DESCRIPTION_NOT_QUERY_FUNCTION"}
    raw=json.dumps(evidence)
    if swiss:
        c.executescript('''
        CREATE TABLE protein(query_sha256 TEXT,aa_length INTEGER,state TEXT);
        CREATE TABLE outcome(query_sha256 TEXT,dataset_id TEXT,batch_index INTEGER,observation TEXT,hit_count INTEGER,receipt_query_json TEXT);
        CREATE TABLE dataset(dataset_id TEXT,provenance_json TEXT);
        CREATE TABLE batch(dataset_id TEXT,batch_index INTEGER,provenance_json TEXT);
        CREATE TABLE source_metadata(key TEXT,value TEXT);
        CREATE TABLE _query_key(id INTEGER,query_sha256 TEXT);
        CREATE TABLE _hit_pack(query_id INTEGER,source_texts_zlib BLOB,uncompressed_sha256 TEXT);
        CREATE TABLE _subject(id INTEGER,details_json TEXT);
        CREATE TABLE _hit(query_id INTEGER,source_rank INTEGER,subject_id INTEGER,query_union_coverage_pct REAL);
        ''')
        for q,state in (("a"*64,"VERIFIED_HITS"),("b"*64,"VERIFIED_NO_HIT"),("c"*64,"NO_VERIFIED_SEARCH")):
            c.execute("INSERT INTO protein VALUES (?,?,?)",(q,200,state))
        c.execute("INSERT INTO dataset VALUES (?,?)",("dataset",'{"run_inputs_sha256":"recorded"}'))
        c.execute("INSERT INTO batch VALUES (?,?,?)",("dataset",1,'{"raw_xml_sha256":"recorded"}'))
        for q,count,obs in (("a"*64,1,"HITS_UNDER_RECORDED_SETTINGS"),("b"*64,0,"NO_HIT_UNDER_RECORDED_SETTINGS_NOT_BIOLOGICAL_ABSENCE")):
            c.execute("INSERT INTO outcome VALUES (?,?,?,?,?,?)",(q,"dataset",1,obs,count,'{}'))
        packed=json.dumps([raw]).encode()
        c.execute("INSERT INTO _query_key VALUES (?,?)",(1,"a"*64))
        c.execute("INSERT INTO _hit_pack VALUES (?,?,?)",(1,zlib.compress(packed),hashlib.sha256(packed).hexdigest()))
        c.execute("INSERT INTO _subject VALUES (?,?)",(1,'["EXAMPLE","recorded subject description",200]'))
        c.execute("INSERT INTO _hit VALUES (?,?,?,?)",(1,1,1,50))
    else:
        c.executescript('''
        CREATE TABLE protein(query_sha256 TEXT,protein_length INTEGER,availability_state TEXT,search_count INTEGER);
        CREATE TABLE search(id INTEGER,xml_id INTEGER,query_sha256 TEXT,query_title TEXT,observation TEXT,query_proof_json TEXT,admission_state TEXT);
        CREATE TABLE hit(search_id INTEGER,source_rank INTEGER,all_evidence_zlib BLOB);
        CREATE TABLE source_xml(id INTEGER,original_locator TEXT,sha256 TEXT,source_status TEXT,detail TEXT,channel TEXT);
        CREATE TABLE source_metadata(xml_id INTEGER,metadata_json TEXT);
        CREATE TABLE source_job(id INTEGER,xml_id INTEGER,source_provenance_zlib BLOB,source_status TEXT);
        ''')
        for q,state,n in (("a"*64,"VERIFIED_MIXED_OUTCOMES",2),("b"*64,"VERIFIED_NO_HIT",1),("c"*64,"NO_VERIFIED_SEARCH",0)):
            c.execute("INSERT INTO protein VALUES (?,?,?,?)",(q,200,state,n))
        c.execute("INSERT INTO source_xml VALUES (?,?,?,?,?,?)",(1,"recorded/source.xml","d"*64,"RECORDED",None,channel))
        c.execute("INSERT INTO source_metadata VALUES (?,?)",(1,'{"parameters":[{"expect":"1e-5"}]}'))
        c.execute("INSERT INTO source_job VALUES (?,?,?,?)",(1,1,zlib.compress(b'{"retention_limit":10}'),"RECORDED"))
        for sid,q,obs in ((1,"a"*64,"HITS_UNDER_RECORDED_SETTINGS"),(2,"a"*64,"NO_HIT_UNDER_RECORDED_SETTINGS_NOT_BIOLOGICAL_ABSENCE"),(3,"b"*64,"NO_HIT_UNDER_RECORDED_SETTINGS_NOT_BIOLOGICAL_ABSENCE")):
            c.execute("INSERT INTO search VALUES (?,?,?,?,?,?,?)",(sid,1,q,"recorded query label",obs,'[]',"SEQUENCE_BOUND_CURRENT_LOCUS_PROJECTION"))
        c.execute("INSERT INTO hit VALUES (?,?,?)",(1,1,zlib.compress(raw.encode())))
    c.commit();c.close()
    blastp_manifest(root,adapter)
    return evidence


def blastp_manifest(root,adapter):
    db=root/"evidence.sqlite";channel,version=reader.BLASTP_ADAPTERS[adapter]
    (root/"RELEASE_MANIFEST.json").write_text(json.dumps({"schema":reader.SCHEMA,"channel":channel,"version":version,"database":db.name,"database_sha256":hashlib.sha256(db.read_bytes()).hexdigest(),"bytes":db.stat().st_size}))


@pytest.mark.parametrize("adapter",reader.BLASTP_ADAPTERS)
def test_blastp_all_states_and_raw_hsp_pagination(tmp_path,adapter):
    e=blastp_fixture(tmp_path,adapter,hsps=1002)
    kw=dict(adapter=adapter,identity=ID)
    r=inspect(tmp_path,**kw,limit=2)["results"]
    assert r["next_offset"]==2 and r["total_records"]==4
    assert r["records"][0]["availability_state"]==("VERIFIED_HITS" if "swiss" in adapter else "VERIFIED_MIXED_OUTCOMES")
    other=inspect(tmp_path,**kw,offset=2)["results"]["records"]
    assert [x["availability_state"] for x in other]==["NO_VERIFIED_SEARCH","MISSING_OR_UNBOUND_PROTEIN_HOLD"]
    searches=inspect(tmp_path,**kw,gene_order=0,view="searches",limit=1)["results"]
    assert searches["records"][0]["search_id"]==1
    if "swiss" not in adapter:
        assert searches["next_offset"]==1
        assert "NO_HIT" in inspect(tmp_path,**kw,gene_order=0,view="searches",offset=1)["results"]["records"][0]["observation"]
    hit=inspect(tmp_path,**kw,gene_order=0,view="hits",search_id=1)["results"]["records"][0]
    assert hit["retained_hsp_count"]==1002 and "hsps" not in hit["evidence"]
    hs=inspect(tmp_path,**kw,gene_order=0,view="hsps",search_id=1,hit_rank=1,offset=1000)["results"]
    assert hs["records"]==e["hsps"][1000:] and hs["next_offset"] is None
    assert inspect(tmp_path,**kw,gene_order=2,view="searches")["results"]["total_records"]==0
    assert inspect(tmp_path,**kw,gene_order=3,view="searches")["results"]["gene_query_state"]=="MISSING_OR_UNBOUND_PROTEIN_HOLD"


@pytest.mark.parametrize("kw,code",[
    ({"view":"hsps","gene_order":0,"search_id":1},"INCOMPLETE_OR_CONFLICTING_BLASTP_SELECTOR"),
    ({"view":"searches"},"INCOMPLETE_OR_CONFLICTING_BLASTP_SELECTOR"),
    ({"view":"hits","gene_order":0,"search_id":3},"SEARCH_NOT_BOUND_TO_EXACT_GENE"),
    ({"view":"hsps","gene_order":0,"search_id":1,"hit_rank":9},"HIT_NOT_BOUND_TO_EXACT_SEARCH"),
    ({"gene_order":True},"INVALID_BLASTP_SELECTOR"),
    ({"view":"arbitrary"},"INVALID_BLASTP_SELECTOR"),
])
def test_blastp_selector_holds(tmp_path,kw,code):
    blastp_fixture(tmp_path)
    with pytest.raises(reader.ToolDatabaseInspectionError,match=code):
        inspect(tmp_path,adapter="blastp-nr-v1",identity=ID,**kw)


@pytest.mark.parametrize("sql,code",[
    ("UPDATE binding SET exact_identity='conflicting' WHERE gene_order=0","HELD_IDENTITY_OR_ROSTER_CONFLICT"),
    ("UPDATE binding SET gene_order=0 WHERE gene_order=1","HELD_DUPLICATE_OR_NULL_GENE_ORDER"),
    ("INSERT INTO partition SELECT * FROM partition","HELD_IDENTITY_CONFLICT"),
    ("UPDATE metadata SET value='wrong' WHERE key='channel'","ADAPTER_METADATA_VARIANT_MISMATCH"),
    ("UPDATE protein SET search_count=9 WHERE query_sha256 LIKE 'a%'","SEARCH_COUNT_CONFLICT"),
])
def test_blastp_schema_and_identity_holds(tmp_path,sql,code):
    blastp_fixture(tmp_path);c=sqlite3.connect(tmp_path/"evidence.sqlite");c.execute("PRAGMA journal_mode=MEMORY");c.execute(sql);c.commit();c.close();blastp_manifest(tmp_path,"blastp-nr-v1")
    with pytest.raises(reader.ToolDatabaseInspectionError,match=code):inspect(tmp_path,adapter="blastp-nr-v1",identity=ID)


def test_swiss_pack_hash_and_foreign_search_refused(tmp_path):
    blastp_fixture(tmp_path,"blastp-swissprot-v2")
    with pytest.raises(reader.ToolDatabaseInspectionError,match="SEARCH_NOT_BOUND_TO_EXACT_GENE"):
        inspect(tmp_path,adapter="blastp-swissprot-v2",identity=ID,gene_order=0,view="hits",search_id=2)
    c=sqlite3.connect(tmp_path/"evidence.sqlite");c.execute("PRAGMA journal_mode=MEMORY");c.execute("UPDATE _hit_pack SET uncompressed_sha256=?",("0"*64,));c.commit();c.close();blastp_manifest(tmp_path,"blastp-swissprot-v2")
    with pytest.raises(reader.ToolDatabaseInspectionError,match="EVIDENCE_PACK_HASH_MISMATCH"):
        inspect(tmp_path,adapter="blastp-swissprot-v2",identity=ID,gene_order=0,view="hits",search_id=1)


@pytest.mark.parametrize("raw,code",[
    (b'not zlib',"INVALID_COMPRESSED_EVIDENCE"),
    (zlib.compress(b'{}')+b'trailing',"INVALID_COMPRESSED_EVIDENCE"),
    (zlib.compress(b'{}')[:-1],"INVALID_COMPRESSED_EVIDENCE"),
    (zlib.compress(b'{"a":1,"a":2}'),"DUPLICATE_MANIFEST_KEY"),
    (zlib.compress(b'{"value":NaN}'),"NONFINITE_EVIDENCE_HOLD"),
])
def test_blastp_bad_compression_and_json(raw,code):
    with pytest.raises(reader.ToolDatabaseInspectionError,match=code):reader._unpack(raw)


def test_blastp_decompression_budget(monkeypatch):
    monkeypatch.setattr(reader,"PACK_LIMIT",1024)
    with pytest.raises(reader.ToolDatabaseInspectionError,match="DECOMPRESSED_EVIDENCE_SIZE_HOLD"):
        reader._unpack(zlib.compress(b' '*2048))


@pytest.mark.parametrize("adapter",reader.BLASTP_ADAPTERS)
def test_blastp_hit_pagination_over1000(tmp_path,adapter):
    e=blastp_fixture(tmp_path,adapter,hsps=1);c=sqlite3.connect(tmp_path/"evidence.sqlite");c.execute("PRAGMA journal_mode=MEMORY")
    if "swiss" in adapter:
        texts=[]
        for rank in range(1,1003):
            e["source_rank"]=rank;texts.append(json.dumps(e))
            if rank>1:c.execute("INSERT INTO _hit VALUES (?,?,?,?)",(1,rank,1,50))
        raw=json.dumps(texts).encode();c.execute("UPDATE _hit_pack SET source_texts_zlib=?,uncompressed_sha256=?",(zlib.compress(raw),hashlib.sha256(raw).hexdigest()))
        c.execute("UPDATE outcome SET hit_count=1002 WHERE query_sha256=?",("a"*64,))
    else:
        for rank in range(2,1003):
            e["source_rank"]=rank;c.execute("INSERT INTO hit VALUES (?,?,?)",(1,rank,zlib.compress(json.dumps(e).encode())))
    c.commit();c.close();blastp_manifest(tmp_path,adapter)
    r=inspect(tmp_path,adapter=adapter,identity=ID,gene_order=0,view="hits",search_id=1,offset=1000)["results"]
    assert r["total_records"]==1002 and r["next_offset"] is None
    assert [h["evidence"]["source_rank"] for h in r["records"]]==[1001,1002]


@pytest.mark.parametrize("sql,view,code",[
    ("UPDATE protein SET availability_state='VERIFIED_HITS' WHERE query_sha256 LIKE 'a%'","genes","PROTEIN_STATE_OR_LENGTH_CONFLICT"),
    ("UPDATE search SET observation='unknown' WHERE id=1","genes","UNKNOWN_SEARCH_OBSERVATION_HOLD"),
    ("UPDATE search SET id=1 WHERE id=2","genes","DUPLICATE_SEARCH_ID_HOLD"),
    ("UPDATE hit SET search_id=2","searches","SEARCH_OBSERVATION_HIT_COUNT_CONFLICT"),
    ("UPDATE hit SET search_id=2","hits","SEARCH_OBSERVATION_HIT_COUNT_CONFLICT"),
    ("UPDATE source_xml SET channel='wrong'","hits","SEARCH_SOURCE_CHANNEL_CONFLICT"),
])
def test_blastp_contradictory_history_refused(tmp_path,sql,view,code):
    blastp_fixture(tmp_path);c=sqlite3.connect(tmp_path/"evidence.sqlite");c.execute("PRAGMA journal_mode=MEMORY");c.execute(sql);c.commit();c.close();blastp_manifest(tmp_path,"blastp-nr-v1")
    kw={} if view=="genes" else {"gene_order":0,"view":view}
    if view=="hits":kw["search_id"]=1
    with pytest.raises(reader.ToolDatabaseInspectionError,match=code):inspect(tmp_path,adapter="blastp-nr-v1",identity=ID,**kw)


def test_blastp_cli_selectors(tmp_path):
    blastp_fixture(tmp_path)
    from mamey.cli import build_parser
    args=build_parser().parse_args(["tool-database-inspect","--root",str(tmp_path),"--manifest","RELEASE_MANIFEST.json","--adapter","blastp-nr-v1","--locus",*ID,"--gene-order","0","--view","hsps","--search-id","1","--hit-rank","1","--offset","2"])
    assert args.func(args)==0
