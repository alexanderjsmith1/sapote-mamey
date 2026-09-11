"""Generic adversarial 16S data and additive-output regression tests; no live services."""
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import _phylo16s as common
import phylo_16s_build_db as build
import phylo_16s_fetch as fetch
import phylo_16s_esearch as search
import phylo_16s_rank as rank
import phylo_16s_from_genome as genome
import phylo_16s_audit_merges as audit
import phylo_16s_panel as panel


def row(acc='AB123456.2',seq=None,source='pdf_candidate',designation='REF_A'):
    return (acc.split('.')[0],acc,source,'Example bacterium 16S ribosomal RNA gene',
            'Example bacterium','Example',designation,'[]',None,seq,len(seq) if seq else None,
            None,'fixture',0)


def database(tmp_path,rows=None):
    db=tmp_path/'input.sqlite'
    with sqlite3.connect(db) as con:
        con.executescript(build.SCHEMA)
        for values in rows or [row()]:build.upsert(con,[values],values[2])
    return db


def gb(acc='AB123456.2',seq='ACGT'*150,compound=False):
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature,SimpleLocation,CompoundLocation
    rec=SeqRecord(Seq(seq),id=acc,name=acc.split('.')[0],
                  description='Example bacterium 16S ribosomal RNA gene')
    rec.annotations={'molecule_type':'DNA','accessions':[acc.split('.')[0]],
                     'sequence_version':int(acc.split('.')[1]),'organism':'Example bacterium',
                     'taxonomy':['Bacteria','Unrankedlineageia','Exampleales']}
    location=(CompoundLocation([SimpleLocation(0,300),SimpleLocation(300,len(seq))])
              if compound else SimpleLocation(0,len(seq)))
    rec.features=[SeqFeature(location,type='source',qualifiers={
        'organism':['Example bacterium'],'strain':['R_A'],
        'isolation_source':['a long source description repeated to exercise a multiline qualifier '*3],
        'geo_loc_name':['Exampleland: District, Site']})]
    out=io.StringIO();SeqIO.write(rec,out,'genbank');return out.getvalue()


def event(db):
    with sqlite3.connect(db) as con:
        return json.loads(con.execute('SELECT details_json FROM operation_event ORDER BY event_id DESC').fetchone()[0])


@pytest.mark.parametrize('compound',[False,True])
def test_terminal_source_and_compound_location_parse(compound):
    data=fetch.parse_gb(gb(compound=compound))
    assert data['strain']=='R_A' and 'multiline qualifier' in data['isolation_source']
    assert data['geo_loc_name']=='Exampleland: District, Site'
    assert data['country']=='Exampleland'
    assert data.get('subregion') is None and data.get('class_') is None
    assert data['seq']=='ACGT'*150 and data['acc_version']=='AB123456.2'


@pytest.mark.parametrize('text,requested',[
    (gb('AB123456.3'),['AB123456.2']),
    (gb('AB123457.2'),['AB123456.2']),
    (gb()+gb(),['AB123456.2']),
    (gb().replace('//',''),['AB123456.2'])])
def test_batch_rejects_wrong_versions_unknown_duplicate_and_truncated(text,requested):
    with pytest.raises(ValueError):fetch.bind_batch(text,requested)


def test_fetch_partial_failure_nonzero_and_input_immutable(tmp_path,monkeypatch):
    db=database(tmp_path,[row(),row('AB123457.2')]);before=db.read_bytes()
    monkeypatch.setattr(fetch,'fetch_batch',lambda ids:gb())
    monkeypatch.setattr(fetch.time,'sleep',lambda x:None)
    out=tmp_path/'fetched.sqlite'
    assert fetch.main(['--db',str(db),'--out-db',str(out),'--no-cache'])==1
    assert db.read_bytes()==before
    receipt=event(out)
    assert receipt['status']=='PARTIAL_WITH_HOLDS'
    assert [x['status'] for x in receipt['results']]==['STORED','NOT_RETURNED']
    with sqlite3.connect(out) as con:
        stored=con.execute('SELECT seq_len,seq_md5,seq_sha256 FROM record WHERE acc_base="AB123456"').fetchone()
    assert stored==(600,hashlib.md5(('ACGT'*150).encode()).hexdigest(),hashlib.sha256(('ACGT'*150).encode()).hexdigest())
    assert not (tmp_path/'gb_cache').exists()


def test_fetch_wrong_batch_never_updates_unrequested_record(tmp_path,monkeypatch):
    db=database(tmp_path,[row(),row('AB123457.2',source='external')])
    monkeypatch.setattr(fetch,'fetch_batch',lambda ids:gb('AB123457.2'))
    out=tmp_path/'held.sqlite'
    assert fetch.main(['--db',str(db),'--out-db',str(out)])==1
    with sqlite3.connect(out) as con:assert con.execute('SELECT count(*) FROM record WHERE seq IS NOT NULL').fetchone()[0]==0
    assert not (tmp_path/'gb_cache').exists()


def test_cache_bound_to_selected_database(tmp_path,monkeypatch):
    selected=tmp_path/'selected';selected.mkdir();db=database(selected)
    wrong=tmp_path/'wrong';wrong.mkdir()
    monkeypatch.setattr(fetch,'DB',str(wrong/'other.sqlite'))
    monkeypatch.delenv('SAPOTE_16S_GB_CACHE',raising=False)
    monkeypatch.setattr(fetch,'fetch_batch',lambda ids:gb())
    monkeypatch.setattr(fetch.time,'sleep',lambda x:None)
    assert fetch.main(['--db',str(db),'--out-db',str(tmp_path/'out.sqlite')])==0
    assert len(list((selected/'gb_cache'/common.sha256_file(db)).glob('*.gb')))==1
    assert list(wrong.iterdir())==[]


@pytest.mark.parametrize('module',[fetch,search,rank,audit])
def test_all_database_dry_runs_have_no_disk_or_network_mutation(tmp_path,monkeypatch,module):
    db=database(tmp_path);before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    monkeypatch.setattr(fetch,'fetch_batch',lambda *a,**k:pytest.fail('dry run fetched'))
    monkeypatch.setattr(search,'esearch',lambda *a,**k:pytest.fail('dry run searched'))
    monkeypatch.setattr(audit,'align',lambda *a,**k:pytest.fail('dry run aligned'))
    assert module.main(['--db',str(db),'--dry-run'])==0
    assert {p.name:p.read_bytes() for p in tmp_path.iterdir()}==before


@pytest.mark.parametrize('body',[
    '<eSummaryResult><DocSum><Id>2</Id><Item Name="AccessionVersion">AB123456.2</Item></DocSum></eSummaryResult>',
    '<eSummaryResult><DocSum><Id>1</Id></DocSum></eSummaryResult>',
    '<eSummaryResult><DocSum><Id>1</Id><Item Name="AccessionVersion">AB123456.2</Item></DocSum><DocSum><Id>1</Id><Item Name="AccessionVersion">AB123457.2</Item></DocSum></eSummaryResult>'])
def test_esummary_exact_uid_binding(body,monkeypatch):
    monkeypatch.setattr(search.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=body))
    monkeypatch.setattr(search.time,'sleep',lambda x:None)
    with pytest.raises(SystemExit):search.acc_for(['1'])


def test_esearch_incomplete_count_publishes_nothing(tmp_path,monkeypatch):
    db=database(tmp_path);before=db.read_bytes();out=tmp_path/'out.sqlite'
    monkeypatch.setattr(search,'esearch',lambda *a:(['1'],2,False))
    with pytest.raises(ValueError,match='completeness'):
        search.main(['--db',str(db),'--out-db',str(out),'--sets','moss'])
    assert not out.exists() and db.read_bytes()==before


def test_esearch_full_result_on_fresh_schema_is_additive(tmp_path,monkeypatch):
    db=database(tmp_path);out=tmp_path/'out.sqlite'
    monkeypatch.setattr(search,'esearch',lambda *a:(['9'],1,True))
    monkeypatch.setattr(search,'acc_for',lambda *a:['AB123459.3'])
    assert search.main(['--db',str(db),'--out-db',str(out),'--sets','moss'])==0
    with sqlite3.connect(out) as con:
        assert con.execute('SELECT acc_version,seq FROM record WHERE acc_base="AB123459"').fetchone()==('AB123459.3',None)
        assert con.execute('SELECT tag FROM record_tag').fetchone()[0]=='query:moss'


@pytest.mark.parametrize('body',['>x a\nACGT\n>x b\nTGCA\n','ACGT\n>x\nACGT\n','>x\n','>x\nACGZ\n'])
def test_fasta_identity_and_missingness_refusals(tmp_path,body):
    file=tmp_path/'input.fa';file.write_text(body)
    with pytest.raises(ValueError):common.read_fasta(file)


def test_build_local_record_is_not_accession_and_schema_supports_rank(tmp_path):
    fa=tmp_path/'input.fa';fa.write_text('>QUERY_A\n'+'acgt'*150+'\n')
    db=tmp_path/'built.sqlite'
    assert build.main(['--db',str(db),'--authoritative-fasta',str(fa)])==0
    with sqlite3.connect(db) as con:
        stored=con.execute('SELECT * FROM record').fetchone()
        assert stored[0].startswith('LOCAL:') and stored[1] is None and stored[8] is None
        con.row_factory=sqlite3.Row
        rec=dict(con.execute('SELECT * FROM record').fetchone())
        assert panel._versioned(rec)==''
    ranked=tmp_path/'ranked.sqlite'
    assert rank.main(['--db',str(db),'--out-db',str(ranked)])==0
    assert event(ranked)['rescue_status']=='NOT_MEASURED'
    with sqlite3.connect(ranked) as con:
        assert con.execute('SELECT priority_reason FROM record').fetchone()[0].endswith('not established by these tags')
        assert con.execute('SELECT sequence_status FROM panel_candidates').fetchone()[0]=='AVAILABLE'


def test_builder_explicit_sources_and_additive_outputs(tmp_path):
    out=tmp_path/'out.sqlite'
    with pytest.raises(SystemExit):build.main(['--db',str(out)])
    assert not out.exists()
    missing=tmp_path/'missing.fa'
    with pytest.raises(FileNotFoundError):build.main(['--db',str(out),'--authoritative-fasta',str(missing)])
    fa=tmp_path/'ok.fa';fa.write_text('>QUERY_A\nACGT\n')
    before=set(tmp_path.iterdir())
    assert build.main(['--db',str(out),'--authoritative-fasta',str(fa),'--dry-run'])==0
    assert set(tmp_path.iterdir())==before
    out.write_text('existing')
    with pytest.raises(ValueError,match='exists'):build.main(['--db',str(out),'--authoritative-fasta',str(fa)])
    assert out.read_text()=='existing'


def test_accession_provenance_requires_sequence_hash(tmp_path):
    fa=tmp_path/'input.fa';fa.write_text('>QUERY_A\nACGT\n')
    prov=tmp_path/'metadata.tsv';prov.write_text('strain\taccession\tsequence_sha256\nQUERY_A\tAB123456.2\twrong\n')
    with pytest.raises(ValueError,match='sequence_sha256'):
        build.main(['--db',str(tmp_path/'out.sqlite'),'--authoritative-fasta',str(fa),'--provenance',str(prov)])
    assert not (tmp_path/'out.sqlite').exists()


def test_duplicate_accession_conflicts_hold_even_stronger_source():
    con=sqlite3.connect(':memory:');con.executescript(build.SCHEMA)
    build.upsert(con,[row(seq='ACGT',source='nontype_fetch')],'nontype_fetch')
    with pytest.raises(ValueError,match='conflicting'):
        build.upsert(con,[row(seq='TGCA',source='as_governed')],'as_governed')


def test_collection_identifier_is_not_type_evidence():
    assert build.parse_title('Example bacterium strain DSM 12345')[3] is False


def test_missing_hit_identity_does_not_become_zero_or_rescue(tmp_path,monkeypatch):
    hits=tmp_path/'hits.tsv';hits.write_text('strain\taccession\tpct_identity\nQUERY_A\tAB123456\t\nQUERY_A\tAB123457\t97.5\n')
    monkeypatch.setattr(rank,'PDFHITS',str(hits))
    assert rank.rescue_tags()==({},0)


def test_rank_replaces_stale_generated_tags_but_preserves_search_tags(tmp_path):
    db=database(tmp_path,[row(seq='ACGT'*150)])
    with sqlite3.connect(db) as con:
        fetch.ensure_columns(con)
        con.executemany('INSERT INTO record_tag VALUES (?,?,?)',[
            ('AB123456','host:bee','stale'),('AB123456','query:moss','query')])
    out=tmp_path/'ranked.sqlite';rank.main(['--db',str(db),'--out-db',str(out)])
    with sqlite3.connect(out) as con:
        tags={r[0] for r in con.execute('SELECT tag FROM record_tag')}
        assert 'host:bee' not in tags and 'query:moss' in tags


def mock_extraction(tmp_path,monkeypatch,output):
    fa=tmp_path/'genome.fa';fa.write_text('>contig description\n'+'ACGTRY'*600+'\n')
    stage=tmp_path/'stage';stage.mkdir()
    monkeypatch.setattr(genome._p16,'space_free_workdir',lambda *a:str(stage))
    monkeypatch.setattr(genome._p16,'stage_blastdb',lambda *a:'db')
    monkeypatch.setattr(genome._p16,'stage_file',lambda *a:'query')
    monkeypatch.setattr(genome._p16,'blast_bin',lambda *a:'blastn')
    monkeypatch.setattr(genome._p16,'run_checked',lambda *a,**k:SimpleNamespace(stdout=output))
    return fa,stage


def test_two_opposite_loci_on_one_contig_keep_local_orientation(tmp_path,monkeypatch):
    output='contig\t1\t600\t1\t600\t99\t600\tAB123456.2\ncontig\t1801\t2400\t600\t1\t98\t600\tAB123457.2\n'
    fa,stage=mock_extraction(tmp_path,monkeypatch,output);events=[]
    rows=genome.extract(fa,500,False,1,events)
    assert rows[0][6]=='ACGTRY'*100
    assert rows[1][6]==genome.rc('ACGTRY'*100)
    assert [r['orientation_relative_to_reference'] for r in events]==['forward','reverse']
    assert rows[1][4:6]==(98.0,'AB123457.2') and not stage.exists()


@pytest.mark.parametrize('output',[
    'contig\t1\t600\t1\t600\t99\t600\tAB123456.2\ncontig\t1\t600\t600\t1\t99\t600\tAB123456.2\n',
    'unknown\t1\t600\t1\t600\t99\t600\tAB123456.2\n',
    'contig\t1\t9000\t1\t600\t99\t600\tAB123456.2\n',
    'garbage'])
def test_extraction_ambiguous_or_unbound_results_fail_closed(tmp_path,monkeypatch,output):
    fa,stage=mock_extraction(tmp_path,monkeypatch,output)
    with pytest.raises(ValueError):genome.extract(fa,500,False,1)
    assert not stage.exists()


def test_reverse_query_coordinates_and_iupac_complement(tmp_path,monkeypatch):
    fa,stage=mock_extraction(tmp_path,monkeypatch,'contig\t600\t1\t1\t600\t99\t600\tAB123456.2\n')
    assert genome.extract(fa,500,False,1)[0][6]==genome.rc('ACGTRY'*100)
    assert genome.rc('ACGTRYSWKMBDHVN')=='NBDHVKMWSRYACGT'


def test_genome_missing_input_and_duplicate_paths_never_create_output(tmp_path):
    out=tmp_path/'out.fa'
    with pytest.raises(FileNotFoundError):genome.main([str(tmp_path/'missing.fa'),'--out',str(out)])
    assert not out.exists()
    fa=tmp_path/'g.fa';fa.write_text('>x\nACGT\n')
    with pytest.raises(SystemExit):genome.main([str(fa),str(fa),'--out',str(out)])
    assert not out.exists()


def test_alignment_identity_excludes_all_ambiguous_bases():
    assert audit.ident('NNR-Y','NNA-Y')==(None,0)
    assert audit.ident('AcGTN','ACGAN')==(75.0,4)
    with pytest.raises(ValueError):audit.ident('AAA','AA')


@pytest.mark.parametrize('stdout',['>a\nACGT\n','>a\nACGT\n>b\nTGCA\n','>a\nACGT\n>a\nACGT\n','>a\nACGT\n>b\nACG-T\n'])
def test_mafft_alignment_requires_exact_ids_sequences_and_equal_columns(monkeypatch,stdout):
    monkeypatch.setattr(audit._p16,'mafft_bin',lambda:'mafft')
    monkeypatch.setattr(audit._p16,'run_checked',lambda *a,**k:SimpleNamespace(stdout=stdout))
    with pytest.raises(ValueError):audit.align('ACGT','ACGT')


def test_input_wal_state_is_explicit_hold(tmp_path):
    db=database(tmp_path);Path(str(db)+'-wal').write_bytes(b'pending')
    with pytest.raises(ValueError,match='WAL'):common.database_copy(str(db))


def test_blast_alias_refused_before_staging(tmp_path):
    prefix=tmp_path/'alias';Path(str(prefix)+'.nal').write_text('DBLIST other\n')
    stage=tmp_path/'stage';stage.mkdir()
    with pytest.raises(ValueError,match='alias'):common.stage_blastdb(prefix,stage)
    assert list(stage.iterdir())==[]


def test_panel_local_query_retains_record_key_without_fake_accession(tmp_path):
    fa=tmp_path/'input.fa';fa.write_text('>QUERY_A\n'+'ACGT'*150+'\n')
    db=tmp_path/'built.sqlite';build.main(['--db',str(db),'--authoritative-fasta',str(fa)])
    args=SimpleNamespace(strains='QUERY_A',set=None,genus=None,refs='type:0x',habitat_tags=None,scope_genus=None,outgroup=None)
    with sqlite3.connect(db) as con:records,counts=panel.prepare_panel(con,args)
    assert records[0]['accession']=='' and records[0]['record_key'].startswith('LOCAL:')
    assert 'LOCAL:' not in records[0]['label']


def test_duplicate_genome_content_refuses_even_with_distinct_filenames(tmp_path):
    a,b=tmp_path/'first.fa',tmp_path/'second.fa'
    a.write_text('>contig\nACGT\n');b.write_text(a.read_text())
    with pytest.raises(SystemExit,match='2'):
        genome.main([str(a),str(b),'--out',str(tmp_path/'out.fa')])
    assert not (tmp_path/'out.fa').exists()


def test_build_refseq_rejects_bad_rows_and_cleans_staging(tmp_path,monkeypatch):
    stage=tmp_path/'stage';stage.mkdir()
    monkeypatch.setattr(build._p16,'space_free_workdir',lambda *a:str(stage))
    monkeypatch.setattr(build._p16,'stage_blastdb',lambda *a:'db')
    monkeypatch.setattr(build._p16,'blast_bin',lambda *a:'blastdbcmd')
    monkeypatch.setattr(build._p16,'run_checked',lambda *a,**k:SimpleNamespace(stdout='malformed'))
    con=sqlite3.connect(':memory:');con.executescript(build.SCHEMA)
    with pytest.raises(ValueError,match='malformed'):build.ingest_refseq(con)
    assert not stage.exists()
    assert con.execute('SELECT count(*) FROM record').fetchone()[0]==0


def test_database_output_refuses_alias_of_input(tmp_path):
    db=database(tmp_path);alias=tmp_path/'alias.sqlite';alias.symlink_to(db)
    with pytest.raises(ValueError,match='exists'):rank.main(['--db',str(db),'--out-db',str(alias)])


def test_stage_copy_fallback_preserves_volume_content(tmp_path,monkeypatch):
    source=tmp_path/'source with spaces';source.mkdir()
    prefix=source/'reference';(source/'reference.nin').write_bytes(b'volume')
    stage=tmp_path/'stage';stage.mkdir()
    def fail(*args,**kwargs):raise OSError('symlinks unavailable')
    monkeypatch.setattr(common.os,'symlink',fail)
    result=common.stage_blastdb(prefix,stage)
    assert Path(result+'.nin').read_bytes()==b'volume'
    assert not Path(result+'.nin').is_symlink()


def test_missing_binary_is_not_a_measurement():
    with pytest.raises(SystemExit,match='no measurement'):
        common.run_checked(['/nonexistent-generic-16s-binary'],'fixture')


def test_alignment_audit_keeps_original_kmer_note(tmp_path,monkeypatch):
    db=database(tmp_path,[row(seq='ACGT'*150),row('AB123457.2',seq='ACGT'*150)])
    with sqlite3.connect(db) as con:
        con.execute('INSERT INTO merge_audit VALUES (?,?,?,?,?)',('GROUP:fixture','AB123456','AB123457',0.8,'original screen'))
    monkeypatch.setattr(audit,'align',lambda a,b:(a,b))
    out=tmp_path/'audit.sqlite';audit.main(['--db',str(db),'--out-db',str(out)])
    with sqlite3.connect(out) as con:
        assert con.execute('SELECT note FROM merge_audit').fetchone()[0]=='original screen'
        assert con.execute('SELECT status FROM merge_alignment_screen').fetchone()[0]=='SIMILARITY_SCREEN_PASS'
    assert event(out)['status']=='MERGE_ACCEPTANCE_HELD'


def test_known_genome_records_are_held_without_remote_full_genome_fetch(tmp_path,monkeypatch):
    db=database(tmp_path)
    with sqlite3.connect(db) as con:con.execute('UPDATE record SET seq_len=5000000')
    monkeypatch.setattr(fetch,'fetch_batch',lambda *a,**k:pytest.fail('must not fetch whole genome'))
    out=tmp_path/'held.sqlite'
    assert fetch.main(['--db',str(db),'--out-db',str(out),'--no-cache'])==1
    assert event(out)['results'][0]['status']=='GENOME_EXTRACTION_REQUIRED'


def test_genbank_declared_length_mismatch_is_a_hold():
    text=gb().replace('600 bp','601 bp')
    with pytest.warns(Warning):
        with pytest.raises(ValueError,match='LOCUS'):fetch.parse_gb(text)


def test_rich_genbank_parser_refuses_when_biopython_is_unavailable(monkeypatch):
    import builtins
    original = builtins.__import__
    def without_bio(name, *args, **kwargs):
        if name == "Bio" or name.startswith("Bio."):
            raise ImportError("dependency deliberately unavailable")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", without_bio)
    with pytest.raises(RuntimeError, match="requires the optional Biopython"):
        fetch.parse_gb("")
