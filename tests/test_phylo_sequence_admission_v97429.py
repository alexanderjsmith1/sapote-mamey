import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from phylo_sequence_admission import validate, read_fasta
from gtotree_execution_gate import validate as validate_gtt, digest

def row(tip,seq,**kw):
    d=dict(tip=tip,role='reference',organism='Saccharopolyspora erythraea',expected_genus='Saccharopolyspora',accession='NR_000001.1',sequence_sha256=hashlib.sha256(seq.encode()).hexdigest(),type_status='type',isolation_source='soil',geography='Asia',sequence_evidence='record.json#sequence',metadata_evidence='record.json#source',biological_sample_id='not_applicable',admission='admitted');d.update(kw);return d

def test_complete_16s_roster_passes_and_fragment_fails():
    s='A'*1400
    assert validate([row('R1',s)],{'R1':s})['status']=='ADMISSION_PASS'
    with pytest.raises(ValueError,match='SEQUENCE_LENGTH'):validate([row('R1','A'*173)],{'R1':'A'*173})

def test_genus_metadata_and_geography_fail_closed():
    s='A'*1400
    with pytest.raises(ValueError,match='GENUS_CONTRADICTION'):validate([row('R1',s,expected_genus='Nocardia')],{'R1':s})
    with pytest.raises(ValueError,match='METADATA_INCOMPLETE'):validate([row('R1',s,isolation_source='unknown')],{'R1':s})
    with pytest.raises(ValueError,match='GEOGRAPHY_VOCABULARY'):validate([row('R1',s,geography='Yunnan Province')],{'R1':s})

def test_duplicate_type_representatives_fail():
    a,b='A'*1400,'C'*1400
    with pytest.raises(ValueError,match='DUPLICATE_TYPE_REPRESENTATIVE'):
        validate([row('R1',a),row('R2',b,accession='NR_2.1')],{'R1':a,'R2':b})

def test_same_sample_identical_queries_fail():
    s='A'*1400
    rows=[row('Q1',s,role='query',type_status='not_applicable',organism='Streptomyces sp.',expected_genus='Streptomyces',biological_sample_id='EXP55-S2'),row('Q2',s,role='query',type_status='not_applicable',organism='Streptomyces sp.',expected_genus='Streptomyces',biological_sample_id='EXP55-S2',accession='PX2')]
    with pytest.raises(ValueError,match='DUPLICATE_QUERY_SAME_SAMPLE_SEQUENCE'):validate(rows,{'Q1':s,'Q2':s})

def test_gtotree_packet_binds_version_resources_dirs_and_panel(tmp_path):
    root=tmp_path/'runroot';root.mkdir();work=root/'jobs'/'p1';out=root/'outputs'/'p1';work.mkdir(parents=True);out.mkdir(parents=True)
    g=tmp_path/'GToTree';g.write_text('tool');h=tmp_path/'Actinobacteria.hmm';h.write_text('hmm');f=tmp_path/'g.fna';f.write_text('>x\nACGT\n')
    p={'run_id':'x','gtotree':{'path':str(g),'sha256':digest(g),'version':'GToTree v1.8.19'},'hmm':{'path':str(h),'sha256':digest(h)},'panel':[{'tip':'x','genome_path':str(f),'sha256':digest(f)}],'working_directory':str(work),'output_directory':str(out),'max_concurrent_jobs':4}
    assert validate_gtt(p,root)['panel_size']==1
    p['gtotree']['version']='1.8.16'
    with pytest.raises(ValueError,match='GTOTREE_VERSION'):validate_gtt(p,root)

def test_gtotree_postflight_rejects_silent_tip_loss(tmp_path):
    root=tmp_path/'r';root.mkdir();w=root/'w';o=root/'o';w.mkdir();o.mkdir();g=tmp_path/'g';h=tmp_path/'h';f=tmp_path/'f';aln=tmp_path/'a';
    for p in (g,h,f,aln):p.write_text('x')
    packet={'run_id':'x','gtotree':{'path':str(g),'sha256':digest(g),'version':'1.8.19'},'hmm':{'path':str(h),'sha256':digest(h)},'panel':[{'tip':'A','genome_path':str(f),'sha256':digest(f)}],'working_directory':str(w),'output_directory':str(o),'max_concurrent_jobs':1,'postflight':{'retained_tips':[],'alignment_path':str(aln)}}
    with pytest.raises(ValueError,match='SILENT_TIP_LOSS'):validate_gtt(packet,root,True)
