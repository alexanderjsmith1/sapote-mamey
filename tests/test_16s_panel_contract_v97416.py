import importlib.util,sqlite3,sys
from pathlib import Path
from types import SimpleNamespace
import pytest


def test_explicit_type_strain_target_preserves_deposited_sp_and_named_target():
    module = panel._p16
    target, evidence = module.explicit_type_strain_target(
        "Nocardia sp. strain X; type strain of Nocardia exemplaris; 16S ribosomal RNA"
    )
    assert target == "Nocardia exemplaris"
    assert evidence == "type strain of Nocardia exemplaris"


@pytest.mark.parametrize("text", [
    "Nocardia sp. strain X, type material",
    "Nocardia sp. strain X, type strain",
    "Nocardia sp. strain X",
])
def test_type_material_without_named_target_is_not_promoted(text):
    module = panel._p16
    assert module.explicit_type_strain_target(text) == ("", "")
TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
import phylo_16s_panel as panel
import phylo_16s_build_db as builder

def fixture():
    con=sqlite3.connect(':memory:');con.executescript(builder.SCHEMA)
    for acc,role,designation in [('NR_100001','as_governed','QUERY_A'),('NR_100002','refseq_type','R_A'),('NR_100003','refseq_type','R_B'),('NR_100004','refseq_type','R_O')]:
        row=(acc,acc+'.2',role,'Example bacterium strain '+designation,'Example bacterium','Example',designation,'[]',1,'A'*1400,1400,'hash','fixture',0)
        builder.upsert(con,[row],role)
        con.execute('INSERT INTO record_strain VALUES (?,?)',(acc,'AS:'+designation if role=='as_governed' else 'REC:'+acc))
    return con

def args(**kw):
    return SimpleNamespace(**(dict(strains='QUERY_A',set=None,genus=None,scope_genus=None,habitat_tags=None,refs='type:0x',outgroup=None)|kw))

def test_zero_reference_cap_never_calls_blast(monkeypatch):
    monkeypatch.setattr(panel,'rank_references',lambda *a,**k:pytest.fail('zero cap must not rank'))
    records,counts=panel.prepare_panel(fixture(),args())
    assert len(records)==1 and counts==[dict(kind='type',requested=0,selected=0)]
    assert records[0]['accession']=='NR_100001.2'
    assert records[0]['label'].startswith('Example sp. QUERY_A ')

def test_same_species_distinct_reference_strains_are_retained(monkeypatch):
    monkeypatch.setattr(panel,'rank_references',lambda *a,**k:[('NR_100002','Example bacterium','A'*1400,'Example bacterium','refseq_type',99,1400),('NR_100003','Example bacterium','A'*1400,'Example bacterium','refseq_type',98,1400)])
    rows,counts=panel.prepare_panel(fixture(),args(refs='type:2x'))
    assert len(rows)==3 and counts[0]['selected']==2
    assert [r['accession'] for r in rows[1:]]==['NR_100002.2','NR_100003.2']

def test_wrong_outgroup_version_refuses():
    with pytest.raises(ValueError,match='record/version'):panel.prepare_panel(fixture(),args(outgroup='NR_100004.1'))

def test_missing_explicit_query_refuses():
    with pytest.raises(ValueError,match='incomplete'):panel.prepare_panel(fixture(),args(strains='QUERY_A,QUERY_B'))

def test_conflicting_query_hosts_refuse():
    con=fixture();con.executemany('INSERT INTO strain_meta VALUES (?,?,?,?)',[('AS:QUERY_A','host','plant','a'),('AS:QUERY_A','host','insect','b')])
    with pytest.raises(ValueError,match='conflicting host'):panel.prepare_panel(con,args())

def test_upsert_works_after_store_extension():
    con=fixture();con.execute('ALTER TABLE record ADD COLUMN host TEXT')
    row=('NR_100005','NR_100005.1','pdf_candidate','Example bacterium','Example bacterium','Example','R_C','[]',None,None,None,None,'fixture',0)
    builder.upsert(con,[row],'pdf_candidate')
    assert con.execute('SELECT source FROM record WHERE acc_base=?',('NR_100005',)).fetchone()==('pdf_candidate',)

@pytest.mark.parametrize('output', ['bad row', 'NR_100001\tUNKNOWN\t99\t600', 'NR_100001\tNR_100002\tnan\t600'])
def test_malformed_rank_output_refuses_and_releases_owned_temp(monkeypatch,tmp_path,output):
    stage=tmp_path/'ranking';stage.mkdir()
    monkeypatch.setattr(panel._p16,'space_free_workdir',lambda *a:str(stage))
    monkeypatch.setattr(panel._p16,'blast_bin',lambda x:x)
    monkeypatch.setattr(panel._p16,'run_checked',lambda *a,**kw:SimpleNamespace(stdout=output))
    with pytest.raises(ValueError):
        panel.rank_references(fixture(), [('NR_100001','','A'*600,'QUERY_A')], ('refseq_type',), {'NR_100001'}, None)
    assert not stage.exists()


def test_failed_rank_process_releases_owned_temp(monkeypatch,tmp_path):
    stage=tmp_path/'ranking';stage.mkdir()
    monkeypatch.setattr(panel._p16,'space_free_workdir',lambda *a:str(stage))
    monkeypatch.setattr(panel._p16,'blast_bin',lambda x:x)
    def fail(*a,**kw):raise SystemExit('failed command')
    monkeypatch.setattr(panel._p16,'run_checked',fail)
    with pytest.raises(SystemExit):
        panel.rank_references(fixture(), [('NR_100001','','A'*600,'QUERY_A')], ('refseq_type',), {'NR_100001'}, None)
    assert not stage.exists()


def test_panel_exports_explicit_display_roles_and_recorded_taxon(monkeypatch):
    monkeypatch.setattr(panel,'rank_references',lambda *a,**k:[('NR_100002','Example bacterium','A'*1400,'Example bacterium','refseq_type',99,1400)])
    rows,_=panel.prepare_panel(fixture(),args(refs='type:1x',outgroup='NR_100004.2'))
    assert [row['role'] for row in rows]==['query','reference','outgroup']
    assert all(row['taxon']=='Example bacterium' for row in rows)
    assert all(row['taxon_source']=='record.binomial' for row in rows)


def test_designation_collision_prefers_governed_source_before_length(caplog):
    con = fixture()
    row = ('NR_199999', 'NR_199999.1', 'refseq_type',
           'Other archaeon strain QUERY_A', 'Other archaeon', 'Other',
           'QUERY_A', '[]', 1, 'C' * 1600, 1600, 'other', 'fixture', 0)
    builder.upsert(con, [row], 'refseq_type')
    chosen = panel._select_query_records(
        con,
        [('NR_100001', '', 'A' * 1400, 'QUERY_A'),
         ('NR_199999', '', 'C' * 1600, 'QUERY_A')],
    )
    assert chosen['QUERY_A'][0] == 'NR_100001'
    assert 'DESIGNATION_ORIGIN_COLLISION' in caplog.text


def test_local_record_key_is_retained_without_fabricating_accession():
    assert panel._versioned({'acc_base': 'AS_LOCAL_QUERY-1', 'acc_version': None}) == ''
