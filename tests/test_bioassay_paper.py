import json
from pathlib import Path
import pytest
from mamey.bioassay_paper import prepare, write, numeric, activity, cli, sha

@pytest.fixture
def assay(tmp_path):
    roster=tmp_path/'roster.tsv';aliases=tmp_path/'aliases.json';table=tmp_path/'assay.tsv'
    write(roster,[dict(strain='AS-1',genus='Streptomyces',group='Bryophytes'),dict(strain='AS-2',genus='Nocardia',group='Bryophytes'),dict(strain='AS-3',genus='Unassigned',group='Bryophytes')])
    aliases.write_text(json.dumps({'AS-4':'AS-1'}))
    data=[('AS-1','Candida albicans','Crude extract','20'),('AS-1','Candida auris','Crude extract','50'),('AS-1','Candida (species not named)','Crude extract','90'),('AS-1','MRSA','Crude extract','0'),('AS-1','Foulbrood 19118-1','Crude extract','30'),('AS-1','Foulbrood 818','Crude extract','80'),('AS-2','MRSA','Crude extract','79.99'),('AS-2','Candida albicans','Crude extract',''),('AS-3','Candida albicans','Crude extract','n.t.'),('AS-3','MRSA','Crude extract','−'),('AS-4','Candida albicans','Fraction','108.81'),('AS-4','MRSA','Fraction','96.41')]
    rows=[dict(zip(('strain','organism','material','best_pct'),r)) for r in data]
    write(table,rows)
    return table,roster,aliases,rows

def test_pool_three_candida_and_two_larvae(assay):
    table,roster,aliases,_=assay
    p=prepare(table,roster,aliases,'A03','moss')
    x={r['target']:r['best_pct'] for r in p['pooled'] if r['strain']=='AS-1'}
    assert x=={'Candida sp.':90,'MRSA':0,'P. larvae':80}
    assert len(p['plot'])==1 and p['plot'][0]['y']==0

def test_missingness_and_four_states_are_not_zero(assay):
    table,roster,aliases,rows=assay
    rows.extend([dict(strain='AS-3',organism='Candida auris',material='Crude extract',best_pct='+')])
    write(table,rows)
    p=prepare(table,roster,aliases,'A01','bee')   # a pooling profile: this test is about the four states
    lookup={(r['strain'],r['target']):r for r in p['pooled']}
    assert lookup['AS-2','Candida sp.']['state']==''
    assert lookup['AS-3','MRSA']['state']=='−'
    assert lookup['AS-3','Candida sp.']['state']=='mixed_qualitative'
    assert set(json.loads(lookup['AS-3','Candida sp.']['source_states']))=={'n.t.','+'}
    assert all(r['strain']=='AS-1' or r['target']=='MRSA' for r in p['plot'])
    assert numeric('0')==0
    assert all(numeric(x) is None for x in ('','n.t.','+','−','-'))

def test_alias_keeps_fraction_and_does_not_double_count(assay):
    table,roster,aliases,_=assay
    p=prepare(table,roster,aliases,'A04','moss','Fraction')
    assert len(p['plot'])==1
    assert p['plot'][0]['strain']=='AS-1' and p['plot'][0]['x']==108.81
    assert p['used'][0]['source_strains']=='AS-4'

def test_a02_separate_species_and_materials(assay):
    table,roster,aliases,_=assay
    p=prepare(table,roster,aliases,'A02','moss')
    x={(r['material'],r['target']):r for r in p['plot']}
    assert x['Crude extract','Candida albicans']['label']=='0/1'
    assert x['Fraction','Candida albicans']['label']=='1/1'
    assert x['Crude extract','E. coli']['label']=='n.t.'
    assert x['Crude extract','E. coli']['pct']==''

def test_a06_denominators_are_target_specific(assay):
    table,roster,aliases,_=assay
    p=prepare(table,roster,aliases,'A06','moss')
    x={(r['group'],r['target']):r for r in p['plot']}
    assert x['Streptomyces','Candida sp.']['label']=='1/1'
    assert x['Other genera','MRSA']['label']=='0/1'
    # AS-3 (Unassigned) MRSA crude is a recorded qualitative '−': a tested negative, shown as itself, never 'n.t.'.
    assert x['No 16S sequence','MRSA']['label']=='−'
    assert x['No 16S sequence','MRSA']['n_qual_negative']==1 and x['No 16S sequence','MRSA']['n_untested']==0

def test_duplicate_input_refused(assay):
    table,roster,aliases,rows=assay;write(table,rows+[rows[0]])
    with pytest.raises(ValueError,match='Duplicate'):prepare(table,roster,aliases,'A01','moss')

def test_duplicate_roster_refused(assay):
    table,roster,aliases,_=assay
    r=dict(strain='AS-1',genus='Streptomyces',group='Bryophytes');write(roster,[r,r])
    with pytest.raises(ValueError,match='Duplicate'):prepare(table,roster,aliases,'A01','moss')

@pytest.mark.parametrize('bad',['nan','inf','-inf','unparsed'])
def test_nonfinite_or_invalid_refused(bad):
    with pytest.raises(ValueError):numeric(bad)

@pytest.mark.parametrize('value,expected',[(0,'Inactive (<25%)'),(24.99,'Inactive (<25%)'),(25,'Weak (25–49%)'),(50,'Moderate (50–79%)'),(79.99,'Moderate (50–79%)'),(80,'Strong (≥80%)'),(108.81,'Strong (≥80%)')])
def test_threshold_boundaries(value,expected):assert activity(value)==expected

def test_bound_hash_refusal_creates_no_output(assay,tmp_path):
    table,roster,aliases,_=assay;lock=tmp_path/'lock';lock.write_text('ratified')
    out=tmp_path/'out'
    with pytest.raises(ValueError,match='hash mismatch'):
        cli('A01',Path(__file__),['--table',str(table),'--roster',str(roster),'--aliases',str(aliases),'--lock',str(lock),'--out',str(out),'--table-sha256','wrong','--lock-sha256',sha(lock),'--layout','moss','--prepare-only'])
    assert not out.exists()

def test_input_immutability(assay):
    table,roster,aliases,_=assay;before=[sha(p) for p in (table,roster,aliases)]
    for kind in ['A01','A02','A03','A04','A06']:prepare(table,roster,aliases,kind,'moss')
    assert before==[sha(p) for p in (table,roster,aliases)]
